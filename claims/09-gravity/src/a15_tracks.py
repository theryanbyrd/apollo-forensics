"""Track the Apollo 15 hammer and feather in the ALSJ TV clip.

Clip: a15v_1672206.mpg (320x240, 30 fps, 49.05 s), starting ~167:22:01 GET.
Scene layout (established by inspection, see README):
  - Scott stands facing the LRV TV camera; helmet top y~48, boot soles y~176.
  - His right hand (image LEFT, x~120-135) holds the hammer; left hand
    (image RIGHT, x~165-180) holds the feather; both at y~100-112.
  - Landing positions (pre/post scene difference): hammer patch x 110-135,
    feather streak x 157-195, both at image y~195-203.
  - The GCTA field-sequential colour camera + NTSC conversion means a small
    moving object's position updates in ~3-frame (10 Hz) steps.

Outputs: results/a15_tracks.csv (raw lane detections + step-aggregated track),
         results/a15_track_overlay.png, results/a15_streak.png
"""
import csv
import os

import cv2
import numpy as np

import common as C

FPS = 30.0  # container rate; broadcast NTSC 29.97 (0.1% difference, ignored)

# manual annotation gates (frames/pixels), from exploratory analysis
BG_RANGE = range(1145, 1176)          # pre-release frames for background
FEATHER_LANE = dict(xa=155, xb=205, ya=110, yb=215, thr=13)
FEATHER_X = (168.5, 177.5)            # accept detections in this x band
FEATHER_FRAMES = range(1183, 1202)
HAMMER_LANE = dict(xa=104, xb=148, ya=108, yb=215, thr=11)
HAMMER_X = (126.0, 137.0)
HAMMER_FRAMES = range(1186, 1199)
SPEECH_END_S = 38.5                   # end of "...at the same time." (audio)


def step_aggregate(track, jump=6.0):
    """Group a (frame, y) track into field-sequential steps: a new step starts
    when y jumps by more than `jump` px. Returns (mean_frame, mean_y, n)."""
    steps = []
    cur = [track[0]]
    for f, y in track[1:]:
        if y - cur[-1][1] > jump:
            steps.append(cur)
            cur = []
        cur.append((f, y))
    steps.append(cur)
    return [(np.mean([f for f, _ in s]), np.mean([y for _, y in s]), len(s))
            for s in steps]


