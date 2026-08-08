# Apollo Forensics

**Treating the Moon landing like an untrusted system: 12 hoax claims, 12 falsifiable software tests, run on public data.**

Every moon-landing hoax claim that can be tested purely in software — tested. Not with rhetoric, with code: each claim gets a pipeline, real public data (NASA archives, JPL ephemerides, foreign space-agency terrain data, the actual 1969 flight software), an explicit **falsification criterion** stating what result would *support* the hoax, and a verdict from the numbers.

A test that can't fail isn't a test. Every experiment here could, in principle, have come out for the conspiracy. None did.

## The claims

| # | Claim | Test | Verdict |
|---|-------|------|---------|
| [1](claims/01-shadows/) | Non-parallel shadows = studio lights | Geometric light-source fit + JPL ephemeris cross-check | ⏳ |
| [2](claims/02-fill-light/) | Astronauts visible in shadow = fill lamps | Hapke-BRDF radiometry of regolith bounce light | ✅ **REFUTED** — regolith bounce predicts the shadowed suit at 40% of sunlit ground [22–72%]; the photo measures 26%. Slightly *less* light than physics supplies — the opposite of a lamp |
| [4](claims/04-backdrop-parallax/) | Identical backgrounds = painted backdrop | Feature-match parallax between camera stations | ⏳ |
| [6](claims/06-photo-quality/) | Photos too good for chest cameras | Quality-score the whole archive, not the famous 50 | ⏳ |
| [7](claims/07-c-rock/) | The "C" prop rock | Generational film forensics on AS16-107-17446 | ⏳ |
| [9](claims/09-gravity/) | Slowed-down Earth footage | Ballistics + biomechanics g-fit from EVA film | ⏳ |
| [10](claims/10-wire-rigs/) | Astronauts on wires | Acceleration-profile analysis of jumps and falls | ✅ **REFUTED** — both jump-salute jumps fit free ballistic flight at g = 1.68–1.69 ± 0.11 m/s² with ~2 mm residuals; no tension events, no wires down to 0.16 mm |
| [11](claims/11-van-allen/) | Van Allen belts are lethal | Radiation-transport dose model along the real trajectory | ⏳ |
| [15](claims/15-agc/) | 1960s computers too weak | Run the actual Apollo 11 flight software, emulated | ✅ **REFUTED** — the real Luminary 099 reassembles bit-identical (36/36 checksums) and runs at 99% of authentic speed on 3–5% of one core |
| [17](claims/17-secret-keeping/) | 400,000 people can't keep a secret | Grimes leak model + sensitivity analysis | ✅ **CONFIRMED (anti-hoax)** — a 411k-person hoax leaks in ~1.2 yr expected; max 57-yr-silent core ≈ 49 people vs ≥ 874 needed to fake the evidence |
| [20](claims/20-foreign-orbiters/) | (Independence check) Non-NASA orbiters | Terrain-match 1969 photos vs JAXA Kaguya elevation data | ⏳ |
| [22](claims/22-light-delay/) | (Independence check) Radio physics | Measure the 2.6 s Earth–Moon light delay in mission audio | ✅ **CONFIRMED (anti-hoax)** — CapCom's voice measurably returns from the Moon 2.644 ± 0.035 s after he speaks (5.0σ, n=43), matching the JPL ephemeris. You can [hear it](claims/22-light-delay/results/echo_example.wav) |

## Ground rules

1. **Falsifiable or it doesn't count.** Each claim states up front what result would support the hoax.
2. **Public data only.** Every input is fetch-able by anyone; each claim's README documents sources and URLs. Raw data is git-ignored, not hidden.
3. **Honest scope.** These are scaled-down (hours-to-days, not months) versions of the full methodologies in the source playbook. Each README states its limitations.
4. **No faked numbers.** Every figure and statistic in these READMEs was produced by the code in the same directory.

## Running

```bash
python3 -m venv .venv
.venv/bin/pip install numpy scipy matplotlib opencv-python pillow requests pandas soundfile tqdm imageio imageio-ffmpeg scikit-image
cd claims/<claim>/ && ../../.venv/bin/python run.py
```

---

*Built with Claude Code. Claims and methodology from "The Moon Landing Verification Playbook."*
