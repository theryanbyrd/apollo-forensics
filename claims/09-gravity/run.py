#!/usr/bin/env python
"""Claim 09 - "The footage is Earth gravity slowed down ~2.46x."

Reproduces the full analysis:
  1. download the ALSJ Apollo 15 hammer-feather TV clip, the ALSJ Apollo 16
     jump-salute clip, and an independent-lineage archive.org copy (cached
     in data/, gitignored);
  2. track the falling hammer and feather (a15_tracks);
  3. fit y(t) parabolas -> apparent g (a15_fit);
  4. simulate a falcon feather with air drag vs the hoax hypothesis
     (feather_drag);
  5. measure Scott's speech tempo in the same clip and build the
     joint-hypothesis figure (a15_tempo);
  6. analyse John Young's Apollo 16 jump salute: ballistic arcs + push-off
     biomechanics (a16_jump);
  7. write results/summary.json.

Usage:  ../../.venv/bin/python run.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "src"))

import common as C  # noqa: E402


def main():
    os.makedirs(C.RESULTS, exist_ok=True)

    import a15_fit
    fit = a15_fit.main()

    import feather_drag
    drag = feather_drag.main()

    import a15_tempo
    tempo = a15_tempo.main()

    import a16_jump
    jump = a16_jump.main()

    g = fit["feather_fit"]["g_apparent_m_s2"]
    ge = fit["feather_fit"]["g_err_m_s2"]
    gj = jump["combined_g_m_s2"]
    gje = jump["combined_g_stat_err_m_s2"]        # statistical only
    gjs = jump["combined_g_scale_sys_err_m_s2"]   # correlated scale systematic
    gjt = jump["combined_g_total_err_m_s2"]
    rel = fit["release_extrapolation"]
    summary = {
        "claim": 9,
        "title": "Slowed-down Earth footage",
        "verdict": "REFUTED",
        "headline": (
            f"Tracked ballistics fit apparent g = {g} +/- {ge} m/s^2 "
            f"(Apollo 15 feather) and {gj} +/- {gje} (stat) +/- {gjs} "
            f"(scale) m/s^2 (Apollo 16 "
            "jump), consistent with lunar 1.62 and excluding real-time Earth "
            "gravity at >6 sigma - while the slowed-Earth escape route "
            "(s=2.46) fails the same clip's synced audio (Scott would have "
            "been speaking 9.9 syllables/s) and the feather's drag physics "
            "(its screen-time impact speed, 2.35 +/- 0.48 m/s, is ~4x the "
            "maximum any Earth-air feather could show in 2.46x-slowed "
            "footage)."
        ),
        "impressive": (
            "One 49-second NASA TV clip kills the claim three independent "
            "ways at once: the feather's tracked fall matches vacuum free "
            "fall at lunar g; the same clip's PTS-synced audio matches the "
            "mission transcript second-for-second (so no global slow-down "
            "is available); and a drag ODE shows a real feather in Earth "
            "air would have crossed the last 0.3 m of its fall 4-7x slower "
            "than observed, landing ~2.5 s of screen time after the hammer "
            "instead of the observed 0.20 +/- 0.07 s."
        ),
        "numbers": {
            "a15_feather_g_m_s2": [g, ge],
            "a15_feather_a_px_s2": [fit["feather_fit"]["a_px_per_s2"],
                                    fit["feather_fit"]["a_err_px_per_s2"]],
            "a15_release_frame_point": rel["t_rel_frame_point_estimate"],
            "a15_release_frame_ci68": rel["t_rel_frame_ci68"],
            "a16_jump_g_m_s2": [gj, gje, gjs, gjt],
            "a16_jump_g_per_jump_m_s2": [
                jump["jump1"]["g_apparent_m_s2"],
                jump["jump2"]["g_apparent_m_s2"]],
            "a16_scale_px_per_m": jump["scale_px_per_m"],
            "a16_pushoff_s": [jump["jump1"]["push_off_s"],
                              jump["jump2"]["push_off_s"]],
            "a16_hang_time_s": [jump["jump1"]["hang_time_s"],
                                jump["jump2"]["hang_time_s"]],
            "speech_rate_obs_syl_s": tempo["monologue"][
                "syl_rate_gross_incl_pauses"],
            "speech_rate_hoax_syl_s": tempo["hoax_implication"][
                "implied_real_rate_gross"],
            "feather_impact_speed_obs_m_s": fit["feather_fit"][
                "v_at_landing_m_s"],
            "feather_impact_speed_hoax_max_m_s": drag["scenarios"][
                "earth_air_vt1.5"][
                "apparent_impact_speed_in_slowed_footage_m_s"],
            "landing_gap_obs_s": fit["landing_separation"]["observed_s"],
            "landing_gap_hoax_air_s": 2.5,
        },
    }
    with open(os.path.join(C.RESULTS, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print("\n=== summary.json ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
