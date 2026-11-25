import { describe, expect, it, vi } from "vitest";
import { type AudioLike, TimerStore } from "../src/timers";

function setup(audioState: "running" | "suspended" | null = "running", resumeWorks = true) {
  let now = 1_000_000;
  let tick: (() => void) | null = null;
  const beep = vi.fn();
  const vibrate = vi.fn();
  const audio: AudioLike | null =
    audioState === null
      ? null
      : {
          state: audioState,
          resume: vi.fn(async function (this: AudioLike) {
            if (resumeWorks) (audio as { state: string }).state = "running";
          }),
          beep,
        };
  const store = new TimerStore({
    now: () => now,
    setInterval: (fn) => {
      tick = fn;
      return 1;
    },
    clearInterval: () => {
      tick = null;
    },
    createAudio: () => audio,
    vibrate,
  });
  return {
    store,
    beep,
    vibrate,
    advance(ms: number) {
      now += ms;
      tick?.();
    },
    get ticking() {
      return tick !== null;
    },
  };
}

describe("Küchentimer", () => {
  it("läuft ab, piept und vibriert", () => {
    const env = setup();
    const timer = env.store.start("Nudeln", 1, 10);
    expect(env.ticking).toBe(true);
    env.advance(5000);
    expect(env.store.remaining(env.store.timers[0])).toBe(5000);
    env.advance(5000);
    expect(env.store.timers[0].state).toBe("done");
    expect(env.beep).toHaveBeenCalledOnce();
    expect(env.vibrate).toHaveBeenCalledOnce();
    expect(env.store.soundBlocked).toBe(false);
    expect(env.ticking).toBe(false);
    env.store.remove(timer.id);
    expect(env.store.timers).toEqual([]);
  });

  it("Pause und Fortsetzen erhalten die Restzeit", () => {
    const env = setup();
    const timer = env.store.start("Soße", 1, 60);
    env.advance(20_000);
    env.store.pause(timer.id);
    expect(env.ticking).toBe(false);
    env.advance(120_000); // Pause zählt nicht
    expect(env.store.remaining(env.store.timers[0])).toBe(40_000);
    env.store.resume(timer.id);
    env.advance(40_000);
    expect(env.store.timers[0].state).toBe("done");
  });

  it("mehrere Timer laufen unabhängig", () => {
    const env = setup();
    env.store.start("A", 1, 10);
    env.store.start("B", 2, 30);
    env.advance(10_000);
    expect(env.store.timers.map((t) => t.state)).toEqual(["done", "running"]);
    expect(env.ticking).toBe(true);
  });

  it("schaltet Audio beim Start frei (Autoplay-Sperre)", async () => {
    const env = setup("suspended", true);
    env.store.start("A", 1, 1);
    await Promise.resolve();
    await Promise.resolve();
    env.advance(1000);
    expect(env.beep).toHaveBeenCalledOnce();
    expect(env.store.soundBlocked).toBe(false);
  });

  it("zeigt Hinweis, wenn kein Ton möglich ist", async () => {
    const env = setup("suspended", false);
    env.store.start("A", 1, 1);
    await Promise.resolve();
    await Promise.resolve();
    env.advance(1000);
    expect(env.beep).not.toHaveBeenCalled();
    expect(env.store.soundBlocked).toBe(true);
    expect(env.vibrate).toHaveBeenCalledOnce(); // Vibration trotzdem

    const noAudio = setup(null);
    noAudio.store.start("B", 1, 1);
    noAudio.advance(1000);
    expect(noAudio.store.soundBlocked).toBe(true);
  });

  it("meldet Änderungen per Event", () => {
    const env = setup();
    const listener = vi.fn();
    env.store.addEventListener("change", listener);
    env.store.start("A", 1, 5);
    expect(listener).toHaveBeenCalled();
  });
});
