"use client";

// Stylized Earth→Moon→Earth trajectory with a position dot driven by GET.
// Not to scale; path shape follows the mission's actual sequence of arcs.

import { MISSION_END, hms } from "@/lib/mission";

// piecewise route keyed by GET fraction over well-known segment boundaries
const SEG = {
  eoi: hms(0, 11, 42),
  tli: hms(2, 44, 16),
  loi: hms(75, 49, 50),
  pdi: hms(102, 33, 5),
  liftoff: hms(124, 22, 1),
  tei: hms(135, 23, 42),
  entry: hms(195, 3, 6),
  end: MISSION_END,
};

const EARTH = { x: 105, y: 150 };
const MOON = { x: 555, y: 60 };

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function onCircle(cx: number, cy: number, r: number, deg: number) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

// quadratic bezier point
function qbez(p0: { x: number; y: number }, p1: { x: number; y: number }, p2: { x: number; y: number }, t: number) {
  const x = (1 - t) ** 2 * p0.x + 2 * (1 - t) * t * p1.x + t ** 2 * p2.x;
  const y = (1 - t) ** 2 * p0.y + 2 * (1 - t) * t * p1.y + t ** 2 * p2.y;
  return { x, y };
}

const OUT_CTRL = { x: 330, y: 210 };
const BACK_CTRL = { x: 330, y: -30 };
const OUT_START = onCircle(EARTH.x, EARTH.y, 34, 60);
const OUT_END = onCircle(MOON.x, MOON.y, 26, 200);
const BACK_START = onCircle(MOON.x, MOON.y, 26, 340);
const BACK_END = onCircle(EARTH.x, EARTH.y, 34, -20);

export function positionAt(get: number) {
  if (get <= SEG.tli) {
    // parking orbit: sweep around Earth
    const t = get / SEG.tli;
    return onCircle(EARTH.x, EARTH.y, 34, 60 + 720 * t);
  }
  if (get <= SEG.loi) {
    const t = (get - SEG.tli) / (SEG.loi - SEG.tli);
    return qbez(OUT_START, OUT_CTRL, OUT_END, Math.pow(t, 0.75)); // fast at first, slowing uphill
  }
  if (get <= SEG.pdi) {
    const t = (get - SEG.loi) / (SEG.pdi - SEG.loi);
    return onCircle(MOON.x, MOON.y, 26, 200 + 1080 * t);
  }
  if (get <= SEG.liftoff) {
    // on the surface
    return onCircle(MOON.x, MOON.y, 20, 120);
  }
  if (get <= SEG.tei) {
    const t = (get - SEG.liftoff) / (SEG.tei - SEG.liftoff);
    return onCircle(MOON.x, MOON.y, 26, 120 + 800 * t);
  }
  if (get <= SEG.end) {
    const t = (get - SEG.tei) / (SEG.end - SEG.tei);
    return qbez(BACK_START, BACK_CTRL, BACK_END, Math.pow(t, 1.2)); // accelerating downhill
  }
  return BACK_END;
}

export default function TrajectoryMap({ get }: { get: number }) {
  const pos = positionAt(get);
  const onSurface = get > SEG.pdi && get <= SEG.liftoff;
  return (
    <svg viewBox="0 0 660 220" className="w-full" role="img" aria-label="Mission trajectory diagram">
      {/* outbound + return paths */}
      <path
        d={`M ${OUT_START.x} ${OUT_START.y} Q ${OUT_CTRL.x} ${OUT_CTRL.y} ${OUT_END.x} ${OUT_END.y}`}
        fill="none"
        stroke="currentColor"
        strokeOpacity={0.25}
        strokeDasharray="3 5"
      />
      <path
        d={`M ${BACK_START.x} ${BACK_START.y} Q ${BACK_CTRL.x} ${BACK_CTRL.y} ${BACK_END.x} ${BACK_END.y}`}
        fill="none"
        stroke="currentColor"
        strokeOpacity={0.25}
        strokeDasharray="3 5"
      />
      {/* parking + lunar orbits */}
      <circle cx={EARTH.x} cy={EARTH.y} r={34} fill="none" stroke="currentColor" strokeOpacity={0.2} />
      <circle cx={MOON.x} cy={MOON.y} r={26} fill="none" stroke="currentColor" strokeOpacity={0.2} />
      {/* bodies */}
      <circle cx={EARTH.x} cy={EARTH.y} r={20} className="fill-sky-500/80" />
      <text x={EARTH.x} y={EARTH.y + 34 + 16} textAnchor="middle" className="fill-current text-[10px] opacity-60">
        Earth
      </text>
      <circle cx={MOON.x} cy={MOON.y} r={12} className="fill-neutral-400" />
      <text x={MOON.x} y={MOON.y + 26 + 16} textAnchor="middle" className="fill-current text-[10px] opacity-60">
        Moon
      </text>
      {/* spacecraft */}
      <circle cx={pos.x} cy={pos.y} r={onSurface ? 3 : 4.5} className="fill-el">
        <animate attributeName="opacity" values="1;0.5;1" dur="1.6s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
}
