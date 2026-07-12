/* cad_forge — CAD assembly status: parts, validation, constraints */
export default function CadForge({ payload }: { payload?: Record<string, unknown> }) {
  const p = payload ?? {};
  const parts = (p.parts as string[]) ?? ['gear_sun', 'gear_planet x3', 'ring_gear', 'carrier', 'shaft'];
  const dfm = Number(p.dfm ?? 96);
  const stress = Number(p.stress ?? 0.42);
  return (
    <div className="w-cad">
      <div className="w-cad-vis">
        <svg viewBox="0 0 120 120">
          <g className="spin-slow" style={{ transformOrigin: '60px 60px' }}>
            {Array.from({ length: 12 }).map((_, i) => {
              const a = (i / 12) * Math.PI * 2;
              return <rect key={i} x={58} y={10} width="4" height="10" fill="var(--accent)"
                transform={`rotate(${(a * 180) / Math.PI} 60 60)`} />;
            })}
            <circle cx="60" cy="60" r="40" fill="none" stroke="var(--accent)" strokeWidth="1.4" />
            <circle cx="60" cy="60" r="16" fill="none" stroke="#ff2630" strokeWidth="1.4" />
            <circle cx="60" cy="60" r="4" fill="#ff2630" />
          </g>
        </svg>
      </div>
      <div className="w-cad-info">
        <div className="w-chips">{parts.map((pt) => <span key={pt} className="w-chip">{pt}</span>)}</div>
        <div className="w-row"><span className="w-row-k">DFM CHECK</span><span className="w-row-line" /><span className="w-row-v ok">{dfm}%</span></div>
        <div className="w-row"><span className="w-row-k">PEAK STRESS</span><span className="w-row-line" /><span className="w-row-v">{stress} GPa</span></div>
      </div>
    </div>
  );
}
