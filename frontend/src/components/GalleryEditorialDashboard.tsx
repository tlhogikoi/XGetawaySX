import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, ClipboardCheck, Download, FileImage, FileText, RefreshCw, ShieldCheck, XCircle } from "lucide-react";
import "./gallery-editorial-dashboard.css";

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
  ai_assisted: boolean; ai_source_facts: string[]; revision_count: number;
  quality_review_version: number | null;
};
type Queue = { rights_reviews: RightsReview[]; media_reviews: MediaReview[]; story_reviews: StoryReview[] };
type Tab = "stories" | "rights" | "media";
const API_BASE = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";

const emptyQueue: Queue = { rights_reviews: [], media_reviews: [], story_reviews: [] };

export default function GalleryEditorialDashboard() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [queue, setQueue] = useState<Queue>(emptyQueue);
  const [tab, setTab] = useState<Tab>("stories");
  const [busy, setBusy] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [checks, setChecks] = useState<Record<number, Record<string, boolean>>>({});
  const [preview, setPreview] = useState<{ title: string; url: string } | null>(null);

  const totals = useMemo(() => ({
    stories: queue.story_reviews.length,
    rights: queue.rights_reviews.length,
    media: queue.media_reviews.length,
  }), [queue]);

  useEffect(() => () => { if (preview?.url) URL.revokeObjectURL(preview.url); }, [preview]);

  async function request(path: string, method = "GET", body?: unknown) {
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: {
        Authorization: `Basic ${btoa(`${email.trim()}:${password}`)}`,
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || data.non_field_errors?.[0] || "The editorial request could not be completed.");
    return data;
  }

  async function loadQueue() {
    setBusy(true); setError(""); setNotice("");
    try {
      const data = await request("/api/v1/gallery/editorial/queue/");
      setQueue({
        rights_reviews: Array.isArray(data.rights_reviews) ? data.rights_reviews : [],
        media_reviews: Array.isArray(data.media_reviews) ? data.media_reviews : [],
        story_reviews: Array.isArray(data.story_reviews) ? data.story_reviews : [],
      });
      setAuthenticated(true);
      setNotice("Editorial queue refreshed.");
    } catch (err) {
      setAuthenticated(false);
      setError(err instanceof Error ? err.message : "Unable to load the editorial queue.");
    } finally { setBusy(false); }
  }

  async function act(path: string, body: unknown, success: string) {
    setBusy(true); setError(""); setNotice("");
    try {
      await request(path, "POST", body);
      setNotice(success);
      await loadQueue();
    } catch (err) { setError(err instanceof Error ? err.message : "The action could not be completed."); }
    finally { setBusy(false); }
  }

  async function openPrivateFile(path: string, title: string, download = false) {
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_BASE}${path}`, {
        headers: { Authorization: `Basic ${btoa(`${email.trim()}:${password}`)}` },
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Private file could not be opened.");
      }
      const url = URL.createObjectURL(await response.blob());
      if (download) {
        const anchor = document.createElement("a");
        anchor.href = url; anchor.download = title.replace(/[^a-z0-9-_]+/gi, "-") || "gallery-evidence";
        anchor.click(); URL.revokeObjectURL(url);
      } else {
        setPreview(current => { if (current?.url) URL.revokeObjectURL(current.url); return { title, url }; });
      }
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to open private file."); }
    finally { setBusy(false); }
  }

  function setCheck(storyId: number, key: string, value: boolean) {
    setChecks(current => ({ ...current, [storyId]: { ...current[storyId], [key]: value } }));
  }

  const qualityFields = [
    ["claims_verified", "Story claims verified"],
    ["source_facts_checked", "Source facts checked"],
    ["unsupported_claims_resolved", "Unsupported claims resolved"],
    ["media_context_accurate", "Image and story context accurate"],
  ] as const;

  return <main className="ged-shell">
    <header className="ged-header">
      <div><p className="ged-eyebrow">XGETAWAYSX · INTERNAL WORKSPACE</p><h1>Gallery Editorial Desk</h1><p>Review partner rights, image submissions and story quality before anything is published.</p></div>
      <div className="ged-header-mark"><ShieldCheck size={25}/><span>Publication controls active</span></div>
    </header>

    {!authenticated && <section className="ged-login">
      <h2>Editorial staff sign-in</h2><p>Use an authorised staff account. Partner accounts cannot access this queue.</p>
      <label htmlFor="ged-email">Staff email</label><input id="ged-email" type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} placeholder="editor@xgetawaysx.co.za"/>
      <label htmlFor="ged-password">Password</label><input id="ged-password" type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Staff account password"/>
      <button disabled={!email.trim() || !password || busy} onClick={loadQueue}>{busy ? "Connecting…" : "Open editorial queue"}</button>
      <small>Credentials remain in page memory only. Use HTTPS outside local development.</small>
    </section>}

    {error && <p className="ged-message is-error" role="alert">{error}</p>}
    {notice && <p className="ged-message" role="status">{notice}</p>}

    {authenticated && <>
      <div className="ged-toolbar"><span>Live review queue</span><button className="ged-refresh" disabled={busy} onClick={loadQueue}><RefreshCw size={15}/> Refresh queue</button></div>
      <section className="ged-stats" aria-label="Pending review totals">
        <article><span>Story reviews</span><strong>{totals.stories}</strong></article>
        <article><span>Rights evidence</span><strong>{totals.rights}</strong></article>
        <article><span>Media approvals</span><strong>{totals.media}</strong></article>
      </section>
      <nav className="ged-tabs" aria-label="Editorial review categories">
        <button className={tab === "stories" ? "is-active" : ""} onClick={() => setTab("stories")}>Stories ({totals.stories})</button>
        <button className={tab === "rights" ? "is-active" : ""} onClick={() => setTab("rights")}>Rights ({totals.rights})</button>
        <button className={tab === "media" ? "is-active" : ""} onClick={() => setTab("media")}>Images ({totals.media})</button>
      </nav>

      {tab === "stories" && <section className="ged-list">
        {queue.story_reviews.length === 0 && <div className="ged-empty"><ClipboardCheck size={25}/><strong>No stories awaiting editorial review</strong><span>New owner-approved submissions will appear here.</span></div>}
        {queue.story_reviews.map(story => {
          const currentChecks = checks[story.id] || {};
          const qualityComplete = qualityFields.every(([key]) => currentChecks[key] === true);
          const hasCurrentQuality = story.quality_review_version === story.current_version;
          return <article className="ged-card" key={story.id}>
            <div className="ged-card-heading"><div><span className="ged-kicker">STORY #{story.id} · VERSION {story.current_version}</span><h2>{story.media_title}</h2><p>{story.partner_name}</p></div><span className="ged-status">{hasCurrentQuality ? "Quality checked" : "Needs quality review"}</span></div>
            <p className="ged-summary">{story.summary}</p>
            <div className="ged-meta"><span>Owner approval: {story.owner_approved_version === story.current_version ? "Current version" : "Not current"}</span><span>Cover media: {story.media_status}</span><span>Partner: {story.partner_gallery_status}</span><span>{story.revision_count} revision(s)</span></div>
            {story.ai_assisted && <div className="ged-facts"><strong>AI-assisted draft · verify against partner source facts</strong>{story.ai_source_facts.length ? <ul>{story.ai_source_facts.map((fact, i) => <li key={i}>{fact}</li>)}</ul> : <p>No source facts were supplied. Do not approve unsupported claims.</p>}</div>}
            <div className="ged-quality"><strong>Editorial quality checklist</strong>{qualityFields.map(([key, label]) => <label key={key}><input type="checkbox" checked={!!currentChecks[key]} onChange={e => setCheck(story.id, key, e.target.checked)}/>{label}</label>)}
              <label className="ged-field-label" htmlFor={`ged-notes-${story.id}`}>Review notes (minimum 10 characters)</label>
              <textarea id={`ged-notes-${story.id}`} value={notes[`story-${story.id}`] || ""} onChange={e => setNotes(current => ({ ...current, [`story-${story.id}`]: e.target.value }))} placeholder="Record the verification performed and any editorial context."/>
              <div className="ged-actions">
                <button disabled={busy || !qualityComplete || (notes[`story-${story.id}`] || "").trim().length < 10 || hasCurrentQuality} onClick={() => act(`/api/v1/gallery/stories/${story.id}/quality-review/`, { story_version: story.current_version, ...Object.fromEntries(qualityFields.map(([key]) => [key, true])), reviewer_notes: notes[`story-${story.id}`] }, "Quality review recorded for the current story version.")}><CheckCircle2 size={15}/> Record quality review</button>
                <button className="is-approve" disabled={busy || !hasCurrentQuality} onClick={() => act(`/api/v1/gallery/stories/${story.id}/editorial-approve/`, {}, "Story published after all server-side checks passed.")}><ShieldCheck size={15}/> Approve & publish</button>
              </div>
            </div>
            <div className="ged-return"><label htmlFor={`ged-return-${story.id}`}>Request partner changes</label><textarea id={`ged-return-${story.id}`} value={notes[`return-${story.id}`] || ""} onChange={e => setNotes(current => ({ ...current, [`return-${story.id}`]: e.target.value }))} placeholder="Explain the required correction (minimum 10 characters)."/><button className="is-danger" disabled={busy || (notes[`return-${story.id}`] || "").trim().length < 10} onClick={() => act(`/api/v1/gallery/stories/${story.id}/request-changes/`, { reason: notes[`return-${story.id}`] }, "Story returned to the partner with documented feedback.")}><XCircle size={15}/> Request changes</button></div>
          </article>;
        })}
      </section>}

      {tab === "rights" && <section className="ged-list">
        {queue.rights_reviews.length === 0 && <div className="ged-empty"><FileText size={25}/><strong>No rights evidence awaiting review</strong><span>Pending evidence submissions will appear here.</span></div>}
        {queue.rights_reviews.map(item => <article className="ged-card" key={item.id}>
          <div className="ged-card-heading"><div><span className="ged-kicker">RIGHTS SUBMISSION #{item.id} · MEDIA #{item.media_id}</span><h2>{item.media_title}</h2><p>{item.partner_name}</p></div><span className="ged-status">Pending evidence</span></div>
          <div className="ged-meta"><span>Rights holder: {item.rights_holder}</span><span>Channels: {item.permitted_channels.join(", ") || "Not specified"}</span><span>Granted: {new Date(item.granted_at).toLocaleDateString()}</span><span>Expires: {item.expires_at ? new Date(item.expires_at).toLocaleDateString() : "No expiry supplied"}</span></div>
          <div className="ged-actions"><button className="is-secondary" disabled={busy} onClick={() => openPrivateFile(item.evidence_url, `rights-evidence-${item.id}`, true)}><Download size={15}/> Download private evidence</button>
            <button className="is-approve" disabled={busy} onClick={() => act(`/api/v1/gallery/media/${item.media_id}/permissions/${item.id}/review/`, { decision: "approve", review_notes: notes[`rights-${item.id}`] || "" }, "Rights evidence approved. Website publication still requires website permission.")}><CheckCircle2 size={15}/> Approve rights</button>
            <button className="is-danger" disabled={busy} onClick={() => act(`/api/v1/gallery/media/${item.media_id}/permissions/${item.id}/review/`, { decision: "reject", review_notes: notes[`rights-${item.id}`] || "Evidence does not establish permission for the requested channels." }, "Rights evidence rejected.")}><XCircle size={15}/> Reject rights</button>
          </div>
          <label className="ged-field-label" htmlFor={`ged-rights-${item.id}`}>Rights review notes</label><textarea id={`ged-rights-${item.id}`} value={notes[`rights-${item.id}`] || ""} onChange={e => setNotes(current => ({ ...current, [`rights-${item.id}`]: e.target.value }))} placeholder="Record the evidence review outcome."/>
        </article>)}
      </section>}

      {tab === "media" && <section className="ged-list">
        {queue.media_reviews.length === 0 && <div className="ged-empty"><FileImage size={25}/><strong>No images awaiting media approval</strong><span>Eligible partner images will appear here after rights review.</span></div>}
        {queue.media_reviews.map(item => <article className="ged-card ged-media-card" key={item.id}>
          <div className="ged-card-heading"><div><span className="ged-kicker">IMAGE #{item.id}</span><h2>{item.title}</h2><p>{item.partner_name}</p></div><span className="ged-status">{item.status}</span></div>
          <p>{item.alt_text}</p>
          <div className="ged-actions"><button className="is-secondary" disabled={busy} onClick={() => openPrivateFile(`/api/v1/gallery/media/${item.id}/private-preview/`, item.title)}><FileImage size={15}/> Preview private image</button><button className="is-approve" disabled={busy} onClick={() => act(`/api/v1/gallery/media/${item.id}/editorial-approve/`, {}, "Image approved for Gallery use, subject to story publication review.")}><CheckCircle2 size={15}/> Approve image</button></div>
        </article>)}
      </section>}
    </>}

    {preview && <div className="ged-preview-backdrop" role="dialog" aria-modal="true" aria-label="Private image preview" onClick={() => setPreview(null)}><div className="ged-preview" onClick={e => e.stopPropagation()}><div><strong>{preview.title}</strong><button onClick={() => setPreview(null)} aria-label="Close preview">×</button></div><img src={preview.url} alt="Private partner image preview"/></div></div>}
  </main>;
}
