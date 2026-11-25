import { useCallback, useEffect, useState } from "react";

const API = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";
type Preference = { purpose: string; label: string; enabled: boolean; policy_version: string; updated_at: string | null };
const descriptions: Record<string, string> = {
  marketing_email: "Product news, getaway inspiration and promotional offers by email.",
  marketing_sms: "Promotional updates and offers by SMS.",
  marketing_whatsapp: "Promotional updates and offers through WhatsApp.",
};

export default function ConsentPreferences() {
  const token = sessionStorage.getItem("xgs_access");
  const [items, setItems] = useState<Preference[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    setLoading(true);
    try {
      const response = await fetch(`${API}/api/v1/accounts/consent-preferences/`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load your preferences.");
      setItems(data as Preference[]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load your preferences.");
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  async function change(item: Preference, enabled: boolean) {
    if (!token) return;
    setBusy(item.purpose); setError(""); setNotice("");
    try {
      const response = await fetch(`${API}/api/v1/accounts/consent-preferences/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ purpose: item.purpose, enabled, policy_version: "2026-11", source: "privacy_centre" }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(Object.values(data).flat().join(" ") || "Could not update this preference.");
      setItems(current => current.map(value => value.purpose === item.purpose ? { ...value, enabled: data.enabled, policy_version: data.policy_version } : value));
      setNotice(`${item.label} preference saved.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update this preference.");
    } finally { setBusy(""); }
  }

  return <section className="consent-preferences">
    <h2>Marketing preferences</h2>
    <p className="privacy-intro">Choose separately whether XGetawaySX may send you promotional messages through each channel. All channels start switched off unless you actively opt in.</p>
    {error && <p className="privacy-feedback privacy-error" role="alert">{error}</p>}
    {notice && <p className="privacy-feedback" role="status">{notice}</p>}
    {loading ? <p className="privacy-intro">Loading preferences…</p> : <div className="consent-options">
      {items.map(item => <label className="consent-option" key={item.purpose}>
        <span><strong>{item.label}</strong><small>{descriptions[item.purpose] ?? "Promotional communications."}</small></span>
        <input type="checkbox" checked={item.enabled} disabled={Boolean(busy)} onChange={event => change(item, event.target.checked)} aria-label={`Allow ${item.label}`}/>
      </label>)}
    </div>}
    <p className="consent-service-note">These settings cover marketing only. Essential account, security, booking and transaction messages may still be sent when needed to provide a service you requested. Changing a preference is recorded in an account-linked audit history.</p>
  </section>;
}
