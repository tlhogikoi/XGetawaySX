import { useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, MapPin, Globe2 } from "lucide-react";
import GalleryStoryCard, { type GalleryStoryCardProps } from "./GalleryStoryCard";
import GalleryContentPlaceholder from "./GalleryContentPlaceholder";
import "./gallery.css";

type PartnerProfileData = {
  name: string;
  slug: string;
  category: string;
  description: string;
  city: string;
  province: string;
  country: string;
  website_url: string;
  stories: Array<{ id: number; title: string; summary: string; image: string; alt_text: string; partner_name: string; partner_slug: string }>;
};

const API_BASE = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";

export default function PublicPartnerProfile({ slug }: { slug: string }) {
  const [profile, setProfile] = useState<PartnerProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/v1/partners/${encodeURIComponent(slug)}/`, { signal: controller.signal })
      .then(async response => {
        if (response.status === 404) throw new Error("This partner profile is not available in the public Gallery.");
        if (!response.ok) throw new Error("Unable to load this partner profile right now.");
        return response.json() as Promise<PartnerProfileData>;
      })
      .then(setProfile)
      .catch(err => {
        if (err instanceof Error && err.name !== "AbortError") setError(err.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [slug]);

  if (loading) return <main className="public-profile-shell"><p role="status">Loading partner profile…</p></main>;
  if (error || !profile) return <main className="public-profile-shell"><a href="/#gallery" className="profile-back"><ArrowLeft size={16}/> Back to Gallery</a><h1>Partner profile unavailable</h1><p role="status">{error || "This profile could not be found."}</p></main>;

  const stories: GalleryStoryCardProps[] = profile.stories.map(story => ({
    storyId: story.id, imageUrl: story.image, imageAlt: story.alt_text,
    title: story.title, partnerName: story.partner_name, summary: story.summary,
    partnerUrl: "/#gallery",
  }));

  return <main className="public-profile-shell">
    <header className="profile-topbar"><a href="/#gallery" className="profile-back"><ArrowLeft size={16}/> Back to Gallery</a><a href="/" className="profile-wordmark">XGETAWAYS<span>X</span></a></header>
    <section className="profile-hero">
      <p className="eyebrow">APPROVED XGETAWAYSX PARTNER</p>
      <h1>{profile.name}</h1>
      <p className="profile-category">{profile.category.replace(/_/g, " ")}</p>
      {(profile.city || profile.province || profile.country) && <p className="profile-location"><MapPin size={16}/>{[profile.city, profile.province, profile.country].filter(Boolean).join(", ")}</p>}
      {profile.description && <p className="profile-description">{profile.description}</p>}
      {profile.website_url && <a className="profile-website" href={profile.website_url} target="_blank" rel="noreferrer"><Globe2 size={16}/> Visit partner website <ArrowUpRight size={15}/></a>}
    </section>
    <section className="profile-stories"><p className="eyebrow">THE STORIES BEHIND THE PICTURES</p><h2>Discover {profile.name}</h2>{stories.length ? <div className="gallery-partner-grid">{stories.map(story => <GalleryStoryCard key={story.storyId} {...story}/>)}</div> : <GalleryContentPlaceholder compact eyebrow="MORE TO DISCOVER" title="More stories are on the way." message="This partner’s Gallery collection is being prepared. Please check back soon." />}</section>
    <footer><span>© {new Date().getFullYear()} XGetawaySX</span><a href="/">Discover more getaways</a></footer>
  </main>;
}
