import { useRef, useState } from "react";
import { ArrowUpRight, BookOpen } from "lucide-react";

export type GalleryStoryCardProps = {
  storyId: string | number;
  imageUrl: string;
  imageAlt: string;
  title: string;
  partnerName: string;
  summary: string;
  partnerUrl: string;
};

export default function GalleryStoryCard({
  storyId,
  imageUrl,
  imageAlt,
  title,
  partnerName,
  summary,
  partnerUrl,
}: GalleryStoryCardProps) {
  const [storyVisible, setStoryVisible] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const summaryId = `gallery-story-${storyId}`;

  return (
    <article
      className="gallery-story-card"
      onMouseLeave={(event) => {
        if (!event.currentTarget.contains(document.activeElement)) {
          setStoryVisible(false);
        }
      }}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setStoryVisible(false);
        }
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape" && storyVisible) {
          event.preventDefault();
          setStoryVisible(false);
          triggerRef.current?.focus();
        }
      }}
    >
      <button
        ref={triggerRef}
        type="button"
        className="gallery-story-trigger"
        aria-expanded={storyVisible}
        aria-controls={summaryId}
        onClick={() => setStoryVisible(true)}
        onMouseEnter={() => setStoryVisible(true)}
        onFocus={() => setStoryVisible(true)}
      >
        <img src={imageUrl} alt={imageAlt} loading="lazy" />
        <span className="gallery-story-shade" aria-hidden="true" />
        <span className="gallery-story-heading">
          <span>{partnerName}</span>
          <strong>{title}</strong>
          <span className="gallery-story-hint">
            <BookOpen size={14} aria-hidden="true" />
            {storyVisible ? "Story revealed" : "Discover the story"}
          </span>
        </span>
      </button>

      <div
        className="gallery-story-summary"
        id={summaryId}
        role="region"
        aria-label={`Story behind ${title}`}
        hidden={!storyVisible}
      >
        <p>{summary}</p>
        <a href={partnerUrl}>
          Explore partner story <ArrowUpRight size={15} aria-hidden="true" />
        </a>
      </div>
    </article>
  );
}
