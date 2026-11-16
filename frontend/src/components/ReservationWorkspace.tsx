import { useEffect, useState } from "react";
import { CalendarCheck, ClipboardList, Send, Ban } from "lucide-react";
import "./reservation.css";

type Partner = { id: number; name: string; city: string; province: string };
type Reservation = { id: number; partner: Partner; start_date: string; end_date: string; guests: number; status: string; booking_reference: string | null; partner_response: string };
type Cancellation = { id: number; reservation_id: number; partner_name: string; reason: string; status: string; decision_note: string; requested_at: string };
type Notice = { id:number; title:string; message:string; event:string; read_at:string|null; created_at:string };
type Availability = { date: string; available_guests: number; price_per_guest: string | null; currency: string };
const API = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";

export default function ReservationWorkspace({ accessToken }: { accessToken: string }) {
  const headers = { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" };
  const [partners,setPartners]=useState<Partner[]>([]);
  const [items,setItems]=useState<Reservation[]>([]);
  const [cancellations,setCancellations]=useState<Cancellation[]>([]);
  const [notifications,setNotifications]=useState<Notice[]>([]);
  const [reasons,setReasons]=useState<Record<number,string>>({});
  const [partnerId,setPartnerId]=useState("");
  const [start,setStart]=useState("");
  const [end,setEnd]=useState("");
  const [guests,setGuests]=useState(2);
  const [message,setMessage]=useState("");
  const [availability,setAvailability]=useState<Availability[]>([]);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  async function load(){
    const [p,r,c,n]=await Promise.all([
      fetch(`${API}/api/v1/partners/?booking_ready=true`),
      fetch(`${API}/api/v1/partners/reservations/`,{headers}),
      fetch(`${API}/api/v1/partners/reservations/cancellations/`,{headers}),
      fetch(`${API}/api/v1/partners/notifications/`,{headers})
    ]);
    if(!p.ok||!r.ok||!c.ok||!n.ok)throw new Error("Could not load booking information.");
    setPartners(await p.json());setItems(await r.json());setCancellations(await c.json());setNotifications(await n.json());
  }
  useEffect(()=>{let live=true;load().catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[accessToken]);
  async function check(){setError("");setNotice("");setAvailability([]);if(!partnerId||!start||!end){setError("Choose a partner and both dates first.");return;}const r=await fetch(`${API}/api/v1/partners/availability/?partner_id=${partnerId}&start_date=${start}&end_date=${end}`);const data=await r.json();if(!r.ok){setError(data.detail||"Could not check availability.");return;}setAvailability(data);if(!data.length)setNotice("No published availability was found for this date range.");}
  async function submit(){setBusy(true);setError("");setNotice("");try{const r=await fetch(`${API}/api/v1/partners/reservations/`,{method:"POST",headers,body:JSON.stringify({partner_id:Number(partnerId),start_date:start,end_date:end,guests,message})});const data=await r.json();if(!r.ok)throw new Error(data.detail||JSON.stringify(data));setItems(v=>[data,...v]);setNotice("Reservation request sent. It is not confirmed until the partner accepts it.");setMessage("");}catch(e){setError(e instanceof Error?e.message:"Could not submit request.");}finally{setBusy(false);}}
  async function markRead(id:number){
    const r=await fetch(`${API}/api/v1/partners/notifications/${id}/read/`,{method:"POST",headers});
    const data=await r.json();if(r.ok)setNotifications(v=>v.map(n=>n.id===id?data:n));
  }
  async function cancel(id:number){
    setError("");setNotice("");
    const reservation=items.find(x=>x.id===id);
    const reason=reasons[id]?.trim()||"";
    if(reservation?.status==="confirmed"&&reason.length<10){setError("Please provide a cancellation reason of at least ten characters.");return;}
    const r=await fetch(`${API}/api/v1/partners/reservations/${id}/cancel/`,{method:"POST",headers,body:JSON.stringify({reason})});
    const data=await r.json();if(!r.ok){setError(data.detail||"Could not submit cancellation.");return;}
    if(typeof data.reservation_id==="number"){
      setCancellations(v=>[data,...v.filter(x=>x.id!==data.id)]);
      setNotice("Cancellation request submitted. The partner must review it; captured payments require confirmed refunds before cancellation is completed.");
    }else{
      setItems(v=>v.map(x=>x.id===id?data:x));setNotice("Reservation request withdrawn.");
    }
  }
  return <section className="reservation-workspace"><header><p className="eyebrow">YOUR GETAWAY</p><h2>Reservation requests</h2><p>Check partner-published availability, request your dates and manage cancellation requests.</p></header>
    {error&&<p className="reservation-feedback error" role="alert">{error}</p>}{notice&&<p className="reservation-feedback" role="status">{notice}</p>}
    <div className="reservation-form"><h3><CalendarCheck size={18}/> Request a stay or experience</h3>
      <label>Partner<select value={partnerId} onChange={e=>{setPartnerId(e.target.value);setAvailability([]);}}><option value="">Choose a partner</option>{partners.map(p=><option key={p.id} value={p.id}>{p.name} — {[p.city,p.province].filter(Boolean).join(", ")}</option>)}</select></label>
      <div className="reservation-fields"><label>Check-in / start<input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label><label>Check-out / end (exclusive)<input type="date" value={end} onChange={e=>setEnd(e.target.value)}/></label><label>Guests<input type="number" min="1" max="100" value={guests} onChange={e=>setGuests(Number(e.target.value))}/></label></div>
      <button className="reservation-secondary" onClick={check}>Check availability</button>
      {availability.length>0&&<div className="availability-list"><strong>Published availability</strong>{availability.map(d=><span key={d.date}>{d.date}: {d.available_guests} guests available {d.price_per_guest?(`· ${d.currency} ${d.price_per_guest} per guest`):""}</span>)}</div>}
      <label>Message to partner<textarea rows={3} value={message} onChange={e=>setMessage(e.target.value)} placeholder="Add any requests or details for the partner."/></label>
      <button disabled={busy||!partnerId||!start||!end||guests<1} onClick={submit}><Send size={15}/> Send reservation request</button>
    </div>
    <div className="reservation-history"><h3>Notifications</h3>{notifications.length?notifications.map(n=><article key={n.id}><div><strong>{n.title}</strong><span className={`reservation-status ${n.read_at?"":"confirmed"}`}>{n.read_at?"read":"new"}</span></div><p>{n.message}</p>{!n.read_at&&<button className="reservation-secondary" onClick={()=>markRead(n.id)}>Mark as read</button>}</article>):<p>No notifications yet.</p>}</div>
    <div className="reservation-history"><h3><ClipboardList size={18}/> Your reservation history</h3>{items.length?items.map(item=>{
      const cancellation=cancellations.find(x=>x.reservation_id===item.id&&["pending","approved"].includes(x.status));
      return <article key={item.id}><div><strong>{item.partner.name}</strong><span className={`reservation-status ${item.status}`}>{item.status}</span></div><p>{item.start_date} to {item.end_date} · {item.guests} guests</p>{item.booking_reference&&<p>Booking reference: <strong>{item.booking_reference}</strong></p>}{item.partner_response&&<p>{item.partner_response}</p>}
      {cancellation&&<div className="availability-list"><strong>Cancellation: {cancellation.status.replace("_"," ")}</strong><span>{cancellation.decision_note||"Awaiting partner review or refund completion."}</span></div>}
      {["pending","confirmed"].includes(item.status)&&!cancellation&&<><label>Cancellation reason<textarea rows={2} value={reasons[item.id]||""} onChange={e=>setReasons(v=>({...v,[item.id]:e.target.value}))} placeholder="Explain why you need to cancel (10 characters minimum for confirmed bookings)."/></label><button className="reservation-secondary" onClick={()=>cancel(item.id)}><Ban size={15}/> {item.status==="confirmed"?"Request cancellation":"Withdraw request"}</button></>}
      </article>;
    }):<p>No reservation requests yet.</p>}</div>
  </section>;
}
