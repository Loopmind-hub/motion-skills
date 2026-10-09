#!/usr/bin/env python3
"""beatgrid.py — tempo, beat times and downbeat of a music file (numpy only).

For when the video is cut to a real song (Mixkit / Pixabay) instead of the synth score:
    uv run --with numpy --with scipy ~/.claude/skills/motion-studio/scripts/beatgrid.py song.mp3 \
        [--min-bpm 70 --max-bpm 180] [-o beats.json]

Method: spectral-flux onset envelope → tempo by autocorrelation (70–180 BPM, octave-corrected
toward 90–150) → beat phase by comb-filter search → downbeat = the beat phase (of 4) with the
most low-frequency onset energy. Start the video on the first downbeat it reports.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 22_050
HOP = 256


def load_mono(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1",
                          "-ar", str(SR), "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def onset_envelopes(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(full-band flux, low-band flux) at SR/HOP frames per second."""
    n_fft = 1024
    win = np.hanning(n_fft)
    frames = np.lib.stride_tricks.sliding_window_view(np.pad(x, (n_fft // 2, n_fft // 2)), n_fft)[::HOP]
    mag = np.log1p(np.abs(np.fft.rfft(frames * win, axis=1)) * 10)
    flux = np.maximum(np.diff(mag, axis=0, prepend=mag[:1]), 0)
    low_bins = int(150 / (SR / n_fft))
    full, low = flux.sum(axis=1), flux[:, :max(low_bins, 2)].sum(axis=1)
    for e in (full, low):
        e -= np.convolve(e, np.ones(16) / 16, mode="same")   # remove slow trend
        np.maximum(e, 0, out=e)
    return full, low


def estimate_tempo(env: np.ndarray, fps: float, lo: float, hi: float) -> float:
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    lags = np.arange(len(ac))
    bpm = np.where(lags > 0, 60 * fps / np.maximum(lags, 1), 0)
    ok = (bpm >= lo) & (bpm <= hi)
    # prefer the musically common range by a gentle log-Gaussian prior centred on 120
    prior = np.exp(-0.5 * (np.log2(np.maximum(bpm, 1e-6) / 120) / 0.9) ** 2)
    score = np.where(ok, ac * prior, -np.inf)
    lag = int(np.argmax(score))
    # parabolic refinement for sub-frame precision
    if 1 <= lag < len(ac) - 1:
        a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
        denom = a - 2 * b + c
        lag = lag + (0.5 * (a - c) / denom if denom != 0 else 0)
    return 60 * fps / lag


def beat_phase(env: np.ndarray, period: float) -> float:
    best, best_off = -1.0, 0.0
    for off in np.arange(0, period, 0.25):
        idx = np.arange(off, len(env) - 1, period).astype(int)
        s = env[idx].sum()
        if s > best:
            best, best_off = s, off
    return best_off


def analyse(x: np.ndarray, lo: float = 70, hi: float = 180) -> dict:
    fps = SR / HOP
    full, low = onset_envelopes(x)
    bpm = estimate_tempo(full, fps, lo, hi)
    period = fps * 60 / bpm
    off = beat_phase(full, period)
    beats = np.arange(off, len(full) - 1, period) / fps
    # downbeat: which of the 4 beat positions carries the most low-end onset energy
    strength = [low[np.clip((beats[k::4] * fps).astype(int), 0, len(low) - 1)].mean() if len(beats[k::4]) else 0
                for k in range(4)]
    k = int(np.argmax(strength))
    downbeats = beats[k::4]
    return {"bpm": round(float(bpm), 2), "beat_s": round(60 / float(bpm), 4),
            "first_downbeat_s": round(float(downbeats[0]), 3) if len(downbeats) else 0.0,
            "beats": [round(float(b), 3) for b in beats],
            "downbeats": [round(float(b), 3) for b in downbeats]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("audio", type=Path)
    ap.add_argument("--min-bpm", type=float, default=70)
    ap.add_argument("--max-bpm", type=float, default=180)
    ap.add_argument("-o", "--out", type=Path)
    args = ap.parse_args(argv)
    res = analyse(load_mono(args.audio), args.min_bpm, args.max_bpm)
    if args.out:
        args.out.write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k not in ("beats", "downbeats")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
