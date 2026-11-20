import { useEffect, useState } from "react";
import { Check, MessageSquare, X } from "lucide-react";
import "./trip-planner.css";

type Enquiry = { id: number; partner: { name: string }; customer_email: string; message: string; requested_start_date: string | null; requested_end_date: string | null; status: string; partner_response: string };
const API_BASE = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";

export default function PartnerEnquiryDashboard({ accessToken }: { accessToken: string }) {
  const [items,setItems]=useState<Enquiry[]>([]);
  const [responses,setResponses]=useState<Record<number,string>>({});
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  async function load(){
    const r=await fetch(`${API_BASE}/api/v1/partners/partner/enquiries/`,{headers:{Authorization:`Bearer ${accessToken}`}});
    if(!r.ok) throw new Error("Could not load partner enquiries.");
    setItems(await r.json());
  }
  useEffect(()=>{let active=true;load().catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[accessToken]);
  async function respond(id:number,status:"accepted"|"declined"){
    const text=responses[id]?.trim()||"";
    if(text.length<5){setError("Please enter a response of at least five characters.");return;}
    setError("");setNotice("");
    const r=await fetch(`${API_BASE}/api/v1/partners/partner/enquiries/${id}/respond/`,{method:"POST",headers:{Authorization:`Bearer ${accessToken}`,"Content-Type":"application/json"},body:JSON.stringify({status,partner_response:text})});
    if(!r.ok){setError("Your response could not be saved.");return;}
    const updated=await r.json();setItems(current=>current.map(item=>item.id===id?updated:item));setNotice("Enquiry response recorded.");
  }
  if(loading)return <section className="trip-planner"><p>Loading enquiries…</p></section>;
  return <section className="trip-planner"><header className="trip-planner-heading"><div><p className="eyebrow">PARTNER WORKSPACE</p><h2>Customer enquiries</h2><p>Review customer requests and respond to each enquiry.</p></div><MessageSquare size={24}/></header>
    {error&&<p className="trip-feedback is-error" role="alert">{error}</p>}{notice&&<p className="trip-feedback" role="status">{notice}</p>}
    {items.length===0?<p className="trip-muted">No enquiries have been received yet.</p>:items.map(item=><article className="partner-enquiry-card" key={item.id}><div className="partner-enquiry-meta"><strong>{item.partner.name}</strong><span>{item.status}</span></div><p className="partner-enquiry-customer">{item.customer_email} · {[item.requested_start_date,item.requested_end_date].filter(Boolean).join(" to ")||"Dates not specified"}</p><p>{item.message}</p>{item.status==="pending"?<><textarea rows={3} value={responses[item.id]||""} onChange={e=>setResponses(current=>({...current,[item.id]:e.target.value}))} placeholder="Write a response for the customer…"/><div className="partner-enquiry-actions"><button onClick={()=>respond(item.id,"accepted")}><Check size={15}/> Accept enquiry</button><button onClick={()=>respond(item.id,"declined")}><X size={15}/> Decline enquiry</button></div></>:<p className="partner-enquiry-response">Your response: {item.partner_response}</p>}</article>)}
  </section>;
}
