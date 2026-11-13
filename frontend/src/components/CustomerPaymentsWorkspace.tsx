import { useEffect, useState } from "react";
import { CreditCard, ReceiptText } from "lucide-react";
import "./finance.css";

type Partner={name:string};
type Reservation={id:number;partner:Partner;booking_reference:string|null;start_date:string;end_date:string;guests:number;status:string};
type Gateway="payfast"|"yoco";
type Payment={id:number;reservation:number;reservation_reference:string|null;partner_name:string;kind:string;status:string;amount:string;currency:string;provider:string;checkout_session_id:string;checkout_url:string;provider_reference:string|null;failure_reason:string;created_at:string;captured_at:string|null};
type CheckoutResponse={payment:Payment;provider:Gateway;checkout_url:string;form_fields:Record<string,string>|null};
const API=(import.meta as ImportMeta & {env:Record<string,string|undefined>}).env.VITE_API_BASE_URL??"";

export default function CustomerPaymentsWorkspace({accessToken}:{accessToken:string}){
 const headers={Authorization:`Bearer ${accessToken}`,"Content-Type":"application/json"};
 const [reservations,setReservations]=useState<Reservation[]>([]);
 const [payments,setPayments]=useState<Payment[]>([]);
 const [reservationId,setReservationId]=useState("");
 const [gateway,setGateway]=useState<Gateway>("payfast");
 const [busy,setBusy]=useState(false);
 const [busyPaymentId,setBusyPaymentId]=useState<number|null>(null);
 const [error,setError]=useState("");
 const [notice,setNotice]=useState("");

 async function load(){
  const [r,p]=await Promise.all([
   fetch(`${API}/api/v1/partners/reservations/`,{headers}),
   fetch(`${API}/api/v1/partners/payments/`,{headers}),
  ]);
  if(!r.ok||!p.ok)throw new Error("Could not load your reservations and payment records.");
  setReservations(await r.json());setPayments(await p.json());
 }
 useEffect(()=>{let live=true;load().catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[accessToken]);

 async function launchCheckout(paymentId:number,provider:Gateway){
  setBusyPaymentId(paymentId);setError("");setNotice("");
  try{
   const response=await fetch(`${API}/api/v1/partners/payments/${paymentId}/checkout/`,{
    method:"POST",headers,body:JSON.stringify({provider}),
   });
   const data=await response.json() as CheckoutResponse|{detail?:string};
   if(!response.ok)throw new Error("detail" in data?data.detail||"Could not start checkout.":"Could not start checkout.");
   const checkout=data as CheckoutResponse;
   setPayments(current=>current.map(p=>p.id===paymentId?checkout.payment:p));
   if(provider==="payfast"){
    const allowed=["https://sandbox.payfast.co.za/eng/process","https://www.payfast.co.za/eng/process"];
    if(!allowed.includes(checkout.checkout_url)||!checkout.form_fields)throw new Error("PayFast returned an invalid checkout form.");
    const form=document.createElement("form");form.method="POST";form.action=checkout.checkout_url;
    Object.entries(checkout.form_fields).forEach(([name,value])=>{
     const input=document.createElement("input");input.type="hidden";input.name=name;input.value=value;form.appendChild(input);
    });
    document.body.appendChild(form);form.submit();
    return;
   }
   const redirect=new URL(checkout.checkout_url);
   if(redirect.protocol!=="https:"||!(redirect.hostname==="yoco.com"||redirect.hostname.endsWith(".yoco.com")))throw new Error("Yoco returned an unexpected checkout destination.");
   window.location.assign(redirect.toString());
  }catch(e){setError(e instanceof Error?e.message:"Could not start checkout.");await load().catch(()=>{});}
  finally{setBusyPaymentId(null);}
 }

 async function startPayment(){
  setBusy(true);setError("");setNotice("");
  try{
   const response=await fetch(`${API}/api/v1/partners/payments/`,{
    method:"POST",headers,
    body:JSON.stringify({reservation_id:Number(reservationId),idempotency_key:crypto.randomUUID()}),
   });
   const data=await response.json();
   if(!response.ok)throw new Error(data.detail||JSON.stringify(data));
   setPayments(current=>[data,...current.filter(p=>p.id!==data.id)]);
   await launchCheckout(data.id,gateway);
  }catch(e){setError(e instanceof Error?e.message:"Could not create payment.");}
  finally{setBusy(false);}
 }

 return <section className="finance-workspace">
  <header><p className="eyebrow">YOUR ACCOUNT</p><h2>Payments & receipts</h2><p>Pay for confirmed reservations through PayFast or Yoco. XGetawaySX confirms payment only after a verified provider notification.</p></header>
  {error&&<p className="finance-feedback error" role="alert">{error}</p>}
  {notice&&<p className="finance-feedback" role="status">{notice}</p>}
  <div className="finance-panel">
   <h3><CreditCard size={18}/> Pay for a reservation</h3>
   <label>Confirmed reservation<select value={reservationId} onChange={e=>setReservationId(e.target.value)}>
    <option value="">Select a confirmed reservation</option>
    {reservations.filter(r=>r.status==="confirmed").map(r=><option key={r.id} value={r.id}>{r.partner.name} · {r.start_date} to {r.end_date} · {r.booking_reference||`Request #${r.id}`}</option>)}
   </select></label>
   <label>Payment provider<select value={gateway} onChange={e=>setGateway(e.target.value as Gateway)}>
    <option value="payfast">PayFast</option><option value="yoco">Yoco</option>
   </select></label>
   <button disabled={!reservationId||busy||busyPaymentId!==null} onClick={startPayment}>{busy?"Preparing checkout…":`Continue with ${gateway==="payfast"?"PayFast":"Yoco"}`}</button>
   <p className="finance-note">The payment amount is calculated by XGetawaySX from the confirmed reservation quote. Card details are entered only on the provider's hosted checkout page.</p>
  </div>
  <div className="finance-panel">
   <h3><ReceiptText size={18}/> Payment history</h3>
   {payments.length?payments.map(p=><article className="finance-row" key={p.id}>
    <div><strong>{p.partner_name}</strong><span className={`finance-status ${p.status}`}>{p.status}</span></div>
    <p>{p.kind} · {p.currency} {p.amount} · {p.created_at.slice(0,10)}</p>
    {p.reservation_reference&&<p>Booking: {p.reservation_reference}</p>}
    {p.provider_reference&&<p>Provider reference: {p.provider_reference}</p>}
    {p.failure_reason&&<p>{p.failure_reason}</p>}
    {p.status==="pending"&&<div className="finance-checkout-actions">
     {p.provider==="manual_reconciliation"?<>
      <button disabled={busyPaymentId!==null} onClick={()=>launchCheckout(p.id,"payfast")}>Pay with PayFast</button>
      <button disabled={busyPaymentId!==null} onClick={()=>launchCheckout(p.id,"yoco")}>Pay with Yoco</button>
     </>:<button disabled={busyPaymentId!==null} onClick={()=>launchCheckout(p.id,p.provider as Gateway)}>Continue with {p.provider}</button>}
    </div>}
   </article>):<p>No payment records yet.</p>}
  </div>
 </section>;
}
