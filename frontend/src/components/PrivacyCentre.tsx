import { useCallback, useEffect, useState } from "react";
import "./privacy-centre.css";

const API = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";
type RequestType = "access" | "correction" | "deletion" | "consent_withdrawal" | "marketing_optout";
type PrivacyRequest = {
  reference: string;
  request_type: RequestType;
  description: string;
  status: string;
  created_at: string;
  identity_verified: boolean;
};
const requestTypes: { value: RequestType; label: string }[] = [
  { value: "access", label: "Access my personal information" },
  { value: "correction", label: "Correct my personal information" },
  { value: "deletion", label: "Request deletion of personal information" },
  { value: "consent_withdrawal", label: "Withdraw consent where applicable" },
  { value: "marketing_optout", label: "Opt out of marketing communications" },
];
const statusLabels: Record<string, string> = {
  submitted: "Submitted", under_review: "Under review",
  awaiting_verification: "Awaiting identity verification",
  fulfilled: "Completed", declined: "Declined", withdrawn: "Withdrawn",
};

export default function PrivacyCentre() {
  const token = sessionStorage.getItem("xgs_access");
  const [requests, setRequests] = useState<PrivacyRequest[]>([]);
  const [requestType, setRequestType] = useState<RequestType>("access");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadRequests = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const response = await fetch(`${API}/api/v1/accounts/privacy-requests/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load privacy requests.");
      setRequests(data as PrivacyRequest[]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load privacy requests.");
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { loadRequests(); }, [loadRequests]);

  async function submitRequest(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch(`${API}/api/v1/accounts/privacy-requests/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ request_type: requestType, description }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(Object.values(data).flat().join(" ") || "Could not submit your request.");
      setDescription("");
      setNotice(`Request submitted. Reference: ${data.reference}`);
      await loadRequests();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not submit your request.");
    } finally { setBusy(false); }
  }

  async function withdraw(reference: string) {
    if (!token) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch(`${API}/api/v1/accounts/privacy-requests/${reference}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ status: "withdrawn" }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not withdraw this request.");
      setNotice("Your request has been withdrawn.");
      await loadRequests();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not withdraw this request.");
    } finally { setBusy(false); }
  }

  const signedIn = Boolean(token);
  return <main className="privacy-centre">
    <header><a href="/" className="privacy-brand">XGETAWAYS<span>X</span></a><nav><a href="/account/">My account</a><a href="/privacy/">Privacy information</a></nav></header>
    <section className="privacy-hero"><p className="eyebrow">YOUR INFORMATION · YOUR CHOICES</p><h1>Privacy Centre</h1><p>Submit and track privacy-related requests associated with your XGetawaySX account.</p><span className="privacy-stage">STAGING WORKFLOW · IDENTITY CHECKS REQUIRE STAFF REVIEW</span></section>
    <section className="privacy-main">
      <div className="privacy-account-state"><div><h2>{signedIn ? "Your account privacy requests" : "Sign in to continue"}</h2><p>{signedIn ? "Requests are linked to your authenticated account. Staff may need to verify your identity before actioning a request." : "Sign in to submit and view requests linked to your account."}</p></div><a href="/account/">{signedIn ? "Account" : "Sign in"} →</a></div>
      {error && <p className="privacy-feedback privacy-error" role="alert">{error}</p>}
      {notice && <p className="privacy-feedback" role="status">{notice}</p>}
      {signedIn && <>
        <h2>Submit a privacy request</h2>
        <p className="privacy-intro">Choose the request that best describes what you need. Do not include passwords, payment-card details, identity-document numbers or other unnecessary sensitive information.</p>
        <form className="privacy-request-form" onSubmit={submitRequest}>
          <label>Request type<select value={requestType} onChange={event=>setRequestType(event.target.value as RequestType)}>{requestTypes.map(item=><option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <label>What would you like us to know?<textarea value={description} onChange={event=>setDescription(event.target.value)} minLength={10} maxLength={4000} rows={4} required placeholder="Describe the information or action relevant to your request. Avoid including sensitive document details."/></label>
          <button type="submit" disabled={busy}>{busy ? "Submitting…" : "Submit privacy request"}</button>
        </form>
        <h2>Your request history</h2>
        {loading ? <p className="privacy-intro">Loading your requests…</p> : requests.length === 0 ? <p className="privacy-intro">You have not submitted any privacy requests yet.</p> : <div className="privacy-request-list">{requests.map(item=><article key={item.reference}><div className="privacy-request-heading"><strong>{requestTypes.find(type=>type.value===item.request_type)?.label ?? item.request_type}</strong><span>{statusLabels[item.status] ?? item.status}</span></div><p>{item.description}</p><small>Reference: {item.reference} · Submitted {new Date(item.created_at).toLocaleString()}</small><small>Identity verification: {item.identity_verified ? "Recorded as verified" : "Not yet recorded"}</small>{item.status === "submitted" && <button type="button" className="privacy-withdraw" disabled={busy} onClick={()=>withdraw(item.reference)}>Withdraw request</button>}</article>)}</div>}
      </>}
      <aside className="privacy-notice"><strong>Important safeguards</strong><p>Submitting a request does not automatically disclose, correct or erase information, change marketing subscriptions, or withdraw consent from third-party providers. Staff must review the request, verify identity where appropriate, assess legal obligations and record the outcome. A deletion request does not automatically delete your account or transaction records.</p><a href="/privacy/">Read the current privacy information →</a></aside>
      <p className="privacy-footnote">This workflow is a technical staging implementation, not legal advice or proof of POPIA compliance. Confirm the responsible legal entity, Information Officer, response timelines, secure identity-verification process, retention schedule and complaint channel before public launch.</p>
    </section>
    <footer><a href="/">XGETAWAYS<span>X</span></a><span>TRAVEL THROUGH US.</span></footer>
  </main>;
}
