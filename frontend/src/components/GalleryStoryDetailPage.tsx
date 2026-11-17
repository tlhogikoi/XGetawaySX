import { useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, MapPin, CalendarDays, Compass, Share2, ChevronLeft, ChevronRight } from "lucide-react";
import GalleryStoryCard, { type GalleryStoryCardProps } from "./GalleryStoryCard";
import GalleryContentPlaceholder from "./GalleryContentPlaceholder";
import "./gallery.css";

type GalleryStoryImage = {
  id: number;
  position: number;
  image: string;
  alt_text: string;
  caption?: string;
  media_credit?: string;
};
type GalleryStory = {
  id: number; title: string; summary: string; published_at: string; image: string;
  alt_text: string; partner_name: string; partner_slug: string; partner_city?: string;
  owner_original_history?: string | null; caption?: string; media_credit?: string;
  images?: GalleryStoryImage[];
};
const API_BASE = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";

export default function GalleryStoryDetailPage({ storyId }: { storyId: string }) {
  const [story, setStory] = useState<GalleryStory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [relatedStories, setRelatedStories] = useState<GalleryStoryCardProps[]>([]);
  const [shareFeedback, setShareFeedback] = useState("");
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/v1/gallery/stories/${encodeURIComponent(storyId)}/`, { signal: controller.signal })
      .then(async response => {
        if (response.status === 404) throw new Error("This story is no longer available in the public Gallery.");
        if (!response.ok) throw new Error("Unable to load this story right now.");
        return response.json() as Promise<GalleryStory>;
      }).then(data => { setStory(data); setActiveImageIndex(0); }).catch(err => {
        if (err instanceof Error && err.name !== "AbortError") setError(err.message);
      }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    fetch(`${API_BASE}/api/v1/gallery/stories/`, { signal: controller.signal })
      .then(response => response.ok ? response.json() as Promise<GalleryStory[]> : [])
      .then(items => setRelatedStories(items.filter(item => String(item.id) !== storyId).slice(0, 3).map(item => ({
        storyId: item.id, imageUrl: item.image, imageAlt: item.alt_text,
        title: item.title, partnerName: item.partner_name, summary: item.summary,
        partnerUrl: `/partners/${encodeURIComponent(item.partner_slug)}/`,
        storyUrl: `/gallery/stories/${item.id}/`,
      }))))
      .catch(() => { /* Related stories are optional; keep the main story available. */ });
    return () => controller.abort();
  }, [storyId]);
  if (loading) return <main className="gallery-story-detail-shell"><p role="status">Loading approved story…</p></main>;
  if (error || !story) return <main className="gallery-story-detail-shell"><a className="profile-back" href="/gallery/"><ArrowLeft size={16}/> Back to Gallery</a><GalleryContentPlaceholder eyebrow="XGETAWAYSX GALLERY" title="Story unavailable." message={error || "This story could not be found."} /></main>;
  const shareStory = async () => {
    const url = window.location.href;
    try {
      if (navigator.share) {
        await navigator.share({ title: story.title, text: `${story.summary} — XGetawaySX`, url });
        setShareFeedback("Share sheet opened.");
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url);
        setShareFeedback("Story link copied.");
      } else {
        setShareFeedback(`Copy this link: ${url}`);
      }
    } catch (shareError) {
      if (!(shareError instanceof Error) || shareError.name !== "AbortError") {
        setShareFeedback("Sharing is unavailable here. Copy the page address from your browser.");
      }
    }
  };
  const publishedDate = story.published_at ? new Date(story.published_at) : null;
  const validDate = publishedDate && !Number.isNaN(publishedDate.getTime());
  const galleryImages = story.images?.length ? story.images : [{
    id: story.id, position: 0, image: story.image, alt_text: story.alt_text,
    caption: story.caption, media_credit: story.media_credit,
  }];
  const activeImage = galleryImages[Math.min(activeImageIndex, galleryImages.length - 1)];
  return <main className="gallery-story-detail-shell">
    <header className="profile-topbar"><a className="profile-back" href="/gallery/"><ArrowLeft size={16}/> Back to Gallery</a><a className="profile-wordmark" href="/"><span>X</span>GETAWAYS<span>X</span></a><a className="profile-back" href="/account">Plan a getaway <ArrowUpRight size={16}/></a></header>
    <article>
      <section className="gallery-story-detail-hero"><div className="gallery-story-detail-heading"><p className="eyebrow">AN APPROVED XGETAWAYSX STORY</p><h1>{story.title}</h1><a className="gallery-story-detail-partner" href={`/partners/${encodeURIComponent(story.partner_slug)}/`}>{story.partner_name} <ArrowUpRight size={15}/></a><div className="gallery-story-detail-meta">{story.partner_city && <span><MapPin size={15}/>{story.partner_city}</span>}{validDate && <span><CalendarDays size={15}/>{publishedDate.toLocaleDateString(undefined,{year:"numeric",month:"long",day:"numeric"})}</span>}</div></div>
        <div className="gallery-story-image-viewer">
          <figure className="gallery-story-detail-image">
            <img src={activeImage.image} alt={activeImage.alt_text}/>
            {(activeImage.caption || activeImage.media_credit) && <figcaption>{activeImage.caption}{activeImage.media_credit && <span>Image: {activeImage.media_credit}</span>}</figcaption>}
          </figure>
          {galleryImages.length > 1 && <div className="gallery-image-navigation" aria-label="Gallery image navigation">
            <button type="button" onClick={() => setActiveImageIndex(index => Math.max(0, index - 1))} disabled={activeImageIndex === 0} aria-label="Previous photo"><ChevronLeft size={18}/><span>Previous</span></button>
            <span aria-live="polite">Photo {activeImageIndex + 1} of {galleryImages.length}</span>
            <button type="button" onClick={() => setActiveImageIndex(index => Math.min(galleryImages.length - 1, index + 1))} disabled={activeImageIndex === galleryImages.length - 1} aria-label="Next photo"><span>Next</span><ChevronRight size={18}/></button>
          </div>}
        </div>
      </section>
      <section className="gallery-story-detail-body"><p className="eyebrow">THE STORY BEHIND THE PLACE</p><h2>Discover the experience.</h2><p className="gallery-story-detail-summary">{story.summary}</p>
        {story.owner_original_history && <div className="gallery-owner-history"><p className="eyebrow">SHARED BY THE PARTNER</p><h3>The story from the people behind it.</h3><p>{story.owner_original_history}</p></div>}
        <div className="gallery-story-detail-cta"><div><Compass size={22}/><div><strong>Inspired to experience it?</strong><span>Explore the partner or start planning your next getaway.</span></div></div><a className="primary-button" href={`/partners/${encodeURIComponent(story.partner_slug)}/`}>Explore partner <ArrowUpRight size={16}/></a><a className="gallery-plan-link" href="/account">Plan a getaway <ArrowUpRight size={15}/></a><button className="gallery-share-button" type="button" onClick={shareStory}><Share2 size={16}/> Share story</button>{shareFeedback && <p className="gallery-share-feedback" role="status">{shareFeedback}</p>}</div>
      </section>
      {relatedStories.length > 0 && <section className="gallery-related-stories" aria-labelledby="gallery-related-title"><p className="eyebrow">KEEP EXPLORING</p><h2 id="gallery-related-title">More stories to discover.</h2><div className="gallery-partner-grid">{relatedStories.map(item => <GalleryStoryCard key={item.storyId} {...item}/>)}</div></section>}
    </article>
    <footer className="gallery-explore-footer"><span>© {new Date().getFullYear()} XGetawaySX</span><strong>TRAVEL THROUGH US.</strong><a href="/gallery/">Discover more stories</a></footer>
  </main>;
}
