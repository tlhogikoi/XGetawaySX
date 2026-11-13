import GalleryPartnerGrid from "./components/GalleryPartnerGrid";
import PublicPartnerProfile from "./components/PublicPartnerProfile";
import GalleryStoryEditor from "./components/GalleryStoryEditor";
import PartnerDiscovery from "./components/PartnerDiscovery";\nimport DestinationExplorer from "./components/DestinationExplorer";\nimport "./components/destination-explorer.css";
import { ArrowRight, Compass, Globe2, Heart, MapPin } from "lucide-react";

const categories = [
  "Romance & Couples", "Wellness & Rejuvenation", "Adventure & Exploration",
  "Family & Togetherness", "Heritage & Culture", "Business Class",
  "Friends & Social Getaways", "Luxury & Exclusive Escapes", "Road Trips & Discovery",
  "Seasonal & Holiday Specials", "Group Adventures & Shared Experiences",
  "Solo Travel & Self-Discovery",
];

export default function App() {
  if (window.location.pathname === "/partner/gallery" || window.location.pathname === "/partner/gallery/") return <GalleryStoryEditor />;
  const destinationMatch = window.location.pathname.match(/^\/destinations\/([^/]+)\/?$/);\n  if (destinationMatch || window.location.pathname === "/destinations" || window.location.pathname === "/destinations/") return <DestinationExplorer />;\n  const collectionMatch = window.location.pathname.match(/^\/collections\/([^/]+)\/?$/);\n  if (collectionMatch) return <DestinationExplorer />;\n  const partnerMatch = window.location.pathname.match(/^\/partners\/([^/]+)\/?$/);
  if (partnerMatch) return <PublicPartnerProfile slug={decodeURIComponent(partnerMatch[1])} />;

  return (
    <main className="site-shell">
      <header className="topbar">
        <a className="wordmark" href="/" aria-label="XGetawaySX home"><span className="wordmark-x">X</span>GETAWAYS<span className="wordmark-x">X</span></a>
        <nav aria-label="Main navigation"><a href="#about">About</a><a href="#trips">Trips</a><a href="#partner-discovery">Partners</a><a href="#destinations">Destinations</a><a href="#gallery">Gallery</a></nav>
        <a className="nav-cta" href="#discover">Explore getaways <ArrowRight size={16} /></a>
      </header>
      <section className="hero" id="discover">
        <div className="hero-glow" aria-hidden="true" />
        <p className="eyebrow"><Globe2 size={15} /> SOUTH AFRICA, OPEN TO DISCOVERY</p>
        <h1>Escape the ordinary.<br /><span>Experience more.</span></h1>
        <p className="hero-copy">Your next unforgettable getaway is closer than you think.</p>
        <div className="hero-actions"><a className="primary-button" href="#trips">Explore trips <ArrowRight size={17} /></a><a className="secondary-button" href="#about">Build your getaway</a></div>
        <div className="hero-foot"><span>TRAVEL THROUGH US.</span><span>DISCOVER. ESCAPE. EXPERIENCE.</span></div>
      </section>
      <section className="intro-section" id="about">
        <div><p className="eyebrow">A DIFFERENT WAY TO GET AWAY</p><h2>Find the place.<br />Make the story.</h2></div>
        <p className="intro-copy">Discover destinations, accommodation and experiences. Plan your own escape or let XGetawaySX help shape a getaway around what matters to you.</p>
      </section>
      <section className="category-section" id="trips">
        <div className="section-heading"><div><p className="eyebrow">FIND YOUR KIND OF ESCAPE</p><h2>Explore by experience</h2></div><a href="#discover">Discover the possibilities <ArrowRight size={16} /></a></div>
        <div className="category-grid">{categories.map((category,index)=><article className="category-card" key={category}><span className="category-number">{String(index+1).padStart(2,"0")}</span><h3>{category}</h3><ArrowRight className="category-arrow" size={18} /></article>)}</div>
      </section>
      <section className="feature-band" id="partners">
        <div className="feature-icon"><Compass size={26} /></div>
        <div><p className="eyebrow">FOR TOURISM BUSINESSES & FAMILY HOSTS</p><h2>Be part of the journey.</h2><p>Bring your place, service or experience to a growing travel community.</p></div>
        <a className="primary-button" href="mailto:partners@xgetawaysx.co.za">Partner with us <ArrowRight size={17} /></a>
      </section>
      <section className="partner-discovery-section" id="partner-discovery">
        <div className="partner-discovery-intro"><p className="eyebrow">FIND YOUR NEXT EXPERIENCE</p><h2>Discover approved partners.</h2><p>Search places and experiences by name, category or destination.</p></div>
        <PartnerDiscovery />
      </section>
      <section className="destination-home-section" id="destinations"><div><p className="eyebrow">EXPLORE SOUTH AFRICA</p><h2>Discover destinations and curated escapes.</h2><p>Find destination guides and handpicked experiences from approved local partners.</p></div><a className="primary-button" href="/destinations/">Explore destinations <ArrowRight size={17}/></a></section>\n      <section className="destination-home-section" id="destinations"><div><p className="eyebrow">EXPLORE SOUTH AFRICA</p><h2>Discover destinations and curated escapes.</h2><p>Find destination guides and handpicked experiences from approved local partners.</p></div><a className="primary-button" href="/destinations/">Explore destinations <ArrowRight size={17}/></a></section>\n      <section className="gallery-teaser" id="gallery">
        <div><p className="eyebrow">THE PEOPLE & PLACES BEHIND THE PICTURE</p><h2>Every picture tells a story.</h2><p>Discover the history and character behind our approved partner places and experiences.</p></div>
        <div className="gallery-mark"><Heart size={28} /><span>STORIES THAT<br />TAKE YOU PLACES</span><MapPin size={18} /></div>
      </section>
      <section className="gallery-live-preview" aria-label="Approved partner gallery"><GalleryPartnerGrid /></section>
      <footer><span>© {new Date().getFullYear()} XGetawaySX</span><strong>TRAVEL THROUGH US.</strong><span>Discover. Escape. Experience.</span></footer>
    </main>
  );
}
