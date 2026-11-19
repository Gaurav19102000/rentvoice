import { useEffect, useState } from "react";
import { api, rupees } from "../api.js";

const EMPTY = { title: "", locality: "", lat: 12.97, lng: 77.59, rent: "", deposit: "", bhk: 2, property_type: "apartment",
  furnishing: "semi", area_sqft: "", amenities: "", pets_allowed: false, owner_name: "", owner_phone: "", description: "" };

export default function Admin() {
  const [token, setToken] = useState("");
  const [authed, setAuthed] = useState(false);
  const [tab, setTab] = useState("listings");
  const [props, setProps] = useState([]);
  const [reqs, setReqs] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");

  const a = api.admin(token);
  const load = () => Promise.all([a.properties(), a.requests()]).then(([p, r]) => { setProps(p); setReqs(r); });

  async function login(e) {
    e.preventDefault();
    try { await load(); setAuthed(true); setError(""); } catch (err) { setError(err.message); }
  }

  async function add(e) {
    e.preventDefault();
    try {
      await a.create({ ...form, rent: +form.rent, deposit: +form.deposit || 0, bhk: +form.bhk, area_sqft: +form.area_sqft || 0,
        lat: +form.lat, lng: +form.lng, amenities: form.amenities.split(",").map((s) => s.trim()).filter(Boolean) });
      setForm(EMPTY); setError(""); load();
    } catch (err) { setError(err.message); }
  }

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const stale = (iso) => (Date.now() - new Date(iso + "Z")) / 86400000 > 30;

  useEffect(() => { if (authed) { const t = setInterval(load, 5000); return () => clearInterval(t); } }, [authed, token]);

  if (!authed) {
    return (
      <form className="panel narrow" onSubmit={login}>
        <h1>Owner and admin access</h1>
        <label>Admin token<input type="password" value={token} onChange={(e) => setToken(e.target.value)} /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn-primary">Sign in</button>
      </form>
    );
  }

  return (
    <section className="admin">
      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "listings"} onClick={() => setTab("listings")}>Listings ({props.length})</button>
        <button role="tab" aria-selected={tab === "requests"} onClick={() => setTab("requests")}>Renter requests ({reqs.length})</button>
        <button role="tab" aria-selected={tab === "add"} onClick={() => setTab("add")}>Add listing</button>
      </div>

      {tab === "listings" && (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Listing</th><th>Rent</th><th>Owner</th><th>Last confirmed</th><th></th></tr></thead>
            <tbody>
              {props.map((p) => (
                <tr key={p.id} className={!p.is_active || stale(p.last_verified_at) ? "is-dim" : ""}>
                  <td>{p.title}<br /><small>{p.furnishing} · {p.area_sqft} sq ft</small></td>
                  <td>{rupees(p.rent)}</td>
                  <td>{p.owner_name}<br /><small>{p.owner_phone}</small></td>
                  <td>{new Date(p.last_verified_at + "Z").toLocaleDateString("en-IN")}{stale(p.last_verified_at) && <span className="tag">Hidden: stale</span>}</td>
                  <td className="row-actions">
                    <button className="btn btn-quiet" onClick={() => a.verify(p.id).then(load)}>Mark available</button>
                    <button className="btn btn-quiet" onClick={() => a.toggle(p.id).then(load)}>{p.is_active ? "Unlist" : "Relist"}</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "requests" && (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Renter</th><th>Status</th><th>Preferences</th><th>Matches</th><th>Received</th></tr></thead>
            <tbody>
              {reqs.map((r) => (
                <tr key={r.id}>
                  <td>{r.name}<br /><small>{r.phone} · {r.call_mode}</small></td>
                  <td><span className={`tag tag-${r.status}`}>{r.status.replace("_", " ")}</span></td>
                  <td><small>{Object.entries(r.preferences || {}).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join("/") : v}`).join(", ") || "Not collected yet"}</small></td>
                  <td>{r.matches}</td>
                  <td>{new Date(r.created_at + "Z").toLocaleString("en-IN")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "add" && (
        <form className="panel add-grid" onSubmit={add}>
          <label className="wide">Title<input required value={form.title} onChange={set("title")} placeholder="2 BHK apartment in Jayanagar" /></label>
          <label>Locality<input required value={form.locality} onChange={set("locality")} /></label>
          <label>Monthly rent<input required type="number" value={form.rent} onChange={set("rent")} /></label>
          <label>Deposit<input type="number" value={form.deposit} onChange={set("deposit")} /></label>
          <label>BHK<input type="number" min="0" max="6" value={form.bhk} onChange={set("bhk")} /></label>
          <label>Type<select value={form.property_type} onChange={set("property_type")}>
            <option value="apartment">Apartment</option><option value="independent_house">Independent house</option>
            <option value="villa">Villa</option><option value="pg">PG</option><option value="studio">Studio</option></select></label>
          <label>Furnishing<select value={form.furnishing} onChange={set("furnishing")}>
            <option value="unfurnished">Unfurnished</option><option value="semi">Semi</option><option value="fully">Fully</option></select></label>
          <label>Size (sq ft)<input type="number" value={form.area_sqft} onChange={set("area_sqft")} /></label>
          <label>Latitude<input required type="number" step="any" value={form.lat} onChange={set("lat")} /></label>
          <label>Longitude<input required type="number" step="any" value={form.lng} onChange={set("lng")} /></label>
          <label className="wide">Amenities (comma separated)<input value={form.amenities} onChange={set("amenities")} placeholder="parking, lift, power backup" /></label>
          <label>Owner name<input required value={form.owner_name} onChange={set("owner_name")} /></label>
          <label>Owner phone<input required value={form.owner_phone} onChange={set("owner_phone")} /></label>
          <label className="consent wide"><input type="checkbox" checked={form.pets_allowed} onChange={set("pets_allowed")} />Pets allowed</label>
          <label className="wide">Description<textarea rows="3" value={form.description} onChange={set("description")} /></label>
          {error && <p className="error wide" role="alert">{error}</p>}
          <button className="btn btn-primary">Publish listing</button>
        </form>
      )}
    </section>
  );
}
