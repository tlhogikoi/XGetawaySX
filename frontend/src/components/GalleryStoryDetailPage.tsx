import { useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, MapPin, CalendarDays, Compass } from "lucide-react";
import GalleryContentPlaceholder from "./GalleryContentPlaceholder";
import "./gallery.css";

type GalleryStory = {
  id: number; title: string; summary: string; published_at: string; image: string;
  alt_text: string; partner_name: string; partner_slug: string; partner_city?: string;
  owner_original_history?: string | null; caption?: string; media_credit?: string;
};
const API_BASE = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";

export default function GalleryStoryDetailPage({ storyId }: { storyId: string }) {
  const [story, setStory] = useState<GalleryStory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/v1/gallery/stories/${encodeURIComponent(storyId)}/`, { signal: controller.signal })
      .then(async response => {
        if (response.status === 404) throw new Error("This story is no longer available in the public Gallery.");
        if (!response.ok) throw new Error("Unable to load this story right now.");
        return response.json() as Promise<GalleryStory>;
      }).then(setStory).catch(err => {
        if (err instanceof Error && err.name !== "AbortError") setError(err.message);
      }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [storyId]);
  if (loading) return <main className="gallery-story-detail-shell"><p role="status">Loading approved story…</p></main>;
  if (error || !story) return <main className="gallery-story-detail-shell"><a className="profile-back" href="/gallery/"><ArrowLeft size={16}/> Back to Gallery</a><GalleryContentPlaceholder eyebrow="XGETAWAYSX GALLERY" title="Story unavailable." message={error || "This story could not be found."} /></main>;
  const publishedDate = story.published_at ? new Date(story.published_at) : null;
  const validDate = publishedDate && !Number.isNaN(publishedDate.getTime());
  return <main className="gallery-story-detail-shell">
    <header className="profile-topbar"><a className="profile-back" href="/gallery/"><ArrowLeft size={16}/> Back to Gallery</a><a className="profile-wordmark" href="/"><span>X</span>GETAWAYS<span>X</span></a><a className="profile-back" href="/account">Plan a getaway <ArrowUpRight size={16}/></a></header>
    <article>
      <section className="gallery-story-detail-hero"><div className="gallery-story-detail-heading"><p className="eyebrow">AN APPROVED XGETAWAYSX STORY</p><h1>{story.title}</h1><a className="gallery-story-detail-partner" href={`/partners/${encodeURIComponent(story.partner_slug)}/`}>{story.partner_name} <ArrowUpRight size={15}/></a><div className="gallery-story-detail-meta">{story.partner_city && <span><MapPin size={15}/>{story.partner_city}</span>}{validDate && <span><CalendarDays size={15}/>{publishedDate.toLocaleDateString(undefined,{year:"numeric",month:"long",day:"numeric"})}</span>}</div></div>
        <figure className="gallery-story-detail-image"><img src={story.image} alt={story.alt_text}/>{(story.caption || story.media_credit) && <figcaption>{story.caption}{story.media_credit && <span>Image: {story.media_credit}</span>}</figcaption>}</figure>
      </section>
      <section className="gallery-story-detail-body"><p className="eyebrow">THE STORY BEHIND THE PLACE</p><h2>Discover the experience.</h2><p className="gallery-story-detail-summary">{story.summary}</p>
        {story.owner_original_history && <div className="gallery-owner-history"><p className="eyebrow">SHARED BY THE PARTNER</p><h3>The story from the people behind it.</h3><p>{story.owner_original_history}</p></div>}
        <div className="gallery-story-detail-cta"><div><Compass size={22}/><div><strong>Inspired to experience it?</strong><span>Explore the partner or start planning your next getaway.</span></div></div><a className="primary-button" href={`/partners/${encodeURIComponent(story.partner_slug)}/`}>Explore partner <ArrowUpRight size={16}/></a><a className="gallery-plan-link" href="/account">Plan a getaway <ArrowUpRight size={15}/></a></div>
      </section>
    </article>
    <footer className="gallery-explore-footer"><span>© {new Date().getFullYear()} XGetawaySX</span><strong>TRAVEL THROUGH US.</strong><a href="/gallery/">Discover more stories</a></footer>
  </main>;
}
