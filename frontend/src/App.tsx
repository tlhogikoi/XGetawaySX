import GalleryPartnerGrid from "./components/GalleryPartnerGrid";
import GalleryExplorePage from "./components/GalleryExplorePage";
import GalleryStoryDetailPage from "./components/GalleryStoryDetailPage";
import PublicPartnerProfile from "./components/PublicPartnerProfile";
import GalleryStoryEditor from "./components/GalleryStoryEditor";
import GalleryEditorialDashboard from "./components/GalleryEditorialDashboard";
import PartnerDiscovery from "./components/PartnerDiscovery";
import DestinationExplorer from "./components/DestinationExplorer";
import CustomerAccount from "./components/CustomerAccount";
import PartnerVerificationWorkspace from "./components/PartnerVerificationWorkspace";
import SitePages from "./components/SitePages";
import HelpPages from "./components/HelpPages";
import "./components/destination-explorer.css";
import { ArrowRight, Compass, Globe2, Heart, MapPin } from "lucide-react";

const categories = [
  "Romance & Couples", "Wellness & Rejuvenation", "Adventure & Exploration",
  "Family & Togetherness", "Heritage & Culture", "Business Class",
  "Friends & Social Getaways", "Luxury & Exclusive Escapes", "Road Trips & Discovery",
  "Seasonal & Holiday Specials", "Group Adventures & Shared Experiences",
  "Solo Travel & Self-Discovery",
];

export default function App() {
  const pathname = window.location.pathname;
  if (/^\/(about|services|trips|contact)\/?$/.test(pathname)) return <SitePages />;
  if (/^\/(faq|booking-process|cancellation-policy|privacy)\/?$/.test(pathname)) return <HelpPages />;
  if (pathname === "/gallery" || pathname === "/gallery/") return <GalleryExplorePage />;
  if (pathname === "/staff/gallery/editorial" || pathname === "/staff/gallery/editorial/") return <GalleryEditorialDashboard />;
  const galleryStoryMatch = pathname.match(/^\/gallery\/stories\/(\d+)\/?$/);
  if (galleryStoryMatch) return <GalleryStoryDetailPage storyId={galleryStoryMatch[1]} />;
  if (pathname === "/account" || pathname === "/account/") return <CustomerAccount />;
  if (pathname === "/partner/onboarding" || pathname === "/partner/onboarding/") return sessionStorage.getItem("xgs_access") ? <PartnerVerificationWorkspace accessToken={sessionStorage.getItem("xgs_access") || ""} /> : <main className="site-shell"><section className="intro-section"><div><p className="eyebrow">PARTNER CENTRE</p><h2>Sign in to continue</h2><p className="intro-copy">Please sign in to access your partner verification application.</p><a className="primary-button" href="/account">Go to account</a></div></section></main>;
  if (pathname === "/staff/partner/onboarding" || pathname === "/staff/partner/onboarding/") return sessionStorage.getItem("xgs_access") ? <PartnerVerificationWorkspace accessToken={sessionStorage.getItem("xgs_access") || ""} staffMode /> : <main className="site-shell"><section className="intro-section"><div><h2>Staff sign-in required</h2><a className="primary-button" href="/account">Go to account</a></div></section></main>;
  if (pathname === "/partner/gallery" || pathname === "/partner/gallery/") return <GalleryStoryEditor />;
  const destinationMatch = pathname.match(/^\/destinations\/([^/]+)\/?$/);
  if (destinationMatch || pathname === "/destinations" || pathname === "/destinations/") return <DestinationExplorer />;
  const collectionMatch = pathname.match(/^\/collections\/([^/]+)\/?$/);
  if (collectionMatch) return <DestinationExplorer />;
  const partnerMatch = pathname.match(/^\/partners\/([^/]+)\/?$/);
  if (partnerMatch) return <PublicPartnerProfile slug={decodeURIComponent(partnerMatch[1])} />;

  return (
    <main className="site-shell">
      <header className="topbar">
        <a className="wordmark" href="/" aria-label="XGetawaySX home"><span className="wordmark-x">X</span>GETAWAYS<span className="wordmark-x">X</span></a>
        <nav aria-label="Main navigation"><a href="/about/">About</a><a href="/trips/">Trips</a><a href="/services/">Services</a><a href="#partner-discovery">Partners</a><a href="#destinations">Destinations</a><a href="/gallery/">Gallery</a><a href="/contact/">Contact</a></nav>
        <a className="nav-cta" href="/account">My account <ArrowRight size={16} /></a>
      </header>
      <section className="hero" id="discover">
        <div className="hero-glow" aria-hidden="true" />
        <p className="eyebrow"><Globe2 size={15} /> SOUTH AFRICA, OPEN TO DISCOVERY</p>
        <h1>Escape the ordinary.<br /><span>Experience more.</span></h1>
        <p className="hero-copy">Your next unforgettable getaway is closer than you think.</p>
        <div className="hero-actions"><a className="primary-button" href="#trips">Explore trips <ArrowRight size={17} /></a><a className="secondary-button" href="/account">Plan your getaway</a></div>
        <div className="hero-foot"><span>TRAVEL THROUGH US.</span><span>DISCOVER. ESCAPE. EXPERIENCE.</span></div>
      </section>
      <section className="intro-section" id="about">
        <div><p className="eyebrow">A DIFFERENT WAY TO GET AWAY</p><h2>Find the place.<br />Make the story.</h2></div>
        <p className="intro-copy">Discover destinations, accommodation and experiences. Plan your own escape or let XGetawaySX help shape a getaway around what matters to you.</p>
      </section>
      <section className="category-section" id="trips">
        <div className="section-heading"><div><p className="eyebrow">FIND YOUR KIND OF ESCAPE</p><h2>Explore by experience</h2></div><a href="/account">Start planning <ArrowRight size={16} /></a></div>
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
      <section className="destination-home-section" id="destinations"><div><p className="eyebrow">EXPLORE SOUTH AFRICA</p><h2>Discover destinations and curated escapes.</h2><p>Find destination guides and handpicked experiences from approved local partners.</p></div><a className="primary-button" href="/destinations/">Explore destinations <ArrowRight size={17}/></a></section>
      <section className="gallery-teaser" id="gallery">
        <div><p className="eyebrow">THE PEOPLE & PLACES BEHIND THE PICTURE</p><h2>Every picture tells a story.</h2><p>Discover the history and character behind our approved partner places and experiences.</p></div>
        <div className="gallery-mark"><Heart size={28} /><span>STORIES THAT<br />TAKE YOU PLACES</span><MapPin size={18} /></div>
      </section>
      <section className="gallery-live-preview" aria-label="Approved partner gallery"><GalleryPartnerGrid /></section>
      <footer><span>© {new Date().getFullYear()} XGetawaySX</span><strong>TRAVEL THROUGH US.</strong><span>Discover. Escape. Experience.</span><a href="/account">Customer account</a></footer>
    </main>
  );
}
