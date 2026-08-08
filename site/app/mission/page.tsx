"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { CaretLeft, CaretRight, MoonStars, Pause, Play, Gauge } from "@phosphor-icons/react";
import DSKY from "@/components/DSKY";
import TrajectoryMap from "@/components/TrajectoryMap";
import {
  DESCENT_ALARMS,
  EVENTS,
  MISSION_END,
  PHASES,
  eventAt,
  fmtGET,
  fmtWallClock,
  hms,
  phaseAt,
  type DskyState,
} from "@/lib/mission";
import { PDI, TOUCHDOWN, descentState, inDescent } from "@/lib/descent";

type PlayMode = null | "descent" | "tour";

const pad5 = (n: number) => {
  const v = Math.round(Math.abs(n));
  return `${n < 0 ? "-" : "+"}${String(Math.min(v, 99999)).padStart(5, "0")}`;
};

export default function MissionPage() {
  const [get, setGet] = useState(0);
  const [play, setPlay] = useState<PlayMode>(null);
  const [descentSpeed, setDescentSpeed] = useState(8);
  const [compActy, setCompActy] = useState(false);

  // -- user DSKY entry state
  const [buffer, setBuffer] = useState<string>(""); // e.g. "V16N65"
  const [entryMode, setEntryMode] = useState<null | "verb" | "noun">(null);
  const [userMonitor, setUserMonitor] = useState<null | { verb: string; noun: string }>(null);
  const [oprErr, setOprErr] = useState(false);
  const [lampTest, setLampTest] = useState(false);
  const [pressedKey, setPressedKey] = useState<string | null>(null);

  const raf = useRef<number | null>(null);
  const lastT = useRef<number | null>(null);
  const tourTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // animation loop for descent playback
  useEffect(() => {
    if (play !== "descent") return;
    const step = (t: number) => {
      if (lastT.current == null) lastT.current = t;
      const dt = (t - lastT.current) / 1000;
      lastT.current = t;
      setGet((g) => {
        const ng = g + dt * descentSpeed;
        if (ng >= TOUCHDOWN + 8) {
          setPlay(null);
          return TOUCHDOWN;
        }
        return ng;
      });
      raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
      lastT.current = null;
    };
  }, [play, descentSpeed]);

  // tour mode: step through events
  useEffect(() => {
    if (play !== "tour") return;
    const idx = EVENTS.findIndex((e) => e.get > get);
    if (idx === -1) {
      setPlay(null);
      return;
    }
    tourTimer.current = setTimeout(() => setGet(EVENTS[idx].get), 5000);
    return () => {
      if (tourTimer.current) clearTimeout(tourTimer.current);
    };
  }, [play, get]);

  // COMP ACTY flicker, busier during descent. Under prefers-reduced-motion the
  // lamp holds steady-on during descent (state, not animation) instead of flickering.
  useEffect(() => {
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setCompActy(inDescent(get));
      return;
    }
    const id = setInterval(
      () => setCompActy((c) => (Math.random() < (inDescent(get) ? 0.65 : 0.25) ? !c : c)),
      280
    );
    return () => clearInterval(id);
  }, [get]);

  const ev = eventAt(get);
  const phase = phaseAt(get);
  const wall = fmtWallClock(get);
  const descent = inDescent(get) ? descentState(get) : null;

  // -- scripted DSKY state for "now"
  const scripted: DskyState = useMemo(() => {
    if (descent) {
      if (descent.alarm) {
        return {
          prog: descent.program,
          verb: "05",
          noun: "09",
          r1: `+0${descent.alarm}`,
          r2: "+00000",
          r3: "+00000",
          lights: ["PROG"],
          flash: true,
        };
      }
      if (descent.program === "64") {
        return {
          prog: "64",
          verb: "06",
          noun: "64",
          r1: pad5(descent.velocity),
          r2: pad5(descent.hdot),
          r3: pad5(descent.altitude),
        };
      }
      if (descent.program === "66") {
        return {
          prog: "66",
          verb: "06",
          noun: "60",
          r1: pad5(Math.min(descent.velocity, 99)),
          r2: pad5(descent.hdot),
          r3: pad5(descent.altitude),
        };
      }
      return {
        prog: descent.program,
        verb: "06",
        noun: "63",
        r1: pad5(descent.velocity),
        r2: pad5(descent.hdot),
        r3: pad5(descent.altitude),
      };
    }
    return ev.dsky;
  }, [descent, ev]);

  // -- user monitor displays override the scripted state
  const displayed: DskyState = useMemo(() => {
    const lights = [...(scripted.lights ?? [])];
    if (oprErr) lights.push("OPR ERR");
    if (lampTest)
      return {
        prog: "88",
        verb: "88",
        noun: "88",
        r1: "+88888",
        r2: "+88888",
        r3: "+88888",
        lights: ["UPLINK", "TEMP", "NO ATT", "GIMBAL", "STBY", "PROG", "KEY REL", "RESTART", "OPR ERR", "TRACKER", "ALT", "VEL"],
      };
    if (userMonitor) {
      const { verb, noun } = userMonitor;
      if (verb === "16" && noun === "65") {
        // mission clock
        return {
          prog: scripted.prog,
          verb,
          noun,
          r1: pad5(Math.floor(get / 3600)),
          r2: pad5(Math.floor((get % 3600) / 60)),
          r3: pad5(Math.floor(get % 60)),
          lights,
        };
      }
      if (verb === "16" && noun === "63" && descent) {
        return {
          prog: scripted.prog,
          verb,
          noun,
          r1: pad5(descent.velocity),
          r2: pad5(descent.hdot),
          r3: pad5(descent.altitude),
          lights,
        };
      }
      if (verb === "05" && noun === "09") {
        const past = DESCENT_ALARMS.filter((a) => a.get <= get);
        const last = past[past.length - 1];
        return {
          prog: scripted.prog,
          verb,
          noun,
          r1: last ? `+0${last.code}` : "+00000",
          r2: past.length > 1 ? `+0${past[past.length - 2].code}` : "+00000",
          r3: "+00000",
          lights,
        };
      }
    }
    // entry-in-progress: show partial verb/noun being keyed
    if (buffer) {
      const v = buffer.match(/V(\d{0,2})/)?.[1] ?? scripted.verb;
      const n = buffer.match(/N(\d{0,2})/)?.[1] ?? "";
      return { ...scripted, verb: v.padEnd(2, " "), noun: n.padEnd(2, " "), lights };
    }
    return { ...scripted, lights };
  }, [scripted, userMonitor, oprErr, lampTest, buffer, get, descent]);

  const handleKey = useCallback(
    (k: string) => {
      setPressedKey(k);
      setTimeout(() => setPressedKey(null), 150);
      if (k === "RSET") {
        setOprErr(false);
        setLampTest(false);
        return;
      }
      if (k === "KEY REL") {
        setBuffer("");
        setEntryMode(null);
        setUserMonitor(null);
        return;
      }
      if (k === "CLR") {
        setBuffer("");
        setEntryMode(null);
        return;
      }
      if (k === "VERB") {
        setBuffer("V");
        setEntryMode("verb");
        return;
      }
      if (k === "NOUN") {
        setBuffer((b) => (b.startsWith("V") ? b.replace(/N\d*/, "") + "N" : "N"));
        setEntryMode("noun");
        return;
      }
      if (/^\d$/.test(k)) {
        if (!entryMode) return;
        setBuffer((b) => {
          const part = entryMode === "verb" ? b.match(/V(\d*)/)?.[1] ?? "" : b.match(/N(\d*)/)?.[1] ?? "";
          if (part.length >= 2) return b;
          return entryMode === "verb" ? b.replace(/V\d*/, `V${part}${k}`) : b.replace(/N\d*/, `N${part}${k}`);
        });
        return;
      }
      if (k === "ENTR") {
        const v = buffer.match(/V(\d{2})/)?.[1];
        const n = buffer.match(/N(\d{2})/)?.[1];
        setBuffer("");
        setEntryMode(null);
        if (v === "35") {
          // lamp test
          setLampTest(true);
          setTimeout(() => setLampTest(false), 4000);
          return;
        }
        if ((v === "16" && (n === "65" || n === "63")) || (v === "05" && n === "09")) {
          if (n === "63" && !descent) {
            setOprErr(true);
            return;
          }
          setUserMonitor({ verb: v!, noun: n! });
          return;
        }
        setOprErr(true);
        return;
      }
      if (k === "PRO" || k === "+" || k === "-") {
        // accepted silently, like a patient machine
        return;
      }
    },
    [buffer, entryMode, descent]
  );

  const jump = (idx: number) => {
    setPlay(null);
    setGet(EVENTS[idx].get);
    setUserMonitor(null);
  };
  const evIdx = EVENTS.indexOf(ev);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Apollo 11, as the computer flew it</h1>
          <p className="mt-1 max-w-2xl text-sm opacity-70">
            Scrub the eight-day mission and watch what the Apollo Guidance Computer was running at every moment:
            the same Luminary 099 / Colossus 2A software we reassembled bit-for-bit and ran in{" "}
            <Link href="/#claim-15" className="underline">
              claim&nbsp;#15
            </Link>
            . The DSKY below is live: try <span className="font-mono">VERB 1 6 NOUN 6 5 ENTR</span> for the mission
            clock, or <span className="font-mono">VERB 3 5 ENTR</span> for the lamp test.
          </p>
        </div>
        <Link href="/" className="text-sm underline opacity-70 hover:opacity-100">
          ← All 12 claims
        </Link>
      </header>

      {/* clocks + controls */}
      <div className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border border-neutral-700/60 bg-neutral-900/40 px-4 py-3">
        <div>
          <div className="text-[10px] uppercase tracking-widest opacity-50">Ground elapsed time</div>
          <div className="dseg text-xl text-el">{fmtGET(get)}</div>
        </div>
        <div className="text-sm opacity-70">
          <div>{wall.edt}</div>
          <div className="opacity-60">{wall.utc}</div>
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <button onClick={() => jump(Math.max(0, evIdx - 1))} className="btn-ctl inline-flex items-center gap-1.5" aria-label="Previous event">
            <CaretLeft size={14} weight="bold" aria-hidden /> Prev
          </button>
          <button onClick={() => jump(Math.min(EVENTS.length - 1, evIdx + 1))} className="btn-ctl inline-flex items-center gap-1.5" aria-label="Next event">
            Next <CaretRight size={14} weight="bold" aria-hidden />
          </button>
          <button
            onClick={() => setPlay(play === "tour" ? null : "tour")}
            className={`btn-ctl inline-flex items-center gap-1.5 ${play === "tour" ? "border-el text-el" : ""}`}
          >
            {play === "tour" ? <><Pause size={14} weight="fill" aria-hidden /> Stop tour</> : <><Play size={14} weight="fill" aria-hidden /> Tour the mission</>}
          </button>
          <button
            onClick={() => {
              if (play === "descent") setPlay(null);
              else {
                setGet(PDI - 0.1 >= 0 ? PDI : 0);
                setPlay("descent");
              }
            }}
            className={`btn-ctl inline-flex items-center gap-1.5 ${play === "descent" ? "border-amber-400 text-amber-300" : "border-amber-500/60 text-amber-200"}`}
          >
            {play === "descent" ? <><Pause size={14} weight="fill" aria-hidden /> Stop descent</> : <><MoonStars size={14} weight="fill" aria-hidden /> Fly the landing</>}
          </button>
          {play === "descent" && (
            <button onClick={() => setDescentSpeed((s) => (s === 8 ? 1 : 8))} className="btn-ctl inline-flex items-center gap-1.5">
              <Gauge size={14} aria-hidden /> {descentSpeed === 8 ? "Slow to real time" : "Back to 8x speed"}
            </button>
          )}
        </div>
      </div>

      {/* scrubber */}
      <div className="mb-6">
        <div className="relative h-2 w-full overflow-hidden rounded-full">
          {PHASES.map((p) => (
            <div
              key={p.id}
              className={`absolute top-0 h-full ${p.id === phase.id ? "bg-el/60" : "bg-neutral-700/60"}`}
              style={{
                left: `${(p.start / MISSION_END) * 100}%`,
                width: `${((p.end - p.start) / MISSION_END) * 100}%`,
              }}
              title={p.label}
            />
          ))}
        </div>
        <input
          type="range"
          min={0}
          max={MISSION_END}
          step={10}
          value={get}
          onChange={(e) => {
            setPlay(null);
            setGet(Number(e.target.value));
          }}
          className="mt-[-8px] block w-full cursor-pointer appearance-none bg-transparent"
          aria-label="Mission time scrubber"
        />
        <div className="relative mt-1 h-4 text-[9px] opacity-60">
          {EVENTS.map((e, i) => (
            <button
              key={i}
              onClick={() => jump(i)}
              className="absolute -translate-x-1/2 hover:text-el"
              style={{ left: `${(e.get / MISSION_END) * 100}%` }}
              title={`${fmtGET(e.get)} ${e.title}`}
            >
              <span aria-hidden className="block h-2 w-px bg-current" />
            </button>
          ))}
        </div>
        <div className="mt-1 flex justify-between text-[10px] uppercase tracking-widest opacity-50">
          {PHASES.map((p) => (
            <span key={p.id}>{p.label}</span>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* event card */}
        <section className="rounded-lg border border-neutral-700/60 bg-neutral-900/40 p-5">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-widest opacity-60">
            <span>{fmtGET(ev.get)}</span>
            <span>·</span>
            <span>{phase.label}</span>
          </div>
          <h2 className="mt-1 text-xl font-bold">{descent && !descent.alarm ? "Powered descent" : ev.title}</h2>
          <div className="mt-2 flex items-center gap-2 text-xs">
            <span className="rounded bg-el/15 px-2 py-0.5 font-mono text-el">{ev.computer}</span>
            <span className="font-mono opacity-80">{descent ? `P${descent.program}` : ev.program}</span>
          </div>
          <p className="mt-3 text-sm leading-relaxed opacity-90">{ev.narration}</p>
          <div className="mt-3 rounded-md border border-el/20 bg-el/5 p-3 text-sm leading-relaxed">
            <div className="mb-1 text-[10px] uppercase tracking-widest text-el/70">What the computer is doing</div>
            {ev.computing}
          </div>
          {ev.quote && (
            <blockquote className="mt-3 border-l-2 border-neutral-500 pl-3 text-sm italic opacity-80">
              “{ev.quote.text}” <span className="not-italic opacity-60">{ev.quote.who}</span>
            </blockquote>
          )}

          {descent && (
            <div className="mt-4 grid grid-cols-3 gap-3 text-center">
              <div className="rounded-md bg-neutral-800/70 p-2">
                <div className="text-[10px] uppercase tracking-widest opacity-50">Altitude</div>
                <div className="dseg text-lg text-el">{Math.round(descent.altitude).toLocaleString()}</div>
                <div className="text-[10px] opacity-50">feet</div>
              </div>
              <div className="rounded-md bg-neutral-800/70 p-2">
                <div className="text-[10px] uppercase tracking-widest opacity-50">Velocity</div>
                <div className="dseg text-lg text-el">{Math.round(descent.velocity).toLocaleString()}</div>
                <div className="text-[10px] opacity-50">ft/s</div>
              </div>
              <div className="rounded-md bg-neutral-800/70 p-2">
                <div className="text-[10px] uppercase tracking-widest opacity-50">DPS fuel</div>
                <div className="dseg text-lg text-el">{descent.fuelPct.toFixed(1)}</div>
                <div className="text-[10px] opacity-50">% remaining</div>
              </div>
            </div>
          )}
        </section>

        {/* DSKY */}
        <section>
          <DSKY state={displayed} compActy={compActy} onKey={handleKey} pressedKey={pressedKey} />
          <p className="mt-2 text-center text-[11px] opacity-50">
            Register values are representative reconstructions from mission documentation; alarms, programs, and event
            times follow the flight record.
          </p>
        </section>
      </div>

      {/* trajectory */}
      <section className="mt-8 rounded-lg border border-neutral-700/60 bg-neutral-900/40 p-4 text-neutral-300">
        <TrajectoryMap get={get} />
      </section>

      <footer className="mt-8 text-center text-xs opacity-60">
        The flight software in this story is real and public:{" "}
        <a className="underline" href="https://github.com/theryanbyrd/apollo-forensics/tree/main/claims/15-agc">
          we reassembled and ran it in claim #15
        </a>
        .
      </footer>
    </main>
  );
}
