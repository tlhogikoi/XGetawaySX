import { ArrowRight, Compass, Globe2, HeartHandshake, Mail, MapPin, ShieldCheck, Sparkles } from "lucide-react";
import "./site-pages.css";

type PageKey = "about" | "services" | "trips" | "contact";

const page = (): PageKey => {
  const segment = window.location.pathname.replace(/\/$/, "").split("/").pop();
  return segment === "about" || segment === "services" || segment === "trips" || segment === "contact" ? segment : "about";
};

const pageContent = {
  about: {
    eyebrow: "OUR STORY",
    title: "Travel should feel personal.",
    intro: "XGetawaySX is being built to make discovering places, planning escapes and connecting with local tourism businesses feel more considered and more human.",
  },
  services: {
    eyebrow: "HOW WE HELP",
    title: "One journey. More ways to experience it.",
    intro: "Explore independently, bring your own ideas or ask for help shaping a getaway. The platform is being developed around the needs of travellers and trusted local providers.",
  },
  trips: {
    eyebrow: "FIND YOUR NEXT ESCAPE",
    title: "A getaway that means something.",
    intro: "Explore the kinds of journeys XGetawaySX is designed to support. Organised departures and bookable offers will appear here only when their details have been confirmed.",
  },
  contact: {
    eyebrow: "LET'S CONNECT",
    title: "Your next conversation starts here.",
    intro: "Whether you are planning a getaway, operate a tourism business or want to learn more about the platform, choose the route that best describes your enquiry.",
  },
};

const serviceItems = [
  { icon: Compass, title: "Discover places & experiences", text: "Explore destinations, accommodation, activities and tourism services from participating providers." },
  { icon: Sparkles, title: "Plan a more personal escape", text: "Build ideas around your interests, travel style and preferences, with AI-assisted suggestions planned as a support tool—not a substitute for verified facts." },
  { icon: HeartHandshake, title: "Get human assistance", text: "A concierge pathway is planned for travellers who would rather discuss their needs with a person when assistance is available." },
  { icon: ShieldCheck, title: "Travel with clearer information", text: "Provider details, terms, availability and payment steps should be clear before a traveller commits to a booking." },
];

const tripTypes = [
  ["01", "Romance & couples", "Thoughtful breaks for two, from quiet retreats to shared adventures."],
  ["02", "Family & togetherness", "Time away designed around family moments and different ages."],
  ["03", "Wellness & rejuvenation", "Space to slow down, recharge and focus on wellbeing."],
  ["04", "Adventure & exploration", "Outdoor experiences, road trips and new places to discover."],
  ["05", "Heritage & culture", "Get closer to local stories, traditions, food and cultural experiences."],
  ["06", "Business Class", "Leisure-first social getaways with room to connect and network."],
  ["07", "Friends & group escapes", "Shared experiences for friends, communities and organised groups."],
  ["08", "Luxury & exclusive escapes", "Special-occasion stays and elevated experiences."],
  ["09", "Seasonal & holiday specials", "Getaway inspiration for changing seasons and holiday periods."],
  ["10", "Solo travel & self-discovery", "Make room for independence, reflection and discovery."],
  ["11", "Family homes & smart stays", "Discover home-style stays and accommodation suited to your trip."],
  ["12", "Road trips & discovery", "Flexible journeys that make the route part of the experience."],
];

function Shell({ children }: { children: React.ReactNode }) {
  return <main className="site-pages">
    <header className="site-pages-nav">
      <a className="site-pages-brand" href="/" aria-label="XGetawaySX home"><span>X</span>GETAWAYS<span>X</span></a>
      <nav aria-label="Main navigation">
        <a href="/about/">About</a><a href="/services/">Services</a><a href="/trips/">Trips</a><a href="/destinations/">Destinations</a><a href="/gallery/">Gallery</a>
      </nav>
      <a className="site-pages-account" href="/account/">My account <ArrowRight size={15}/></a>
    </header>
    {children}
    <footer className="site-pages-footer"><a href="/">XGETAWAYS<span>X</span></a><span>TRAVEL THROUGH US.</span><div><a href="/about/">About</a><a href="/services/">Services</a><a href="/trips/">Trips</a><a href="/contact/">Contact</a></div><small>© {new Date().getFullYear()} XGetawaySX. Discover. Escape. Experience.</small></footer>
  </main>;
}

function PageHero({ current }: { current: PageKey }) {
  const item = pageContent[current];
  return <section className="site-pages-hero">
    <p className="site-pages-eyebrow"><Globe2 size={15}/>{item.eyebrow}</p>
    <h1>{item.title}</h1>
    <p>{item.intro}</p>
    <div className="site-pages-hero-actions"><a className="site-pages-primary" href={current === "trips" ? "/destinations/" : "/account/"}>{current === "trips" ? "Explore destinations" : "Start planning"} <ArrowRight size={16}/></a><a className="site-pages-secondary" href="/contact/">Talk to us</a></div>
  </section>;
}

