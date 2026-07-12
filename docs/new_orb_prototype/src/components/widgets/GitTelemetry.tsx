/* CODE_INTEL — Git Telemetry Stream: git_status / generate_docs */
export default function GitTelemetry({ payload }: { payload?: Record<string, unknown> }) {
  const branch = String(payload?.branch ?? 'feat/morphic-field');
  const commits = (payload?.commits as { hash: string; msg: string }[]) ?? [
    { hash: 'a3f9c1', msg: 'add cognitive monitor binding' },
    { hash: '7be204', msg: 'fix swarm consensus race' },
    { hash: 'd1188e', msg: 'docs: regenerate kernel API' },
  ];
  return (
    <div className="w-git">
      <div className="w-git-branch"><span className="w-git-ic">⎇</span> {branch} <span className="w-git-ahead">↑2 ↓0</span></div>
      <div className="w-git-log">
        {commits.map((c) => (
          <div key={c.hash} className="w-git-row"><span className="w-git-hash">{c.hash}</span><span>{c.msg}</span></div>
        ))}
      </div>
      <div className="w-git-foot"><span className="ok">DOCS · AUTO-GENERATED</span></div>
    </div>
  );
}
