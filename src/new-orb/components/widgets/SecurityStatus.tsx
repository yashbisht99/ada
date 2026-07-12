/* security_status — process vulnerabilities + secret scan results */
export default function SecurityStatus({ payload }: { payload?: Record<string, unknown> }) {
  const p = payload ?? {};
  const findings = (p.findings as { label: string; level: string }[]) ?? [
    { label: 'No leaked API keys', level: 'ok' },
    { label: '2 outdated dependencies', level: 'warn' },
    { label: 'Suspicious process PID 4821', level: 'crit' },
    { label: 'Workspace integrity verified', level: 'ok' },
  ];
  return (
    <ul className="w-sec">
      {findings.map((f, i) => (
        <li key={i} className={`lvl-${f.level}`}>
          <span className="w-sec-dot" />{f.label}
          <span className="w-sec-tag">{f.level.toUpperCase()}</span>
        </li>
      ))}
    </ul>
  );
}
