import GalleryStoryCard, { type GalleryStoryCardProps } from "./GalleryStoryCard";
import "./gallery.css";

type GalleryPartnerGridProps = {
  stories: GalleryStoryCardProps[];
};

export default function GalleryPartnerGrid({ stories }: GalleryPartnerGridProps) {
  if (stories.length === 0) {
    return (
      <div className="gallery-empty-state">
        <p className="eyebrow">APPROVED PARTNER STORIES</p>
        <h2>Stories worth discovering.</h2>
        <p>Partner stories will appear here after the business, image rights and story have been approved by the owner and XGetawaySX editorial team.</p>
      </div>
    );
  }

  return (
    <div className="gallery-partner-grid">
      {stories.map((story) => <GalleryStoryCard key={story.storyId} {...story} />)}
    </div>
  );
}
