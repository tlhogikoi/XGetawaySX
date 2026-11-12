import { ImagePlus } from "lucide-react";
import "./gallery.css";

type Props = {
  eyebrow: string;
  title: string;
  message: string;
  compact?: boolean;
};

export default function GalleryContentPlaceholder({ eyebrow, title, message, compact = false }: Props) {
  return (
    <section className={`gallery-content-placeholder${compact ? " gallery-content-placeholder--compact" : ""}`} aria-label={title}>
      <span className="gallery-content-placeholder__icon" aria-hidden="true"><ImagePlus size={compact ? 20 : 24} /></span>
      <p className="eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}
