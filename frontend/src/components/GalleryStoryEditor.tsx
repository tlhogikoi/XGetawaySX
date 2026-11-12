import { useMemo, useState } from "react";
import { CheckCircle2, FileText, LockKeyhole, Sparkles } from "lucide-react";
import "./gallery.css";

type StoryDraft = {
  id: number;
  media: number;
  owner_original_history: string;
  owner_history_private: boolean;
  original_history_public_permission: boolean;
  summary: string;
  ai_assisted: boolean;
  ai_source_facts: string[];
  status: string;
  current_version: number;
  editorial_feedback: string | null;
  media_status: string;
  partner_gallery_status: string;
};

const API_BASE = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";
const statusLabel: Record<string, string> = {
  draft: "Draft", owner_review: "Awaiting your approval",
  editorial_review: "With XGetawaySX editorial", published: "Published",
  rejected: "Changes requested", withdrawn: "Withdrawn",
};

export default function GalleryStoryEditor() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [drafts, setDrafts] = useState<StoryDraft[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [history, setHistory] = useState("");
  const [factsText, setFactsText] = useState("");
  const [summary, setSummary] = useState("");
  const [privateHistory, setPrivateHistory] = useState(true);
  const [publicPermission, setPublicPermission] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const selected = useMemo(() => drafts.find(item => item.id === selectedId) ?? null, [drafts, selectedId]);
  const wordCount = summary.trim() ? summary.trim().split(/\\s+/).length : 0;

  async function request(path: string, method = "GET", body?: unknown) {
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: {
        Authorization: `Basic ${btoa(`${email.trim()}:${password}`)}`,
        ...(body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      },
      body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || data.summary || data.owner_original_history || "The request could not be completed.");
    return data;
  }

  function loadDraft(item: StoryDraft) {
    setSelectedId(item.id);
    setHistory(item.owner_original_history || "");
    setFactsText((item.ai_source_facts || []).join("\\n"));
    setSummary(item.summary || "");
    setPrivateHistory(item.owner_history_private);
    setPublicPermission(item.original_history_public_permission);
    setNotice("");
    setError("");
  }

  async function loadDrafts() {
    setBusy(true); setError(""); setNotice("");
    try {
      const data = await request("/api/v1/gallery/stories/drafts/");
      setDrafts(data);
      if (data.length) loadDraft(data[0]);
      else { setSelectedId(null); setNotice("No Gallery story drafts are linked to this account yet."); }
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to load drafts."); }
    finally { setBusy(false); }
  }

  async function saveDraft() {
    if (!selected) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const data = await request(`/api/v1/gallery/stories/${selected.id}/draft/`, "PATCH", {
        owner_original_history: history,
        ai_source_facts: factsText.split("\\n").map(value => value.trim()).filter(Boolean),
        summary,
      });
      setDrafts(items => items.map(item => item.id === selected.id ? { ...item, ...data } : item));
      setPrivateHistory(true); setPublicPermission(false);
      setNotice("Draft saved. Any previous approvals have been reset for this version.");
      await loadDrafts();
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to save this draft."); }
    finally { setBusy(false); }
  }

  async function createAiDraft() {
    if (!selected) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const data = await request(`/api/v1/gallery/stories/${selected.id}/ai-draft/`, "POST", {});
      setSummary(data.summary);
      setNotice("AI draft created from your source facts. Please verify every detail and edit it before approval.");
      await loadDrafts();
    } catch (err) { setError(err instanceof Error ? err.message : "AI drafting is currently unavailable."); }
    finally { setBusy(false); }
  }

  async function setHistoryConsent(decision: "grant" | "revoke") {
    if (!selected) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await request(`/api/v1/gallery/stories/${selected.id}/history-consent/`, "POST", { decision });
      setPrivateHistory(decision === "revoke");
      setPublicPermission(decision === "grant");
      setNotice(decision === "grant" ? "Separate permission recorded for this story version. You can revoke it at any time." : "Original history remains private.");
      await loadDrafts();
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to update publication permission."); }
    finally { setBusy(false); }
  }

  async function approveStory() {
    if (!selected) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await request(`/api/v1/gallery/stories/${selected.id}/owner-approve/`, "POST", {});
      setNotice("Your approval has been recorded. XGetawaySX editorial review is still required before publication.");
      await loadDrafts();
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to approve this story."); }
    finally { setBusy(false); }
  }

  return <main className="gallery-editor-shell">
    <header className="gallery-editor-heading">
      <p className="eyebrow">XGETAWAYSX PARTNER WORKSPACE</p>
      <h1>Gallery Story Editor</h1>
      <p>Share the story behind your place or experience. Your original history and source notes stay private unless you separately authorise publication.</p>
    </header>
    <section className="gallery-editor-access">
      <label htmlFor="gallery-partner-email">Partner account email</label>
      <input id="gallery-partner-email" type="email" autoComplete="username" value={email} onChange={event => setEmail(event.target.value)} placeholder="you@yourbusiness.co.za" />
      <label htmlFor="gallery-partner-password">Password</label>
      <input id="gallery-partner-password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} placeholder="Your partner account password" />
      <button type="button" disabled={!email.trim() || !password || busy} onClick={loadDrafts}>{busy ? "Connecting…" : "Load my story drafts"}</button>
      <small>Credentials are held in page memory only. This uses the backend’s configured HTTP Basic authentication; use HTTPS outside local development.</small>
    </section>
    {error && <p className="gallery-editor-message is-error" role="alert">{error}</p>}
    {notice && <p className="gallery-editor-message" role="status">{notice}</p>}
    {drafts.length > 0 && <div className="gallery-editor-layout">
      <aside className="gallery-editor-list" aria-label="Your story drafts">
        <h2>Your stories</h2>
        {drafts.map(item => <button type="button" key={item.id} className={item.id === selectedId ? "is-selected" : ""} onClick={() => loadDraft(item)}>
          <span>Media #{item.media}</span><strong>{statusLabel[item.status] || item.status}</strong><small>Version {item.current_version}</small>
        </button>)}
      </aside>
      {selected && <section className="gallery-editor-form">
        <div className="gallery-editor-status"><span>{statusLabel[selected.status] || selected.status}</span><span>Media: {selected.media_status}</span><span>Partner: {selected.partner_gallery_status}</span></div>
        {selected.editorial_feedback && <div className="gallery-editor-feedback"><strong>Editorial feedback</strong><p>{selected.editorial_feedback}</p></div>}
        <label htmlFor="owner-history">Your original story / history <em>Private source material</em></label>
        <textarea id="owner-history" rows={6} value={history} onChange={event => setHistory(event.target.value)} placeholder="Tell us how the business, property or experience came to exist. Include only facts you can verify." />
        <p className="gallery-editor-help"><LockKeyhole size={14}/> This original account is private by default and is not shown in the public Gallery.</p>
        <label htmlFor="source-facts">Verified facts for the public summary</label>
        <textarea id="source-facts" rows={5} value={factsText} onChange={event => setFactsText(event.target.value)} placeholder={"One fact per line. For example:\nEstablished in 2018 by the current owners.\nLocated near the Magaliesberg range."} />
        <p className="gallery-editor-help">AI drafting, when configured, can use only these facts. It must not invent origins, dates, founders or achievements.</p>
        <div className="gallery-editor-label-row"><label htmlFor="public-summary">Public story summary</label><span>{wordCount}/60 words (30–60 required)</span></div>
        <textarea id="public-summary" rows={5} value={summary} onChange={event => setSummary(event.target.value)} placeholder="A concise 30–60-word story for visitors to discover." />
        <div className="gallery-editor-actions">
          <button type="button" className="is-secondary" disabled={busy || !selected} onClick={createAiDraft}><Sparkles size={16}/> Draft with AI</button>
          <button type="button" disabled={busy} onClick={saveDraft}><FileText size={16}/> Save changes</button>
        </div>
        <div className="gallery-editor-consent">
          <div><strong>Separate permission to publish your original history</strong><p>Optional. Your public summary can be published while the full original history remains private.</p></div>
          <span className={publicPermission && !privateHistory ? "consent-enabled" : ""}>{publicPermission && !privateHistory ? "Permission granted" : "Private"}</span>
          <div className="gallery-editor-actions">
            <button type="button" className="is-secondary" disabled={busy || !history.trim() || publicPermission} onClick={() => setHistoryConsent("grant")}>Allow original history to be public</button>
            <button type="button" className="is-secondary" disabled={busy || privateHistory} onClick={() => setHistoryConsent("revoke")}>Keep original history private</button>
          </div>
        </div>
        <div className="gallery-editor-approval">
          <div><strong>Owner approval</strong><p>Approve only when the summary is accurate. Editorial approval, media rights approval and partner approval are also required before publication.</p></div>
          <button type="button" disabled={busy || selected.status !== "owner_review" || wordCount < 30 || wordCount > 60 || selected.media_status !== "approved" || selected.partner_gallery_status !== "approved"} onClick={approveStory}><CheckCircle2 size={16}/> Approve this version</button>
        </div>
      </section>}
    </div>}
  </main>;
}
