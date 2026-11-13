import { useEffect, useMemo, useState } from "react";
import { ArrowRight, CalendarDays, MapPin, Plus, Send, Trash2 } from "lucide-react";
import "./trip-planner.css";

type Partner = { id: number; name: string; slug: string; category: string; city: string; province: string; country: string; description: string };
type TripItem = { id: number; partner: Partner; note: string };
type TripPlan = { id: number; title: string; notes: string; start_date: string | null; end_date: string | null; items: TripItem[] };
type Enquiry = { id: number; status: string; partner: Partner };

const API_BASE = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";

export default function TripPlanner({ accessToken }: { accessToken: string }) {
  const [plans, setPlans] = useState<TripPlan[]>([]);
  const [partners, setPartners] = useState<Partner[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [selectedPartnerId, setSelectedPartnerId] = useState<number | null>(null);
  const [title, setTitle] = useState("My getaway");
  const [message, setMessage] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [enquiries, setEnquiries] = useState<Enquiry[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const headers = useMemo(() => ({ Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" }), [accessToken]);
  const selectedPlan = plans.find(plan => plan.id === selectedPlanId) ?? null;
  const selectedPartner = partners.find(partner => partner.id === selectedPartnerId) ?? null;

  async function request(path: string, init: RequestInit = {}) {
    const response = await fetch(`${API_BASE}/api/v1/partners/${path}`, { ...init, headers: { ...headers } });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || body.message || "The request could not be completed.");
    }
    return response.status === 204 ? null : response.json();
  }

  async function refreshPlans() {
    const data = await request("trips/") as TripPlan[];
    setPlans(data);
    if (!selectedPlanId && data.length) setSelectedPlanId(data[0].id);
    return data;
  }

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetch(`${API_BASE}/api/v1/partners/?enquiry_ready=true`, { headers, signal: controller.signal }).then(async r => { if (!r.ok) throw new Error("Could not load approved partners."); return r.json(); }),
      fetch(`${API_BASE}/api/v1/partners/trips/`, { headers, signal: controller.signal }).then(async r => { if (!r.ok) throw new Error("Could not load your trip plans."); return r.json(); }),
      fetch(`${API_BASE}/api/v1/partners/enquiries/`, { headers, signal: controller.signal }).then(async r => { if (!r.ok) throw new Error("Could not load your enquiries."); return r.json(); }),
    ]).then(([p, t, e]) => {
      setPartners(p as Partner[]); setPlans(t as TripPlan[]); setEnquiries(e as Enquiry[]);
      if ((t as TripPlan[]).length) setSelectedPlanId((t as TripPlan[])[0].id);
    }).catch(reason => { if (reason instanceof Error && reason.name !== "AbortError") setError(reason.message); });
    return () => controller.abort();
  }, [accessToken]);

  async function createPlan() {
    setBusy(true); setError(""); setNotice("");
    try {
      const plan = await request("trips/", { method: "POST", body: JSON.stringify({ title: title.trim() || "My getaway" }) }) as TripPlan;
      setPlans(current => [plan, ...current]); setSelectedPlanId(plan.id); setTitle("My getaway"); setNotice("Your private getaway plan has been created.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not create plan."); }
    finally { setBusy(false); }
  }

  async function addPartner(partnerId: number) {
    if (!selectedPlan) { setError("Create or select a trip plan first."); return; }
    setBusy(true); setError(""); setNotice("");
    try {
      await request(`trips/${selectedPlan.id}/items/`, { method: "POST", body: JSON.stringify({ partner_id: partnerId }) });
      await refreshPlans(); setNotice("Partner added to your getaway plan.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not add partner."); }
    finally { setBusy(false); }
  }

  async function removeItem(itemId: number) {
    if (!selectedPlan) return;
    setBusy(true); setError("");
    try { await request(`trips/${selectedPlan.id}/items/${itemId}/`, { method: "DELETE" }); await refreshPlans(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not remove partner."); }
    finally { setBusy(false); }
  }

  async function submitEnquiry() {
    if (!selectedPlan || !selectedPartner || message.trim().length < 10) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const enquiry = await request("enquiries/", { method: "POST", body: JSON.stringify({
        partner_id: selectedPartner.id, trip_plan_id: selectedPlan.id, message: message.trim(),
        requested_start_date: startDate || selectedPlan.start_date,
        requested_end_date: endDate || selectedPlan.end_date,
      }) }) as Enquiry;
      setEnquiries(current => [enquiry, ...current]); setMessage(""); setNotice("Your enquiry has been sent to the partner. This is a request, not a confirmed booking.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not send enquiry."); }
    finally { setBusy(false); }
  }

  return <section className="trip-planner">
    <header className="trip-planner-heading"><div><p className="eyebrow">MAKE IT YOURS</p><h2>Build your getaway.</h2><p>Save approved places into a private plan, then contact each partner directly.</p></div><span className="trip-planner-mark"><MapPin size={22}/></span></header>
    {error && <p className="trip-feedback is-error" role="alert">{error}</p>}
    {notice && <p className="trip-feedback" role="status">{notice}</p>}
    <div className="trip-planner-layout">
      <div className="trip-plan-panel">
        <h3>Your getaway plans</h3>
        <div className="trip-create-row"><input value={title} onChange={e => setTitle(e.target.value)} aria-label="New getaway plan title" placeholder="Name your getaway"/><button disabled={busy} onClick={createPlan}><Plus size={15}/> New plan</button></div>
        <label className="trip-field"><span>Selected plan</span><select value={selectedPlanId ?? ""} onChange={e => setSelectedPlanId(Number(e.target.value) || null)}><option value="">Choose a plan</option>{plans.map(plan => <option key={plan.id} value={plan.id}>{plan.title}</option>)}</select></label>
        {selectedPlan && <><div className="trip-date-grid"><label><span>Start date</span><input type="date" value={startDate || selectedPlan.start_date || ""} onChange={e => setStartDate(e.target.value)}/></label><label><span>End date</span><input type="date" value={endDate || selectedPlan.end_date || ""} onChange={e => setEndDate(e.target.value)}/></label></div>
          <button className="trip-save-dates" disabled={busy} onClick={async()=>{setBusy(true);try{const updated=await request(`trips/${selectedPlan.id}/`,{method:"PATCH",body:JSON.stringify({start_date:startDate||selectedPlan.start_date,end_date:endDate||selectedPlan.end_date})}) as TripPlan;setPlans(current=>current.map(p=>p.id===updated.id?updated:p));setNotice("Trip dates saved.");}catch(e){setError(e instanceof Error?e.message:"Could not save dates.");}finally{setBusy(false);}}}><CalendarDays size={15}/> Save dates</button>
          <div className="trip-itinerary"><h4>Saved places <span>{selectedPlan.items.length}</span></h4>{selectedPlan.items.length ? selectedPlan.items.map(item=><div className="trip-itinerary-item" key={item.id}><div><strong>{item.partner.name}</strong><small>{[item.partner.city,item.partner.province].filter(Boolean).join(", ")}</small></div><button aria-label={`Remove ${item.partner.name}`} disabled={busy} onClick={()=>removeItem(item.id)}><Trash2 size={15}/></button></div>):<p className="trip-muted">Your itinerary is empty. Add an approved partner below.</p>}</div>
        </>}
      </div>
      <div className="trip-discovery-panel"><h3>Discover approved partners</h3><div className="trip-partner-list">{partners.map(partner=><article key={partner.id}><div><span>{partner.category.replace(/_/g," ")}</span><strong>{partner.name}</strong><small>{[partner.city,partner.province].filter(Boolean).join(", ")}</small></div><button disabled={busy || !selectedPlan || !!selectedPlan.items.some(i=>i.partner.slug===partner.slug)} onClick={()=>addPartner(partner.id)}><Plus size={15}/> Add</button></article>)}</div></div>
    </div>
    {selectedPlan?.items.length ? <div className="trip-enquiry-panel"><h3>Contact a partner</h3><p>Send a separate enquiry to each partner in your plan. They will respond directly through their partner workspace.</p>
      <label className="trip-field"><span>Partner</span><select value={selectedPartnerId ?? ""} onChange={e=>setSelectedPartnerId(Number(e.target.value)||null)}><option value="">Choose a saved partner</option>{selectedPlan.items.map(item=><option key={item.partner.slug} value={item.partner.id}>{item.partner.name}</option>)}</select></label>
      <label className="trip-field"><span>Your enquiry</span><textarea rows={4} value={message} onChange={e=>setMessage(e.target.value)} placeholder="Tell the partner about your plans, group size and what you would like to know."/></label>
      <button className="trip-send-button" disabled={busy || !selectedPartner || message.trim().length<10} onClick={submitEnquiry}><Send size={15}/> Send enquiry <ArrowRight size={15}/></button>
    </div>:null}
    <div className="trip-enquiry-history"><h3>Enquiry tracking</h3>{enquiries.length ? enquiries.map(item=><div key={item.id}><strong>{item.partner.name}</strong><span>{item.status.replace(/_/g," ")}</span></div>):<p className="trip-muted">Your partner enquiries will appear here.</p>}</div>
  </section>;
}
