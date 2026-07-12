import React, { useMemo } from 'react';

const radialTicks = Array.from({ length: 120 }, (_, index) => ({
    angle: index * 3,
    major: index % 10 === 0,
    medium: index % 5 === 0,
    hot: index % 17 === 0 || (index > 74 && index < 94 && index % 2 === 0),
}));

const signalBars = Array.from({ length: 34 }, (_, index) => ({
    angle: -70 + index * 3.7,
    length: 8 + ((index * 13) % 24),
    hot: index % 4 !== 0,
}));

const systemNodes = [
    { label: 'MEM', x: 286, y: 258 },
    { label: 'IO', x: 270, y: 307 },
    { label: 'NET', x: 282, y: 356 },
    { label: 'VEC', x: 307, y: 401 },
    { label: 'SYS', x: 344, y: 438 },
];

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const SourceFusionJarvisStage = ({
    snapshot,
    audioAmp = 0,
    reactivity,
    connected = false,
    activeTasks = 0,
    telemetry,
    isMuted = true,
}) => {
    const mode = snapshot?.mode || 'idle';
    const signal = clamp(Number(reactivity?.level ?? audioAmp) || 0, 0, 1);
    const taskCount = Number(activeTasks || 0);
    const cpu = clamp(Math.round(Number(telemetry?.cpu) || signal * 42 + taskCount * 7), 0, 99);
    const memory = clamp(Math.round(Number(telemetry?.memory) || 38 + taskCount * 5), 0, 99);
    const focus = mode === 'thinking' || mode === 'building' ? 92 : mode === 'listening' ? 78 : 64;
    const integrity = connected ? clamp(98 - taskCount * 3, 72, 98) : 24;
    const voice = isMuted ? 0 : clamp(Math.round(32 + signal * 67), 0, 99);
    const energy = clamp(0.35 + signal * 0.9 + taskCount * 0.08, 0.35, 1.25);

    const status = connected ? (isMuted ? 'VOICE LINKED / MUTED' : 'VOICE CHANNEL ACTIVE') : 'LOCAL CORE STANDBY';
    const modeLabel = mode === 'idle' ? 'FLIGHT' : mode.toUpperCase();

    const metrics = useMemo(() => ([
        { label: 'CORE', value: integrity, tone: 'red' },
        { label: 'FOCUS', value: focus, tone: 'white' },
        { label: 'VOICE', value: voice, tone: 'red' },
        { label: 'TASK BUS', value: clamp(taskCount * 19, 0, 99), tone: 'white' },
    ]), [focus, integrity, taskCount, voice]);

    return (
        <section
            className={`ada-source-fusion-stage ada-mark7-stage mode-${mode}`}
            aria-label="ADA radial diagnostic command interface"
            style={{ '--ada-reactivity': energy }}
        >
            <div className="mark7-header" aria-hidden="true">
                <span>A.D.A // ADAPTIVE DIAGNOSTIC ARRAY</span>
                <strong>{status}</strong>
                <span>MK VII / {mode.toUpperCase()}</span>
            </div>

            <div className="mark7-face">
                <svg className="mark7-svg" viewBox="0 0 1000 700" role="img" aria-label={`ADA ${mode} diagnostic face`}>
                    <defs>
                        <filter id="mark7-soft-glow" x="-50%" y="-50%" width="200%" height="200%">
                            <feGaussianBlur stdDeviation="2.2" result="blur" />
                            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                        </filter>
                    </defs>

                    <g className="mark7-outer-architecture">
                        <circle cx="520" cy="350" r="316" className="mark7-guide guide-a" />
                        <circle cx="520" cy="350" r="289" className="mark7-guide guide-b" />
                        <circle cx="520" cy="350" r="256" className="mark7-guide guide-c" />
                        <circle cx="520" cy="350" r="224" className="mark7-guide guide-d" />
                        <path d="M249 170 A317 317 0 0 1 740 83" className="mark7-structural-line" />
                        <path d="M193 498 A342 342 0 0 0 407 667" className="mark7-structural-line is-red" />
                        <path d="M761 106 A318 318 0 0 1 835 414" className="mark7-structural-line" />
                    </g>

                    <g className="mark7-tick-ring">
                        {radialTicks.map((tick, index) => (
                            <line
                                key={index}
                                x1={tick.major ? 806 : tick.medium ? 811 : 816}
                                y1="350"
                                x2="827"
                                y2="350"
                                transform={`rotate(${tick.angle} 520 350)`}
                                className={`${tick.major ? 'major' : ''} ${tick.medium ? 'medium' : ''} ${tick.hot ? 'hot' : ''}`}
                            />
                        ))}
                    </g>

                    <g className="mark7-bands">
                        <circle cx="520" cy="350" r="279" pathLength="100" strokeDasharray="20 6 4 8 11 9 24 18" />
                        <circle cx="520" cy="350" r="242" pathLength="100" strokeDasharray="4 2 17 5 7 9 22 8 12 14" className="reverse" />
                        <circle cx="520" cy="350" r="204" pathLength="100" strokeDasharray="31 12 6 8 21 22" className="hot-band" />
                        <circle cx="520" cy="350" r="174" pathLength="100" strokeDasharray="4 3 9 4 18 6 7 9 23 17" />
                        <circle cx="520" cy="350" r="142" pathLength="100" strokeDasharray="22 8 4 3 13 7 29 14" className="hot-band reverse" />
                    </g>

                    <g className="mark7-signal-crown">
                        {signalBars.map((bar, index) => (
                            <line
                                key={index}
                                x1="520"
                                y1="106"
                                x2="520"
                                y2={106 - bar.length}
                                transform={`rotate(${bar.angle} 520 350)`}
                                className={bar.hot ? 'hot' : ''}
                            />
                        ))}
                    </g>

                    <g className="mark7-left-sector">
                        <path d="M244 201 A326 326 0 0 0 202 485" className="sector-bracket" />
                        <path d="M222 231 A294 294 0 0 0 188 425" className="sector-bracket is-hot" />
                        <text x="141" y="373" transform="rotate(-78 141 373)" className="vertical-label">ADA / COGNITIVE DIAGNOSTICS</text>
                        {systemNodes.map((node, index) => (
                            <g key={node.label} className={`system-node node-${index}`}>
                                {index < systemNodes.length - 1 && <line x1={node.x} y1={node.y} x2={systemNodes[index + 1].x} y2={systemNodes[index + 1].y} />}
                                <circle cx={node.x} cy={node.y} r={index === 2 ? 12 : 8} />
                                <circle cx={node.x} cy={node.y} r="3" />
                                <text x={node.x - 33} y={node.y + 4}>{node.label}</text>
                            </g>
                        ))}
                    </g>

                    <g className="mark7-lower-gauge">
                        <path d="M264 510 A168 168 0 0 0 452 599" />
                        <path d="M280 508 A150 150 0 0 0 437 582" className="hot" />
                        <path d="M304 507 A124 124 0 0 0 419 560" />
                        {Array.from({ length: 15 }, (_, index) => (
                            <line key={index} x1="311" y1="508" x2="311" y2={index % 3 === 0 ? 491 : 497} transform={`rotate(${index * 7 - 4} 414 508)`} />
                        ))}
                        <text x="296" y="546">COGNITIVE LOAD</text>
                        <text x="331" y="575" className="gauge-value">{cpu}%</text>
                    </g>

                    <g className="mark7-right-bank">
                        {metrics.map((metric, index) => (
                            <g key={metric.label} transform={`translate(744 ${214 + index * 67})`} className={`metric-stack ${metric.tone}`}>
                                <text x="0" y="0">{metric.label}</text>
                                <text x="0" y="31" className="metric-value">{metric.value}%</text>
                                <line x1="0" y1="42" x2={34 + metric.value * 0.72} y2="42" />
                                <line x1="0" y1="47" x2="112" y2="47" className="metric-track" />
                            </g>
                        ))}
                    </g>

                    <g className="mark7-reactor" filter="url(#mark7-soft-glow)">
                        <circle cx="520" cy="350" r="119" className="reactor-outer" />
                        <circle cx="520" cy="350" r="102" className="reactor-index" pathLength="100" strokeDasharray="3 2 14 4 7 3 19 6 9 33" />
                        <circle cx="520" cy="350" r="81" className="reactor-hot" pathLength="100" strokeDasharray="26 8 5 4 17 7 22 11" />
                        <polygon points="520,285 575,318 575,382 520,415 465,382 465,318" className="reactor-hex" />
                        <polygon points="520,309 555,330 555,370 520,391 485,370 485,330" className="reactor-core" />
                        <circle cx="520" cy="350" r="20" className="reactor-iris" />
                        <circle cx="520" cy="350" r="7" className="reactor-dot" />
                        <line x1="520" y1="268" x2="520" y2="312" />
                        <line x1="591" y1="391" x2="554" y2="370" />
                        <line x1="449" y1="391" x2="486" y2="370" />
                    </g>

                    <g className="mark7-center-copy">
                        <text x="520" y="340" textAnchor="middle">A.D.A</text>
                        <text x="520" y="365" textAnchor="middle" className="flight-label">{modeLabel}</text>
                    </g>

                    <g className="mark7-memory-readout">
                        <text x="632" y="548">MEMORY ARRAY</text>
                        <text x="632" y="574" className="memory-value">{memory}%</text>
                        <line x1="632" y1="586" x2={632 + memory * 1.35} y2="586" />
                    </g>
                </svg>

                <div className="mark7-telemetry-strip" aria-label="Live ADA diagnostics">
                    <span><i className={connected ? 'online' : ''} />{connected ? 'CORE ONLINE' : 'STANDBY'}</span>
                    <span>CPU {cpu}%</span>
                    <strong>{modeLabel}</strong>
                    <span>{taskCount.toString().padStart(2, '0')} ACTIVE TASKS</span>
                    <span>{isMuted ? 'VOICE MUTED' : `VOICE ${voice}%`}</span>
                </div>
            </div>
        </section>
    );
};

export default SourceFusionJarvisStage;
