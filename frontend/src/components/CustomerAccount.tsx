import { FormEvent, useEffect, useState } from "react";
import { ArrowRight, LogIn, UserPlus, ShieldCheck, LogOut } from "lucide-react";
import ReservationWorkspace from "./ReservationWorkspace";
import CustomerPaymentsWorkspace from "./CustomerPaymentsWorkspace";
import TripPlanner from "./TripPlanner";
import PartnerQuoteWorkspace from "./PartnerQuoteWorkspace";
import PartnerPaymentScheduleWorkspace from "./PartnerPaymentScheduleWorkspace";
import "./customer-account.css";

const API = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";
type Account = { id: number; email: string; first_name: string; last_name: string; role: string; is_staff: boolean };
type Tokens = { access: string; refresh: string };

export default function CustomerAccount() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [tokens, setTokens] = useState<Tokens | null>(() => {
    const access = sessionStorage.getItem("xgs_access");
    const refresh = sessionStorage.getItem("xgs_refresh");
    return access && refresh ? { access, refresh } : null;
  });
  const [account, setAccount] = useState<Account | null>(null);
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!tokens) { setAccount(null); return; }
    const activeTokens = tokens;
    let active = true;
    async function loadAccount() {
      let access = activeTokens.access;
      let response = await fetch(`${API}/api/v1/accounts/me/`, { headers: { Authorization: `Bearer ${access}` } });
      if (response.status === 401) {
        const refreshResponse = await fetch(`${API}/api/v1/accounts/token/refresh/`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh: activeTokens.refresh }),
        });
        const refreshed = await refreshResponse.json();
        if (!refreshResponse.ok || !refreshed.access) throw new Error("Your session has expired. Please sign in again.");
        access = refreshed.access as string;
        const nextRefresh = (refreshed.refresh as string | undefined) ?? activeTokens.refresh;
        sessionStorage.setItem("xgs_access", access);
        sessionStorage.setItem("xgs_refresh", nextRefresh);
        if (active) setTokens({ access, refresh: nextRefresh });
        response = await fetch(`${API}/api/v1/accounts/me/`, { headers: { Authorization: `Bearer ${access}` } });
      }
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load your account.");
      if (active) setAccount(data as Account);
    }
    loadAccount().catch(reason => {
      if (!active) return;
      sessionStorage.removeItem("xgs_access");
      sessionStorage.removeItem("xgs_refresh");
      setTokens(null);
      setError(reason instanceof Error ? reason.message : "Could not load your account.");
    });
    return () => { active = false; };
  }, [tokens]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      if (mode === "register") {
        const response = await fetch(`${API}/api/v1/accounts/register/`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, first_name: firstName, last_name: lastName, password, password_confirm: passwordConfirm }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(Object.values(data).flat().join(" ") || "Could not create your account.");
        setNotice("Account created. Sign in to manage your getaway.");
        setMode("login"); setPassword(""); setPasswordConfirm("");
        return;
      }
      const response = await fetch(`${API}/api/v1/accounts/token/`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json() as Tokens & { detail?: string };
      if (!response.ok) throw new Error(data.detail || "Email or password was not recognised.");
      sessionStorage.setItem("xgs_access", data.access);
      sessionStorage.setItem("xgs_refresh", data.refresh);
      setTokens({ access: data.access, refresh: data.refresh });
      setPassword("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Something went wrong. Please try again.");
    } finally { setBusy(false); }
  }

  function signOut() {
    sessionStorage.removeItem("xgs_access"); sessionStorage.removeItem("xgs_refresh");
    setTokens(null); setAccount(null); setNotice("You have signed out.");
  }

  if (tokens && account) return (
    <main className="customer-account-shell">
      <header className="account-topbar">
        <a href="/" className="account-wordmark"><span>X</span>GETAWAYS<span>X</span></a>
        <button className="account-signout" onClick={signOut}><LogOut size={16}/> Sign out</button>
      </header>
      <section className="account-welcome">
        <p className="eyebrow">YOUR XGETAWAYSX ACCOUNT</p>
        <h1>Welcome{account.first_name ? `, ${account.first_name}` : ""}.</h1>
        <p>{account.email} · Your getaway plans, reservations and payments in one place.</p>
        <div className="account-trust"><ShieldCheck size={17}/> Your account information and bookings are private to your account.</div>
        <div className="account-workspace-links"><a href="/wishlist/">My wishlist <ArrowRight size={15}/></a><a href="/privacy-centre/">Privacy Centre <ArrowRight size={15}/></a>{account.role === "partner" && <a href="/partner/onboarding">Partner verification <ArrowRight size={15}/></a>}{account.is_staff && <a href="/staff/partner/onboarding">Staff verification queue <ArrowRight size={15}/></a>}</div>
      </section>
      <TripPlanner accessToken={tokens.access}/>
      <PartnerQuoteWorkspace accessToken={tokens.access}/>
      <PartnerPaymentScheduleWorkspace accessToken={tokens.access}/>
      <ReservationWorkspace accessToken={tokens.access}/>
      <CustomerPaymentsWorkspace accessToken={tokens.access}/>
      <footer className="account-footer"><a href="/">Back to XGetawaySX</a><span>TRAVEL THROUGH US.</span></footer>
    </main>
  );

  return (
    <main className="customer-account-shell">
      <header className="account-topbar"><a href="/" className="account-wordmark"><span>X</span>GETAWAYS<span>X</span></a><a href="/" className="account-back">Explore the site <ArrowRight size={15}/></a></header>
      <section className="account-auth-layout">
        <div className="account-auth-story">
          <p className="eyebrow">YOUR JOURNEY, IN ONE PLACE</p>
          <h1>Make room for<br/><span>more moments.</span></h1>
          <p>Sign in to manage reservation requests, keep track of payments and shape your next escape.</p>
          <div className="account-trust"><ShieldCheck size={17}/> Secure sign-in. Your travel details stay linked to your account.</div>
        </div>
        <form className="account-auth-card" onSubmit={submit}>
          <div className="account-auth-heading">{mode === "login" ? <LogIn size={20}/> : <UserPlus size={20}/>}<div><p className="eyebrow">TRAVEL THROUGH US</p><h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2></div></div>
          {notice && <p className="account-notice" role="status">{notice}</p>}
          {error && <p className="account-error" role="alert">{error}</p>}
          {mode === "register" && <div className="account-name-fields"><label>First name<input autoComplete="given-name" value={firstName} onChange={e=>setFirstName(e.target.value)} required/></label><label>Last name<input autoComplete="family-name" value={lastName} onChange={e=>setLastName(e.target.value)} required/></label></div>}
          <label>Email address<input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} required/></label>
          <label>Password<input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={8} value={password} onChange={e=>setPassword(e.target.value)} required/></label>
          {mode === "register" && <label>Confirm password<input type="password" autoComplete="new-password" minLength={8} value={passwordConfirm} onChange={e=>setPasswordConfirm(e.target.value)} required/></label>}
          <button className="account-submit" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"} <ArrowRight size={17}/></button>
          <p className="account-switch">{mode === "login" ? "New to XGetawaySX?" : "Already have an account?"} <button type="button" onClick={()=>{setMode(mode === "login" ? "register" : "login");setError("");setNotice("");}}> {mode === "login" ? "Create an account" : "Sign in"}</button></p>
          <p className="account-legal">By creating an account, you agree to use XGetawaySX responsibly. Terms and privacy information will be presented before public launch.</p>
        </form>
      </section>
      <footer className="account-footer"><span>© {new Date().getFullYear()} XGetawaySX</span><span>TRAVEL THROUGH US.</span></footer>
    </main>
  );
}
