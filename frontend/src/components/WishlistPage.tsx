import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Bookmark, BookmarkCheck, Compass, Heart, MapPin, Trash2 } from "lucide-react";
import "./wishlist-page.css";

const API = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";
type Partner = { id: number; name: string; slug: string; category: string; city: string; province: string; country: string; description: string };
type Destination = { name: string; slug: string; introduction: string; description: string; city: string; province: string; country: string; partners: Partner[] };
type Collection = { title: string; slug: string; summary: string; description: string; destination_slug: string | null; partners: Partner[] };
type TripPlan = { id: number; title: string; notes: string; start_date: string | null; end_date: string | null; items: unknown[] };
type SavedMeta = { _xgs_wishlist: 1; type: "destination" | "collection"; slug: string };

function savedMeta(plan: TripPlan): SavedMeta | null {
  try {
    const value = JSON.parse(plan.notes) as Partial<SavedMeta>;
    return value._xgs_wishlist === 1 && (value.type === "destination" || value.type === "collection") && typeof value.slug === "string"
      ? value as SavedMeta : null;
  } catch { return null; }
}

export default function WishlistPage({ accessToken }: { accessToken: string | null }) {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [plans, setPlans] = useState<TripPlan[]>([]);
  const [busyKey, setBusyKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const saved = useMemo(() => {
    const result = new Set<string>();
    plans.forEach(plan => {
      const meta = savedMeta(plan);
      if (meta) result.add(meta.type + ":" + meta.slug);
    });
    return result;
  }, [plans]);

  async function load() {
    setLoading(true); setError("");
    try {
      const [destinationResponse, collectionResponse] = await Promise.all([
        fetch(`${API}/api/v1/partners/destinations/`),
        fetch(`${API}/api/v1/partners/collections/`),
      ]);
      if (!destinationResponse.ok || !collectionResponse.ok) throw new Error("We could not load destination ideas right now.");
      const [destinationData, collectionData] = await Promise.all([destinationResponse.json(), collectionResponse.json()]);
      setDestinations(destinationData as Destination[]);
      setCollections(collectionData as Collection[]);
      if (accessToken) {
        const response = await fetch(`${API}/api/v1/partners/trips/`, { headers: { Authorization: `Bearer ${accessToken}` } });
        if (!response.ok) throw new Error("Your saved ideas could not be loaded. Please sign in again.");
        setPlans(await response.json() as TripPlan[]);
      } else setPlans([]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Something went wrong while loading your wishlist.");
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [accessToken]);

  async function toggle(type: SavedMeta["type"], slug: string, title: string) {
    if (!accessToken) { window.location.href = "/account/"; return; }
    const key = type + ":" + slug;
    setBusyKey(key); setError(""); setNotice("");
    try {
      const existing = plans.find(plan => {
        const meta = savedMeta(plan);
        return meta?.type === type && meta.slug === slug;
      });
      if (existing) {
        const response = await fetch(`${API}/api/v1/partners/trips/${existing.id}/`, {
          method: "DELETE", headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (!response.ok && response.status !== 204) throw new Error("This saved idea could not be removed.");
        setPlans(current => current.filter(plan => plan.id !== existing.id));
        setNotice("Removed from your wishlist.");
      } else {
        const meta: SavedMeta = { _xgs_wishlist: 1, type, slug };
        const response = await fetch(`${API}/api/v1/partners/trips/`, {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
          body: JSON.stringify({ title: `Wishlist · ${title}`.slice(0, 160), notes: JSON.stringify(meta) }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "This idea could not be saved.");
        setPlans(current => [data as TripPlan, ...current]);
        setNotice("Saved to your private wishlist.");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The wishlist could not be updated.");
    } finally { setBusyKey(""); }
  }

  const savedItems = plans.filter(plan => savedMeta(plan));
  return <main className="wishlist-shell">
    <header className="wishlist-nav"><a className="wishlist-brand" href="/"><span>X</span>GETAWAYS<span>X</span></a><nav><a href="/destinations/">Destinations</a><a href="/gallery/">Gallery</a><a href="/account/">My account</a></nav></header>
    <section className="wishlist-hero"><p className="wishlist-eyebrow"><Heart size={15}/> YOUR TRAVEL IDEAS</p><h1>Keep the places<br/><span>you love close.</span></h1><p>Save destination guides and curated experience collections while you decide where your next getaway will take you.</p><div className="wishlist-hero-meta"><span><Bookmark size={15}/> Private to your account</span><span><ShieldCheckIcon/> Manage saved ideas anytime</span></div></section>
    <section className="wishlist-content">
      {!accessToken && <div className="wishlist-signin"><div><strong>Your wishlist is waiting for you.</strong><p>Sign in to save destinations and collections privately to your account.</p></div><a href="/account/">Sign in <ArrowRight size={15}/></a></div>}
      {error && <p className="wishlist-message is-error" role="alert">{error}</p>}
      {notice && <p className="wishlist-message" role="status">{notice}</p>}
      <div className="wishlist-section-heading"><div><p className="wishlist-eyebrow">YOUR SHORTLIST</p><h2>Saved ideas</h2></div><span>{savedItems.length} saved</span></div>
      {savedItems.length ? <div className="wishlist-saved-list">{savedItems.map(plan => {
        const meta = savedMeta(plan)!;
        const destination = meta.type === "destination" ? destinations.find(item => item.slug === meta.slug) : undefined;
        const collection = meta.type === "collection" ? collections.find(item => item.slug === meta.slug) : undefined;
        const label = destination?.name || collection?.title || plan.title.replace("Wishlist · ","");
        const href = meta.type === "destination" ? `/destinations/${meta.slug}/` : `/collections/${meta.slug}/`;
        return <article key={plan.id}><div className="wishlist-saved-icon"><BookmarkCheck size={18}/></div><div className="wishlist-saved-copy"><span>{meta.type === "destination" ? "DESTINATION" : "EXPERIENCE COLLECTION"}</span><strong>{label}</strong><small>{destination?.introduction || collection?.summary || "This saved idea is not currently published."}</small></div><a href={href}>View <ArrowRight size={14}/></a><button aria-label={`Remove ${label} from wishlist`} disabled={busyKey === meta.type+":"+meta.slug} onClick={()=>void toggle(meta.type,meta.slug,label)}><Trash2 size={15}/></button></article>;
      })}</div> : <p className="wishlist-empty">Your saved destinations and collections will appear here.</p>}

      <div className="wishlist-section-heading"><div><p className="wishlist-eyebrow">EXPLORE & SAVE</p><h2>Destination guides</h2></div><a href="/destinations/">Browse all <ArrowRight size={15}/></a></div>
      {loading ? <p className="wishlist-empty">Loading published destination guides…</p> : <div className="wishlist-card-grid">{destinations.map(item => {
        const key = "destination:"+item.slug; const isSaved = saved.has(key);
        return <article className="wishlist-card" key={item.slug}><div className="wishlist-card-mark"><MapPin size={20}/><span>{[item.city,item.province].filter(Boolean).join(", ") || item.country}</span></div><p className="wishlist-eyebrow">DESTINATION GUIDE</p><h3>{item.name}</h3><p>{item.introduction || item.description || "Explore this destination and its local experiences."}</p><div className="wishlist-card-foot"><small>{item.partners.length} approved partner{item.partners.length===1?"":"s"}</small><button disabled={busyKey===key} aria-pressed={isSaved} onClick={()=>void toggle("destination",item.slug,item.name)}>{isSaved?<BookmarkCheck size={15}/>:<Bookmark size={15}/>} {isSaved?"Saved":"Save"}</button></div></article>;
      })}</div>}

      <div className="wishlist-section-heading"><div><p className="wishlist-eyebrow">CURATED FOR DISCOVERY</p><h2>Experience collections</h2></div></div>
      {loading ? <p className="wishlist-empty">Loading published collections…</p> : <div className="wishlist-card-grid">{collections.map(item => {
        const key = "collection:"+item.slug; const isSaved = saved.has(key);
        return <article className="wishlist-card" key={item.slug}><div className="wishlist-card-mark"><Compass size={20}/><span>{item.destination_slug ? "Destination collection" : "Curated collection"}</span></div><p className="wishlist-eyebrow">EXPERIENCE COLLECTION</p><h3>{item.title}</h3><p>{item.summary}</p><div className="wishlist-card-foot"><small>{item.partners.length} approved partner{item.partners.length===1?"":"s"}</small><button disabled={busyKey===key} aria-pressed={isSaved} onClick={()=>void toggle("collection",item.slug,item.title)}>{isSaved?<BookmarkCheck size={15}/>:<Bookmark size={15}/>} {isSaved?"Saved":"Save"}</button></div></article>;
      })}</div>}
    </section>
    <footer className="wishlist-footer"><a href="/">XGETAWAYS<span>X</span></a><span>TRAVEL THROUGH US.</span><a href="/privacy/">Privacy information</a></footer>
  </main>;
}

function ShieldCheckIcon() { return <span aria-hidden="true">✓</span>; }
