import { useEffect, useMemo, useState } from "react";
import { ArrowRight, CalendarDays, MapPin, Plus, Send, Trash2 } from "lucide-react";
import "./trip-planner.css";

type Partner = { id: number; name: string; slug: string; category: string; city: string; province: string; country: string; description: string };
type TripItem = { id: number; partner: Partner; note: string };
type TripPlan = { id: number; title: string; notes: string; start_date: string | null; end_date: string | null; items: TripItem[] };
type Enquiry = { id: number; status: string; partner: Partner; requested_start_date: string | null; requested_end_date: string | null; partner_response: string; reservation_request_id: number | null };

const API_BASE = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";

export default function TripPlanner({ accessToken }: { accessToken: string }) {
  const [plans, setPlans] = useState<TripPlan[]>([]);
  const [partners, setPartners] = useState<Partner[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [selectedPartnerId, setSelectedPartnerId] = useState<number | null>(null);
  const [title, setTitle] = useState("My getaway");
  const [message, setMessage] = useState("");
  const [planNotes, setPlanNotes] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [enquiries, setEnquiries] = useState<Enquiry[]>([]);
  const [guestCount, setGuestCount] = useState(1);
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
    if (!selectedPlanId && data.length) { setSelectedPlanId(data[0].id); setStartDate(data[0].start_date || ""); setEndDate(data[0].end_date || ""); setPlanNotes(data[0].notes || ""); }
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
      if ((t as TripPlan[]).length) { const first = (t as TripPlan[])[0]; setSelectedPlanId(first.id); setStartDate(first.start_date || ""); setEndDate(first.end_date || ""); setPlanNotes(first.notes || ""); }
    }).catch(reason => { if (reason instanceof Error && reason.name !== "AbortError") setError(reason.message); });
    return () => controller.abort();
  }, [accessToken]);

  async function createPlan() {
    setBusy(true); setError(""); setNotice("");
    try {
      const plan = await request("trips/", { method: "POST", body: JSON.stringify({ title: title.trim() || "My getaway" }) }) as TripPlan;
      setPlans(current => [plan, ...current]); setSelectedPlanId(plan.id); setStartDate(""); setEndDate(""); setPlanNotes(""); setTitle("My getaway"); setNotice("Your private getaway plan has been created.");
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



  async function convertEnquiry(enquiryId: number) {
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await request(`enquiries/${enquiryId}/convert/`, {
        method: "POST", body: JSON.stringify({ guests: guestCount }),
      }) as { enquiry: Enquiry; reservation: { id: number } };
      setEnquiries(current => current.map(item => item.id === enquiryId ? result.enquiry : item));
      setNotice(`Reservation request #${result.reservation.id} created. The partner must still confirm it before payment is available.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create the reservation request.");
    } finally { setBusy(false); }
  }

  return <section className="trip-planner">
    <header className="trip-planner-heading"><div><p className="eyebrow">MAKE IT YOURS</p><h2>Build your getaway.</h2><p>Save approved places into a private plan, then contact each partner directly.</p></div><span className="trip-planner-mark"><MapPin size={22}/></span></header>
    {error && <p className="trip-feedback is-error" role="alert">{error}</p>}
    {notice && <p className="trip-feedback" role="status">{notice}</p>}
    <div className="trip-planner-layout">
      <div className="trip-plan-panel">
        <h3>Your getaway plans</h3>
        <div className="trip-create-row"><input value={title} onChange={e => setTitle(e.target.value)} aria-label="New getaway plan title" placeholder="Name your getaway"/><button disabled={busy} onClick={createPlan}><Plus size={15}/> New plan</button></div>
        <label className="trip-field"><span>Selected plan</span><select value={selectedPlanId ?? ""} onChange={e => { const id = Number(e.target.value) || null; const plan = plans.find(item => item.id === id); setSelectedPlanId(id); setStartDate(plan?.start_date || ""); setEndDate(plan?.end_date || ""); setPlanNotes(plan?.notes || ""); setSelectedPartnerId(null); }}><option value="">Choose a plan</option>{plans.map(plan => <option key={plan.id} value={plan.id}>{plan.title}</option>)}</select></label>
        {selectedPlan && <><div className="trip-date-grid"><label><span>Start date</span><input type="date" value={startDate || selectedPlan.start_date || ""} onChange={e => setStartDate(e.target.value)}/></label><label><span>End date</span><input type="date" value={endDate || selectedPlan.end_date || ""} onChange={e => setEndDate(e.target.value)}/></label></div>
          <label className="trip-field"><span>Private trip notes</span><textarea rows={3} maxLength={5000} value={planNotes} onChange={e=>setPlanNotes(e.target.value)} placeholder="Add your plans, group preferences, special occasions or things to remember."/></label>
          <div className="trip-plan-save-row"><span>{planNotes.length}/5000 characters</span><button className="trip-save-dates" disabled={busy || (!!startDate && !!endDate && endDate < startDate)} onClick={async()=>{setBusy(true);setError("");try{const updated=await request(`trips/${selectedPlan.id}/`,{method:"PATCH",body:JSON.stringify({start_date:startDate||null,end_date:endDate||null,notes:planNotes})}) as TripPlan;setPlans(current=>current.map(p=>p.id===updated.id?updated:p));setNotice("Your trip dates and notes have been saved.");}catch(e){setError(e instanceof Error?e.message:"Could not save trip details.");}finally{setBusy(false);}}}><CalendarDays size={15}/> Save trip details</button></div>
          <div className="trip-itinerary"><h4>Saved places <span>{selectedPlan.items.length}</span></h4>{selectedPlan.items.length ? selectedPlan.items.map(item=><div className="trip-itinerary-item" key={item.id}><div><strong>{item.partner.name}</strong><small>{[item.partner.city,item.partner.province].filter(Boolean).join(", ")}</small></div><button aria-label={`Remove ${item.partner.name}`} disabled={busy} onClick={()=>removeItem(item.id)}><Trash2 size={15}/></button></div>):<p className="trip-muted">Your itinerary is empty. Add an approved partner below.</p>}</div>
        </>}
      </div>
      <div className="trip-discovery-panel"><h3>Discover approved partners</h3><div className="trip-partner-list">{partners.map(partner=><article key={partner.id}><div><span>{partner.category.replace(/_/g," ")}</span><strong>{partner.name}</strong><small>{[partner.city,partner.province].filter(Boolean).join(", ")}</small></div><button disabled={busy || !selectedPlan || !!selectedPlan.items.some(i=>i.partner.slug===partner.slug)} onClick={()=>addPartner(partner.id)}><Plus size={15}/> Add</button></article>)}</div></div>
    </div>
    {selectedPlan?.items.length ? <div className="trip-enquiry-panel"><h3>Turn your plan into an enquiry</h3><p>Choose a saved partner and send your dates and requirements. This is an enquiry only; it does not confirm availability or create a booking.</p>
      <label className="trip-field"><span>Partner</span><select value={selectedPartnerId ?? ""} onChange={e=>setSelectedPartnerId(Number(e.target.value)||null)}><option value="">Choose a saved partner</option>{selectedPlan.items.map(item=><option key={item.partner.slug} value={item.partner.id}>{item.partner.name}</option>)}</select></label>
      <label className="trip-field"><span>Your enquiry</span><textarea rows={4} value={message} onChange={e=>setMessage(e.target.value)} placeholder="Tell the partner about your plans, group size and what you would like to know."/></label>
      <button className="trip-send-button" disabled={busy || !selectedPartner || message.trim().length<10} onClick={submitEnquiry}><Send size={15}/> Send enquiry <ArrowRight size={15}/></button>
    </div>:null}
    <div className="trip-enquiry-history">
      <h3>Enquiry tracking</h3>
      {enquiries.length ? <>
        <label className="trip-field"><span>Guests for accepted enquiries</span><input type="number" min="1" max="100" value={guestCount} onChange={e=>setGuestCount(Math.max(1,Math.min(100,Number(e.target.value)||1)))}/></label>
        {enquiries.map(item=><article key={item.id} className="trip-enquiry-record">
          <strong>{item.partner.name}</strong><span>{item.status.replace(/_/g," ")}</span>
          <small>{item.requested_start_date || "Dates not set"}{item.requested_end_date ? ` — ${item.requested_end_date}` : ""}</small>
          {item.partner_response && <p>{item.partner_response}</p>}
          {item.reservation_request_id
            ? <p className="trip-muted">Reservation request #{item.reservation_request_id} — awaiting partner confirmation</p>
            : item.status === "accepted"
              ? <button disabled={busy || !item.requested_start_date || !item.requested_end_date} onClick={()=>convertEnquiry(item.id)}>Continue to reservation request <ArrowRight size={15}/></button>
              : null}
        </article>)}
      </> : <p className="trip-muted">Your partner enquiries will appear here.</p>}
    </div>
  </section>;
}
