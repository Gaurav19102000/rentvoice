import { useEffect, useRef, useState } from "react";
import Vapi from "@vapi-ai/web";
import Waveform from "./Waveform.jsx";
import { api } from "../api.js";

// Talk to the same voice agent from the browser (free on Vapi's web channel, ideal for demos).
export default function WebCall({ requestId, config, onEnded }) {
  const vapiRef = useRef(null);
  const [state, setState] = useState("idle"); // idle | connecting | live | ended
  const [level, setLevel] = useState(0);
  const [lines, setLines] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => () => vapiRef.current?.stop(), []);

  async function start() {
    setError("");
    setState("connecting");
    try {
      const vars = await api.callVariables(requestId);
      const vapi = new Vapi(config.vapi_public_key);
      vapiRef.current = vapi;
      vapi.on("call-start", () => setState("live"));
      vapi.on("volume-level", (v) => setLevel(v));
      vapi.on("message", (m) => {
        if (m.type === "transcript" && m.transcriptType === "final") {
          setLines((l) => [...l.slice(-5), { role: m.role, text: m.transcript }]);
        }
      });
      vapi.on("call-end", () => { setState("ended"); setLevel(0); onEnded?.(); });
      vapi.on("error", (e) => { setError(e?.error?.message || e?.message || "The call dropped. Try again."); setState("idle"); });
      const call = await vapi.start(config.vapi_assistant_id, {
        variableValues: vars,
        metadata: { request_id: requestId },
      });
      if (call?.id) await api.attachWebCall(requestId, call.id);
    } catch (e) {
      setError(e.message || "Couldn't start the call. Check microphone permission.");
      setState("idle");
    }
  }

  return (
    <div className="callcard">
      <Waveform live={state === "live"} level={level} />
      <div className="callcard-body">
        {state === "idle" && (
          <>
            <p>Talk to Asha, our rental assistant, right here. She'll ask about area, budget and size.</p>
            <button className="btn btn-primary" onClick={start}>Start talking</button>
          </>
        )}
        {state === "connecting" && <p>Connecting… allow microphone access if your browser asks.</p>}
        {state === "live" && (
          <>
            <ol className="transcript" aria-live="polite">
              {lines.length === 0 && <li className="muted">Asha is about to speak…</li>}
              {lines.map((l, i) => (
                <li key={i} className={l.role === "assistant" ? "from-agent" : "from-you"}>
                  <b>{l.role === "assistant" ? "Asha" : "You"}</b> {l.text}
                </li>
              ))}
            </ol>
            <button className="btn btn-quiet" onClick={() => vapiRef.current?.stop()}>End call</button>
          </>
        )}
        {state === "ended" && <p>Call ended. Your matches are below.</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </div>
    </div>
  );
}
