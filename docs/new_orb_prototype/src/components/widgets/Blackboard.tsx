import { useEffect, useRef, useState } from 'react';

/* SWARM_HUD — Live Blackboard Stream: show_blackboard / get_agent_findings */
export default function Blackboard({ payload }: { payload?: Record<string, unknown> }) {
  const seed = (payload?.lines as { who: string; text: string; kind: string }[]) ?? [
    { who: 'α', text: 'Hypothesis: gear ratio 3.2 optimal', kind: 'pro' },
    { who: 'β', text: 'Contradiction — backlash exceeds tol', kind: 'con' },
    { who: 'γ', text: 'Synthesis: taper teeth, ratio 3.0', kind: 'syn' },
    { who: 'δ', text: 'Audit: DFM passes at 3.0', kind: 'audit' },
  ];
  const [lines, setLines] = useState(seed.slice(0, 2));
  const idx = useRef(2);
  useEffect(() => {
    const i = setInterval(() => {
      setLines((prev) => [...prev, seed[idx.current % seed.length]].slice(-4));
      idx.current++;
    }, 1800);
    return () => clearInterval(i);
  }, []);
  return (
    <div className="w-bb">
      {lines.map((l, i) => (
        <div key={i} className={`w-bb-row k-${l.kind}`}>
          <span className="w-bb-who">{l.who}</span>{l.text}
        </div>
      ))}
      <div className="w-bb-consensus">CONSENSUS · 78%</div>
    </div>
  );
}
