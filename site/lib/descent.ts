// Continuous powered-descent profile for Apollo 11 (PDI → touchdown),
// interpolated between anchor points from the Apollo 11 Mission Report
// descent trajectory. Values are representative of the documented profile.

import { hms, DESCENT_ALARMS } from "./mission";

export const PDI = hms(102, 33, 5);
export const TOUCHDOWN = hms(102, 45, 40);

// [GET sec, altitude ft, inertial velocity fps, altitude-rate fps]
const ANCHORS: [number, number, number, number][] = [
  [PDI, 49376, 5560, -4],
  [PDI + 26, 48725, 5529, -50], // throttle to full
  [hms(102, 36, 57), 44934, 4970, -100], // rotate face-up, radar lock soon after
  [hms(102, 38, 26), 39698, 4310, -125], // first 1202
  [hms(102, 39, 31), 33500, 3573, -145], // throttle down on schedule
  [hms(102, 41, 32), 7515, 1100, -125], // high gate, P64
  [hms(102, 42, 35), 3000, 470, -70],
  [hms(102, 43, 20), 500, 68, -16], // P66
  [hms(102, 44, 20), 250, 25, -9],
  [hms(102, 45, 8), 100, 10, -4], // dust visible
  [hms(102, 45, 40), 0, 0, -2], // contact
];

export type DescentState = {
  altitude: number; // ft
  velocity: number; // fps
  hdot: number; // fps (negative down)
  program: "63" | "64" | "66" | "68";
  noun: "63" | "64" | "60" | "43";
  alarm: "1201" | "1202" | null; // active alarm within flash window
  fuelPct: number; // DPS propellant remaining, rough linear burn from 100 to ~3.5%
};

export function descentState(get: number): DescentState {
  const t = Math.min(Math.max(get, PDI), TOUCHDOWN);
  let i = 0;
  while (i < ANCHORS.length - 2 && ANCHORS[i + 1][0] <= t) i++;
  const [t0, a0, v0, h0] = ANCHORS[i];
  const [t1, a1, v1, h1] = ANCHORS[i + 1];
  const f = t1 === t0 ? 0 : (t - t0) / (t1 - t0);
  const lerp = (x: number, y: number) => x + (y - x) * f;

  const program = t >= hms(102, 45, 40) ? "68" : t >= hms(102, 43, 20) ? "66" : t >= hms(102, 41, 32) ? "64" : "63";
  const noun = program === "68" ? "43" : program === "66" ? "60" : program === "64" ? "64" : "63";

  // an alarm "rings" (PROG light + V05N09 flash) for 6 s after it fires
  const active = DESCENT_ALARMS.find((a) => t >= a.get && t < a.get + 6);

  return {
    altitude: Math.max(0, lerp(a0, a1)),
    velocity: Math.max(0, lerp(v0, v1)),
    hdot: lerp(h0, h1),
    program,
    noun,
    alarm: active ? active.code : null,
    fuelPct: Math.max(3.5, 100 - ((t - PDI) / (TOUCHDOWN - PDI)) * 96.5),
  };
}

export function inDescent(get: number): boolean {
  return get >= PDI && get < TOUCHDOWN;
}
