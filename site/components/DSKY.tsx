"use client";

// The DSKY (Display & Keyboard), the astronauts' interface to the AGC.
// Layout mirrors the flight unit: caution/status annunciators on the left,
// COMP ACTY + PROG / VERB / NOUN + three signed 5-digit registers on the right,
// 19-key keyboard below. Digits render in DSEG7 (EL-segment style).

import { useEffect, useRef, useState } from "react";
import type { DskyState } from "@/lib/mission";

const LIGHTS: { id: string; label: string }[] = [
  { id: "UPLINK", label: "UPLINK ACTY" },
  { id: "TEMP", label: "TEMP" },
  { id: "NO ATT", label: "NO ATT" },
  { id: "GIMBAL", label: "GIMBAL LOCK" },
  { id: "STBY", label: "STBY" },
  { id: "PROG", label: "PROG" },
  { id: "KEY REL", label: "KEY REL" },
  { id: "RESTART", label: "RESTART" },
  { id: "OPR ERR", label: "OPR ERR" },
  { id: "TRACKER", label: "TRACKER" },
  { id: "BLANK1", label: "" },
  { id: "ALT", label: "ALT" },
  { id: "BLANK2", label: "" },
  { id: "VEL", label: "VEL" },
];

function Seg({ text, className = "" }: { text: string; className?: string }) {
  // render sign+digits in DSEG7; spaces stay blank, "8" ghost behind for EL feel
  return (
    <span className={`dseg relative inline-block ${className}`}>
      <span aria-hidden className="absolute inset-0 opacity-[0.07] select-none">
        {text.replace(/[+-]/g, "8").replace(/[0-9]/g, "8")}
      </span>
      <span className="relative">{text}</span>
    </span>
  );
}

export type DskyOverride = {
  state: DskyState;
  compActy?: boolean;
};

export default function DSKY({
  state,
  compActy = false,
  onKey,
  pressedKey,
}: {
  state: DskyState;
  compActy?: boolean;
  onKey?: (k: string) => void;
  pressedKey?: string | null;
}) {
  const [flashOn, setFlashOn] = useState(true);
  const flashTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    flashTimer.current = setInterval(() => setFlashOn((f) => !f), 750);
    return () => {
      if (flashTimer.current) clearInterval(flashTimer.current);
    };
  }, []);

  const lightsOn = new Set(state.lights ?? []);
  const vnVisible = !state.flash || flashOn;

  const KEYS: string[][] = [
    ["VERB", "+", "7", "8", "9", "CLR"],
    ["NOUN", "-", "4", "5", "6", "PRO"],
    ["", "0", "1", "2", "3", "KEY REL"],
    ["", "", "", "ENTR", "RSET", ""],
  ];

  return (
    <div className="dsky select-none rounded-lg border border-neutral-700 bg-neutral-900 p-4 shadow-2xl">
      <div className="flex gap-4">
        {/* annunciator panel */}
        <div className="grid w-28 sm:w-36 grid-cols-2 content-start gap-1">
          {LIGHTS.map((l) => (
            <div
              key={l.id}
              className={`flex h-8 items-center justify-center rounded-sm border text-center text-[9px] font-bold leading-tight tracking-wide ${
                l.label === ""
                  ? "border-neutral-800 bg-neutral-800/50"
                  : lightsOn.has(l.id) || lightsOn.has(l.label)
                    ? l.id === "PROG" || l.id === "OPR ERR" || l.id === "RESTART"
                      ? "border-amber-300 bg-amber-400 text-black shadow-[0_0_14px_rgba(251,191,36,0.9)]"
                      : "border-neutral-200 bg-neutral-100 text-black"
                    : "border-neutral-700 bg-neutral-800 text-neutral-400"
              }`}
            >
              {l.label}
            </div>
          ))}
        </div>

        {/* EL display panel */}
        <div className="flex-1 rounded-md border border-neutral-700 bg-[#050807] p-3">
          <div className="flex items-start justify-between">
            <div
              className={`flex h-10 w-16 items-center justify-center rounded-sm text-[10px] font-bold tracking-widest ${
                compActy ? "bg-el/90 text-black shadow-[0_0_18px_rgba(94,255,205,0.8)]" : "bg-neutral-900 text-neutral-600"
              }`}
            >
              COMP
              <br />
              ACTY
            </div>
            <div className="text-right">
              <div className="dsky-label">PROG</div>
              <Seg text={state.prog} className="text-2xl sm:text-3xl text-el" />
            </div>
          </div>

          <div className="mt-2 flex justify-between">
            <div>
              <div className="dsky-label">VERB</div>
              <Seg text={vnVisible ? state.verb : "  "} className="text-2xl sm:text-3xl text-el" />
            </div>
            <div className="text-right">
              <div className="dsky-label">NOUN</div>
              <Seg text={vnVisible ? state.noun : "  "} className="text-2xl sm:text-3xl text-el" />
            </div>
          </div>

          {[state.r1, state.r2, state.r3].map((r, i) => (
            <div key={i} className="mt-1 border-t border-el/40 pt-1 text-right">
              <Seg text={r} className="text-2xl sm:text-3xl tracking-wider text-el" />
            </div>
          ))}
        </div>
      </div>

      {/* keyboard */}
      <div className="mt-4 grid grid-cols-6 gap-1.5">
        {KEYS.flat().map((k, i) =>
          k === "" ? (
            <div key={i} />
          ) : (
            <button
              key={i}
              onClick={() => onKey?.(k)}
              className={`h-11 rounded-md border text-xs font-bold transition-all ${
                pressedKey === k
                  ? "border-el bg-el/20 text-el"
                  : "border-neutral-600 bg-neutral-800 text-neutral-200 hover:border-neutral-400 active:translate-y-px"
              } ${k.length > 2 ? "text-[10px]" : "text-sm"}`}
            >
              {k}
            </button>
          )
        )}
      </div>
    </div>
  );
}
