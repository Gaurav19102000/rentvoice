import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import Waveform from "../components/Waveform.jsx";

export default function RequestForm() {
  const nav = useNavigate();
  const [cfg, setCfg] = useState(null);
  const [form, setForm] = useState({ name: "", phone: "", email: "", city: "Bengaluru", call_mode: "web", consent: false });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.config().then((c) => {
      setCfg(c);
      if (c.phone_calls_enabled) setForm((f) => ({ ...f, call_mode: "phone" }));
    }).catch(() => setError("Can't reach the server. Is the backend running on port 8000?"));
  }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const req = await api.createRequest(form);
      nav(`/requests/${req.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <section className="hero">
      <div className="hero-copy">
        <h1>Say what home you want. We'll find it while you're still on the call.</h1>
        <p className="lede">
          Leave your number and our voice assistant calls you within a minute. Describe the area,
          budget and size in your own words, and hear three verified homes before you hang up.
        </p>
        <figure className="sample" aria-label="Example conversation">
          <Waveform live level={0.35} bars={18} />
          <blockquote>
            <p><b>You</b> Something near Koramangala, 2 BHK, under 35k. Need parking.</p>
            <p><b>Asha</b> Found three. The closest is a semi-furnished 2 BHK in HSR, ₹32,000.</p>
          </blockquote>
        </figure>
      </div>

      <form className="panel" onSubmit={submit} noValidate>
        <h2>Request a call</h2>
        <label>Your name<input required value={form.name} onChange={set("name")} autoComplete="name" /></label>
        <label>Mobile number<input required value={form.phone} onChange={set("phone")} inputMode="tel" placeholder="+91 98765 43210" autoComplete="tel" /></label>
        <label>City
          <select value={form.city} onChange={set("city")}>
            <option>Bengaluru</option>
          </select>
          <small>More cities soon. Listings are currently Bengaluru only.</small>
        </label>
        <fieldset className="choice">
          <legend>How should we talk?</legend>
          <label className={!cfg?.phone_calls_enabled ? "is-disabled" : ""}>
            <input type="radio" name="mode" value="phone" checked={form.call_mode === "phone"} onChange={set("call_mode")} disabled={!cfg?.phone_calls_enabled} />
            Call my phone
          </label>
          <label>
            <input type="radio" name="mode" value="web" checked={form.call_mode === "web"} onChange={set("call_mode")} />
            Talk in this browser
          </label>
        </fieldset>
        <label className="consent">
          <input type="checkbox" checked={form.consent} onChange={set("consent")} />
          I agree to receive an automated call about my rental search. The call may be recorded to improve matches.
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn-primary" disabled={busy || !form.consent}>
          {busy ? "Requesting…" : form.call_mode === "phone" ? "Call me now" : "Continue to call"}
        </button>
      </form>
    </section>
  );
}
