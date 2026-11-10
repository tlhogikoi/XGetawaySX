import { useState } from "react";
import { ArrowUpRight, BookOpen } from "lucide-react";

export type GalleryStoryCardProps = {
  imageUrl: string;
  imageAlt: string;
  title: string;
  partnerName: string;
  summary: string;
  partnerUrl: string;
};

export default function GalleryStoryCard({
  imageUrl,
  imageAlt,
  title,
  partnerName,
  summary,
  partnerUrl,
}: GalleryStoryCardProps) {
  const [storyVisible, setStoryVisible] = useState(false);

  return (
    <article className="gallery-story-card">
      <button
        type="button"
        className="gallery-story-trigger"
        aria-expanded={storyVisible}
        aria-controls={`story-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
        onClick={() => setStoryVisible((visible) => !visible)}
        onMouseEnter={() => setStoryVisible(true)}
        onMouseLeave={() => setStoryVisible(false)}
        onFocus={() => setStoryVisible(true)}
        onBlur={(event) => {
          if (!event.currentTarget.parentElement?.contains(event.relatedTarget as Node | null)) {
            setStoryVisible(false);
          }
        }}
      >
        <img src={imageUrl} alt={imageAlt} loading="lazy" />
        <span className="gallery-story-shade" />
        <span className="gallery-story-heading">
          <span>{partnerName}</span>
          <strong>{title}</strong>
          <span className="gallery-story-hint"><BookOpen size={14} /> {storyVisible ? "Story revealed" : "Discover the story"}</span>
        </span>
      </button>
      {storyVisible && (
        <div
          className="gallery-story-summary"
          id={`story-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
          role="region"
          aria-label={`Story behind ${title}`}
        >
          <p>{summary}</p>
          <a href={partnerUrl}>Explore partner story <ArrowUpRight size={15} /></a>
        </div>
      )}
      <button
        type="button"
        className="gallery-story-mobile-toggle"
        aria-expanded={storyVisible}
        onClick={() => setStoryVisible((visible) => !visible)}
      >
        {storyVisible ? "Hide story" : "Tap to read the story"}
      </button>
    </article>
  );
}
