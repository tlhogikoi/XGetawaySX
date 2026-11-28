import { useEffect, useState } from "react";
import { FileText, Plus, Send } from "lucide-react";
import "./partner-quotes.css";

const API=(import.meta as ImportMeta & {env:Record<string,string|undefined>}).env.VITE_API_BASE_URL??"";
type Line={description:string;quantity:string;unit_price:string};
type Reservation={id:number;partner:{name:string};customer_email:string;start_date:string;end_date:string;guests:number;status:string;latest_quote:unknown};
const emptyLine=():Line=>({description:"Accommodation / experience",quantity:"1",unit_price:""});
export default function PartnerQuoteWorkspace({accessToken}:{accessToken:string}){
 const headers={Authorization:`Bearer ${accessToken}`,"Content-Type":"application/json"};
 const [items,setItems]=useState<Reservation[]>([]);
 const [lines,setLines]=useState<Record<number,Line[]>>({});
 const [deposits,setDeposits]=useState<Record<number,string>>({});
 const [expiries,setExpiries]=useState<Record<number,string>>({});
 const [terms,setTerms]=useState<Record<number,string>>({});
 const [responses,setResponses]=useState<Record<number,string>>({});
 const [busy,setBusy]=useState<number|null>(null);
 const [error,setError]=useState("");
 const [notice,setNotice]=useState("");
 async function load(){
  const r=await fetch(`${API}/api/v1/partners/partner/reservations/`,{headers});
  if(!r.ok)throw new Error("Could not load partner reservation requests.");
  setItems(await r.json());
 }
 useEffect(()=>{let live=true;load().catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[accessToken]);
 function updateLine(id:number,index:number,key:keyof Line,value:string){
  setLines(v=>({...v,[id]:(v[id]??[emptyLine()]).map((line,i)=>i===index?{...line,[key]:value}:line)}));
 }
 async function decideReservation(id:number,decision:"confirmed"|"declined"){
  setBusy(id);setError("");setNotice("");
  try{
   const responseText=(responses[id]||"").trim();
   if(responseText.length<5)throw new Error("Add a partner response of at least five characters.");
   const r=await fetch(`${API}/api/v1/partners/partner/reservations/${id}/decision/`,{
    method:"POST",headers,body:JSON.stringify({status:decision,partner_response:responseText}),
   });
   const data=await r.json();if(!r.ok)throw new Error(data.detail||"Could not update reservation.");
   setNotice(decision==="confirmed"?"Reservation confirmed. The customer can now proceed to payment.":"Reservation request declined.");
   await load();
  }catch(e){setError(e instanceof Error?e.message:"Could not update reservation.");}
  finally{setBusy(null);}
 }
 async function issueQuote(id:number){
  setBusy(id);setError("");setNotice("");
  try{
   const expiry=expiries[id]||"";
   if(!expiry)throw new Error("Choose a quotation expiry date and time.");
   const payload={
    currency:"ZAR",
    items:(lines[id]??[emptyLine()]).map(line=>({...line,quantity:Number(line.quantity),unit_price:Number(line.unit_price)})),
    deposit_amount:Number(deposits[id]||"0"),
    terms:terms[id]||"",
    expires_at:new Date(expiry).toISOString(),
   };
   const r=await fetch(`${API}/api/v1/partners/partner/reservations/${id}/quotes/`,{method:"POST",headers,body:JSON.stringify(payload)});
   const data=await r.json();if(!r.ok)throw new Error(data.detail||JSON.stringify(data));
   setNotice(`Quotation v${data.version} sent for reservation request #${id}.`);
   await load();
  }catch(e){setError(e instanceof Error?e.message:"Could not issue quotation.");}
  finally{setBusy(null);}
 }
 return <section className="partner-quotes">
  <header><p className="eyebrow">PARTNER WORKSPACE</p><h2>Reservation quotations</h2><p>Prepare itemised pricing for your reservation requests. Customers must explicitly accept a quotation before you can confirm the reservation.</p></header>
  {error&&<p className="pq-feedback error" role="alert">{error}</p>}{notice&&<p className="pq-feedback" role="status">{notice}</p>}
  {items.length?items.filter(x=>x.status==="pending").map(item=><article className="pq-card" key={item.id}>
   <div className="pq-card-head"><div><strong>{item.partner.name} · Request #{item.id}</strong><span>{item.customer_email}</span></div><span className="pq-status">{item.status}</span></div>
   <p>{item.start_date} to {item.end_date} · {item.guests} guests</p>
   {item.latest_quote != null&&<div className="pq-existing"><strong>Latest quote: v{(item.latest_quote as {version:number}).version}</strong><span>Status: {(item.latest_quote as {status:string}).status}</span></div>}
   {(item.latest_quote as {status:string}|null)?.status==="accepted"
    ? <div className="pq-accepted">
       <p>Customer accepted the quotation. Review availability and make your final reservation decision.</p>
       <label>Partner response<textarea rows={2} value={responses[item.id]??"Your reservation is confirmed."} onChange={e=>setResponses(v=>({...v,[item.id]:e.target.value}))}/></label>
       <div className="pq-decision-actions"><button disabled={busy===item.id} onClick={()=>decideReservation(item.id,"confirmed")}>Confirm reservation</button><button disabled={busy===item.id} onClick={()=>decideReservation(item.id,"declined")}>Decline request</button></div>
      </div>
    : <><h3><FileText size={16}/> Build quotation (ZAR)</h3>
   {(lines[item.id]??[emptyLine()]).map((line,index)=><div className="pq-line" key={index}>
    <label>Description<input value={line.description} onChange={e=>updateLine(item.id,index,"description",e.target.value)}/></label>
    <label>Qty<input type="number" min="0.01" step="0.01" value={line.quantity} onChange={e=>updateLine(item.id,index,"quantity",e.target.value)}/></label>
    <label>Unit price<input type="number" min="0" step="0.01" value={line.unit_price} onChange={e=>updateLine(item.id,index,"unit_price",e.target.value)}/></label>
    {index>0&&<button type="button" className="pq-remove" onClick={()=>setLines(v=>({...v,[item.id]:(v[item.id]??[]).filter((_,i)=>i!==index)}))}>Remove</button>}
   </div>)}
   <button type="button" className="pq-add" onClick={()=>setLines(v=>({...v,[item.id]:[...(v[item.id]??[emptyLine()]),emptyLine()]}))}><Plus size={14}/> Add line item</button>
   <div className="pq-fields">
    <label>Deposit amount (ZAR)<input type="number" min="0" step="0.01" value={deposits[item.id]??"0"} onChange={e=>setDeposits(v=>({...v,[item.id]:e.target.value}))}/></label>
    <label>Quote expires at<input type="datetime-local" value={expiries[item.id]??""} onChange={e=>setExpiries(v=>({...v,[item.id]:e.target.value}))}/></label>
   </div>
   <label className="pq-terms">Terms and inclusions<textarea rows={3} maxLength={3000} value={terms[item.id]??""} onChange={e=>setTerms(v=>({...v,[item.id]:e.target.value}))} placeholder="Describe inclusions, exclusions, payment conditions and any important restrictions."/></label>
   <button className="pq-submit" disabled={busy===item.id} onClick={()=>issueQuote(item.id)}><Send size={15}/>{busy===item.id?"Sending…":"Send quotation to customer"}</button>
    </>}
  </article>):<p className="pq-empty">No pending reservation requests are available for partner profiles linked to this account.</p>}
 </section>;
}
