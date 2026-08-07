#!/usr/bin/env python3
"""
Figure: AGC (1969) vs the laptop that emulated it (2026).
Panel A: memory capacity on a log scale (the only honest scale for a 7-order-of-
         magnitude gap), horizontal bars, direct-labeled.
Panel B: how much of ONE laptop core real-time emulation actually cost (measured).
All numbers are measured or documented-spec; see README for provenance.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# --- palette (validated: dataviz reference instance, light mode) ---
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
AGC_BLUE = "#2a78d6"     # entity: AGC 1969
MAC_ORANGE = "#eb6834"   # entity: MacBook 2026

# --- data (bytes) ---
rows = [
    ("AGC erasable memory (RAM)\n2,048 x 15-bit words", 3840, AGC_BLUE, "3.75 KB"),
    ("AGC fixed rope memory (ROM)\n36,864 x 15-bit words", 69120, AGC_BLUE, "67.5 KB"),
    ("This laptop's RAM\n(2019 MacBook Pro, i9-9880H)", 68719476736, MAC_ORANGE, "64 GB"),
]

fig = plt.figure(figsize=(9.6, 6.2), dpi=150)
fig.patch.set_facecolor(SURFACE)

fig.text(0.02, 0.965, "Apollo 11 flight computer vs. the laptop that just re-ran its code",
         fontsize=14.5, fontweight="bold", color=INK)

# legend row (entity colors)
fig.text(0.055, 0.915, "■", color=AGC_BLUE, fontsize=11)
fig.text(0.075, 0.915, "Apollo Guidance Computer, 1969 (55 W, 32 kg)", fontsize=9.5, color=INK2)
fig.text(0.50, 0.915, "■", color=MAC_ORANGE, fontsize=11)
fig.text(0.52, 0.915, "MacBook Pro running the emulation, 2026", fontsize=9.5, color=INK2)

# ---------------- Panel A: memory, log scale ----------------
fig.text(0.02, 0.845, "Memory: the entire Apollo 11 LM flight program fits in 67.5 KB",
         fontsize=12, color=INK, fontweight="bold")
fig.text(0.02, 0.812, "bytes, log scale — the laptop holds ~17.9 million x the AGC's RAM",
         fontsize=9, color=INK2)

ax = fig.add_axes([0.30, 0.40, 0.64, 0.36])
ax.set_facecolor(SURFACE)
y = [2, 1, 0]
for yi, (label, val, color, human) in zip(y, rows):
    ax.barh(yi, val, height=0.52, color=color, zorder=3)
    ax.text(val * 1.6, yi, human, va="center", ha="left",
            fontsize=11, color=INK, fontweight="bold")
ax.set_xscale("log")
ax.set_xlim(1e3, 3e12)
ax.set_ylim(-0.55, 2.55)
ax.set_yticks(y)
ax.set_yticklabels([r[0] for r in rows], fontsize=9.5, color=INK)
ax.set_xticks([1e3, 1e6, 1e9, 1e12])
ax.set_xticklabels(["1 KB", "1 MB", "1 GB", "1 TB"], fontsize=9, color=INK2)
ax.tick_params(length=0)
ax.grid(axis="x", color="#e6e5e2", linewidth=0.8, zorder=0)
for s in ax.spines.values():
    s.set_visible(False)

# ---------------- Panel B: CPU cost meter ----------------
fig.text(0.02, 0.255, "CPU needed to run the AGC in real time on this laptop",
         fontsize=12, color=INK, fontweight="bold")

ax2 = fig.add_axes([0.30, 0.115, 0.64, 0.09])
ax2.set_facecolor(SURFACE)
ax2.set_xlim(0, 100)
ax2.set_ylim(0, 1)
ax2.axis("off")
ax2.add_patch(FancyBboxPatch((0, 0.25), 100, 0.5,
              boxstyle="round,pad=0,rounding_size=0.18",
              linewidth=0, facecolor="#e6e5e2", zorder=2))
ax2.add_patch(FancyBboxPatch((0, 0.25), 4.82, 0.5,
              boxstyle="round,pad=0,rounding_size=0.18",
              linewidth=0, facecolor=MAC_ORANGE, zorder=3))
ax2.text(6.2, 0.5, "3-5% of one core (of 16) = under 0.3% of the machine",
         va="center", fontsize=10, color=INK, fontweight="bold")
fig.text(0.94, 0.065, "measured cputime, three runs: 0.98/30s, 1.73/60s, 2.89/60s CPU-seconds - yaAGC pinned to authentic AGC speed",
         ha="right", fontsize=8.5, color=INK2)

out = "/Users/ryanbyrd/apollo-forensics/claims/15-agc/results/agc-vs-laptop.png"
fig.savefig(out, facecolor=SURFACE)
print("wrote", out)
