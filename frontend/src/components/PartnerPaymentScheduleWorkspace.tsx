import { useEffect, useState } from "react";
import "./finance.css";

const API=(import.meta as ImportMeta & {env:Record<string,string|undefined>}).env.VITE_API_BASE_URL??"";
type Reservation={id:number;partner:{name:string};booking_reference:string|null;status:string};
type Profile={id:number;name:string};
type Installment={id:number;sequence:number;kind:string;amount:string;paid_amount:string;outstanding_amount:string;currency:string;due_at:string;status:"paid"|"overdue"|"upcoming"};
type Schedule={reservation_id:number;booking_reference:string;reservation_status:string;currency:string|null;total_amount:string;outstanding_amount:string;installments:Installment[]};
type Policy={deposit_type:"none"|"percentage"|"fixed";deposit_value:string;deposit_due_hours:number;balance_due_days_before:number;currency:string};

export default function PartnerPaymentScheduleWorkspace({accessToken}:{accessToken:string}){
 const [schedules,setSchedules]=useState<Schedule[]>([]);
 const [profiles,setProfiles]=useState<Profile[]>([]);
 const [selectedPartner,setSelectedPartner]=useState("");
 const [policy,setPolicy]=useState<Policy>({deposit_type:"none",deposit_value:"0",deposit_due_hours:48,balance_due_days_before:7,currency:"ZAR"});
 const [error,setError]=useState("");
 const [notice,setNotice]=useState("");
 const [saving,setSaving]=useState(false);
 const headers={Authorization:`Bearer ${accessToken}`};
 useEffect(()=>{
  let active=true;
  async function load(){
   const [reservationsResponse,profilesResponse]=await Promise.all([
    fetch(`${API}/api/v1/partners/partner/reservations/`,{headers}),
    fetch(`${API}/api/v1/partners/partner/profiles/`,{headers}),
   ]);
   if(!reservationsResponse.ok)throw new Error("Could not load partner reservations.");
   const reservations=await reservationsResponse.json() as Reservation[];
   const profileData=profilesResponse.ok?await profilesResponse.json() as Profile[]:[];
   const results=await Promise.all(reservations.filter(item=>item.status==="confirmed").map(async item=>{
    const r=await fetch(`${API}/api/v1/partners/reservations/${item.id}/payment-schedule/`,{headers});
    return r.ok?await r.json() as Schedule:null;
   }));
   if(active){setSchedules(results.filter((item):item is Schedule=>item!==null));setProfiles(profileData);if(profileData.length)setSelectedPartner(String(profileData[0].id));}
  }
  load().catch(reason=>{if(active)setError(reason instanceof Error?reason.message:"Could not load partner payment information.");});
  return()=>{active=false;};
 },[accessToken]);
 useEffect(()=>{
  if(!selectedPartner)return;
  let active=true;
  fetch(`${API}/api/v1/partners/partner/financial-settings/?partner_id=${selectedPartner}`,{headers})
   .then(r=>r.ok?r.json():Promise.reject(new Error("Could not load partner payment terms.")))
   .then((data:Record<string,unknown>[])=>{if(active&&data.length){const item=data[0];setPolicy({deposit_type:item.deposit_type as Policy["deposit_type"],deposit_value:String(item.deposit_value),deposit_due_hours:Number(item.deposit_due_hours),balance_due_days_before:Number(item.balance_due_days_before),currency:String(item.currency)});}else if(active)setPolicy({deposit_type:"none",deposit_value:"0",deposit_due_hours:48,balance_due_days_before:7,currency:"ZAR"});})
   .catch(reason=>{if(active)setError(reason instanceof Error?reason.message:"Could not load payment terms.");});
  return()=>{active=false;};
 },[selectedPartner,accessToken]);
 async function savePolicy(){
  if(!selectedPartner)return;
  setSaving(true);setError("");setNotice("");
  try{
   const response=await fetch(`${API}/api/v1/partners/partner/financial-settings/`,{
    method:"POST",headers:{"Content-Type":"application/json",...headers},
    body:JSON.stringify({partner_id:Number(selectedPartner),...policy}),
   });
   const data=await response.json();
   if(!response.ok)throw new Error(data.detail||JSON.stringify(data));
   setPolicy({deposit_type:data.deposit_type,deposit_value:String(data.deposit_value),deposit_due_hours:data.deposit_due_hours,balance_due_days_before:data.balance_due_days_before,currency:data.currency});
   setNotice("Payment terms saved for this partner profile.");
  }catch(reason){setError(reason instanceof Error?reason.message:"Could not save payment terms.");}
  finally{setSaving(false);}
 }
 return <section className="finance-workspace">
  <header><p className="eyebrow">PARTNER WORKSPACE</p><h2>Reservation payment tracking</h2><p>Monitor customer deposits, balances, deadlines and captured payments for your confirmed bookings.</p></header>
  {error&&<p className="finance-feedback error" role="alert">{error}</p>}
  <div className="finance-panel">
   <h3>Payment terms for your partner profile</h3>
   {profiles.length?<><label>Partner profile<select value={selectedPartner} onChange={e=>setSelectedPartner(e.target.value)}>{profiles.map(profile=><option key={profile.id} value={profile.id}>{profile.name}</option>)}</select></label>
    <label>Deposit policy<select value={policy.deposit_type} onChange={e=>setPolicy(p=>({...p,deposit_type:e.target.value as Policy["deposit_type"],deposit_value:e.target.value==="none"?"0":p.deposit_value}))}><option value="none">No partner-set deposit (platform 30% suggestion)</option><option value="percentage">Percentage</option><option value="fixed">Fixed amount</option></select></label>
    {policy.deposit_type!=="none"&&<label>{policy.deposit_type==="percentage"?"Deposit percentage":"Deposit amount"}<input type="number" min="0" step="0.01" value={policy.deposit_value} onChange={e=>setPolicy(p=>({...p,deposit_value:e.target.value}))}/></label>}
    <label>Deposit due (hours after confirmation)<input type="number" min="1" max="720" value={policy.deposit_due_hours} onChange={e=>setPolicy(p=>({...p,deposit_due_hours:Number(e.target.value)}))}/></label>
    <label>Balance due (days before travel)<input type="number" min="0" max="365" value={policy.balance_due_days_before} onChange={e=>setPolicy(p=>({...p,balance_due_days_before:Number(e.target.value)}))}/></label>
    <button disabled={saving} onClick={savePolicy}>{saving?"Saving…":"Save payment terms"}</button>
   </>:<p>Approved booking partner profiles will appear here when linked to your account.</p>}
   {notice&&<p className="finance-feedback" role="status">{notice}</p>}
   <p className="finance-note">These settings apply to future reservation schedules. Existing confirmed schedules are not silently changed.</p>
  </div>
  {schedules.length?schedules.map(schedule=><article className="finance-panel" key={schedule.reservation_id}>
   <h3>Booking {schedule.booking_reference||`#${schedule.reservation_id}`}</h3>
   <p>Total {schedule.currency} {schedule.total_amount} · Outstanding {schedule.currency} {schedule.outstanding_amount}</p>
   {schedule.installments.map(item=><div className="finance-row" key={item.id}>
    <strong>{item.kind} · {item.currency} {item.amount}</strong>
    <p>Due {new Date(item.due_at).toLocaleString()}</p>
    <p>Captured {item.currency} {item.paid_amount} · Outstanding {item.currency} {item.outstanding_amount}</p>
    <span className={`finance-status ${item.status}`}>{item.status}</span>
   </div>)}
  </article>):<p className="finance-note">Confirmed reservations with payment schedules will appear here.</p>}
 </section>;
}