def main():
    os.makedirs(C.RESULTS, exist_ok=True)
    fdir = C.extract_frames("a15v_1672206.mpg", "frames_a15")
    bg = C.median_background("frames_a15", BG_RANGE)

    rows = []
    feather_raw = []
    prev_y = 118.0
    for i in FEATHER_FRAMES:
        img = C.load_gray("frames_a15", i)
        bl = C.lane_blobs(img, bg, **FEATHER_LANE)
        # feather = largest blob within the x acceptance band, below the hands,
        # never moving upward (monotonic fall; 1.5 px noise allowance)
        cand = [b for b in bl if FEATHER_X[0] <= b[0] <= FEATHER_X[1]
                and b[1] > max(118, prev_y - 1.5)]
        if cand:
            cand.sort(key=lambda b: -b[2])
            x, y, a, p = cand[0]
            prev_y = y
            feather_raw.append((i, x, y, a, p))
            rows.append(["feather_raw", i, round(x, 2), round(y, 2), a])

    hammer_raw = []
    for i in HAMMER_FRAMES:
        img = C.load_gray("frames_a15", i)
        bl = C.lane_blobs(img, bg, **HAMMER_LANE)
        cand = [b for b in bl if HAMMER_X[0] <= b[0] <= HAMMER_X[1]
                and b[1] > 130]
        if cand:
            cand.sort(key=lambda b: -b[2])
            x, y, a, p = cand[0]
            hammer_raw.append((i, x, y, a, p))
            rows.append(["hammer_raw", i, round(x, 2), round(y, 2), a])

    fsteps = step_aggregate([(f, y) for f, _, y, _, _ in feather_raw])
    hsteps = step_aggregate([(f, y) for f, _, y, _, _ in hammer_raw])
    for f, y, n in fsteps:
        rows.append(["feather_step", round(f, 2), "", round(y, 2), n])
    for f, y, n in hsteps:
        rows.append(["hammer_step", round(f, 2), "", round(y, 2), n])

    with open(os.path.join(C.RESULTS, "a15_tracks.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["kind", "frame", "x_px", "y_px", "area_or_n"])
        w.writerows(rows)

    # ---------------- overlay figure ----------------
    frame_show = 1193
    im = cv2.imread(os.path.join(C.DATA, "frames_a15",
                                 f"f{frame_show:05d}.png"))
    s = 3
    big = cv2.resize(im, (320 * s, 240 * s), interpolation=cv2.INTER_CUBIC)
    for f, x, y, a, p in feather_raw:
        col = (0, 255, 255) if f == frame_show else (0, 160, 160)
        cv2.circle(big, (int(x * s), int(y * s)), 5 if f == frame_show else 3,
                   col, 2 if f == frame_show else 1)
    for f, x, y, a, p in hammer_raw:
        col = (0, 128, 255) if f == frame_show else (0, 90, 180)
        cv2.circle(big, (int(x * s), int(y * s)), 5 if f == frame_show else 3,
                   col, 2 if f == frame_show else 1)
    # calibration bar: Scott helmet-top to boot-sole
    cv2.line(big, (150 * s, 48 * s), (150 * s, 176 * s), (255, 80, 255), 2)
    cv2.putText(big, "Scott ~1.92 m = 128 px", (152 * s, 120 * s),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 80, 255), 2)
    cv2.putText(big, "feather track", (185 * s, 150 * s),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
    cv2.putText(big, "hammer track", (60 * s, 160 * s),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 128, 255), 2)
    cv2.putText(big, f"Apollo 15 hammer-feather drop, frame {frame_show}"
                     " (a15v_1672206.mpg)",
                (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    cv2.imwrite(os.path.join(C.RESULTS, "a15_track_overlay.png"), big)

    # ---------------- streak evidence figure ----------------
    f0, f1 = 1150, 1250
    S = np.zeros((240, f1 - f0))
    for i in range(f0, f1):
        S[:, i - f0] = np.abs(C.load_gray("frames_a15", i) - bg)[:, 95:235].max(axis=1)
    Simg = np.clip(S * 4, 0, 255).astype(np.uint8)
    Simg = cv2.resize(Simg, ((f1 - f0) * 7, 720),
                      interpolation=cv2.INTER_NEAREST)
    Simg = cv2.cvtColor(Simg, cv2.COLOR_GRAY2BGR)
    for i in range(f0, f1, 10):
        x = (i - f0) * 7
        cv2.line(Simg, (x, 0), (x, 720), (0, 70, 70), 1)
        cv2.putText(Simg, str(i), (x + 2, 714), cv2.FONT_HERSHEY_PLAIN, 0.9,
                    (0, 0, 255), 1)
    for yy in range(0, 240, 20):
        cv2.putText(Simg, str(yy), (2, yy * 3 + 12), cv2.FONT_HERSHEY_PLAIN,
                    0.9, (0, 255, 0), 1)
    for f, y, n in fsteps:
        cv2.circle(Simg, (int((f - f0) * 7), int(y * 3)), 4, (0, 255, 255), 1)
    for f, y, n in hsteps:
        cv2.circle(Simg, (int((f - f0) * 7), int(y * 3)), 4, (0, 128, 255), 1)
    cv2.putText(Simg, "time (frame) vs image y: |frame - pre-release bg|,"
                      " x-max over lane 95-235", (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.imwrite(os.path.join(C.RESULTS, "a15_streak.png"), Simg)

    print("feather steps:", [(round(f, 1), round(y, 1)) for f, y, _ in fsteps])
    print("hammer  steps:", [(round(f, 1), round(y, 1)) for f, y, _ in hsteps])
    return fsteps, hsteps


if __name__ == "__main__":
    main()
