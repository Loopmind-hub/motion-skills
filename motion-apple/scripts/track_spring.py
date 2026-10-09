#!/usr/bin/env python3
"""track_spring — measure how ONE object moves in a reference video, and fit the spring behind it.

This is how the keynote-ui register got its numbers (2026-10-08): the "19:25" pill of an Apple-style
reference overshot 4.3 % in position with a 0.25 s half-period → ζ ≈ 0.68, ω ≈ 17 rad/s, which is now
MS.SPRINGS.ui. "It looks smooth" becomes two numbers you can type into MS.springEase / MS.springDur.

  track_spring.py VIDEO T0 T1 [--thresh 25]     → per-frame bbox / centroid / area / sharpness table
  track_spring.py --fit OVERSHOOT HALF_PERIOD   → ζ and ω from a measured overshoot (0.043) and
                                                  the time between the peak and the next trough (s)

How to read the table: find the frame where a size/position column peaks past its final value
(overshoot = (peak − final) / (final − start)); the next turning point gives the half-period.
`sharp` (p95 gradient inside the object) dropping while it moves = shutter motion blur.
Foreground = pixels that differ from the frame's border colour by > thresh, so it works on flat
fields (the Apple style); corners are masked to ignore platform watermarks.
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys


def fit_spring(overshoot: float, half_period: float) -> tuple[float, float]:
    """Damped-spring ζ and ω (rad/s) from fractional overshoot and the peak→trough time.
    overshoot = exp(−ζπ/√(1−ζ²)); damped period = 2·half_period = 2π/(ω√(1−ζ²))."""
    if not 0 < overshoot < 1 or half_period <= 0:
        raise ValueError("overshoot must be in (0, 1) and half_period > 0")
    ln = math.log(overshoot)
    zeta = -ln / math.sqrt(math.pi ** 2 + ln ** 2)
    omega = math.pi / (half_period * math.sqrt(1 - zeta ** 2))
    return zeta, omega


def track(video: str, t0: float, t1: float, thresh: float = 25.0, w: int = 512, h: int = 288, fps: float = 30.0):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-t", str(t1 - t0), "-i", video,
                          "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    fr[:, :60, :80] = np.median(fr[:, :60, :80])      # watermark corners
    fr[:, -60:, -80:] = np.median(fr[:, -60:, -80:])
    rows = []
    for i, f in enumerate(fr):
        bg = np.median(np.concatenate([f[:, :6].ravel(), f[:, -6:].ravel(), f[:6].ravel()]))
        m = np.abs(f - bg) > thresh
        ys, xs = np.nonzero(m)
        if len(xs) < 4:
            continue
        gy, gx = np.gradient(f)
        sharp = float(np.percentile(np.hypot(gx, gy)[m], 95))
        rows.append((t0 + i / fps, xs.min(), xs.max(), ys.min(), ys.max(), xs.mean(), ys.mean(), len(xs), sharp))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video", nargs="?")
    ap.add_argument("t0", nargs="?", type=float)
    ap.add_argument("t1", nargs="?", type=float)
    ap.add_argument("--thresh", type=float, default=25.0)
    ap.add_argument("--fit", nargs=2, type=float, metavar=("OVERSHOOT", "HALF_PERIOD"))
    a = ap.parse_args(argv)
    if a.fit:
        z, o = fit_spring(*a.fit)
        print(f"zeta {z:.3f}  omega {o:.1f} rad/s  → MS.springEase({z:.2f}), duration MS.springDur({z:.2f}, {o:.0f})")
        return 0
    if a.video is None or a.t0 is None or a.t1 is None:
        ap.error("give VIDEO T0 T1, or --fit OVERSHOOT HALF_PERIOD")
    print("t       x0  x1  y0  y1    cx     cy   area  sharp")
    for r in track(a.video, a.t0, a.t1, a.thresh):
        print("%.3f %4d %4d %4d %4d %6.1f %6.1f %6d %5.1f" % r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
