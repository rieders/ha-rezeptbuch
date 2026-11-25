// Küchentimer: globaler Speicher auf Modulebene – laufende Timer überleben den Wechsel
// zwischen Ansichten im Panel (und das Neu-Rendern der Panel-Komponente).
//
// Ton: Browser erlauben Audio erst nach einer Nutzerinteraktion. Deshalb wird der
// AudioContext beim Klick auf „Timer starten“ erzeugt/fortgesetzt („freigeschaltet“).
// Gelingt das nicht, zeigt die Oberfläche einen sichtbaren Hinweis (soundBlocked).

export type TimerState = "running" | "paused" | "done";

export interface KitchenTimer {
  id: string;
  label: string;
  recipeId: number;
  durationMs: number;
  endsAt: number | null; // bei running
  remainingMs: number; // bei paused/done
  state: TimerState;
}

export interface AudioLike {
  state: string;
  resume(): Promise<void>;
  beep(): void;
}

export interface TimerEnv {
  now(): number;
  setInterval(fn: () => void, ms: number): unknown;
  clearInterval(handle: unknown): void;
  createAudio(): AudioLike | null;
  vibrate(pattern: number[]): void;
}

export class TimerStore extends EventTarget {
  timers: KitchenTimer[] = [];
  soundBlocked = false;
  private handle: unknown = null;
  private audio: AudioLike | null = null;
  private seq = 0;

  constructor(private readonly env: TimerEnv) {
    super();
  }

  /** Muss aus einem Klick-Handler aufgerufen werden (Audio-Freischaltung). */
  start(label: string, recipeId: number, seconds: number): KitchenTimer {
    this.unlockAudio();
    const timer: KitchenTimer = {
      id: `t${++this.seq}`,
      label,
      recipeId,
      durationMs: seconds * 1000,
      endsAt: this.env.now() + seconds * 1000,
      remainingMs: seconds * 1000,
      state: "running",
    };
    this.timers = [...this.timers, timer];
    this.ensureTicking();
    this.changed();
    return timer;
  }

  pause(id: string): void {
    this.update(id, (t) =>
      t.state === "running" ? { ...t, state: "paused", remainingMs: this.remaining(t), endsAt: null } : t,
    );
    this.stopTickingIfIdle();
  }

  resume(id: string): void {
    this.unlockAudio();
    this.update(id, (t) =>
      t.state === "paused" ? { ...t, state: "running", endsAt: this.env.now() + t.remainingMs } : t,
    );
    this.ensureTicking();
  }

  remove(id: string): void {
    this.timers = this.timers.filter((t) => t.id !== id);
    this.stopTickingIfIdle();
    this.changed();
  }

  remaining(t: KitchenTimer): number {
    return t.state === "running" && t.endsAt !== null ? Math.max(0, t.endsAt - this.env.now()) : t.remainingMs;
  }

  /** Wird regelmäßig aufgerufen; berechnet anhand der Uhrzeit (robust gegen gedrosselte Tabs). */
  tick(): void {
    let finished = false;
    this.timers = this.timers.map((t) => {
      if (t.state === "running" && this.remaining(t) <= 0) {
        finished = true;
        return { ...t, state: "done", remainingMs: 0, endsAt: null };
      }
      return t;
    });
    if (finished) this.alarm();
    this.stopTickingIfIdle();
    this.changed();
  }

  private alarm(): void {
    this.env.vibrate([400, 200, 400, 200, 400]);
    if (this.audio && this.audio.state === "running") {
      this.audio.beep();
      this.soundBlocked = false;
    } else {
      this.soundBlocked = true;
    }
  }

  private unlockAudio(): void {
    try {
      this.audio ??= this.env.createAudio();
      if (!this.audio) {
        this.soundBlocked = true;
        return;
      }
      if (this.audio.state !== "running") {
        this.audio
          .resume()
          .then(() => {
            this.soundBlocked = this.audio?.state !== "running";
            this.changed();
          })
          .catch(() => {
            this.soundBlocked = true;
            this.changed();
          });
      } else {
        this.soundBlocked = false;
      }
    } catch {
      this.soundBlocked = true;
    }
  }

  private update(id: string, fn: (t: KitchenTimer) => KitchenTimer): void {
    this.timers = this.timers.map((t) => (t.id === id ? fn(t) : t));
    this.changed();
  }

  private ensureTicking(): void {
    if (this.handle === null && this.timers.some((t) => t.state === "running")) {
      this.handle = this.env.setInterval(() => this.tick(), 500);
    }
  }

  private stopTickingIfIdle(): void {
    if (this.handle !== null && !this.timers.some((t) => t.state === "running")) {
      this.env.clearInterval(this.handle);
      this.handle = null;
    }
  }

  private changed(): void {
    this.dispatchEvent(new Event("change"));
  }
}

/** Ton ohne externe Datei: kurze Sinus-Pieptöne über WebAudio. */
function browserAudio(): AudioLike | null {
  const Ctor =
    (globalThis as { AudioContext?: typeof AudioContext }).AudioContext ??
    (globalThis as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return null;
  const ctx = new Ctor();
  return {
    get state() {
      return ctx.state;
    },
    resume: () => ctx.resume(),
    beep() {
      const start = ctx.currentTime;
      for (let i = 0; i < 3; i++) {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.value = 880;
        gain.gain.setValueAtTime(0.0001, start + i * 0.6);
        gain.gain.exponentialRampToValueAtTime(0.4, start + i * 0.6 + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + i * 0.6 + 0.4);
        osc.connect(gain).connect(ctx.destination);
        osc.start(start + i * 0.6);
        osc.stop(start + i * 0.6 + 0.45);
      }
    },
  };
}

export const timerStore = new TimerStore({
  now: () => Date.now(),
  setInterval: (fn, ms) => globalThis.setInterval(fn, ms),
  clearInterval: (h) => globalThis.clearInterval(h as ReturnType<typeof setInterval>),
  createAudio: browserAudio,
  vibrate: (pattern) => {
    try {
      (globalThis.navigator as Navigator | undefined)?.vibrate?.(pattern);
    } catch {
      /* nicht unterstützt */
    }
  },
});
