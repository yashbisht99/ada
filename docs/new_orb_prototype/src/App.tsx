import { useEffect } from 'react';
import AdaOrb from './components/AdaOrb';
import StatePill from './components/StatePill';
import { useAda } from './ada/useAda';
import { adaBus } from './ada/bus';

export default function App() {
  const { state, living, amplitude } = useAda();
  const mood = living?.embodied.emotional_state ?? 'focused';

  // gentle ambient state drift so the idle orb feels alive (no widgets)
  useEffect(() => {
    const cycle: Array<'idle' | 'listening' | 'thinking' | 'speaking'> = ['idle', 'listening', 'thinking', 'speaking'];
    let i = 0;
    const t = setInterval(() => {
      i = (i + 1) % cycle.length;
      adaBus.emit('ui:state', cycle[i]);
    }, 5200);
    return () => clearInterval(t);
  }, []);

  const poke = () => adaBus.emit('ui:state',
    state === 'idle' ? 'listening' : state === 'listening' ? 'thinking' : state === 'thinking' ? 'speaking' : 'idle');

  return (
    <div className="stage">
      <div className="stage-grid" />
      <div className="stage-vignette" />

      <StatePill state={state} mood={mood} />

      <AdaOrb state={state} mood={mood} amplitudeRef={amplitude} onPoke={poke} />

      <div className="orb-center">
        <div className="orb-name">ADA</div>
        <div className="orb-online">ONLINE</div>
      </div>
    </div>
  );
}
