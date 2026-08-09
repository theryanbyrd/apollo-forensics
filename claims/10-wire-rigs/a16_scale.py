"""Single metric calibration for the Apollo 16 "jump salute" clip.

    a16salute.mpg, 352x240, 29.97 fps, John Young at Descartes, GET 120:25:42

This module exists so that the two claims that analyse *the same clip* cannot
quote two different answers to the same physical question:

  * claim 09 (`claims/09-gravity/src/a16_jump.py`)  - helmet-top ballistics
  * claim 10 (`claims/10-wire-rigs/run.py`)         - wire-rig dynamics

Both import PX_PER_M / SCALE_RELERR from here.  Nothing else in the repo may
define an a16salute scale.

---------------------------------------------------------------------------
Pixel side (measured, not asserted)
---------------------------------------------------------------------------
`measure_standing_px()` measures Young's helmet-crown-to-boot-sole image
extent directly from the frames, on every frame of the two intervals in which
he is walking on the ground away from a jump crouch (STAND_FRAMES).  Rules:

  crown  the sub-pixel row at which the per-row maximum brightness crosses
         halfway between the black lunar sky and the sunlit-suit plateau.
         Above the horizon this edge is a ~170 DN step, so the crown is
         essentially unambiguous (varying the 0.50 fraction over 0.40-0.60
         moves it by < 0.5 px).
  sole   the bottom row of the connected bright-suit blob containing the
         brightest suit pixel, thresholded at 0.55 of the same sky->suit
         span.  0.55 corresponds to ~123 DN, which sits between the local
         regolith (~95 DN) and the sunlit boot/lower leg (~150 DN); the
         boot's ground-contact shadow is the dark band immediately below.

Result over the 62 frames of STAND_FRAMES: 129.0 px, frame-to-frame
sd 3.5 px (real gait posture change, not tracking noise).  Sweeping the sole
threshold over 0.50-0.60 moves the mean over 131.6-123.5 px, a +/-4 px
systematic.  Quadrature: **129.0 +/- 5.0 px** (3.9 %).

This settles a disagreement between earlier versions of the two claims:
claim 09 used 122 px and claim 10 used 128 px for the identical measurement.
122 px is the crown-to-*ankle* extent - it is what the 0.60 threshold returns,
because the boot is darker than the leg.  Zooming on the boot/ground contact
(frames 195 and 300, rows 176-196) shows the sole at y = 187-189 with the
crown at y = 58-59, i.e. ~129 px.  The 128 px figure was right; 122 was low.

---------------------------------------------------------------------------
Metric side (assumed, with the assumption stated)
---------------------------------------------------------------------------
  John Young's stature                                       1.75 m
    (NASA biography, 5 ft 9 in; other compilations quote up
     to 1.78 m - that spread is inside the error bar below)
  + A7LB pressure garment, LEVA helmet, lunar overboots     +0.11 m
  = fully upright suited stack                               1.86 m
  - pressurised-suit lope stance (knees flexed, torso
    pitched forward under the PLSS), -3 %                   -0.06 m
  = crown-to-sole extent in the posture actually imaged      1.80 m

  +/- 0.10 m (5.6 %) spans the quoted-stature range (1.75-1.78 m), the suit
  stack increment (+0.08 to +0.15 m) and the stance correction (0 to -5 %).

This is the dominant uncertainty in every metric result derived from this
clip, and it is 100 % correlated between the two jumps and between the two
claims - so it must be carried as a *systematic*, never averaged down.
"""
import numpy as np

try:
    import cv2
except ImportError:                                   # pragma: no cover
    cv2 = None

# --- measurement window (claim-10 / imageio 0-based frame index) ------------
# Two intervals in which Young is walking on the ground: the walk-in before
# jump 1 and the walk between the jumps.  Pre-jump crouch frames are excluded
# because a crouched pixel extent does not correspond to the standing metre
# figure below.
STAND_FRAMES = list(range(180, 214)) + list(range(285, 313))

# claim 09 extracts frames with `ffmpeg -vsync 0` (466 PNGs, 1-based) while
# claim 10 decodes with imageio (468 frames, 0-based); the same wall-clock
# frame is claim-09 index n <-> claim-10 index n+1 (verified by pixel match).
STAND_FRAMES_09 = [t - 1 for t in STAND_FRAMES]

BOX = (60, 145, 40, 205)          # x0, x1, y0, y1 around Young
F_CROWN = 0.50
F_SOLE = 0.55

# --- the calibration --------------------------------------------------------
STAND_PX = 129.0        # px, produced by measure_standing_px() (see docstring)
STAND_PX_ERR = 5.0      # px: 3.5 posture scatter (+) 4.0 threshold systematic
STAND_M = 1.80          # m,  derived above
STAND_M_ERR = 0.10      # m

PX_PER_M = STAND_PX / STAND_M                                     # 71.67 px/m
SCALE_RELERR = float(np.hypot(STAND_PX_ERR / STAND_PX,
                              STAND_M_ERR / STAND_M))             # 0.0677


def measure_one(frame, box=BOX, f_crown=F_CROWN, f_sole=F_SOLE):
    """Crown and sole image rows of the suited astronaut in one frame.

    `frame` is a 2-D grayscale array of the full 352x240 image.
    Returns (crown_row, sole_row) or None if no crown edge is found.
    """
    if cv2 is None:                                   # pragma: no cover
        raise RuntimeError("measure_standing_px requires OpenCV")
    x0, x1, y0, y1 = box
    b = np.asarray(frame, dtype=np.float32)[y0:y1, x0:x1]
    sky = float(np.median(b[0:12]))                       # black sky above him
    suit = float(np.median(b[b > np.percentile(b, 90)]))  # sunlit suit plateau
    thr_c = sky + f_crown * (suit - sky)
    rowmax = b.max(axis=1)
    hit = np.flatnonzero(rowmax > thr_c)
    if len(hit) == 0 or hit[0] == 0:
        return None
    i = int(hit[0])
    crown = y0 + (i - 1) + (thr_c - rowmax[i - 1]) / (rowmax[i] - rowmax[i - 1])
    thr_s = sky + f_sole * (suit - sky)
    m = cv2.morphologyEx((b > thr_s).astype(np.uint8), cv2.MORPH_OPEN,
                         np.ones((2, 2), np.uint8))
    if m.sum() == 0:
        return None
    _, lab = cv2.connectedComponents(m)
    sy, sx = np.unravel_index(int(np.argmax(b * (m > 0))), b.shape)
    ys, _ = np.where(lab == lab[sy, sx])
    return float(crown), float(y0 + ys.max())


def measure_standing_px(get_frame, frames=None, f_sole=F_SOLE):
    """Mean +/- sd of the crown-to-sole extent over `frames`.

    `get_frame(t)` must return the 2-D grayscale frame at index t.
    Returns dict(mean, sd, n, per_frame).
    """
    frames = STAND_FRAMES if frames is None else frames
    ext = []
    for t in frames:
        r = measure_one(get_frame(t), f_sole=f_sole)
        if r is not None:
            ext.append(r[1] - r[0])
    ext = np.array(ext)
    return {"mean": float(ext.mean()), "sd": float(ext.std(ddof=1)),
            "n": int(len(ext)), "per_frame": ext}


def threshold_sensitivity(get_frame, frames=None,
                          fractions=(0.50, 0.525, 0.55, 0.575, 0.60)):
    """Mean extent as a function of the sole threshold (the systematic)."""
    return {str(f): round(measure_standing_px(get_frame, frames, f_sole=f)["mean"], 2)
            for f in fractions}
