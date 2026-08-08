// Apollo 11 mission timeline, keyed by Ground Elapsed Time (GET, seconds).
// Launch: July 16 1969, 09:32:00 EDT = 13:32:00 UTC = GET 000:00:00.
// Event times from the Apollo 11 Flight Journal / Mission Report; DSKY register
// values are representative reconstructions from mission documentation (noted in UI).

export type DskyState = {
  prog: string;
  verb: string;
  noun: string;
  r1: string; // 6 chars: sign + 5 digits, spaces allowed
  r2: string;
  r3: string;
  lights?: string[]; // active caution/status light ids
  flash?: boolean; // VERB/NOUN flashing (awaiting crew response)
};

export type MissionEvent = {
  get: number; // seconds
  title: string;
  phase: PhaseId;
  computer: "CMC" | "LGC" | "Saturn IU";
  program: string; // e.g. "P63 · Braking phase"
  narration: string; // what is happening on the mission
  computing: string; // what the guidance computer is doing right now
  dsky: DskyState;
  quote?: { text: string; who: string };
};

export type PhaseId =
  | "launch"
  | "translunar"
  | "lunar-orbit"
  | "descent"
  | "surface"
  | "return"
  | "entry";

export const PHASES: { id: PhaseId; label: string; start: number; end: number }[] = [
  { id: "launch", label: "Launch", start: 0, end: hms(2, 44, 16) },
  { id: "translunar", label: "Translunar coast", start: hms(2, 44, 16), end: hms(75, 49, 50) },
  { id: "lunar-orbit", label: "Lunar orbit", start: hms(75, 49, 50), end: hms(102, 33, 5) },
  { id: "descent", label: "Descent", start: hms(102, 33, 5), end: hms(102, 45, 40) },
  { id: "surface", label: "On the surface", start: hms(102, 45, 40), end: hms(124, 22, 1) },
  { id: "return", label: "Return", start: hms(124, 22, 1), end: hms(195, 3, 6) },
  { id: "entry", label: "Entry", start: hms(195, 3, 6), end: hms(195, 18, 35) },
];

export function hms(h: number, m: number, s: number): number {
  return h * 3600 + m * 60 + s;
}

