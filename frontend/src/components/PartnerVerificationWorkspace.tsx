import { useEffect, useState } from "react";
import { ArrowLeft, CheckCircle2, FileCheck2, FileUp, ShieldCheck, ClipboardList } from "lucide-react";
import "./partner-onboarding.css";

const API = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";
const DOCUMENTS = [
  ["business_registration", "Business registration"],
  ["proof_of_address", "Proof of business address"],
  ["owner_identity", "Owner identity document"],
  ["tax_certificate", "Tax certificate"],
  ["operating_licence", "Operating licence"],
] as const;

type Profile = { id: number; name: string; category: string; city: string; province: string };
type Evidence = { id: number; document_type: string; original_filename: string; uploaded_at: string; download_url?: string };
type Application = {
  id: number; partner_id: number; partner_name: string; legal_business_name: string;
  registration_number: string; is_sole_proprietor: boolean; tax_number: string;
  contact_person: string; contact_email: string; contact_phone: string; physical_address: string;
  document_checklist: string[]; status: string; submitted_at: string | null;
  review_notes: string; documents: Evidence[];
};
type QueueItem = {
  id: number; partner_id: number; partner_name: string; partner_owner_email: string;
  legal_business_name: string; registration_number: string; is_sole_proprietor: boolean;
  contact_person: string; contact_email: string; contact_phone: string;
  physical_address: string; document_checklist: string[]; submitted_at: string;
};

async function api<T>(token: string, path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...options.headers,
    },
  });
  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof data === "string" ? data : data.detail || data.file || data.missing_fields?.join(", ") || Object.values(data).flat().join(" ");
    throw new Error(message || "The request could not be completed.");
  }
  return data as T;
}

const emptyApplication = (partnerId: number, partnerName: string): Application => ({
  id: 0, partner_id: partnerId, partner_name: partnerName, legal_business_name: partnerName,
  registration_number: "", is_sole_proprietor: false, tax_number: "", contact_person: "",
  contact_email: "", contact_phone: "", physical_address: "", document_checklist: [],
  status: "draft", submitted_at: null, review_notes: "", documents: [],
});

