/**
 * Map ADA HUD state → openclaw-jarvis-ui agent states (idle | thinking | responding).
 */
export function mapAdaToAgentState({ connected, isMuted, audioAmp, livingState, activeTasks, status }) {
    if (!connected) return 'idle';

    const statusLower = String(status || '').toLowerCase();
    if (statusLower.includes('connect') || statusLower.includes('think') || statusLower.includes('process')) {
        return 'thinking';
    }
    if (activeTasks > 0) return 'thinking';

    if (audioAmp > 0.08 && !isMuted) return 'responding';

    const mood = livingState?.embodied?.fused_mood;
    if (mood === 'alert' || mood === 'stressed') return 'thinking';

    return 'idle';
}

export function mapAdaToOrbStatusLabel(agentState, connected) {
    if (!connected) return 'OFFLINE · STANDBY';
    const labels = {
        idle: 'IDLE',
        thinking: 'THINKING',
        responding: 'RESPONDING',
    };
    return labels[agentState] || 'IDLE';
}
