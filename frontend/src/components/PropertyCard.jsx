import { rupees } from "../api.js";

const daysAgo = (iso) => Math.max(0, Math.round((Date.now() - new Date(iso + "Z")) / 86400000));
const ago = (d) => (d === 0 ? "today" : d === 1 ? "yesterday" : `${d} days ago`);

export default function PropertyCard({ match, onSelect, selected, disabled }) {
  const p = match.property;
  const kind = p.bhk === 0 ? (p.property_type === "pg" ? "PG room" : "Studio") : `${p.bhk} BHK`;
  return (
    <article className={`home ${selected ? "is-selected" : ""}`}>
      <div className="home-head">
        <span className="home-rank">Option {match.rank}</span>
        <span className="home-fit" title="How well it matches what you said">{Math.round(match.score)}% fit</span>
      </div>
      <h3>{kind} in {p.locality}</h3>
      <p className="home-rent">{rupees(p.rent)}<small>/month</small></p>
      <dl className="home-facts">
        <div><dt>Deposit</dt><dd>{rupees(p.deposit)}</dd></div>
        <div><dt>Size</dt><dd>{p.area_sqft} sq ft</dd></div>
        <div><dt>Furnishing</dt><dd>{p.furnishing === "semi" ? "Semi" : p.furnishing === "fully" ? "Full" : "None"}</dd></div>
        <div><dt>Move in</dt><dd>{new Date(p.available_from).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</dd></div>
      </dl>
      <ul className="home-why">
        {match.reasons.map((r) => <li key={r}>{r}</li>)}
      </ul>
      <p className="home-verified">Owner confirmed availability {ago(daysAgo(p.last_verified_at))}</p>
      {onSelect && (
        <button className={`btn ${selected ? "btn-done" : "btn-primary"}`} disabled={disabled} onClick={() => onSelect(p.id)}>
          {selected ? "Selected" : "Select this home"}
        </button>
      )}
    </article>
  );
}
