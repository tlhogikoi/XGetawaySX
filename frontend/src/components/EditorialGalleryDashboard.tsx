import { useCallback, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, FileText, LoaderCircle, RefreshCw, ShieldCheck } from "lucide-react";
import "./editorial-gallery.css";

type RightsReview = {
  id: number; media_id: number; media_title: string; partner_name: string;
  rights_holder: string; permitted_channels: string[]; granted_at: string;
  expires_at: string | null; evidence_url: string;
};
type MediaReview = { id: number; title: string; partner_name: string; alt_text: string; status: string };
type StoryReview = {
  id: number; media_id: number; media_title: string; partner_name: string;
  summary: string; current_version: number; owner_approved_version: number | null;
  owner_approved_at: string | null; media_status: string; partner_gallery_status: string;
  ai_assisted: boolean; ai_source_facts: string[]; revision_count: number; quality_review_version: number | null;
};
type Queue = { rights_reviews: RightsReview[]; media_reviews: MediaReview[]; story_reviews: StoryReview[] };
type AuditEvent = { id: number; action: string; actor_email: string | null; partner_name: string | null; created_at: string; details: Record<string, unknown> };
type Props = { accessToken: string; apiBaseUrl?: string };

const DEFAULT_API_BASE = (import.meta as ImportMeta & { env: { VITE_API_BASE_URL?: string } }).env.VITE_API_BASE_URL ?? "";
async function api<T>(url: string, token: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url, { ...init, headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...init.headers } });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { const body = await response.json(); message = body.detail ?? message; } catch { /* retain status */ }
    throw new Error(message);
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}
function date(value: string | null) { return value ? new Date(value).toLocaleString() : "No expiry"; }

