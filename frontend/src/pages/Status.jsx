import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, rupees } from "../api.js";
import PropertyCard from "../components/PropertyCard.jsx";
import WebCall from "../components/WebCall.jsx";

const STEPS = [
  { key: "submitted", label: "Request received" },
  { key: "calling", label: "Calling you" },
  { key: "in_call", label: "Understanding what you need" },
  { key: "matched", label: "Homes shortlisted" },
];
const ORDER = { submitted: 0, calling: 1, in_call: 2, matched: 3, no_match: 3, completed: 3, call_failed: 1 };

export default function Status() {
  const { id } = useParams();
  const [req, setReq] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => api.getRequest(id).then(setReq).catch((e) => setError(e.message)), [id]);

  useEffect(() => { api.config().then(setCfg); load(); }, [load]);
  useEffect(() => {
    if (!req || ["matched", "no_match", "completed"].includes(req.status)) return;
    const t = setInterval(load, 3000); // polling is enough here; swap for SSE/WebSocket at scale
    return () => clearInterval(t);
  }, [req, load]);

  if (error) return <p className="empty">{error}. <Link to="/">Start a new search</Link>.</p>;
  if (!req || !cfg) return <p className="empty">Loading your request…</p>;

  const at = ORDER[req.status] ?? 0;
  const done = ["matched", "completed"].includes(req.status);

  return (
    <section className="status">
      <div className="status-side">
        <h1>Hi {req.name.split(" ")[0]}</h1>
        <ol className="steps">
          {STEPS.map((s, i) => (
            <li key={s.key} className={i < at || (i === at && done) ? "is-done" : i === at ? "is-now" : ""}>
              {s.label}
            </li>
          ))}
        </ol>
        {req.status === "call_failed" && (
          <div className="notice">
            <p>We couldn't reach you. Check the number, or talk to us in the browser instead.</p>
            {cfg.phone_calls_enabled && <button className="btn btn-quiet" onClick={() => api.retryCall(id).then(load)}>Call me again</button>}
          </div>
        )}
        {Object.keys(req.preferences).length > 0 && (
          <div className="heard">
            <h2>What we heard</h2>
            <dl>
              {req.preferences.locality && <><dt>Area</dt><dd>{req.preferences.locality}</dd></>}
              {req.preferences.budget_max && <><dt>Budget</dt><dd>up to {rupees(req.preferences.budget_max)}</dd></>}
              {req.preferences.bhk !== undefined && <><dt>Size</dt><dd>{req.preferences.bhk == 0 ? "Studio / PG" : `${req.preferences.bhk} BHK`}</dd></>}
              {req.preferences.furnishing && req.preferences.furnishing !== "any" && <><dt>Furnishing</dt><dd>{req.preferences.furnishing}</dd></>}
              {req.preferences.amenities?.length > 0 && <><dt>Must-haves</dt><dd>{req.preferences.amenities.join(", ")}</dd></>}
            </dl>
          </div>
        )}
      </div>

      <div className="status-main">
        {!done && req.call_mode === "web" && cfg.web_calls_enabled && (
          <WebCall requestId={id} config={cfg} onEnded={() => setTimeout(load, 1500)} />
        )}
        {!done && req.call_mode === "phone" && (
          <div className="callcard"><div className="callcard-body"><p>Pick up when your phone rings. It's Asha from RentVoice.</p></div></div>
        )}
        {!done && cfg.demo_mode && <Simulator id={id} onDone={setReq} />}

        {req.status === "no_match" && (
          <div className="notice"><p>Nothing matched those preferences right now. Try a higher budget or a nearby area.</p></div>
        )}

        {req.matches.length > 0 && (
          <>
            <div className="results-head">
              <h2>Your shortlist</h2>
              <Link className="btn btn-primary" to={`/chat/${req.chat_token}`}>Open chat to contact owners</Link>
            </div>
            {req.relaxation_note && <p className="note">{req.relaxation_note}</p>}
            <div className="homes">
              {req.matches.map((m) => <PropertyCard key={m.property.id} match={m} />)}
            </div>
          </>
        )}
      </div>
    </section>
  );
}

// Demo-only: fills preferences as if the voice agent had collected them.
function Simulator({ id, onDone }) {
  const [p, setP] = useState({ locality: "Koramangala", budget_max: 35000, bhk: 2, furnishing: "any", amenities: "parking" });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setP({ ...p, [k]: e.target.value });
  async function run(e) {
    e.preventDefault();
    setBusy(true);
    const res = await api.simulate(id, { ...p, amenities: p.amenities.split(",").map((s) => s.trim()).filter(Boolean) });
    onDone(res);
    setBusy(false);
  }
  return (
    <details className="sim">
      <summary>No microphone? Simulate the call</summary>
      <form onSubmit={run} className="sim-grid">
        <label>Area<input value={p.locality} onChange={set("locality")} /></label>
        <label>Max rent<input type="number" value={p.budget_max} onChange={set("budget_max")} /></label>
        <label>BHK<input type="number" min="0" max="5" value={p.bhk} onChange={set("bhk")} /></label>
        <label>Furnishing
          <select value={p.furnishing} onChange={set("furnishing")}>
            <option value="any">Any</option><option value="unfurnished">Unfurnished</option>
            <option value="semi">Semi</option><option value="fully">Fully</option>
          </select>
        </label>
        <label className="wide">Must-haves (comma separated)<input value={p.amenities} onChange={set("amenities")} /></label>
        <button className="btn btn-quiet" disabled={busy}>{busy ? "Searching…" : "Run search"}</button>
      </form>
    </details>
  );
}
