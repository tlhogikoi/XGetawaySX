import { useEffect, useMemo, useState } from "react";
import GalleryStoryCard, { type GalleryStoryCardProps } from "./GalleryStoryCard";
import GalleryContentPlaceholder from "./GalleryContentPlaceholder";
import { Search, SlidersHorizontal } from "lucide-react";
import "./gallery.css";

type PublicStory = {
  id: number;
  title: string;
  summary: string;
  image: string;
  alt_text: string;
  partner_name: string;
  partner_slug: string;
  partner_city?: string;
};

const API_BASE = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";

export default function GalleryPartnerGrid() {
  const [stories, setStories] = useState<(GalleryStoryCardProps & { city: string })[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [city, setCity] = useState("all");

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
        storyUrl: `/gallery/stories/${item.id}/`,
        city: item.partner_city?.trim() ?? "",
      }))))
      .catch(err => {
        if (err instanceof Error && err.name !== "AbortError") setError(err.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const cities = useMemo(() => [...new Set(stories.map(story => story.city).filter(Boolean))].sort((a, b) => a.localeCompare(b)), [stories]);
  const filteredStories = useMemo(() => {
    const term = search.trim().toLocaleLowerCase();
    return stories.filter(story => {
      const matchesCity = city === "all" || story.city === city;
      const matchesSearch = !term || [story.title, story.partnerName, story.summary, story.city].some(value => value.toLocaleLowerCase().includes(term));
      return matchesCity && matchesSearch;
    });
  }, [stories, search, city]);

  if (loading) {
    return <div className="gallery-empty-state" role="status" aria-live="polite"><p className="eyebrow">APPROVED PARTNER STORIES</p><h2>Stories worth discovering.</h2><p>Loading approved partner stories…</p></div>;
  }

  if (error) {
    return <div className="gallery-empty-state" role="alert"><p className="eyebrow">APPROVED PARTNER STORIES</p><h2>Stories are taking a moment.</h2><p>{error}</p><button className="gallery-retry-button" type="button" onClick={() => window.location.reload()}>Try again</button></div>;
  }

  if (stories.length === 0) {
    return <GalleryContentPlaceholder eyebrow="THE XGETAWAYSX GALLERY" title="New stories are on the way." message="We’re preparing more places and experiences to discover. Check back soon for stories worth sharing." />;
  }

  return (
    <div className="gallery-discovery">
      <div className="gallery-discovery-toolbar">
        <label className="gallery-search-field">
          <Search size={17} aria-hidden="true" />
          <span className="sr-only">Search Gallery stories</span>
          <input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search places, partners or stories" />
        </label>
        <label className="gallery-city-filter">
          <SlidersHorizontal size={16} aria-hidden="true" />
          <span className="sr-only">Filter by city</span>
          <select value={city} onChange={event => setCity(event.target.value)}>
            <option value="all">All locations</option>
            {cities.map(item => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <p className="gallery-result-count" aria-live="polite">{filteredStories.length} {filteredStories.length === 1 ? "story" : "stories"}</p>
      </div>
      {filteredStories.length ? (
        <div className="gallery-partner-grid">{filteredStories.map(story => <GalleryStoryCard key={story.storyId} {...story} />)}</div>
      ) : (
        <GalleryContentPlaceholder compact eyebrow="NO MATCHES FOUND" title="Try another search." message="We couldn’t find an approved story matching those filters. Clear your search or choose another location." />
      )}
    </div>
  );
}
