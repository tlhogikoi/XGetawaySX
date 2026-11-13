import { useEffect, useState } from "react";
import { ArrowUpRight, Compass, MapPin } from "lucide-react";
import "./destination-explorer.css";

type Partner = { name: string; slug: string; category: string; city: string; province: string; country: string; description: string };
type Collection = { title: string; slug: string; summary: string; description?: string; destination_slug?: string | null; partners?: Partner[] };
type Destination = { name: string; slug: string; introduction: string; description: string; city: string; province: string; country: string; partners: Partner[]; collections: Collection[] };

const API_BASE = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";

function PartnerLinks({ partners }: { partners: Partner[] }) {
  if (!partners.length) return <p className="destination-empty">More approved experiences are being prepared for this destination.</p>;
  return <div className="destination-partner-grid">{partners.map(partner => <article className="destination-partner-card" key={partner.slug}>
    <span>{partner.category.replace(/_/g, " ")}</span><h3>{partner.name}</h3>
    <p>{[partner.city, partner.province, partner.country].filter(Boolean).join(", ")}</p>
    {partner.description && <p className="destination-partner-description">{partner.description}</p>}
    <a href={`/partners/${encodeURIComponent(partner.slug)}/`}>Explore partner <ArrowUpRight size={15}/></a>
  </article>)}</div>;
}

export default function DestinationExplorer() {
  const slug = window.location.pathname.match(/^\/destinations\/([^/]+)\/?$/)?.[1];
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [destination, setDestination] = useState<Destination | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const endpoint = slug
      ? `${API_BASE}/api/v1/partners/destinations/${encodeURIComponent(slug)}/`
      : null;
    const requests = endpoint
      ? [fetch(endpoint, { signal: controller.signal }).then(async r => { if (!r.ok) throw new Error("This destination is not currently available."); return r.json(); })]
      : [
          fetch(`${API_BASE}/api/v1/partners/destinations/`, { signal: controller.signal }).then(async r => { if (!r.ok) throw new Error("Destination discovery is temporarily unavailable."); return r.json(); }),
          fetch(`${API_BASE}/api/v1/partners/collections/`, { signal: controller.signal }).then(async r => { if (!r.ok) throw new Error("Experience collections are temporarily unavailable."); return r.json(); }),
        ];
    setLoading(true); setError("");
    Promise.all(requests).then(results => {
      if (endpoint) setDestination(results[0] as Destination);
      else { setDestinations(results[0] as Destination[]); setCollections(results[1] as Collection[]); }
    }).catch(reason => { if (reason instanceof Error && reason.name !== "AbortError") setError(reason.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [slug]);

  return <main className="destination-shell">
    <header className="destination-topbar"><a className="destination-brand" href="/">XGETAWAYS<span>X</span></a><a href="/#partner-discovery">Discover partners <ArrowUpRight size={15}/></a></header>
    {loading ? <p className="destination-state" role="status">Preparing destinations and experiences…</p>
      : error ? <p className="destination-state" role="alert">{error}</p>
      : slug && destination ? <>
        <section className="destination-hero"><p className="eyebrow"><Compass size={15}/> DESTINATION GUIDE</p><h1>{destination.name}</h1>
          <p className="destination-location"><MapPin size={15}/>{[destination.city, destination.province, destination.country].filter(Boolean).join(", ")}</p>
          {destination.introduction && <h2>{destination.introduction}</h2>}
          {destination.description && <p>{destination.description}</p>}
        </section>
        <section className="destination-content"><div className="destination-section-heading"><p className="eyebrow">APPROVED PLACES & EXPERIENCES</p><h2>Explore this destination</h2></div><PartnerLinks partners={destination.partners || []}/>
          {!!destination.collections?.length && <div className="destination-collections"><h2>Curated experiences</h2>{destination.collections.map(item => <article key={item.slug}><h3>{item.title}</h3><p>{item.summary}</p><a href={`/collections/${encodeURIComponent(item.slug)}/`}>Explore collection <ArrowUpRight size={15}/></a></article>)}</div>}
        </section>
      </> : slug ? <p className="destination-state">This destination is not currently available.</p> : <>
        <section className="destination-index-hero"><p className="eyebrow">GO BEYOND THE USUAL</p><h1>Find your next destination.</h1><p>Explore curated places and approved local experiences across South Africa.</p></section>
        <section className="destination-content"><div className="destination-section-heading"><p className="eyebrow">PLACES TO DISCOVER</p><h2>Destination guides</h2></div>
          {destinations.length ? <div className="destination-grid">{destinations.map(item => <a className="destination-card" href={`/destinations/${encodeURIComponent(item.slug)}/`} key={item.slug}><span>{[item.province, item.country].filter(Boolean).join(" · ")}</span><h3>{item.name}</h3><p>{item.introduction || item.description}</p><strong>Explore destination <ArrowUpRight size={15}/></strong></a>)}</div> : <p className="destination-empty">Destination guides are being prepared. Check back soon.</p>}
          {!!collections.length && <div className="destination-collections"><div className="destination-section-heading"><p className="eyebrow">IDEAS FOR YOUR NEXT ESCAPE</p><h2>Experience collections</h2></div><div className="destination-grid">{collections.map(item => <a className="destination-card" href={`/collections/${encodeURIComponent(item.slug)}/`} key={item.slug}><span>CURATED COLLECTION</span><h3>{item.title}</h3><p>{item.summary}</p><strong>Explore collection <ArrowUpRight size={15}/></strong></a>)}</div></div>}
        </section>
      </>}
    <footer className="destination-footer"><span>© {new Date().getFullYear()} XGetawaySX</span><a href="/">Back to home</a></footer>
  </main>;
}
