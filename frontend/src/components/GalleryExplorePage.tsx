import { ArrowLeft, ArrowRight } from "lucide-react";
import GalleryPartnerGrid from "./GalleryPartnerGrid";
import "./gallery.css";

export default function GalleryExplorePage() {
  return (
    <main className="gallery-explore-shell">
      <header className="profile-topbar">
        <a className="profile-back" href="/"><ArrowLeft size={16} /> Back to XGetawaySX</a>
        <a className="profile-wordmark" href="/" aria-label="XGetawaySX home"><span>X</span>GETAWAYS<span>X</span></a>
        <a className="profile-back" href="/account">Plan a getaway <ArrowRight size={16} /></a>
      </header>
      <section className="gallery-explore-hero">
        <p className="eyebrow">THE XGETAWAYSX GALLERY</p>
        <h1>Discover the places.<br /><span>Meet the stories.</span></h1>
        <p>Explore approved places and experiences through the stories shared by the people behind them. Every feature is reviewed before it appears here.</p>
      </section>
      <section className="gallery-explore-content" aria-labelledby="gallery-explore-heading">
        <p className="eyebrow">REAL PLACES. APPROVED STORIES.</p>
        <h2 id="gallery-explore-heading">Find your next inspiration.</h2>
        <GalleryPartnerGrid />
      </section>
      <footer className="gallery-explore-footer"><span>© {new Date().getFullYear()} XGetawaySX</span><strong>TRAVEL THROUGH US.</strong><a href="/account">Start planning</a></footer>
    </main>
  );
}