export default function EditorialGalleryDashboard({ accessToken, apiBaseUrl = DEFAULT_API_BASE }: Props) {
  const base = `${apiBaseUrl.replace(/\/$/, "")}/api/v1/gallery`;
  const [queue, setQueue] = useState<Queue>({ rights_reviews: [], media_reviews: [], story_reviews: [] });
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [qualityNotes, setQualityNotes] = useState<Record<number, string>>({});
  const [qualityChecks, setQualityChecks] = useState<Record<number, Record<string, boolean>>>({});
  const [comparisons, setComparisons] = useState<Record<number, Array<{version:number;summary:string;change_reason:string;created_at:string}>>>({});
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    if (!accessToken) return;
    const [nextQueue, events] = await Promise.all([
      api<Queue>(`${base}/editorial/queue/`, accessToken),
      api<AuditEvent[] | { results?: AuditEvent[] }>(`${base}/audit/?limit=12`, accessToken),
    ]);
    setQueue(nextQueue);
    setAudit(Array.isArray(events) ? events.slice(0, 12) : (events.results ?? []).slice(0, 12));
  }, [accessToken, base]);

  useEffect(() => { refresh().catch((err: Error) => setError(err.message)); }, [refresh]);

  async function act(key: string, url: string, payload: Record<string, unknown>) {
    setBusy(key); setError(""); setNotice("");
    try {
      await api(url, accessToken, { method: "POST", body: JSON.stringify(payload) });
      setNotice("Review action recorded. The queue has been refreshed.");
      await refresh();
    } catch (err) { setError(err instanceof Error ? err.message : "The review action failed."); }
    finally { setBusy(null); }
  }

  async function compareVersions(item: StoryReview) {
    if (comparisons[item.id]) { setExpanded(current => ({ ...current, [item.id]: !current[item.id] })); return; }
    setBusy(`compare-${item.id}`); setError("");
    try {
      const result = await api<Array<{version:number;summary:string;change_reason:string;created_at:string}>>(`${base}/stories/${item.id}/revisions/`, accessToken);
      setComparisons(current => ({ ...current, [item.id]: result }));
      setExpanded(current => ({ ...current, [item.id]: true }));
    } catch (err) { setError(err instanceof Error ? err.message : "Could not load story versions."); }
    finally { setBusy(null); }
  }

  function saveQualityReview(item: StoryReview) {
    const checks = qualityChecks[item.id] ?? {};
    act(`quality-${item.id}`, `${base}/stories/${item.id}/quality-review/`, { story_version: item.current_version, ...checks, reviewer_notes: qualityNotes[item.id] ?? "" });
  }

  async function downloadEvidence(item: RightsReview) {
    const key = `evidence-${item.id}`; setBusy(key); setError("");
    try {
      const response = await fetch(`${base}/media/${item.media_id}/permissions/${item.id}/evidence/`, { headers: { Authorization: `Bearer ${accessToken}` } });
      if (!response.ok) throw new Error(`Evidence download failed (${response.status}).`);
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a"); link.href = objectUrl; link.download = `gallery-rights-evidence-${item.id}`; link.click();
      URL.revokeObjectURL(objectUrl);
    } catch (err) { setError(err instanceof Error ? err.message : "Evidence download failed."); }
    finally { setBusy(null); }
  }

  if (!accessToken) return <section className="egd-shell"><div className="egd-alert"><ShieldCheck /> Editorial staff sign-in is required.</div></section>;

  return <main className="egd-shell">
    <header className="egd-header"><div><p className="egd-kicker">XGETAWAYSX · CONTENT GOVERNANCE</p><h1>Gallery editorial desk</h1><p>Verify rights, review approved media and publish owner-approved stories.</p></div><button className="egd-refresh" onClick={() => { setBusy("refresh"); refresh().catch((err: Error) => setError(err.message)).finally(() => setBusy(null)); }} disabled={busy !== null}><RefreshCw size={16} /> Refresh queue</button></header>
    {error && <div className="egd-alert egd-alert--error" role="alert"><AlertCircle size={18}/>{error}</div>}
    {notice && <div className="egd-alert egd-alert--success" role="status"><CheckCircle2 size={18}/>{notice}</div>}
    <div className="egd-counts"><div><strong>{queue.rights_reviews.length}</strong><span>Rights checks</span></div><div><strong>{queue.media_reviews.length}</strong><span>Media approvals</span></div><div><strong>{queue.story_reviews.length}</strong><span>Story reviews</span></div></div>

    <section className="egd-section"><div className="egd-section-title"><div><p className="egd-kicker">01 · RIGHTS & PERMISSIONS</p><h2>Evidence verification</h2></div><span>{queue.rights_reviews.length} pending</span></div>
      {queue.rights_reviews.length === 0 ? <p className="egd-empty">No pending rights evidence.</p> : <div className="egd-grid">{queue.rights_reviews.map(item => <article className="egd-card" key={item.id}>
        <div className="egd-card-top"><span className="egd-tag">Evidence pending</span><small>Grant #{item.id}</small></div><h3>{item.media_title}</h3><p className="egd-partner">{item.partner_name}</p>
        <dl><div><dt>Rights holder</dt><dd>{item.rights_holder}</dd></div><div><dt>Permitted channels</dt><dd>{item.permitted_channels.join(", ")}</dd></div><div><dt>Submitted</dt><dd>{date(item.granted_at)}</dd></div><div><dt>Expires</dt><dd>{date(item.expires_at)}</dd></div></dl>
        <button className="egd-evidence" onClick={() => downloadEvidence(item)} disabled={busy !== null}><FileText size={16}/>{busy === `evidence-${item.id}` ? "Downloading…" : "View private evidence"}</button>
        <label className="egd-note">Review notes<textarea value={notes[item.id] ?? ""} onChange={e => setNotes(current => ({ ...current, [item.id]: e.target.value }))} maxLength={4000} rows={2} placeholder="Record what was checked or why it was rejected." /></label>
        <div className="egd-actions"><button className="egd-reject" disabled={busy !== null} onClick={() => act(`rights-${item.id}`, `${base}/media/${item.media_id}/permissions/${item.id}/review/`, { decision: "reject", review_notes: notes[item.id] ?? "" })}>Reject evidence</button><button className="egd-approve" disabled={busy !== null} onClick={() => act(`rights-${item.id}`, `${base}/media/${item.media_id}/permissions/${item.id}/review/`, { decision: "approve", review_notes: notes[item.id] ?? "" })}>Approve rights</button></div>
      </article>)}</div>}
    </section>

    <section className="egd-section"><div className="egd-section-title"><div><p className="egd-kicker">02 · MEDIA CONTROL</p><h2>Media approval</h2></div><span>{queue.media_reviews.length} pending</span></div>
      {queue.media_reviews.length === 0 ? <p className="egd-empty">No media awaiting editorial approval.</p> : <div className="egd-grid">{queue.media_reviews.map(item => <article className="egd-card" key={item.id}><span className="egd-tag">Rights evidence approved</span><h3>{item.title}</h3><p className="egd-partner">{item.partner_name}</p><p className="egd-summary">{item.alt_text}</p><button className="egd-approve egd-full" disabled={busy !== null} onClick={() => act(`media-${item.id}`, `${base}/media/${item.id}/editorial-approve/`, {})}>{busy === `media-${item.id}` ? "Saving…" : "Approve media"}</button></article>)}</div>}
    </section>

    <section className="egd-section"><div className="egd-section-title"><div><p className="egd-kicker">03 · STORY GOVERNANCE</p><h2>Owner-approved stories</h2></div><span>{queue.story_reviews.length} pending</span></div>
      {queue.story_reviews.length === 0 ? <p className="egd-empty">No stories awaiting editorial review.</p> : <div className="egd-grid">{queue.story_reviews.map(item => <article className="egd-card" key={item.id}><div className="egd-card-top"><span className="egd-tag">Owner approved · v{item.owner_approved_version}</span><small>Story #{item.id}</small></div><h3>{item.media_title}</h3><p className="egd-partner">{item.partner_name}</p><blockquote className="egd-story">{item.summary}</blockquote><dl><div><dt>Current version</dt><dd>{item.current_version}</dd></div><div><dt>Revision records</dt><dd>{item.revision_count}</dd></div><div><dt>Media status</dt><dd>{item.media_status}</dd></div><div><dt>Partner status</dt><dd>{item.partner_gallery_status}</dd></div></dl>{item.ai_assisted && <div className="egd-ai-note">AI-assisted draft · verify every claim against the supplied source facts ({item.ai_source_facts.length} recorded).</div>}<p className="egd-privacy">Private original history and internal source notes are deliberately excluded from this review screen.</p>
      <button className="egd-evidence" onClick={() => compareVersions(item)} disabled={busy !== null}>{expanded[item.id] ? "Hide version comparison" : "Compare story versions"}</button>
      {expanded[item.id] && <div className="egd-comparison"><h4>Version history</h4>{(comparisons[item.id] ?? []).map(revision => <article key={revision.version}><strong>Version {revision.version}</strong><small>{date(revision.created_at)} · {revision.change_reason}</small><p>{revision.summary}</p></article>)}<article className="egd-current"><strong>Current version {item.current_version}</strong><p>{item.summary}</p></article></div>}
      <div className="egd-quality"><h4>Editorial quality control · version {item.current_version}</h4>
      {([["claims_verified","Factual claims verified"],["source_facts_checked","Checked against owner-supplied facts"],["unsupported_claims_resolved","Unsupported claims removed or clarified"],["media_context_accurate","Image and story context accurate"]] as const).map(([key,label]) => <label className="egd-check" key={key}><input type="checkbox" checked={Boolean(qualityChecks[item.id]?.[key])} onChange={event => setQualityChecks(current => ({ ...current, [item.id]: { ...current[item.id], [key]: event.target.checked } }))} />{label}</label>)}
      <label className="egd-note">Internal reviewer notes<textarea value={qualityNotes[item.id] ?? ""} onChange={event => setQualityNotes(current => ({ ...current, [item.id]: event.target.value }))} maxLength={2000} rows={2} placeholder="Record the source checks and editorial assessment." /></label>
      <button className="egd-approve egd-full" disabled={busy !== null || !["claims_verified","source_facts_checked","unsupported_claims_resolved","media_context_accurate"].every(key => qualityChecks[item.id]?.[key] === true) || (qualityNotes[item.id] ?? "").trim().length < 10} onClick={() => saveQualityReview(item)}>{busy === `quality-${item.id}` ? "Saving…" : "Save quality review"}</button>
      {item.quality_review_version === item.current_version && <p className="egd-quality-ok">A quality review is recorded for this version.</p>}</div><label className="egd-note">Request changes from partner<textarea value={notes[item.id] ?? ""} onChange={e => setNotes(current => ({ ...current, [item.id]: e.target.value }))} maxLength={1000} rows={3} placeholder="Explain the factual correction or clarification required (minimum 10 characters)." /></label>
      <div className="egd-story-actions"><button className="egd-reject" disabled={busy !== null || (notes[item.id] ?? "").trim().length < 10} onClick={() => act(`story-changes-${item.id}`, `${base}/stories/${item.id}/request-changes/`, { reason: notes[item.id].trim() })}>{busy === `story-changes-${item.id}` ? "Sending…" : "Return for changes"}</button>
      <button className="egd-approve" disabled={busy !== null || item.owner_approved_version !== item.current_version || item.quality_review_version !== item.current_version || item.media_status !== "approved" || item.partner_gallery_status !== "approved"} onClick={() => act(`story-${item.id}`, `${base}/stories/${item.id}/editorial-approve/`, {})}>{busy === `story-${item.id}` ? "Publishing…" : "Approve & publish current version"}</button></div></article>)}</div>}
    </section>

    <section className="egd-section"><div className="egd-section-title"><div><p className="egd-kicker">04 · ACCOUNTABILITY</p><h2>Recent audit activity</h2></div></div>
      {audit.length === 0 ? <p className="egd-empty">No audit events available.</p> : <div className="egd-audit">{audit.map(event => <div key={event.id}><span>{event.action.replaceAll("_", " ")}</span><strong>{event.partner_name ?? "Gallery"}</strong><small>{event.actor_email ?? "System"} · {date(event.created_at)}</small></div>)}</div>}
    </section>
  </main>;
}
