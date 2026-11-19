import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import PropertyCard from "../components/PropertyCard.jsx";

export default function Chat() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

  useEffect(() => { api.getChat(token).then(setData).catch((e) => setError(e.message)); }, [token]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [data?.messages?.length]);

  async function send(e) {
    e.preventDefault();
    if (!text.trim()) return;
    const content = text;
    setText("");
    setSending(true);
    setData((d) => ({ ...d, messages: [...d.messages, { role: "user", content }] }));
    try {
      const res = await api.sendChat(token, content);
      setData((d) => ({ ...d, messages: res.messages }));
    } catch (err) {
      setError(err.message);
    }
    setSending(false);
  }

  async function select(pid) {
    const res = await api.select(token, pid);
    setData((d) => ({ ...d, selected: res.selected, messages: res.messages }));
  }

  if (error && !data) return <p className="empty">{error}. <Link to="/">Start a new search</Link>.</p>;
  if (!data) return <p className="empty">Loading your shortlist…</p>;

  const { request, messages, selected } = data;
  const suggestions = ["Which is cheapest?", "Which allows pets?", "Compare deposits", "Which do you recommend?"];

  return (
    <section className="chat">
      <aside className="chat-homes">
        <h1>Your shortlist</h1>
        {selected && (
          <div className="owner" role="status">
            <h2>Owner contact</h2>
            <p className="owner-name">{selected.owner_name}</p>
            <a className="owner-phone" href={`tel:${selected.owner_phone}`}>{selected.owner_phone}</a>
            <p className="muted">{selected.address}, {selected.locality}</p>
          </div>
        )}
        {request.matches.length === 0 && <p className="muted">No homes yet. Finish your call to see matches here.</p>}
        {request.matches.map((m) => (
          <PropertyCard key={m.property.id} match={m} onSelect={select}
            selected={selected?.id === m.property.id} disabled={selected?.id === m.property.id} />
        ))}
      </aside>

      <div className="chat-thread">
        <ol className="bubbles" aria-live="polite">
          {messages.map((m, i) => (
            <li key={i} className={m.role === "user" ? "from-you" : "from-agent"}>{m.content}</li>
          ))}
          {sending && <li className="from-agent muted">Typing…</li>}
          <li ref={endRef} aria-hidden="true" />
        </ol>
        <div className="chips">
          {suggestions.map((s) => <button key={s} type="button" onClick={() => setText(s)}>{s}</button>)}
        </div>
        <form className="composer" onSubmit={send}>
          <label className="sr-only" htmlFor="msg">Message</label>
          <input id="msg" value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask about rent, deposit, pets, size…" />
          <button className="btn btn-primary" disabled={sending || !text.trim()}>Send</button>
        </form>
        {error && <p className="error" role="alert">{error}</p>}
      </div>
    </section>
  );
}
