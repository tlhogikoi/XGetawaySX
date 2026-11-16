import { useEffect, useState } from "react";
import "./finance.css";

const API=(import.meta as ImportMeta & {env:Record<string,string|undefined>}).env.VITE_API_BASE_URL??"";
type Reservation={id:number;partner:{name:string};booking_reference:string|null;status:string};
type Installment={id:number;sequence:number;kind:string;amount:string;paid_amount:string;outstanding_amount:string;currency:string;due_at:string;status:"paid"|"overdue"|"upcoming"};
type Schedule={reservation_id:number;booking_reference:string;reservation_status:string;currency:string|null;total_amount:string;outstanding_amount:string;installments:Installment[]};

export default function PartnerPaymentScheduleWorkspace({accessToken}:{accessToken:string}){
 const [schedules,setSchedules]=useState<Schedule[]>([]);
 const [error,setError]=useState("");
 const headers={Authorization:`Bearer ${accessToken}`};
 useEffect(()=>{
  let active=true;
  async function load(){
   const response=await fetch(`${API}/api/v1/partners/partner/reservations/`,{headers});
   if(!response.ok)throw new Error("Could not load partner reservations.");
   const reservations=await response.json() as Reservation[];
   const results=await Promise.all(reservations.filter(item=>item.status==="confirmed").map(async item=>{
    const r=await fetch(`${API}/api/v1/partners/reservations/${item.id}/payment-schedule/`,{headers});
    return r.ok?await r.json() as Schedule:null;
   }));
   if(active)setSchedules(results.filter((item):item is Schedule=>item!==null));
  }
  load().catch(reason=>{if(active)setError(reason instanceof Error?reason.message:"Could not load payment schedules.");});
  return()=>{active=false;};
 },[accessToken]);
 return <section className="finance-workspace">
  <header><p className="eyebrow">PARTNER WORKSPACE</p><h2>Reservation payment tracking</h2><p>Monitor customer deposits, balances, deadlines and captured payments for your confirmed bookings.</p></header>
  {error&&<p className="finance-feedback error" role="alert">{error}</p>}
  {schedules.length?schedules.map(schedule=><article className="finance-panel" key={schedule.reservation_id}>
   <h3>Booking {schedule.booking_reference||`#${schedule.reservation_id}`}</h3>
   <p>Total {schedule.currency} {schedule.total_amount} · Outstanding {schedule.currency} {schedule.outstanding_amount}</p>
   {schedule.installments.map(item=><div className="finance-row" key={item.id}>
    <strong>{item.kind} · {item.currency} {item.amount}</strong>
    <p>Due {new Date(item.due_at).toLocaleString()}</p>
    <p>Captured {item.currency} {item.paid_amount} · Outstanding {item.currency} {item.outstanding_amount}</p>
    <span className={`finance-status ${item.status}`}>{item.status}</span>
   </div>)}
  </article>):!error&&<p className="finance-note">Confirmed reservations with payment schedules will appear here.</p>}
 </section>;
}
