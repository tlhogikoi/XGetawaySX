import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, FileImage, FileText, LoaderCircle, RefreshCw, ShieldCheck, UploadCloud } from "lucide-react";
import "./partner-gallery.css";

type DraftStory = {
  id: number;
  media: number;
  summary: string;
  status: string;
  current_version: number;
  owner_approved_version: number | null;
  editorial_approved_version: number | null;
  owner_approved_at: string | null;
  editorial_approved_at: string | null;
  media_status: string;
  partner_gallery_status: string;
};

type ApiError = { detail?: string; [key: string]: unknown };

type Props = {
  accessToken: string;
  partnerId: number;
  partnerName: string;
  galleryApprovalStatus?: "pending" | "approved" | "suspended" | "rejected" | "unknown";
  apiBaseUrl?: string;
};

const DEFAULT_API_BASE = (import.meta as ImportMeta & { env: { VITE_API_BASE_URL?: string } }).env.VITE_API_BASE_URL ?? "";

async function request<T>(url: string, token: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init.headers,
    },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json() as ApiError;
      message = typeof payload.detail === "string" ? payload.detail : Object.entries(payload).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`).join(" · ");
    } catch {
      // Keep the HTTP status message when the response is not JSON.
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function extractList<T>(payload: T[] | { results?: T[] }): T[] {
  return Array.isArray(payload) ? payload : payload.results ?? [];
}

function wordCount(value: string) {
  return value.trim() ? value.trim().split(/\s+/).length : 0;
}

const statusLabel: Record<string, string> = {
  draft: "Draft",
  owner_review: "Awaiting owner approval",
  editorial_review: "Editorial review",
  published: "Published",
  rejected: "Changes requested",
  withdrawn: "Withdrawn",
};

export default function PartnerGalleryWorkspace({
  accessToken,
  partnerId,
  partnerName,
  galleryApprovalStatus = "unknown",
  apiBaseUrl = DEFAULT_API_BASE,
}: Props) {
  const api = `${apiBaseUrl.replace(/\/$/, "")}/api/v1/gallery`;
  const [title, setTitle] = useState("");
  const [altText, setAltText] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [rightsHolder, setRightsHolder] = useState("");
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [channels, setChannels] = useState<string[]>(["website"]);
  const [summary, setSummary] = useState("");
  const [ownerHistory, setOwnerHistory] = useState("");
  const [mediaId, setMediaId] = useState<number | null>(null);
  const [grantId, setGrantId] = useState<number | null>(null);
  const [storyId, setStoryId] = useState<number | null>(null);
  const [drafts, setDrafts] = useState<DraftStory[]>([]);
  const [busy, setBusy] = useState<"media" | "rights" | "story" | "approve" | "refresh" | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const count = useMemo(() => wordCount(summary), [summary]);
  const summaryValid = count >= 30 && count <= 60;

  const loadDrafts = useCallback(async () => {
    if (!accessToken) return;
    const payload = await request<DraftStory[] | { results?: DraftStory[] }>(`${api}/stories/drafts/`, accessToken);
    setDrafts(extractList(payload));
  }, [accessToken, api]);

  useEffect(() => {
    let active = true;
    if (!accessToken) return;
    request<DraftStory[] | { results?: DraftStory[] }>(`${api}/stories/drafts/`, accessToken)
      .then((payload) => { if (active) setDrafts(extractList(payload)); })
      .catch((err: Error) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [accessToken, api]);

  async function submitMedia() {
    if (!imageFile || !title.trim() || !altText.trim() || !rightsHolder.trim()) {
      setError("Complete the image title, alt text, rights holder and image file first.");
      return;
    }
    setBusy("media"); setError(""); setNotice("");
    try {
      const body = new FormData();
      body.append("partner", String(partnerId));
      body.append("title", title.trim());
      body.append("alt_text", altText.trim());
      body.append("rights_holder", rightsHolder.trim());
      body.append("image_file", imageFile);
      const result = await request<{ id: number; status: string }>(`${api}/media/create/`, accessToken, { method: "POST", body });
      setMediaId(result.id);
      setNotice("Image uploaded privately. Next, submit the rights evidence for editorial verification.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Image upload failed.");
    } finally { setBusy(null); }
  }

  async function submitRights() {
    if (!mediaId || !evidenceFile || !rightsHolder.trim() || channels.length === 0) {
      setError("Select the rights evidence file and at least one permitted promotional channel.");
      return;
    }
    setBusy("rights"); setError(""); setNotice("");
    try {
      const body = new FormData();
      body.append("rights_holder", rightsHolder.trim());
      body.append("evidence_file", evidenceFile);
      body.append("permitted_channels", JSON.stringify(channels));
      const result = await request<{ id: number; review_status: string }>(`${api}/media/${mediaId}/permissions/`, accessToken, { method: "POST", body });
      setGrantId(result.id);
      setNotice("Rights evidence submitted privately. Editorial verification is still required before publication.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rights evidence submission failed.");
    } finally { setBusy(null); }
  }

  async function createStory() {
    if (!mediaId || !grantId || !summaryValid) {
      setError("Upload the image, submit its rights evidence and enter a 30–60-word story summary before continuing.");
      return;
    }
    setBusy("story"); setError(""); setNotice("");
    try {
      const result = await request<DraftStory>(`${api}/stories/create/`, accessToken, {
        method: "POST",
        body: JSON.stringify({
          media: mediaId,
          summary: summary.trim(),
          owner_original_history: ownerHistory.trim(),
        }),
      });
      setStoryId(result.id);
      setNotice("Story draft created. Its original history remains private. Owner and editorial approval are separate publication steps.");
      await loadDrafts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Story draft creation failed.");
    } finally { setBusy(null); }
  }

  async function approveStory(id: number) {
    setBusy("approve"); setError(""); setNotice("");
    try {
      await request<{ status: string }>(`${api}/stories/${id}/owner-approve/`, accessToken, { method: "POST", body: "{}" });
      setNotice("Your approval has been recorded for this story version. Editorial approval is still required.");
      await loadDrafts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Owner approval failed.");
    } finally { setBusy(null); }
  }

  async function refresh() {
    setBusy("refresh"); setError("");
    try { await loadDrafts(); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not refresh stories."); }
    finally { setBusy(null); }
  }

  function toggleChannel(channel: string) {
    setChannels((current) => current.includes(channel) ? current.filter((item) => item !== channel) : [...current, channel]);
  }

  if (!accessToken) {
    return <section className="partner-gallery-workspace"><div className="pgw-notice"><ShieldCheck size={22} /><div><strong>Partner sign-in required</strong><p>Sign in through the XGetawaySX partner portal to manage this Gallery profile.</p></div></div></section>;
  }

  return (
    <section className="partner-gallery-workspace" aria-labelledby="pgw-title">
      <header className="pgw-header">
        <div><p className="pgw-eyebrow">PARTNER CONTENT STUDIO</p><h1 id="pgw-title">Your Gallery workspace</h1><p>Manage the images and stories representing <strong>{partnerName}</strong>.</p></div>
        <span className={`pgw-status pgw-status--${galleryApprovalStatus}`}>Gallery: {galleryApprovalStatus.replace("_", " ")}</span>
      </header>

      {galleryApprovalStatus !== "approved" && <div className="pgw-notice"><AlertCircle size={20} /><p>Your partner profile is not yet approved for Gallery publication. You can prepare content, but it will not appear publicly until the partner approval is granted.</p></div>}
      {error && <div className="pgw-feedback pgw-feedback--error" role="alert"><AlertCircle size={18} />{error}</div>}
      {notice && <div className="pgw-feedback pgw-feedback--success" role="status"><CheckCircle2 size={18} />{notice}</div>}

      <div className="pgw-layout">
        <div className="pgw-form-column">
          <article className="pgw-panel">
            <div className="pgw-panel-heading"><span className="pgw-step">01</span><div><h2>Add a Gallery image</h2><p>Upload an image you have authority to submit.</p></div></div>
            <label>Image title<input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={180} placeholder="e.g. The lodge overlooking the valley" /></label>
            <label>Image description for accessibility<input value={altText} onChange={(e) => setAltText(e.target.value)} maxLength={250} placeholder="Describe what a visitor can see" /></label>
            <label>Rights holder<input value={rightsHolder} onChange={(e) => setRightsHolder(e.target.value)} maxLength={180} placeholder="Person or organisation holding image rights" /></label>
            <label className="pgw-file-input"><FileImage size={19} /><span><strong>{imageFile?.name ?? "Choose image"}</strong><small>JPEG, PNG or WebP · maximum 10 MB</small></span><input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setImageFile(e.target.files?.[0] ?? null)} /></label>
            <button className="pgw-button" type="button" onClick={submitMedia} disabled={busy !== null || mediaId !== null}>{busy === "media" ? <LoaderCircle className="pgw-spin" size={17} /> : <UploadCloud size={17} />}{mediaId ? "Image uploaded privately" : "Upload image privately"}</button>
            {mediaId && <p className="pgw-complete"><CheckCircle2 size={15} /> Image record #{mediaId} created</p>}
          </article>

          <article className="pgw-panel">
            <div className="pgw-panel-heading"><span className="pgw-step">02</span><div><h2>Submit media rights evidence</h2><p>Evidence stays private and is reviewed by authorised editorial staff.</p></div></div>
            <label className="pgw-file-input"><FileText size={19} /><span><strong>{evidenceFile?.name ?? "Choose signed rights document"}</strong><small>PDF, JPEG, PNG or WebP · maximum 15 MB</small></span><input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" onChange={(e) => setEvidenceFile(e.target.files?.[0] ?? null)} /></label>
            <fieldset><legend>Where may this image be promoted?</legend>{["website", "social_media", "email", "advertising"].map((channel) => <label className="pgw-check" key={channel}><input type="checkbox" checked={channels.includes(channel)} onChange={() => toggleChannel(channel)} />{channel.replace("_", " ")}</label>)}</fieldset>
            <button className="pgw-button pgw-button--secondary" type="button" onClick={submitRights} disabled={busy !== null || !mediaId || grantId !== null}>{busy === "rights" ? <LoaderCircle className="pgw-spin" size={17} /> : <ShieldCheck size={17} />}{grantId ? "Rights evidence submitted" : "Submit rights evidence"}</button>
            {grantId && <p className="pgw-complete"><CheckCircle2 size={15} /> Evidence submission #{grantId} awaiting editorial verification</p>}
          </article>

          <article className="pgw-panel">
            <div className="pgw-panel-heading"><span className="pgw-step">03</span><div><h2>Write the story behind this image</h2><p>Each image has its own story. Keep the summary concise and fact-based.</p></div></div>
            <label>Public-facing summary <span className={`pgw-word-count ${summaryValid ? "is-valid" : ""}`}>{count}/30–60 words</span><textarea value={summary} onChange={(e) => setSummary(e.target.value)} rows={5} maxLength={600} placeholder="Describe the verified story, experience or facts connected to this image…" /></label>
            <label>Owner's original history <span className="pgw-private-label"><ShieldCheck size={13} /> Private by default</span><textarea value={ownerHistory} onChange={(e) => setOwnerHistory(e.target.value)} rows={4} placeholder="Optional. This stays private unless you separately grant explicit publication permission." /></label>
            <p className="pgw-privacy-note">Original history is never published by default. A separate, version-specific permission is required. AI drafting is not enabled in this workspace and must never invent facts.</p>
            <button className="pgw-button" type="button" onClick={createStory} disabled={busy !== null || !mediaId || !grantId || !summaryValid}>{busy === "story" ? <LoaderCircle className="pgw-spin" size={17} /> : <FileText size={17} />}Create story draft</button>
            {storyId && <p className="pgw-complete"><CheckCircle2 size={15} /> Story #{storyId} created for image #{mediaId}</p>}
          </article>
        </div>

        <aside className="pgw-panel pgw-workflow-panel">
          <div className="pgw-panel-heading"><div><h2>Publication checklist</h2><p>Every gate must pass before a story is public.</p></div></div>
          <ol className="pgw-checklist">
            <li className={mediaId ? "is-done" : ""}><span>1</span><div><strong>Image uploaded</strong><small>Private until approved</small></div></li>
            <li className={grantId ? "is-done" : ""}><span>2</span><div><strong>Rights evidence submitted</strong><small>Editorial verification required</small></div></li>
            <li className={storyId ? "is-done" : ""}><span>3</span><div><strong>Story drafted</strong><small>30–60-word public summary</small></div></li>
            <li><span>4</span><div><strong>Owner approval</strong><small>Applies to the current version</small></div></li>
            <li><span>5</span><div><strong>Editorial approval</strong><small>Partner, media and rights checks</small></div></li>
          </ol>
          <div className="pgw-private-callout"><ShieldCheck size={19} /><p><strong>Private by default</strong><br />Owner history and rights documents are not public Gallery content.</p></div>
        </aside>
      </div>

      <section className="pgw-drafts">
        <div className="pgw-drafts-heading"><div><p className="pgw-eyebrow">CONTENT STATUS</p><h2>Your submitted stories</h2></div><button className="pgw-refresh" type="button" onClick={refresh} disabled={busy !== null}><RefreshCw size={16} className={busy === "refresh" ? "pgw-spin" : ""} />Refresh</button></div>
        {drafts.length === 0 ? <p className="pgw-empty">No story submissions yet. Your saved stories will appear here.</p> : <div className="pgw-draft-list">{drafts.map((draft) => <article className="pgw-draft-row" key={draft.id}><div><strong>Story #{draft.id} · Image #{draft.media}</strong><p>{draft.summary || "Summary not added yet"}</p></div><div className="pgw-draft-actions"><span className="pgw-status">{statusLabel[draft.status] ?? draft.status}</span>{draft.status === "owner_review" && draft.media_status === "approved" && draft.partner_gallery_status === "approved" && <button type="button" className="pgw-approve" onClick={() => approveStory(draft.id)} disabled={busy !== null}>{busy === "approve" ? "Saving…" : "Approve this version"}</button>}{draft.status === "owner_review" && (draft.media_status !== "approved" || draft.partner_gallery_status !== "approved") && <small className="pgw-waiting">Waiting for partner and media approval</small>}</div></article>)}</div>}
      </section>
    </section>
  );
}
