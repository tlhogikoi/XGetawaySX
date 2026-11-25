import "./privacy-centre.css";

const rights = [
  { title: "Access your information", detail: "You may request confirmation of whether personal information is held and ask for a copy, subject to applicable identity checks and lawful limits.", status: "Request channel not yet enabled" },
  { title: "Correct your information", detail: "You may request correction or updating of information that is inaccurate, incomplete or out of date.", status: "Request channel not yet enabled" },
  { title: "Request deletion", detail: "You may request deletion where the law permits. Some records may need to be retained for legal, security, dispute or transaction obligations.", status: "Request channel not yet enabled" },
  { title: "Manage consent", detail: "Where processing relies on consent, you should be able to withdraw it. Withdrawal does not make earlier lawful processing invalid.", status: "Consent controls not yet connected" },
  { title: "Marketing preferences", detail: "Marketing communications should use a separate, clear opt-in and provide a straightforward way to opt out.", status: "Preference controls not yet connected" },
];

export default function PrivacyCentre() {
  const signedIn = Boolean(sessionStorage.getItem("xgs_access"));
  return <main className="privacy-centre">
    <header><a href="/" className="privacy-brand">XGETAWAYS<span>X</span></a><nav><a href="/account/">My account</a><a href="/privacy/">Privacy information</a></nav></header>
    <section className="privacy-hero"><p className="eyebrow">YOUR INFORMATION · YOUR CHOICES</p><h1>Privacy Centre</h1><p>Understand the privacy controls being prepared for XGetawaySX and the steps available before launch.</p><span className="privacy-stage">PRE-LAUNCH · NOT A LIVE REQUEST SERVICE</span></section>
    <section className="privacy-main">
      <div className="privacy-account-state"><div><h2>{signedIn ? "You are signed in on this device" : "Sign in to your account"}</h2><p>{signedIn ? "Your account session is present. The privacy request services below are not yet connected." : "Account-specific privacy tools will require you to sign in and verify your identity."}</p></div><a href="/account/">{signedIn ? "Account" : "Sign in"} →</a></div>
      <h2>Privacy rights and controls</h2>
      <p className="privacy-intro">These are the rights and preference controls the platform is preparing to support. The status beside each item is important: no request or preference change is submitted from this page.</p>
      <div className="privacy-rights">{rights.map((right, index)=><article key={right.title}><span className="privacy-number">0{index+1}</span><div><h3>{right.title}</h3><p>{right.detail}</p><small>{right.status}</small></div></article>)}</div>
      <aside className="privacy-notice"><strong>Need to make a privacy request now?</strong><p>This staging page does not yet have a verified privacy-request channel or confirmed Information Officer contact. Please do not enter sensitive personal information here. Before public launch, the responsible legal entity, privacy contact, identity-verification process, response workflow and audit trail must be configured and tested.</p><a href="/privacy/">Read the current privacy information →</a></aside>
      <p className="privacy-footnote">This page is product information, not legal advice or a statement of POPIA compliance. Applicable rights and exceptions depend on the circumstances and the law.</p>
    </section>
    <footer><a href="/">XGETAWAYS<span>X</span></a><span>TRAVEL THROUGH US.</span></footer>
  </main>;
}
