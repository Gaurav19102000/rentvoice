// The signature element: a voice waveform that breathes while a call is live.
export default function Waveform({ live = false, level = 0, bars = 24 }) {
  return (
    <div className={`wave ${live ? "is-live" : ""}`} aria-hidden="true">
      {Array.from({ length: bars }, (_, i) => {
        const base = 0.25 + 0.75 * Math.abs(Math.sin(i * 1.7));
        const h = live ? Math.max(0.15, base * (0.4 + level * 1.6)) : base * 0.35;
        return <span key={i} style={{ "--h": Math.min(1, h), "--d": `${(i % 6) * 90}ms` }} />;
      })}
    </div>
  );
}