export function fmtGET(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  return `${String(h).padStart(3, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

const LAUNCH_UTC = Date.UTC(1969, 6, 16, 13, 32, 0);

export function fmtWallClock(sec: number): { edt: string; utc: string } {
  const d = new Date(LAUNCH_UTC + sec * 1000);
  const utc = d.toISOString().slice(0, 16).replace("T", " ") + " UTC";
  const e = new Date(LAUNCH_UTC + sec * 1000 - 4 * 3600 * 1000);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const edt = `${months[e.getUTCMonth()]} ${e.getUTCDate()}, ${String(e.getUTCHours()).padStart(2, "0")}:${String(
    e.getUTCMinutes()
  ).padStart(2, "0")} EDT`;
  return { edt, utc };
}

export const EVENTS: MissionEvent[] = [
  {
    get: 0,
    title: "Liftoff",
    phase: "launch",
    computer: "CMC",
    program: "P11 · Earth orbit insertion monitor",
    narration:
      "The Saturn V leaves Pad 39A with Armstrong, Aldrin, and Collins. The Saturn's own Instrument Unit flies the ascent; the Command Module Computer runs P11, monitoring the ride and standing by to take over an abort.",
    computing:
      "P11 integrates the IMU accelerometers and displays inertial velocity, altitude rate, and altitude: the crew's independent check on the Saturn's guidance.",
    dsky: { prog: "11", verb: "06", noun: "62", r1: "+00223", r2: "+00114", r3: "+00007" },
    quote: { text: "Roger. Clock. We have a roll program.", who: "Neil Armstrong" },
  },
  {
    get: hms(0, 11, 42),
    title: "Earth orbit insertion",
    phase: "launch",
    computer: "CMC",
    program: "P11 → P00",
    narration:
      "S-IVB cutoff. Apollo 11 is in a 103-nautical-mile parking orbit at 25,568 ft/s. Two and a half revolutions to check every system before committing to the Moon.",
    computing:
      "P11 confirms insertion velocity against the target, then the crew keys V37E 00E and the CMC drops to P00, its background job: integrating the state vector and keeping the platform aligned.",
    dsky: { prog: "00", verb: "06", noun: "62", r1: "+25568", r2: "+00000", r3: "+00103" },
  },
  {
    get: hms(2, 44, 16),
    title: "Translunar injection",
    phase: "translunar",
    computer: "Saturn IU",
    program: "P15 · TLI monitor",
    narration:
      "Over the Pacific, the S-IVB reignites for 5 minutes 47 seconds, pushing the stack from 25,500 to 35,545 ft/s, leaving Earth orbit for the Moon.",
    computing:
      "The Saturn Instrument Unit flies the burn. The CMC's P15 monitors it: comparing sensed acceleration against the expected TLI profile, ready to hand the crew manual cues if the Saturn's guidance drifts.",
    dsky: { prog: "15", verb: "06", noun: "95", r1: "+00547", r2: "+35545", r3: "+10435" },
    quote: { text: "Apollo 11, this is Houston. You are Go for TLI.", who: "CapCom Bruce McCandless" },
  },
  {
    get: hms(3, 24, 3),
    title: "Transposition and docking",
    phase: "translunar",
    computer: "CMC",
    program: "P00 + digital autopilot",
    narration:
      "Collins separates Columbia, turns her around, and docks nose-to-nose with Eagle, still stowed atop the S-IVB, then pulls the LM free for the coast to the Moon.",
    computing:
      "The CMC's digital autopilot holds attitude deadbands while Collins flies the docking by hand; the computer meters RCS pulses a few at a time.",
    dsky: { prog: "00", verb: "06", noun: "18", r1: "+18021", r2: "+00354", r3: "+00191" },
  },
  {
    get: hms(26, 44, 58),
    title: "Midcourse correction 2",
    phase: "translunar",
    computer: "CMC",
    program: "P30 / P40 · External ΔV + SPS burn",
    narration:
      "The only midcourse correction the trajectory needs: a 3-second Service Propulsion System burn, 20.9 ft/s. The free-return path is that clean.",
    computing:
      "P30 accepts the ground-computed ΔV target; P40 steers the burn with cross-product steering, the same guidance law that will fly the lunar landing, and cuts off within 0.1 ft/s.",
    dsky: { prog: "40", verb: "06", noun: "40", r1: "+00003", r2: "+00209", r3: "+00021", flash: true },
  },
  {
    get: hms(53, 0, 0),
    title: "Platform realign, star sightings",
    phase: "translunar",
    computer: "CMC",
    program: "P52 · IMU realign",
    narration:
      "Housekeeping on the way out: Collins takes sextant marks on Acrux and Antares to correct the slow drift of the inertial platform's gyros.",
    computing:
      "P52 turns two star sightings into a torquing solution: it computes the angle between the measured and stored star vectors and precesses the gyros until the platform agrees with the sky to hundredths of a degree.",
    dsky: { prog: "52", verb: "06", noun: "93", r1: "+00012", r2: "-00034", r3: "+00009" },
  },
  {
    get: hms(75, 49, 50),
    title: "Lunar orbit insertion",
    phase: "lunar-orbit",
    computer: "CMC",
    program: "P40 · SPS burn",
    narration:
      "Behind the Moon, out of contact with Earth, the SPS burns retrograde for 357 seconds. When Apollo 11 reappears around the limb, it is in lunar orbit, 60 by 170 nautical miles.",
    computing:
      "No ground can help behind the Moon: the CMC alone integrates the burn, steering the 20,500-lb engine with cross-product guidance and counting down ΔV-to-go on the DSKY.",
    dsky: { prog: "40", verb: "06", noun: "40", r1: "+00357", r2: "+02917", r3: "+00062" },
  },
  {
    get: hms(100, 12, 0),
    title: "Undocking: the Eagle has wings",
    phase: "lunar-orbit",
    computer: "LGC",
    program: "P00 → P30",
    narration:
      "Armstrong and Aldrin cast off in Eagle. Collins inspects the lander from Columbia's windows as the two ships fly formation 60 miles above the Moon.",
    computing:
      "Eagle's own computer, the LGC running Luminary 099, now owns the mission. It carries its own state vector, its own platform, its own landing targets.",
    dsky: { prog: "00", verb: "06", noun: "36", r1: "+00100", r2: "+00012", r3: "+00000" },
    quote: { text: "The Eagle has wings.", who: "Neil Armstrong" },
  },
  {
    get: hms(101, 36, 14),
    title: "Descent orbit insertion",
    phase: "lunar-orbit",
    computer: "LGC",
    program: "P40 · DPS burn",
    narration:
      "Behind the Moon again: a gentle 30-second burn of the descent engine drops Eagle's orbit to 50,000 feet above the Sea of Tranquility. The landing starts here.",
    computing:
      "P40 throttles the descent engine to 10%, then 40%: the LGC's first live test of the engine it will soon fly to the surface.",
    dsky: { prog: "40", verb: "06", noun: "40", r1: "+00030", r2: "+00762", r3: "+00499" },
  },
  // --- Powered descent: handled continuously by the descent simulator between
  //     PDI (102:33:05) and touchdown (102:45:40). These are its anchor events.
  {
    get: hms(102, 33, 5),
    title: "Powered descent ignition",
    phase: "descent",
    computer: "LGC",
    program: "P63 · Braking phase",
    narration:
      "At 49,376 feet, the descent engine lights. Twelve minutes to the surface. Every second from here on, the computer solves the landing problem from scratch.",
    computing:
      "P63 runs the guidance loop every 2 seconds: read accelerometers, update state, solve the quadratic guidance polynomial for the throttle and attitude that reach high gate, while the Executive juggles a dozen lower-priority jobs around it.",
    dsky: { prog: "63", verb: "06", noun: "63", r1: "+05560", r2: "-00038", r3: "+49376" },
  },
  {
    get: hms(102, 38, 26),
    title: "Program alarm 1202",
    phase: "descent",
    computer: "LGC",
    program: "P63 + BAILOUT",
    narration:
      "A checklist error left the rendezvous radar feeding the computer phantom work, stealing ~13% of its cycles. The Executive runs out of core sets, and does exactly what it was designed to do.",
    computing:
      "BAILOUT: the Executive sheds every job that isn't guidance, flushes its task queues, and restarts the essential ones from checkpoints. Steering never hiccups. In Houston, 26-year-old Steve Bales calls \"GO\" in seconds.",
    dsky: {
      prog: "63",
      verb: "05",
      noun: "09",
      r1: "+01202",
      r2: "+00000",
      r3: "+00000",
      lights: ["PROG"],
      flash: true,
    },
    quote: { text: "Give us a reading on the 1202 Program Alarm.", who: "Neil Armstrong" },
  },
  {
    get: hms(102, 41, 32),
    title: "High gate: P64 pitchover",
    phase: "descent",
    computer: "LGC",
    program: "P64 · Approach phase",
    narration:
      "At 7,515 feet Eagle pitches forward and the crew sees the landing site for the first time, with boulders the size of cars around a crater the computer is aiming for.",
    computing:
      "P64 adds the Landing Point Designator: the computer projects where it intends to land as an angle on Armstrong's window reticle, and redesignates the target every time he clicks the hand controller.",
    dsky: { prog: "64", verb: "06", noun: "64", r1: "+03400", r2: "+00600", r3: "+07515" },
  },
  {
    get: hms(102, 43, 20),
    title: "P66: Armstrong takes it in",
    phase: "descent",
    computer: "LGC",
    program: "P66 · Rate-of-descent",
    narration:
      "500 feet up, long on the target, low on fuel: Armstrong flies past the boulder field by hand, hunting for clear ground, while the computer holds whatever descent rate he commands.",
    computing:
      "P66 is fly-by-wire: Armstrong's stick sets attitude, his switch clicks set descent rate, and the LGC closes the throttle loop 10 times a second to hold it. Man and computer flying one aircraft.",
    dsky: { prog: "66", verb: "06", noun: "60", r1: "+00003", r2: "-00003", r3: "+00320" },
    quote: { text: "60 seconds.", who: "CapCom Charlie Duke (fuel call)" },
  },
  {
    get: hms(102, 45, 40),
    title: "Contact light. Touchdown",
    phase: "surface",
    computer: "LGC",
    program: "P68 · Landing confirmation",
    narration:
      "A 68-inch probe brushes the surface. Contact light. Engine stop. Eagle settles into the Sea of Tranquility with about 17 seconds of hover fuel to spare.",
    computing:
      "P68 confirms touchdown, zeroes the velocity state, stores the landing site vector, and the LGC settles into keeping the platform aligned on a rotating Moon.",
    dsky: { prog: "68", verb: "06", noun: "43", r1: "+00042", r2: "+02337", r3: "+00000" },
    quote: { text: "Houston, Tranquility Base here. The Eagle has landed.", who: "Neil Armstrong" },
  },
  {
    get: hms(109, 24, 15),
    title: "One small step",
    phase: "surface",
    computer: "LGC",
    program: "P00 · Surface idle",
    narration:
      "Armstrong steps off the footpad. Six hundred million people are watching a broadcast relayed through the LM's S-band antenna.",
    computing:
      "Even now the LGC never sleeps: it keeps the inertial platform aligned and streams the telemetry downlist every 2 seconds: the same 50-word-per-second heartbeat we measured coming out of the real code in claim #15.",
    dsky: { prog: "00", verb: "16", noun: "65", r1: "+00109", r2: "+00024", r3: "+00015" },
    quote: { text: "That's one small step for man, one giant leap for mankind.", who: "Neil Armstrong" },
  },
  {
    get: hms(109, 43, 16),
    title: "Aldrin on the surface",
    phase: "surface",
    computer: "LGC",
    program: "P00 · Surface idle",
    narration:
      "Aldrin joins Armstrong. 'Magnificent desolation.' Two and a half hours of flag, experiments, cameras, and 47.5 pounds of rocks.",
    computing:
      "The LGC's downlist carries the EVA's silent bookkeeping: platform gimbal angles, battery currents, RCS temperatures: 3,200 telemetry words a minute to Honeysuckle Creek and Goldstone.",
    dsky: { prog: "00", verb: "16", noun: "65", r1: "+00109", r2: "+00043", r3: "+00016" },
  },
  {
    get: hms(110, 16, 30),
    title: "A call from the White House",
    phase: "surface",
    computer: "LGC",
    program: "P00 · Surface idle",
    narration:
      "President Nixon speaks to Tranquility Base by radio-telephone, 'the most historic phone call ever made,' routed Washington → Houston → Moon.",
    computing:
      "The call rides the same S-band uplink the computer's commands use; each leg to the Moon takes 1.28 seconds at the speed of light. That delay is measurable in the mission tapes: claim #22.",
    dsky: { prog: "00", verb: "16", noun: "65", r1: "+00110", r2: "+00016", r3: "+00030" },
  },
  {
    get: hms(111, 39, 13),
    title: "EVA complete",
    phase: "surface",
    computer: "LGC",
    program: "P00 · Surface idle",
    narration:
      "Hatch closed. Samples, film magazines, and the solar-wind experiment are aboard; a rest period nobody could sleep through begins.",
    computing:
      "Overnight the LGC and the ground run P57 alignments and track Columbia overhead, rehearsing tomorrow's ascent targeting while the crew tries to sleep on the ascent-engine cover.",
    dsky: { prog: "00", verb: "06", noun: "65", r1: "+00111", r2: "+00039", r3: "+00013" },
  },
  {
    get: hms(124, 22, 1),
    title: "Liftoff from the Moon",
    phase: "return",
    computer: "LGC",
    program: "P12 · Ascent guidance",
    narration:
      "The ascent engine, one chance, no test firing, no backup, lights on time. The flag topples in the plume. Seven minutes to orbit.",
    computing:
      "P12 flies the ascent end-to-end: pitch program, cross-product steering into the 9×45-mile insertion orbit, cutoff on its own accelerometers. The crew mostly watches the needles agree.",
    dsky: { prog: "12", verb: "06", noun: "77", r1: "+00437", r2: "+05537", r3: "+00009" },
  },
  {
    get: hms(128, 3, 0),
    title: "Docking with Columbia",
    phase: "return",
    computer: "LGC",
    program: "P34 / P35 · Rendezvous targeting",
    narration:
      "Three and a half hours of rendezvous ballet (CSI, CDH, TPI, braking) ends with Collins welcoming two dusty crewmates back aboard.",
    computing:
      "The LGC and CMC each compute the rendezvous independently: P34's targeting on one ship cross-checked against the other, radar marks folded in by Kalman-style weighting. The solutions agree; the ships meet.",
    dsky: { prog: "35", verb: "06", noun: "39", r1: "+00000", r2: "+00001", r3: "-00001" },
  },
  {
    get: hms(135, 23, 42),
    title: "Trans-Earth injection",
    phase: "return",
    computer: "CMC",
    program: "P40 · SPS burn",
    narration:
      "Behind the Moon one last time, the SPS burns for 2.5 minutes. When Columbia comes around the limb, she is coming home.",
    computing:
      "P40 again, out of contact again: the CMC steers a 3,279 ft/s burn alone and hits the entry corridor, a 40-mile-tall keyhole at the top of Earth's atmosphere, aimed from 240,000 miles out.",
    dsky: { prog: "40", verb: "06", noun: "40", r1: "+00229", r2: "+32832", r3: "+00016" },
    quote: { text: "Time to open up the LRL doors, Charlie.", who: "Michael Collins" },
  },
  {
    get: hms(195, 3, 6),
    title: "Entry interface",
    phase: "entry",
    computer: "CMC",
    program: "P63-P67 · Entry guidance",
    narration:
      "Columbia hits the atmosphere at 36,194 ft/s, the fastest any humans had ever flown, behind a heat shield glowing at 5,000 °F.",
    computing:
      "The CMC's entry programs fly the capsule by rolling its lift vector: steering through a 6.5-g deceleration, threading range and heating constraints toward a splashdown point 1,500 miles downrange.",
    dsky: { prog: "64", verb: "16", noun: "74", r1: "+00655", r2: "+36194", r3: "+01285" },
  },
  {
    get: hms(195, 18, 35),
    title: "Splashdown",
    phase: "entry",
    computer: "CMC",
    program: "P67 → shutdown",
    narration:
      "Three parachutes, then the Pacific, 13 miles from USS Hornet. Eight days, three hours, eighteen minutes, thirty-five seconds after launch.",
    computing:
      "The CMC's last display counts down range-to-go to zero. Total computing hardware that flew the mission: 4 KB of RAM, 72 KB of ROM, 55 watts. It was enough, with margin.",
    dsky: { prog: "67", verb: "16", noun: "66", r1: "+00000", r2: "+01650", r3: "-00013" },
    quote: { text: "Everything's okay. Our checklist is complete. Awaiting swimmers.", who: "Neil Armstrong" },
  },
];

export const MISSION_END = hms(195, 18, 35);

// Alarm schedule inside powered descent (GET seconds → code), per the
// documented sequence: 1202, 1202, 1201, 1202, 1202.
export const DESCENT_ALARMS: { get: number; code: "1201" | "1202" }[] = [
  { get: hms(102, 38, 26), code: "1202" },
  { get: hms(102, 39, 2), code: "1202" },
  { get: hms(102, 42, 18), code: "1201" },
  { get: hms(102, 42, 43), code: "1202" },
  { get: hms(102, 42, 58), code: "1202" },
];

export function eventAt(get: number): MissionEvent {
  let cur = EVENTS[0];
  for (const e of EVENTS) {
    if (e.get <= get) cur = e;
    else break;
  }
  return cur;
}

export function phaseAt(get: number) {
  return PHASES.find((p) => get >= p.start && get < p.end) ?? PHASES[PHASES.length - 1];
}
