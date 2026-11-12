import { useEffect, useState } from "react";
import GalleryStoryCard, { type GalleryStoryCardProps } from "./GalleryStoryCard";
import "./gallery.css";

type PublicStory = {
  id: number;
  title: string;
  summary: string;
  image: string;
  alt_text: string;
  partner_name: string;
  partner_slug: string;
};

const API_BASE = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";

export default function GalleryPartnerGrid() {
  const [stories, setStories] = useState<GalleryStoryCardProps[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/v1/gallery/stories/`, { signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error("The public Gallery is temporarily unavailable.");
        return response.json() as Promise<PublicStory[]>;
      })
      .then(items => setStories(items.map(item => ({
        storyId: item.id,
        imageUrl: item.image,
        imageAlt: item.alt_text,
        title: item.title,
        partnerName: item.partner_name,
        summary: item.summary,
        partnerUrl: `/partners/${encodeURIComponent(item.partner_slug)}/`,
      }))))
      .catch(err => {
        if (err instanceof Error && err.name !== "AbortError") setError(err.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  if (loading) {
    return <div className="gallery-empty-state" role="status"><p className="eyebrow">APPROVED PARTNER STORIES</p><h2>Stories worth discovering.</h2><p>Loading approved partner stories…</p></div>;
  }

  if (error) {
    return <div className="gallery-empty-state" role="status"><p className="eyebrow">APPROVED PARTNER STORIES</p><h2>Stories are taking a moment.</h2><p>{error}</p></div>;
  }

  if (stories.length === 0) {
    return <div className="gallery-empty-state"><p className="eyebrow">APPROVED PARTNER STORIES</p><h2>Stories worth discovering.</h2><p>Partner stories will appear here after the business, image rights and story have been approved by the owner and XGetawaySX editorial team.</p></div>;
  }

  return <div className="gallery-partner-grid">{stories.map(story => <GalleryStoryCard key={story.storyId} {...story} />)}</div>;
}