function AboutPage() {
  return <><section className="site-pages-split"><div><p className="site-pages-eyebrow">THE IDEA</p><h2>More than a place to stay.</h2></div><div><p>XGetawaySX brings travel discovery, local experiences and managed getaway planning into one evolving platform. The goal is to help travellers find options that fit the reason they want to get away—not simply browse a list of places.</p><p>We are starting in South Africa, with an ambition to grow thoughtfully into international travel as the platform, provider network and operating processes mature.</p></div></section>
  <section className="site-pages-values"><article><span>01 / DISCOVER</span><h3>Explore with curiosity.</h3><p>Find destinations and experiences through useful guides and participating providers.</p></article><article><span>02 / CONNECT</span><h3>Keep people at the centre.</h3><p>Support direct provider relationships and human help where the service is available.</p></article><article><span>03 / EXPERIENCE</span><h3>Make the journey count.</h3><p>Build getaways around shared moments, culture, rest, adventure and discovery.</p></article></section>
  <section className="site-pages-note"><MapPin size={22}/><div><h2>Starting locally. Thinking globally.</h2><p>Our first operating focus is South Africa. International expansion will follow only as provider coverage, support and booking operations are ready.</p></div></section></>;
}

function ServicesPage() {
  return <><section className="site-pages-intro"><p className="site-pages-eyebrow">TRAVELLER SERVICES</p><h2>Choose how you want to travel.</h2><p>Use the platform to explore independently or request help with planning. Specific services depend on provider participation and operational availability.</p></section><section className="site-pages-service-grid">{serviceItems.map(({icon: Icon,title,text})=><article key={title}><div><Icon size={23}/></div><h3>{title}</h3><p>{text}</p></article>)}</section><section className="site-pages-partner-callout"><div><p className="site-pages-eyebrow">FOR ACCOMMODATION & TOURISM PROVIDERS</p><h2>Put your experience on the map.</h2><p>Partner onboarding is designed for accommodation providers, family hosts, guides, activity operators, transport and other tourism businesses. Verification and approval are required before public promotion.</p></div><a className="site-pages-primary" href="/partner/onboarding/">Partner with XGetawaySX <ArrowRight size={16}/></a></section></>;
}

function TripsPage() {
  return <><section className="site-pages-intro"><p className="site-pages-eyebrow">12 WAYS TO GET AWAY</p><h2>Find the escape that fits your moment.</h2><p>These are experience categories, not currently available departures. Confirmed trips, dates, inclusions, prices and booking terms will be published when verified.</p></section><section className="site-pages-trip-grid">{tripTypes.map(([number,title,text])=><article key={number}><span>{number}</span><h3>{title}</h3><p>{text}</p><a href="/account/">Plan around this <ArrowRight size={15}/></a></article>)}</section><section className="site-pages-note"><ShieldCheck size={22}/><div><h2>Clear details before you book.</h2><p>When an organised trip or provider offer is published, its dates, inclusions, price, availability, cancellation terms and payment schedule should be shown before acceptance. No live departure is being advertised on this page.</p></div></section></>;
}

function ContactPage() {
  return <><section className="site-pages-contact-grid"><article><div><Compass size={23}/></div><p className="site-pages-eyebrow">TRAVELLER ENQUIRIES</p><h2>Planning a getaway?</h2><p>Start with an account to keep your trip ideas and enquiries together as the platform develops.</p><a className="site-pages-primary" href="/account/">Go to customer account <ArrowRight size={16}/></a></article><article><div><HeartHandshake size={23}/></div><p className="site-pages-eyebrow">PARTNER ENQUIRIES</p><h2>Work with us.</h2><p>Tourism businesses and family hosts can begin through the partner onboarding pathway. Submissions are subject to verification and review.</p><a className="site-pages-primary" href="/partner/onboarding/">Partner onboarding <ArrowRight size={16}/></a></article><article><div><Mail size={23}/></div><p className="site-pages-eyebrow">GENERAL ENQUIRIES</p><h2>Have a question?</h2><p>For general questions, use the customer account pathway or partner onboarding route so your enquiry reaches the appropriate workflow.</p><a className="site-pages-text-link" href="/">Return to the home page <ArrowRight size={15}/></a></article></section><p className="site-pages-contact-footnote">A dedicated contact inbox and live concierge channel will be added after the relevant service details have been confirmed.</p></>;
}

export default function SitePages() {
  const current = page();
  return <Shell><PageHero current={current}/><div className="site-pages-content">{current === "about" ? <AboutPage/> : current === "services" ? <ServicesPage/> : current === "trips" ? <TripsPage/> : <ContactPage/>}</div></Shell>;
}
