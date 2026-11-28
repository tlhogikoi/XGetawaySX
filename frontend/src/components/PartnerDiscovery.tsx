import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, MapPin, Search, SlidersHorizontal } from "lucide-react";
import "./partner-discovery.css";

type Partner = {
  name: string; slug: string; category: string; description: string;
  city: string; province: string; country: string; website_url: string;
};

const API_BASE = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";
const categories = [
  ["", "All categories"], ["accommodation", "Accommodation"], ["family_home", "Family homes"],
  ["tour", "Tours"], ["activity", "Activities"], ["dining", "Dining"],
  ["wellness", "Wellness"], ["transport", "Transport"], ["destination", "Destinations"], ["other", "Other"],
];

export default function PartnerDiscovery() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [city, setCity] = useState("");
  const [province, setProvince] = useState("");
  const [partners, setPartners] = useState<Partner[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const params = useMemo(() => {
    const value = new URLSearchParams();
    if (query.trim()) value.set("q", query.trim());
    if (category) value.set("category", category);
    if (city.trim()) value.set("city", city.trim());
    if (province.trim()) value.set("province", province.trim());
    return value.toString();
  }, [query, category, city, province]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    fetch(`${API_BASE}/api/v1/partners/${params ? `?${params}` : ""}`, { signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error("Partner discovery is temporarily unavailable. Please try again.");
        return response.json() as Promise<Partner[]>;
      })
      .then(setPartners)
      .catch(reason => {
        if (reason instanceof Error && reason.name !== "AbortError") setError(reason.message);
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [params]);

  return <div className="partner-discovery">
    <div className="partner-discovery-filters" role="search" aria-label="Search approved partners">
      <label className="partner-filter partner-filter-search"><span>Search places and experiences</span><div><Search size={17}/><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Try a lodge, activity or destination" /></div></label>
      <label className="partner-filter"><span>Category</span><select value={category} onChange={event => setCategory(event.target.value)}>{categories.map(([value,label]) => <option value={value} key={value}>{label}</option>)}</select></label>
      <label className="partner-filter"><span>City</span><input value={city} onChange={event => setCity(event.target.value)} placeholder="e.g. Johannesburg" /></label>
      <label className="partner-filter"><span>Province</span><input value={province} onChange={event => setProvince(event.target.value)} placeholder="e.g. Gauteng" /></label>
      <button type="button" className="partner-filter-reset" onClick={() => { setQuery(""); setCategory(""); setCity(""); setProvince(""); }}><SlidersHorizontal size={15}/> Clear filters</button>
    </div>
    <div className="partner-discovery-results"><p className="partner-result-count" aria-live="polite">{loading ? "Finding approved partners…" : error ? "" : `${partners.length} approved ${partners.length === 1 ? "partner" : "partners"} found`}</p>
      {loading && <p className="partner-discovery-message" role="status">Searching approved places and experiences…</p>}
      {!loading && error && <p className="partner-discovery-message" role="alert">{error}</p>}
      {!loading && !error && partners.length === 0 && <div className="partner-discovery-message"><strong>No matching partners yet.</strong><p>Try a different search or clear one or more filters.</p></div>}
      {!loading && !error && partners.length > 0 && <div className="partner-discovery-grid">{partners.map(partner => <article className="partner-discovery-card" key={partner.slug}>
        <p className="partner-card-category">{partner.category.replace(/_/g, " ")}</p><h3>{partner.name}</h3>
        {(partner.city || partner.province || partner.country) && <p className="partner-card-location"><MapPin size={14}/>{[partner.city, partner.province, partner.country].filter(Boolean).join(", ")}</p>}
        {partner.description && <p className="partner-card-description">{partner.description}</p>}
        <a href={`/partners/${encodeURIComponent(partner.slug)}/`}>View partner and published stories <ArrowUpRight size={15}/></a>
      </article>)}</div>}
    </div>
  </div>;
}
