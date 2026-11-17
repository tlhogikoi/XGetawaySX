import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, ArrowDown, ArrowUp, CheckCircle2, Download, Eye, FileImage, FileText, LoaderCircle, RefreshCw, ShieldCheck, Trash2, UploadCloud } from "lucide-react";
import "./partner-gallery.css";

type DraftStory = {
  id: number;
  media: number;
  summary: string;
  owner_original_history?: string;
  editorial_feedback?: string | null;
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
type PartnerNotification = { id: number; story_id: number; kind: "story_published" | "story_changes_requested"; title: string; message: string; read_at: string | null; created_at: string };
type PartnerActivity = { id: number; event_type: string; label: string; media_id: number | null; media_title: string | null; story_id: number | null; story_version: number | null; occurred_at: string };
type StoryRevision = { id: number; version: number; summary: string; owner_history_private: boolean; ai_assisted: boolean; change_reason: string; changed_by: string | null; created_at: string };
type StoryImage = { id: number; title: string; alt_text: string; caption: string; media_credit: string; position: number; is_cover: boolean; media_status: string; rights_review_status: string; permitted_channels: string[]; website_permission_active: boolean };
type StoryImageLibrary = { story_id: number; story_version: number; status: string; images: StoryImage[] };
type RightsGrant = { id: number; rights_holder: string; permitted_channels: string[]; evidence_reference: string; evidence_available: boolean; evidence_url: string | null; granted_at: string; expires_at: string | null; revoked_at: string | null; review_status: string; review_notes: string; reviewed_at: string | null; active: boolean };
type RightsResponse = { media_id: number; media_status: string; permissions: RightsGrant[] };

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
  const [attachStoryId, setAttachStoryId] = useState<number | null>(null);
  const [imageManagerBusy, setImageManagerBusy] = useState(false);
  const [imageLibraryStoryId, setImageLibraryStoryId] = useState<number | null>(null);
  const [imageLibrary, setImageLibrary] = useState<Record<number, StoryImageLibrary>>({});
  const [privatePreviews, setPrivatePreviews] = useState<Record<number, string>>({});
  const previewUrls = useRef(new Set<string>());
  const [rightsDetails, setRightsDetails] = useState<Record<number, RightsResponse>>({});
  const [rightsExpandedMediaId, setRightsExpandedMediaId] = useState<number | null>(null);
  const [drafts, setDrafts] = useState<DraftStory[]>([]);
  const [notifications, setNotifications] = useState<PartnerNotification[]>([]);
  const [activity, setActivity] = useState<PartnerActivity[]>([]);
  const [editingStoryId, setEditingStoryId] = useState<number | null>(null);
  const [editSummary, setEditSummary] = useState("");
  const [editHistory, setEditHistory] = useState("");
  const [revisions, setRevisions] = useState<Record<number, StoryRevision[]>>({});
  const [revisionStoryId, setRevisionStoryId] = useState<number | null>(null);
  const [busy, setBusy] = useState<"media" | "rights" | "story" | "approve" | "refresh" | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const count = useMemo(() => wordCount(summary), [summary]);
  const summaryValid = count >= 30 && count <= 60;

  const loadNotifications = useCallback(async () => {
    if (!accessToken) return;
    const payload = await request<PartnerNotification[] | { results?: PartnerNotification[] }>(`${api}/notifications/`, accessToken);
    setNotifications(extractList(payload));
  }, [accessToken, api]);

  const loadActivity = useCallback(async () => {
    if (!accessToken) return;
    const payload = await request<PartnerActivity[] | { results?: PartnerActivity[] }>(api + "/partners/" + partnerId + "/activity/", accessToken);
    setActivity(extractList(payload));
  }, [accessToken, api, partnerId]);

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
    request<PartnerNotification[] | { results?: PartnerNotification[] }>(`${api}/notifications/`, accessToken)
      .then((payload) => { if (active) setNotifications(extractList(payload)); })
      .catch((err: Error) => { if (active) setError(err.message); });
    request<PartnerActivity[] | { results?: PartnerActivity[] }>(api + "/partners/" + partnerId + "/activity/", accessToken)
      .then((payload) => { if (active) setActivity(extractList(payload)); })
      .catch((err: Error) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [accessToken, api, partnerId]);

  async function markNotificationRead(id: number) {
    try {
      const result = await request<{ id: number; read_at: string }>(`${api}/notifications/${id}/read/`, accessToken, { method: "POST", body: "{}" });
      setNotifications((current) => current.map((item) => item.id === id ? { ...item, read_at: result.read_at } : item));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update notification.");
    }
  }

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
      await loadActivity();
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
      await loadActivity();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rights evidence submission failed.");
    } finally { setBusy(null); }
  }

  async function loadImageLibrary(id: number) {
    if (imageLibraryStoryId === id) { setImageLibraryStoryId(null); return; }
    setImageManagerBusy(true); setError("");
    try {
      const result = await request<StoryImageLibrary>(`${api}/stories/${id}/media/`, accessToken);
      setImageLibrary(current => ({ ...current, [id]: result }));
      setImageLibraryStoryId(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this story's image library.");
    } finally { setImageManagerBusy(false); }
  }

  async function loadPrivatePreview(mediaId: number) {
    setImageManagerBusy(true); setError("");
    try {
      const response = await fetch(`${api}/media/${mediaId}/private-preview/`, { headers: { Authorization: `Bearer ${accessToken}` } });
      if (!response.ok) throw new Error(`Preview unavailable (${response.status}).`);
      const url = URL.createObjectURL(await response.blob());
      previewUrls.current.add(url);
      setPrivatePreviews(current => {
        if (current[mediaId]) { URL.revokeObjectURL(current[mediaId]); previewUrls.current.delete(current[mediaId]); }
        return { ...current, [mediaId]: url };
      });
    } catch (err) { setError(err instanceof Error ? err.message : "Could not load private image preview."); }
    finally { setImageManagerBusy(false); }
  }

  async function loadRightsDetails(mediaId: number) {
    if (rightsExpandedMediaId === mediaId) { setRightsExpandedMediaId(null); return; }
    setImageManagerBusy(true); setError("");
    try {
      const result = await request<RightsResponse>(`${api}/media/${mediaId}/permissions/`, accessToken);
      setRightsDetails(current => ({ ...current, [mediaId]: result }));
      setRightsExpandedMediaId(mediaId);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not load rights details."); }
    finally { setImageManagerBusy(false); }
  }

  async function downloadRightsEvidence(mediaId: number, grant: RightsGrant) {
    if (!grant.evidence_available) return;
    setImageManagerBusy(true); setError("");
    try {
      const response = await fetch(`${api}/media/${mediaId}/permissions/${grant.id}/evidence/`, { headers: { Authorization: `Bearer ${accessToken}` } });
      if (!response.ok) throw new Error(`Evidence download unavailable (${response.status}).`);
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url; link.download = "gallery-rights-evidence"; document.body.appendChild(link); link.click(); link.remove();
      URL.revokeObjectURL(url);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not download rights evidence."); }
    finally { setImageManagerBusy(false); }
  }

  useEffect(() => () => { previewUrls.current.forEach(url => URL.revokeObjectURL(url)); previewUrls.current.clear(); }, []);

  async function saveImageOrder(storyId: number, orderedIds: number[]) {
    setImageManagerBusy(true); setError(""); setNotice("");
    try {
      const result = await request<{ story_version: number; ordered_media_ids: number[] }>(
        `${api}/stories/${storyId}/media/`, accessToken,
        { method: "PATCH", body: JSON.stringify({ ordered_media_ids: orderedIds }) },
      );
      const current = imageLibrary[storyId];
      if (current) {
        const byId = new Map(current.images.map(image => [image.id, image]));
        const ordered = orderedIds.map((id, index) => ({ ...byId.get(id)!, position: index + 1 }));
        setImageLibrary(value => ({ ...value, [storyId]: { ...current, story_version: result.story_version, status: "owner_review", images: [current.images[0], ...ordered] } }));
      }
      setNotice(`Photo order saved as story version ${result.story_version}. Owner and editorial approvals must be completed again.`);
      await loadDrafts(); await loadActivity();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not save photo order."); }
    finally { setImageManagerBusy(false); }
  }

  async function moveStoryImage(storyId: number, mediaId: number, direction: -1 | 1) {
    const library = imageLibrary[storyId];
    if (!library) return;
    const ids = library.images.filter(image => !image.is_cover).map(image => image.id);
    const index = ids.indexOf(mediaId);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    await saveImageOrder(storyId, ids);
  }

  async function removeStoryImage(storyId: number, mediaId: number) {
    setImageManagerBusy(true); setError(""); setNotice("");
    try {
      const result = await request<{ story_version: number }>(
        `${api}/stories/${storyId}/media/?media_id=${mediaId}`, accessToken,
        { method: "DELETE" },
      );
      const refreshed = await request<StoryImageLibrary>(`${api}/stories/${storyId}/media/`, accessToken);
      setImageLibrary(current => ({ ...current, [storyId]: refreshed }));
      setNotice(`Photo removed. Story version ${result.story_version} requires fresh owner and editorial approval.`);
      await loadDrafts(); await loadActivity();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not remove this photo."); }
    finally { setImageManagerBusy(false); }
  }

  async function attachUploadedImage() {
    if (!mediaId || !grantId || !attachStoryId) {
      setError("Upload an image, submit its rights evidence and choose a story before attaching it.");
      return;
    }
    setImageManagerBusy(true); setError(""); setNotice("");
    try {
      const result = await request<{ story_id: number; media_id: number; position: number; image_count: number; story_version: number }>(
        `${api}/stories/${attachStoryId}/media/`, accessToken,
        { method: "POST", body: JSON.stringify({ media_id: mediaId }) },
      );
      setNotice(`Image #${result.media_id} attached as photo ${result.position + 1}. Story version ${result.story_version} now requires fresh owner and editorial approval.`);
      setMediaId(null); setGrantId(null); setImageFile(null); setEvidenceFile(null);
      setTitle(""); setAltText(""); setRightsHolder(""); setAttachStoryId(null);
      await loadDrafts(); await loadActivity();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not attach this image to the story.");
    } finally { setImageManagerBusy(false); }
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
      try { await loadDrafts(); await loadNotifications(); await loadActivity(); } catch { /* Keep the successful action notice; refresh can be retried separately. */ }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Story draft creation failed.");
    } finally { setBusy(null); }
  }


  function beginEdit(draft: DraftStory) {
    setEditingStoryId(draft.id);
    setEditSummary(draft.summary);
    setEditHistory(draft.owner_original_history ?? "");
    setError(""); setNotice("");
  }

  async function saveStoryEdit(id: number) {
    if (!wordCount(editSummary) || wordCount(editSummary) < 30 || wordCount(editSummary) > 60) {
      setError("The public summary must contain 30–60 words.");
      return;
    }
    setBusy("refresh"); setError(""); setNotice("");
    try {
      const result = await request<DraftStory>(`${api}/stories/${id}/draft/`, accessToken, {
        method: "PATCH",
        body: JSON.stringify({ summary: editSummary.trim(), owner_original_history: editHistory.trim() }),
      });
      setEditingStoryId(null);
      setNotice(`Story saved as version ${result.current_version}. Previous owner and editorial approvals have been reset; please review and approve this version again.`);
      await loadDrafts();
      await loadActivity();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Story revision failed.");
    } finally { setBusy(null); }
  }

  async function loadRevisions(id: number) {
    if (revisionStoryId === id) { setRevisionStoryId(null); return; }
    setBusy("refresh"); setError("");
    try {
      const payload = await request<StoryRevision[] | { results?: StoryRevision[] }>(`${api}/stories/${id}/revisions/`, accessToken);
      setRevisions((current) => ({ ...current, [id]: extractList(payload) }));
      setRevisionStoryId(id);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not load story revisions."); }
    finally { setBusy(null); }
  }

  async function approveStory(id: number) {
    setBusy("approve"); setError(""); setNotice("");
    try {
      await request<{ status: string }>(`${api}/stories/${id}/owner-approve/`, accessToken, { method: "POST", body: "{}" });
      setNotice("Your approval has been recorded for this story version. Editorial approval is still required.");
      try { await loadDrafts(); await loadNotifications(); await loadActivity(); } catch { /* Approval succeeded; refresh can be retried without repeating the action. */ }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Owner approval failed.");
    } finally { setBusy(null); }
  }

  async function refresh() {
    setBusy("refresh"); setError("");
    try { await loadDrafts(); await loadNotifications(); await loadActivity(); }
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

      <section className="pgw-notifications" aria-labelledby="pgw-notifications-title">
        <div className="pgw-drafts-heading"><div><p className="pgw-eyebrow">REVIEW COMMUNICATION</p><h2 id="pgw-notifications-title">Notifications</h2></div><span className="pgw-unread-count">{notifications.filter((item) => !item.read_at).length} unread</span></div>
        {notifications.length === 0 ? <p className="pgw-empty">You are up to date. Publication and review updates will appear here.</p> : <ul className="pgw-notification-list">{notifications.map((item) => <li className={item.read_at ? "is-read" : "is-unread"} key={item.id}><div><strong>{item.title}</strong><p>{item.message}</p><small>Story #{item.story_id} · {new Date(item.created_at).toLocaleString()}</small></div>{!item.read_at && <button type="button" className="pgw-refresh" onClick={() => markNotificationRead(item.id)}>Mark as read</button>}</li>)}</ul>}
      </section>

      <section className="pgw-activity" aria-labelledby="pgw-activity-title">
        <div className="pgw-drafts-heading"><div><p className="pgw-eyebrow">SUBMISSION TRACKING</p><h2 id="pgw-activity-title">Activity timeline</h2></div><span className="pgw-unread-count">Latest {activity.length} events</span></div>
        {activity.length === 0 ? <p className="pgw-empty">Your submission milestones will appear here as your Gallery content moves through review.</p> : <ol className="pgw-activity-list">{activity.map((item) => <li key={item.id}><span className="pgw-activity-marker" aria-hidden="true" /><div><strong>{item.label}</strong><p>{item.media_title ?? `Gallery media #${item.media_id ?? "—"}`}{item.story_id ? ` · Story #${item.story_id}` : ""}{item.story_version ? ` · Version ${item.story_version}` : ""}</p><small>{new Date(item.occurred_at).toLocaleString()}</small></div></li>)}</ol>}
      </section>

      <div className="pgw-layout">
        <div className="pgw-form-column">
          <article className="pgw-panel">
            <div className="pgw-panel-heading"><span className="pgw-step">01</span><div><h2>Add a Gallery image</h2><p>Upload an image you have authority to submit.</p></div></div>
            <label>Image title<input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={180} placeholder="e.g. The lodge overlooking the valley" /></label>
            <label>Image description for accessibility<input value={altText} onChange={(e) => setAltText(e.target.value)} maxLength={250} placeholder="Describe what a visitor can see" /></label>
            <label>Rights holder<input value={rightsHolder} onChange={(e) => setRightsHolder(e.target.value)} maxLength={180} placeholder="Person or organisation holding image rights" /></label>
            <label className="pgw-file-input"><FileImage size={19} /><span><strong>{imageFile?.name ?? "Choose image"}</strong><small>JPEG, PNG or WebP · maximum 10 MB</small></span><input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setImageFile(e.target.files?.[0] ?? null)} /></label>
            <button className="pgw-button" type="button" onClick={submitMedia} disabled={busy !== null || mediaId !== null}>{busy === "media" ? <LoaderCircle className="pgw-spin" size={17} /> : <UploadCloud size={17} />}{mediaId ? "Image uploaded privately" : "Upload image privately"}</button>
            {mediaId && <p className="pgw-complete"><CheckCircle2 size={15} /> Image record #{mediaId} created privately</p>}
            {mediaId && grantId && drafts.length > 0 && <div className="pgw-image-attach">
              <label htmlFor="pgw-attach-story">Add this approved-rights submission to an existing story</label>
              <select id="pgw-attach-story" value={attachStoryId ?? ""} onChange={event => setAttachStoryId(event.target.value ? Number(event.target.value) : null)}>
                <option value="">Choose a story</option>
                {drafts.filter(draft => ["draft", "owner_review", "editorial_review", "rejected"].includes(draft.status)).map(draft => <option key={draft.id} value={draft.id}>Story #{draft.id} · {statusLabel[draft.status] ?? draft.status}</option>)}
              </select>
              <p>Attaching an image creates a new story version and resets previous approvals. The image must separately pass rights and editorial review before publication.</p>
              <button className="pgw-button pgw-button--secondary" type="button" onClick={attachUploadedImage} disabled={imageManagerBusy || !attachStoryId}>{imageManagerBusy ? <LoaderCircle className="pgw-spin" size={17}/> : <FileImage size={17}/>}Attach image to selected story</button>
            </div>}
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
        {drafts.length === 0 ? <p className="pgw-empty">No story submissions yet. Your saved stories will appear here.</p> : <div className="pgw-draft-list">{drafts.map((draft) => <article className="pgw-draft-row" key={draft.id}><div><strong>Story #{draft.id} · Image #{draft.media}</strong><p>{draft.summary || "Summary not added yet"}</p>{draft.editorial_feedback && draft.status === "rejected" && <div className="pgw-editorial-feedback"><strong>Editorial changes requested</strong><p>{draft.editorial_feedback}</p></div>}
        {editingStoryId === draft.id ? <div className="pgw-story-editor"><label>Revised public summary<textarea rows={5} value={editSummary} onChange={(e) => setEditSummary(e.target.value)} maxLength={600}/><small>{wordCount(editSummary)} words · 30–60 required</small></label><label>Owner's original history <span className="pgw-private-label"><ShieldCheck size={12}/> Private by default</span><textarea rows={4} value={editHistory} onChange={(e) => setEditHistory(e.target.value)} /></label><div className="pgw-edit-actions"><button type="button" className="pgw-button pgw-button--secondary" onClick={() => setEditingStoryId(null)}>Cancel</button><button type="button" className="pgw-button" disabled={busy !== null} onClick={() => saveStoryEdit(draft.id)}>{busy === "refresh" ? "Saving…" : "Save new version"}</button></div></div> : <div className="pgw-draft-tools"><button type="button" className="pgw-refresh" onClick={() => beginEdit(draft)} disabled={draft.status === "published" || draft.status === "withdrawn"}>Edit / respond to review</button><button type="button" className="pgw-refresh" onClick={() => loadRevisions(draft.id)} disabled={busy !== null}> {revisionStoryId === draft.id ? "Hide version history" : "Version history"} </button><button type="button" className="pgw-refresh" onClick={() => loadImageLibrary(draft.id)} disabled={imageManagerBusy || draft.status === "published" || draft.status === "withdrawn"}>{imageLibraryStoryId === draft.id ? "Hide photo manager" : "Manage photos"}</button></div>}
        {imageLibraryStoryId === draft.id && imageLibrary[draft.id] && <div className="pgw-image-library"><div className="pgw-image-library-heading"><strong>Story photo library · version {imageLibrary[draft.id].story_version}</strong><small>Cover image stays first. Additional photos can be reordered or removed.</small></div>{imageLibrary[draft.id].images.map((photo, index) => <div className="pgw-image-library-row" key={photo.id}><div className="pgw-image-library-info"><strong>{photo.is_cover ? "Cover" : `Photo ${index}`} · {photo.title}</strong><small>Media: {photo.media_status.replaceAll("_", " ")} · Rights: {photo.rights_review_status.replaceAll("_", " ")}</small><small>Website permission: {photo.website_permission_active ? "Active" : "Not approved"}</small><div className="pgw-image-library-actions"><button type="button" className="pgw-refresh" onClick={() => loadPrivatePreview(photo.id)} disabled={imageManagerBusy}><Eye size={14}/>Preview</button><button type="button" className="pgw-refresh" onClick={() => loadRightsDetails(photo.id)} disabled={imageManagerBusy}>Rights details</button></div>{privatePreviews[photo.id] && <img className="pgw-private-preview" src={privatePreviews[photo.id]} alt={photo.alt_text || photo.title}/ >}{rightsExpandedMediaId === photo.id && rightsDetails[photo.id] && <div className="pgw-rights-details">{rightsDetails[photo.id].permissions.length === 0 ? <small>No rights submission recorded.</small> : rightsDetails[photo.id].permissions.map(grant => <div key={grant.id}><strong>{grant.rights_holder} · {grant.review_status.replaceAll("_", " ")}</strong><small>Channels: {grant.permitted_channels.join(", ") || "None listed"}</small><small>Granted: {new Date(grant.granted_at).toLocaleDateString()} · Expires: {grant.expires_at ? new Date(grant.expires_at).toLocaleDateString() : "No expiry recorded"}</small>{grant.review_notes && <small>Editorial note: {grant.review_notes}</small>}{grant.evidence_available && <button type="button" className="pgw-refresh" onClick={() => downloadRightsEvidence(photo.id, grant)} disabled={imageManagerBusy}><Download size={14}/>Download evidence</button>}</div>)}</div>}</div>{!photo.is_cover && <div className="pgw-image-library-actions"><button type="button" className="pgw-refresh" aria-label={`Move ${photo.title} up`} title="Move up" disabled={imageManagerBusy || index === 1} onClick={() => moveStoryImage(draft.id, photo.id, -1)}><ArrowUp size={15}/></button><button type="button" className="pgw-refresh" aria-label={`Move ${photo.title} down`} title="Move down" disabled={imageManagerBusy || index === imageLibrary[draft.id].images.length - 1} onClick={() => moveStoryImage(draft.id, photo.id, 1)}><ArrowDown size={15}/></button><button type="button" className="pgw-refresh" aria-label={`Remove ${photo.title}`} disabled={imageManagerBusy} onClick={() => removeStoryImage(draft.id, photo.id)}><Trash2 size={15}/>Remove</button></div>}</div>)}<p>Removing or reordering photos creates a new story version and resets prior approvals. Images without active website rights remain unpublished.</p></div>}{revisionStoryId === draft.id && <div className="pgw-version-list"><strong>Recorded versions</strong>{(revisions[draft.id] ?? []).map((revision) => <div key={revision.id}><span>Version {revision.version}</span><small>{new Date(revision.created_at).toLocaleString()} · {revision.change_reason || "Content revision"}</small><p>{revision.summary}</p></div>)}</div>}
        </div><div className="pgw-draft-actions"><span className="pgw-status">{statusLabel[draft.status] ?? draft.status}</span>{draft.status === "owner_review" && draft.media_status === "approved" && draft.partner_gallery_status === "approved" && <button type="button" className="pgw-approve" onClick={() => approveStory(draft.id)} disabled={busy !== null}>{busy === "approve" ? "Saving…" : "Approve this version"}</button>}{draft.status === "owner_review" && (draft.media_status !== "approved" || draft.partner_gallery_status !== "approved") && <small className="pgw-waiting">Waiting for partner and media approval</small>}</div></article>)}</div>}
      </section>
    </section>
  );
}
