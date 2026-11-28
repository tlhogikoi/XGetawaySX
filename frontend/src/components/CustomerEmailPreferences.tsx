import { useEffect, useState } from "react";
import { Mail, ShieldCheck } from "lucide-react";

const API = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL ?? "";

type PreferenceResponse = {
  marketing_opt_in: boolean;
  updated_at: string;
  essential_transactional_emails: true;
};

export default function CustomerEmailPreferences({ accessToken }: { accessToken: string }) {
  const [enabled, setEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    fetch(`${API}/api/v1/partners/email-preferences/`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Could not load email preferences.");
        return data as PreferenceResponse;
      })
      .then(data => { if (active) setEnabled(data.marketing_opt_in); })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : "Could not load email preferences."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [accessToken]);

  async function updatePreference(nextValue: boolean) {
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(`${API}/api/v1/partners/email-preferences/`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ marketing_opt_in: nextValue }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.marketing_opt_in || data.detail || "Could not save your preference.");
      setEnabled(data.marketing_opt_in);
      setNotice(nextValue
        ? "You are subscribed to XGetawaySX promotional emails."
        : "You are unsubscribed from XGetawaySX promotional emails.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save your preference.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="email-preferences-panel" aria-labelledby="email-preferences-title">
      <div className="email-preferences-heading">
        <span className="email-preferences-icon"><Mail size={19} /></span>
        <div>
          <p className="eyebrow">YOUR COMMUNICATIONS</p>
          <h3 id="email-preferences-title">Email preferences</h3>
        </div>
      </div>
      <p>Choose whether you would like to receive optional XGetawaySX travel inspiration, offers and promotional updates.</p>
      <label className="email-preference-toggle">
        <span>
          <strong>Promotional emails</strong>
          <small>{enabled ? "You are currently subscribed." : "You are currently not subscribed."}</small>
        </span>
        <input
          type="checkbox"
          checked={enabled}
          disabled={loading || saving}
          onChange={event => updatePreference(event.target.checked)}
          aria-label="Receive promotional emails"
        />
      </label>
      <div className="email-essential-note">
        <ShieldCheck size={18} />
        <span><strong>Essential booking emails stay on.</strong> Reservation requests, confirmations, cancellations, payment and refund updates are service messages and are not controlled by this setting.</span>
      </div>
      {loading && <p className="email-preference-status" role="status">Loading your preferences…</p>}
      {saving && <p className="email-preference-status" role="status">Saving your preference…</p>}
      {notice && <p className="email-preference-status" role="status">{notice}</p>}
      {error && <p className="email-preference-error" role="alert">{error}</p>}
    </section>
  );
}