export default function PartnerVerificationWorkspace({ accessToken, staffMode = false }: { accessToken: string; staffMode?: boolean }) {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [partnerId, setPartnerId] = useState("");
  const [application, setApplication] = useState<Application | null>(null);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [selected, setSelected] = useState<QueueItem | null>(null);
  const [staffDocuments, setStaffDocuments] = useState<Evidence[]>([]);
  const [reviewNotes, setReviewNotes] = useState("");
  const [files, setFiles] = useState<Record<string, File | null>>({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  function setField<K extends keyof Application>(key: K, value: Application[K]) {
    setApplication(current => current ? { ...current, [key]: value } : current);
  }

  useEffect(() => {
    if (staffMode) {
      api<QueueItem[]>(accessToken, "/api/v1/partners/partner/onboarding/queue/")
        .then(setQueue).catch(reason => setError(reason instanceof Error ? reason.message : "Could not load the review queue."));
      return;
    }
    api<Profile[]>(accessToken, "/api/v1/partners/partner/my-profiles/")
      .then(items => {
        setProfiles(items);
        if (items.length === 1) setPartnerId(String(items[0].id));
      })
      .catch(reason => setError(reason instanceof Error ? reason.message : "Could not load partner profiles."));
  }, [accessToken, staffMode]);

  useEffect(() => {
    if (staffMode || !partnerId) return;
    const profile = profiles.find(item => String(item.id) === partnerId);
    if (!profile) return;
    setBusy(true); setError(""); setNotice("");
    api<Application>(accessToken, `/api/v1/partners/partner/onboarding/?partner_id=${partnerId}`)
      .then(setApplication)
      .catch(async reason => {
        if (reason instanceof Error && reason.message.includes("No onboarding submission exists")) {
          try {
            const created = await api<Application>(accessToken, "/api/v1/partners/partner/onboarding/", {
              method: "POST", body: JSON.stringify({ partner_id: Number(partnerId) }),
            });
            setApplication(created);
          } catch (createError) {
            setError(createError instanceof Error ? createError.message : "Could not start onboarding.");
          }
        } else setError(reason instanceof Error ? reason.message : "Could not load the application.");
      })
      .finally(() => setBusy(false));
  }, [accessToken, partnerId, profiles, staffMode]);

  async function refreshApplication() {
    if (!partnerId) return;
    const data = await api<Application>(accessToken, `/api/v1/partners/partner/onboarding/?partner_id=${partnerId}`);
    setApplication(data);
  }

  async function saveDraft(submit = false) {
    if (!application) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const payload = {
        partner_id: application.partner_id,
        legal_business_name: application.legal_business_name,
        registration_number: application.registration_number,
        is_sole_proprietor: application.is_sole_proprietor,
        tax_number: application.tax_number,
        contact_person: application.contact_person,
        contact_email: application.contact_email,
        contact_phone: application.contact_phone,
        physical_address: application.physical_address,
        document_checklist: application.document_checklist,
        ...(submit ? { submit: true } : {}),
      };
      const saved = await api<Application>(accessToken, "/api/v1/partners/partner/onboarding/", {
        method: "POST", body: JSON.stringify(payload),
      });
      setApplication(saved);
      setNotice(submit ? "Your verification application has been submitted." : "Your draft has been saved.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save your application."); }
    finally { setBusy(false); }
  }

  async function uploadEvidence(documentType: string) {
    if (!application?.id || !files[documentType]) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const body = new FormData();
      body.append("document_type", documentType);
      body.append("file", files[documentType] as File);
      await api(accessToken, `/api/v1/partners/partner/onboarding/${application.id}/documents/`, { method: "POST", body });
      setFiles(current => ({ ...current, [documentType]: null }));
      await refreshApplication();
      setNotice("Evidence uploaded securely.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Evidence upload failed."); }
    finally { setBusy(false); }
  }

  async function loadStaffDocuments(item: QueueItem) {
    setSelected(item); setReviewNotes(""); setError(""); setNotice("");
    try {
      const documents = await api<Evidence[]>(accessToken, `/api/v1/partners/partner/onboarding/${item.id}/documents/`);
      setStaffDocuments(documents);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load evidence."); }
  }

  async function review(decision: "approved" | "changes_requested" | "rejected") {
    if (!selected) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await api(accessToken, `/api/v1/partners/partner/onboarding/${selected.id}/review/`, {
        method: "POST", body: JSON.stringify({ decision, review_notes: reviewNotes }),
      });
      setNotice(`Application marked ${decision.replaceAll("_", " ")}.`);
      setSelected(null);
      setQueue(current => current.filter(item => item.id !== selected.id));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Review action failed."); }
    finally { setBusy(false); }
  }

  async function downloadEvidence(item: Evidence) {
    try {
      const response = await fetch(`${API}${item.download_url || `/api/v1/partners/partner/onboarding/documents/${item.id}/`}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!response.ok) throw new Error("Evidence download was denied.");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url; link.download = item.original_filename; link.click();
      URL.revokeObjectURL(url);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not download evidence."); }
  }

  const editable = application && ["draft", "changes_requested"].includes(application.status);
  return (
    <section className="partner-verify-shell">
      <div className="partner-verify-heading">
        <div><p className="eyebrow">{staffMode ? "VERIFICATION OPERATIONS" : "PARTNER CENTRE"}</p><h2>{staffMode ? "Partner verification queue" : "Business verification"}</h2><p>{staffMode ? "Review submitted partner applications and their private evidence." : "Complete your business profile and submit the documents needed to verify your partner account."}</p></div>
        <span className="partner-verify-mark"><ShieldCheck size={24}/></span>
      </div>
      {notice && <p className="partner-verify-notice" role="status">{notice}</p>}
      {error && <p className="partner-verify-error" role="alert">{error}</p>}
      {staffMode ? (
        <div className="partner-verify-layout">
          <div className="partner-verify-list">
            <h3><ClipboardList size={17}/> Submitted applications <span>{queue.length}</span></h3>
            {queue.length === 0 && <p className="partner-verify-muted">No applications are waiting for review.</p>}
            {queue.map(item => <button className={selected?.id === item.id ? "partner-verify-queue-item active" : "partner-verify-queue-item"} key={item.id} onClick={() => loadStaffDocuments(item)}><strong>{item.legal_business_name}</strong><small>{item.partner_name} · {item.partner_owner_email}</small></button>)}
          </div>
          <div className="partner-verify-panel">
            {!selected ? <p className="partner-verify-muted">Select an application to inspect its details and evidence.</p> : <>
              <h3>{selected.legal_business_name}</h3><p className="partner-verify-muted">{selected.contact_person} · {selected.contact_email} · {selected.contact_phone}</p>
              <p>{selected.physical_address}</p><p>Registration: {selected.is_sole_proprietor ? "Sole proprietor" : selected.registration_number || "Not supplied"}</p>
              <h4>Private evidence documents</h4>
              {staffDocuments.map(doc => <div className="partner-verify-doc" key={doc.id}><FileCheck2 size={17}/><span>{doc.original_filename}</span><button type="button" onClick={() => downloadEvidence(doc)}>Download</button></div>)}
              <label className="partner-verify-field">Review notes<textarea value={reviewNotes} onChange={e => setReviewNotes(e.target.value)} placeholder="Required when requesting changes or rejecting…" rows={3}/></label>
              <div className="partner-verify-actions"><button disabled={busy} onClick={() => review("approved")}>Approve</button><button className="outline" disabled={busy || !reviewNotes.trim()} onClick={() => review("changes_requested")}>Request changes</button><button className="danger" disabled={busy || !reviewNotes.trim()} onClick={() => review("rejected")}>Reject</button></div>
            </>}
          </div>
        </div>
      ) : <>
        <div className="partner-verify-profile">
          <label>Select your partner profile<select value={partnerId} onChange={e => { setPartnerId(e.target.value); setApplication(null); }}><option value="">Choose a business…</option>{profiles.map(profile => <option key={profile.id} value={profile.id}>{profile.name} · {profile.city || profile.province}</option>)}</select></label>
          {profiles.length === 0 && <p className="partner-verify-muted">No partner profiles are linked to this account yet. Contact XGetawaySX partner support to create your profile.</p>}
        </div>
        {application && <>
          <div className="partner-verify-status"><span className={`status-${application.status}`}>{application.status.replaceAll("_", " ")}</span><small>{application.submitted_at ? `Submitted ${new Date(application.submitted_at).toLocaleDateString()}` : "Not submitted yet"}</small></div>
          {application.review_notes && <div className="partner-verify-feedback"><strong>Feedback from the verification team</strong><p>{application.review_notes}</p></div>}
          <div className="partner-verify-form">
            <label>Legal business name<input disabled={!editable} value={application.legal_business_name} onChange={e => setField("legal_business_name", e.target.value)}/></label>
            <label className="partner-verify-check"><input type="checkbox" disabled={!editable} checked={application.is_sole_proprietor} onChange={e => setField("is_sole_proprietor", e.target.checked)}/> I operate as a sole proprietor</label>
            {!application.is_sole_proprietor && <label>Company registration number<input disabled={!editable} value={application.registration_number} onChange={e => setField("registration_number", e.target.value)}/></label>}
            <label>Tax number (if applicable)<input disabled={!editable} value={application.tax_number} onChange={e => setField("tax_number", e.target.value)}/></label>
            <label>Contact person<input disabled={!editable} value={application.contact_person} onChange={e => setField("contact_person", e.target.value)}/></label>
            <label>Contact email<input type="email" disabled={!editable} value={application.contact_email} onChange={e => setField("contact_email", e.target.value)}/></label>
            <label>Contact phone<input disabled={!editable} value={application.contact_phone} onChange={e => setField("contact_phone", e.target.value)}/></label>
            <label className="wide">Physical business address<textarea disabled={!editable} rows={2} value={application.physical_address} onChange={e => setField("physical_address", e.target.value)}/></label>
          </div>
          <div className="partner-verify-evidence"><h3><FileUp size={18}/> Verification evidence</h3><p>Files are stored privately and can only be accessed by your business account and authorised verification staff. PDF, JPEG, PNG or WebP; maximum 15 MB per file.</p>
            {DOCUMENTS.map(([key, label]) => {
              const existing = application.documents.find(doc => doc.document_type === key);
              return <div className="partner-verify-upload" key={key}><div><strong>{label}</strong><small>{existing ? `Uploaded: ${existing.original_filename}` : "No document uploaded yet"}</small></div>{editable && <div className="partner-verify-file"><input aria-label={`Choose ${label}`} type="file" accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/jpeg,image/png,image/webp" onChange={e => setFiles(current => ({ ...current, [key]: e.target.files?.[0] || null }))}/><button disabled={busy || !files[key]} onClick={() => uploadEvidence(key)}>Upload</button></div>}<span className={existing ? "doc-present" : "doc-missing"}>{existing ? "Received" : "Pending"}</span></div>;
            })}
          </div>
          {editable && <div className="partner-verify-actions"><button className="outline" disabled={busy} onClick={() => saveDraft(false)}>Save draft</button><button disabled={busy} onClick={() => saveDraft(true)}>Submit for verification <ArrowLeft size={16}/></button></div>}
          {!editable && <p className="partner-verify-locked"><CheckCircle2 size={17}/> This application is locked while it is under review or has been finalised.</p>}
        </>}
      </>}
    </section>
  );
}
