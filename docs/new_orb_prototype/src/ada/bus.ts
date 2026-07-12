import type { AdaEventMap } from './types';

/* =========================================================================
   adaBus — a tiny typed event bus that mirrors the backend Socket.IO API.

   In production you bind this to your real socket:
       socket.on('ada:spawn_widget', (p) => adaBus.emit('ada:spawn_widget', p));
       adaBus.on('user_input', (p) => socket.emit('user_input', p));

   For now the demo driver emits the same events so the UI is fully exercised.
   ========================================================================= */

type Handler<T> = (payload: T) => void;

class AdaBus {
  private handlers: Map<keyof AdaEventMap, Set<(p: unknown) => void>> = new Map();

  on<K extends keyof AdaEventMap>(event: K, fn: Handler<AdaEventMap[K]>): () => void {
    let set = this.handlers.get(event);
    if (!set) { set = new Set(); this.handlers.set(event, set); }
    set.add(fn as (p: unknown) => void);
    return () => this.off(event, fn);
  }

  off<K extends keyof AdaEventMap>(event: K, fn: Handler<AdaEventMap[K]>): void {
    this.handlers.get(event)?.delete(fn as (p: unknown) => void);
  }

  emit<K extends keyof AdaEventMap>(event: K, payload: AdaEventMap[K]): void {
    this.handlers.get(event)?.forEach((fn) => fn(payload));
  }
}

export const adaBus = new AdaBus();
