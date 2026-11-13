import { useEffect, useState } from "react";
import { CreditCard, ReceiptText } from "lucide-react";
import "./finance.css";

type Partner={name:string};
type Reservation={id:number;partner:Partner;booking_reference:string|null;start_date:string;end_date:string;guests:number;status:string};
type Payment={id:number;reservation:number;reservation_reference:string|null;partner_name:string;kind:string;status:string;amount:string;currency:string;provider:string;provider_reference:string|null;failure_reason:string;created_at:string;captured_at:string|null};
const API=(import.meta as ImportMeta & {env:Record<string,string|undefined>}).env.VITE_API_BASE_URL??"";

export default function CustomerPaymentsWorkspace({accessToken}:{accessToken:string}){
 const headers={Authorization:`Bearer ${accessToken}`,"Content-Type":"application/json"};
 const [reservations,setReservations]=useState<Reservation[]>([]);const [payments,setPayments]=useState<Payment[]>([]);
 const [reservationId,setReservationId]=useState("");const [busy,setBusy]=useState(false);const [error,setError]=useState("");const [notice,setNotice]=useState("");
 async function load(){const [r,p]=await Promise.all([fetch(`${API}/api/v1/partners/reservations/`,{headers}),fetch(`${API}/api/v1/partners/payments/`,{headers})]);if(!r.ok||!p.ok)throw new Error("Could not load your reservations and payment records.");setReservations(await r.json());setPayments(await p.json());}
 useEffect(()=>{let live=true;load().catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[accessToken]);
 async function startPayment(){setBusy(true);setError("");setNotice("");try{const r=await fetch(`${API}/api/v1/partners/payments/`,{method:"POST",headers,body:JSON.stringify({reservation_id:Number(reservationId),idempotency_key:crypto.randomUUID()})});const data=await r.json();if(!r.ok)throw new Error(data.detail||JSON.stringify(data));setPayments(v=>[data,...v]);setNotice(`Payment record created for ${data.currency} ${data.amount}. It is pending external payment processing and verification; no money has been collected by XGetawaySX.`);}catch(e){setError(e instanceof Error?e.message:"Could not create payment record.");}finally{setBusy(false);}}
 return <section className="finance-workspace"><header><p className="eyebrow">YOUR ACCOUNT</p><h2>Payments & receipts</h2><p>View payment records for confirmed reservations. Payment records do not themselves collect money.</p></header>
 {error&&<p className="finance-feedback error" role="alert">{error}</p>}{notice&&<p className="finance-feedback" role="status">{notice}</p>}
 <div className="finance-panel"><h3><CreditCard size={18}/> Create a payment record</h3><label>Confirmed reservation<select value={reservationId} onChange={e=>setReservationId(e.target.value)}><option value="">Select a confirmed reservation</option>{reservations.filter(r=>r.status==="confirmed").map(r=><option key={r.id} value={r.id}>{r.partner.name} · {r.start_date} to {r.end_date} · {r.booking_reference||`Request #${r.id}`}</option>)}</select></label><button disabled={!reservationId||busy} onClick={startPayment}>{busy?"Creating…":"Prepare deposit / balance payment"}</button><p className="finance-note">The amount is calculated from the partner's published nightly prices and deposit policy. Payment requires an external provider integration or authorised reconciliation.</p></div>
 <div className="finance-panel"><h3><ReceiptText size={18}/> Payment history</h3>{payments.length?payments.map(p=><article className="finance-row" key={p.id}><div><strong>{p.partner_name}</strong><span className={`finance-status ${p.status}`}>{p.status}</span></div><p>{p.kind} · {p.currency} {p.amount} · {p.created_at.slice(0,10)}</p>{p.reservation_reference&&<p>Booking: {p.reservation_reference}</p>}{p.provider_reference&&<p>Provider reference: {p.provider_reference}</p>}{p.failure_reason&&<p>{p.failure_reason}</p>}</article>):<p>No payment records yet.</p>}</div>
 </section>;
}
