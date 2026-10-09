#!/usr/bin/env python3
"""score.py — deterministic score + sound design + mix from a cue sheet.

One JSON cue sheet drives the whole soundtrack: a beat-grid music arrangement
(synthesized, license-free), designed SFX (risers, impacts, whooshes, ticks),
and placed samples (voice chops, library SFX). Output is a mastered stereo WAV
at a loudness target, plus a report. Same cue sheet in -> same bytes out.

Run (never with bare python3 — the system python has no numpy):
    uv run --with numpy --with scipy --with soundfile --with pyloudnorm \
        ~/.claude/skills/motion-studio/scripts/score.py cues.json -o assets/audio/mix.wav

Cue sheet schema: see ../references/cue-sheet.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import ndimage, signal

SR = 48_000
NOTE_INDEX = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
              "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


# ─────────────────────────────── helpers ────────────────────────────────

def rng_for(*key) -> np.random.Generator:
    """Seeded RNG per event, so every noise source is reproducible."""
    h = hashlib.sha256(repr(key).encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))


def db(x: float) -> float:
    return 10 ** (x / 20)


def midi_hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def chord_notes(name: str, octave: int = 3) -> list[int]:
    """'Fm', 'Db', 'Ab', 'Eb', 'Cm7', 'Bbsus2' -> MIDI notes (root position)."""
    root = name[:2] if len(name) > 1 and name[1] in "#b" else name[:1]
    qual = name[len(root):]
    base = 12 * (octave + 1) + NOTE_INDEX[root]
    shape = {"": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10], "m7": [0, 3, 7, 10],
             "maj7": [0, 4, 7, 11], "sus2": [0, 2, 7], "sus4": [0, 5, 7], "5": [0, 7]}
    if qual not in shape:
        raise ValueError(f"unknown chord quality in {name!r}")
    return [base + i for i in shape[qual]]


def env_ad(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(t - attack, 0) / max(decay, 1e-4))


def pan_stereo(mono: np.ndarray, pan: float | np.ndarray) -> np.ndarray:
    """Equal-power pan, pan in [-1, 1] (scalar or per-sample)."""
    p = (np.asarray(pan) + 1) * np.pi / 4
    return np.stack([mono * np.cos(p), mono * np.sin(p)], axis=1)


def butter(kind: str, freq, order: int = 2):
    return signal.butter(order, freq, btype=kind, fs=SR, output="sos")


def sweep_filter(x: np.ndarray, f0: float, f1: float, kind: str = "bandpass",
                 q: float = 1.2, block: int = 256, curve: float = 2.0) -> np.ndarray:
    """Time-varying biquad (cutoff sweeps f0 -> f1 exponentially), block-wise with state."""
    out = np.zeros_like(x)
    n = len(x)
    zi = np.zeros((1, 2))
    for s in range(0, n, block):
        frac = (s / max(n - 1, 1)) ** (1 / curve) if f1 > f0 else (s / max(n - 1, 1))
        f = f0 * (f1 / f0) ** frac
        f = float(np.clip(f, 30, SR / 2 - 200))
        if kind == "bandpass":
            bw = f / q
            lo, hi = max(f - bw / 2, 20), min(f + bw / 2, SR / 2 - 100)
            sos = signal.butter(1, [lo, hi], btype="bandpass", fs=SR, output="sos")
        else:
            sos = signal.butter(2, f, btype=kind, fs=SR, output="sos")
        seg = x[s:s + block]
        if zi.shape[0] != sos.shape[0]:
            zi = np.zeros((sos.shape[0], 2))
        y, zi = signal.sosfilt(sos, seg, zi=zi)
        out[s:s + block] = y
    return out


def place(bus: np.ndarray, clip: np.ndarray, at: float) -> None:
    """Add a (n, 2) clip into a (N, 2) bus at time `at` seconds (clipped to bounds)."""
    i = int(round(at * SR))
    if i >= len(bus) or i + len(clip) <= 0:
        return
    a, b = max(i, 0), min(i + len(clip), len(bus))
    bus[a:b] += clip[a - i:b - i]


# ─────────────────────────────── instruments ────────────────────────────

def kick(vel: float = 1.0, key=()) -> np.ndarray:
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 44 + (170 - 44) * np.exp(-t / 0.032)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.26)
    click = rng_for("kick-click", *key).standard_normal(n) * np.exp(-t / 0.0025)
    click = signal.sosfilt(butter("highpass", 1800), click) * 0.35
    x = np.tanh(2.2 * (body + click)) * 0.9 * vel
    return pan_stereo(x, 0.0)


def clap(vel: float = 1.0, key=()) -> np.ndarray:
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    noise = rng_for("clap", *key).standard_normal(n)
    env = np.zeros(n)
    for k, off in enumerate((0.0, 0.011, 0.022)):
        env += (t >= off) * np.exp(-np.maximum(t - off, 0) / (0.006 if k < 2 else 0.11))
    x = signal.sosfilt(butter("bandpass", [900, 3200]), noise * env) * 1.4 * vel
    return pan_stereo(x, 0.0)


def hat(vel: float = 1.0, open_: bool = False, key=()) -> np.ndarray:
    n = int((0.3 if open_ else 0.08) * SR)
    t = np.arange(n) / SR
    noise = rng_for("hat", open_, *key).standard_normal(n)
    x = signal.sosfilt(butter("highpass", 7500), noise) * np.exp(-t / (0.12 if open_ else 0.022))
    return pan_stereo(x * 0.5 * vel, 0.25)


def tick(vel: float = 1.0, freq: float = 2400.0, pan: float = 0.0) -> np.ndarray:
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.008) * 0.5 * vel
    return pan_stereo(x, pan)


def sub_note(midi: int, dur: float, vel: float = 1.0) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = midi_hz(midi)
    x = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    env = np.clip(t / 0.005, 0, 1) * np.clip((dur - t) / 0.03, 0, 1)
    return pan_stereo(np.tanh(1.6 * x) * env * 0.55 * vel, 0.0)


def pluck(midi: int, vel: float = 1.0, decay: float = 0.22, pan: float = 0.0) -> np.ndarray:
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = midi_hz(midi)
    x = np.zeros(n)
    for k in range(1, 14):
        if f * k > SR / 2.2:
            break
        x += np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * k / (decay * 6))
    x *= np.exp(-t / decay) * np.clip(t / 0.002, 0, 1)
    return pan_stereo(x * 0.22 * vel, pan)


def pad_chord(notes: list[int], dur: float, cutoff: float, vel: float = 1.0, key=()) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    detunes = (-0.14, -0.07, 0.0, 0.07, 0.14)
    for ni, m in enumerate(notes):
        for di, d in enumerate(detunes):
            f = midi_hz(m + d)
            phase = rng_for("pad", ni, di, *key).uniform(0, 1)
            saw = 2 * ((f * t + phase) % 1.0) - 1
            pan = (di - 2) / 2 * 0.8
            out += pan_stereo(saw, pan)
    lp = butter("lowpass", cutoff, order=2)
    out = np.stack([signal.sosfilt(lp, out[:, 0]), signal.sosfilt(lp, out[:, 1])], axis=1)
    env = np.clip(t / 0.25, 0, 1) * np.clip((dur - t) / 0.2, 0, 1)
    return out * env[:, None] * 0.045 * vel


def riser(dur: float, key=()) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng_for("riser", *key).standard_normal(n)
    swept = sweep_filter(noise, 300, 9000, "bandpass", q=1.6)
    tone_f = 180 * (8 ** (t / dur))
    tone = np.sin(2 * np.pi * np.cumsum(tone_f) / SR) * 0.25
    env = (t / dur) ** 2.2
    x = (swept * 1.3 + tone) * env
    pan = np.sin(2 * np.pi * 1.5 * t) * 0.35
    return pan_stereo(x * 0.6, pan)


def downlifter(dur: float, key=()) -> np.ndarray:
    return riser(dur, key=("down", *key))[::-1] * 0.8


def impact(vel: float = 1.0, key=()) -> np.ndarray:
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    f = 34 + (95 - 34) * np.exp(-t / 0.18)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7)
    noise = rng_for("impact", *key).standard_normal(n)
    crack = signal.sosfilt(butter("lowpass", 5000), noise) * np.exp(-t / 0.05) * 0.6
    tail = signal.sosfilt(butter("bandpass", [200, 1800]), noise) * np.exp(-t / 0.5) * 0.12
    x = np.tanh(1.8 * (boom + crack + tail)) * vel
    return pan_stereo(x * 0.95, 0.0)


def whoosh(dur: float, pan_from: float = -0.8, pan_to: float = 0.8, vel: float = 1.0, key=()) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng_for("whoosh", *key).standard_normal(n)
    up = sweep_filter(noise, 400, 5000, "bandpass", q=1.4, curve=1.0)
    bell = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    pan = pan_from + (pan_to - pan_from) * (t / dur)
    return pan_stereo(up * bell * 0.9 * vel, pan)


def ping(vel: float = 1.0, freq: float = 1320.0, pan: float = 0.0) -> np.ndarray:
    """Message-arrived bell: two inharmonic partials, fast attack, ~0.35 s ring.
    Deliberately NOT any app's trademark notification sound."""
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.16)
         + 0.45 * np.sin(2 * np.pi * freq * 1.5 * t) * np.exp(-t / 0.09)
         + 0.15 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t / 0.04))
    x *= np.clip(t / 0.002, 0, 1) * 0.32 * vel
    return pan_stereo(x, pan)


def pop(vel: float = 1.0, pan: float = 0.0) -> np.ndarray:
    """Bubble landing: a short upward sine chirp with a soft body."""
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    f = 380 + 900 * (t / t[-1]) ** 0.6
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.028) * np.clip(t / 0.001, 0, 1)
    return pan_stereo(x * 0.45 * vel, pan)


def blip(vel: float = 1.0, freq: float = 1568.0, notes: list[float] | None = None,
         step: float = 0.055, pan: float = 0.0) -> np.ndarray:
    """keynote-ui chime: soft digital sine notes, one per `step`, `notes` in semitones from `freq`.
    [0] = a single blip (a UI object landing); [12, 7, 3, 0] = the falling arpeggio heard on scene
    turns in an Apple-style reference (spectrogram, 2026-10-08)."""
    notes = notes if notes else [0]
    n = int((step * (len(notes) - 1) + 0.28) * SR)
    out = np.zeros(n)
    for i, st in enumerate(notes):
        f = freq * 2 ** (st / 12)
        m = int(0.28 * SR)
        t = np.arange(m) / SR
        x = (np.sin(2 * np.pi * f * t) + 0.18 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.03))
        x *= np.clip(t / 0.003, 0, 1) * np.exp(-t / 0.075)
        s = int(i * step * SR)
        out[s:s + m] += x * (0.85 ** i)
    return pan_stereo(out * 0.28 * vel, pan)


def ratchet(dur: float, vel: float = 1.0, pan: float = 0.0, key=()) -> list[tuple[float, np.ndarray]]:
    """A train of tiny ticks that speeds up into its end — a counter rolling, a dial turning."""
    r = rng_for("ratchet", *key)
    hits, tt, gap = [], 0.0, 0.07
    while tt < dur:
        n = int(0.012 * SR)
        t = np.arange(n) / SR
        c = signal.sosfilt(butter("bandpass", [2500, 7000]), r.standard_normal(n)) * np.exp(-t / 0.0025)
        hits.append((tt, pan_stereo(c * 0.3 * vel * (0.6 + 0.4 * tt / dur), pan)))
        tt += gap
        gap = max(0.022, gap * 0.86)
    return hits


def shimmer(dur: float, vel: float = 1.0, pan_from: float = -0.4, pan_to: float = 0.4, key=()) -> np.ndarray:
    """Granular sparkle swish for a morph: many tiny rising sine grains under a bell envelope."""
    r = rng_for("shimmer", *key)
    n = int(dur * SR)
    out = np.zeros(n)
    for _ in range(int(dur * 90)):
        at = r.uniform(0, dur * 0.92)
        f = 2200 + 4200 * (at / dur) + r.uniform(-500, 500)
        m = int(0.03 * SR)
        t = np.arange(m) / SR
        g = np.sin(2 * np.pi * f * t) * np.sin(np.pi * t / t[-1]) * r.uniform(0.3, 1.0)
        s = int(at * SR)
        out[s:s + m] += g[: n - s]
    tt = np.arange(n) / SR
    out *= np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 1.2
    return pan_stereo(out * 0.09 * vel, pan_from + (pan_to - pan_from) * tt / dur)


def typing(dur: float, vel: float = 1.0, pan: float = 0.0, key=()) -> list[tuple[float, np.ndarray]]:
    """A burst of soft key clicks at a human, slightly irregular (but seeded) rate."""
    r = rng_for("typing", *key)
    hits, tt = [], 0.0
    while tt < dur:
        n = int(0.025 * SR)
        t = np.arange(n) / SR
        noise = r.standard_normal(n)
        c = signal.sosfilt(butter("bandpass", [1800, 6000]), noise) * np.exp(-t / 0.004)
        hits.append((tt, pan_stereo(c * 0.35 * vel * r.uniform(0.6, 1.0), pan)))
        tt += r.uniform(0.055, 0.11)
    return hits


def snare_roll(dur: float, key=()) -> list[tuple[float, np.ndarray]]:
    """Accelerating hits (8ths -> 32nds) with a gain ramp. Returns (offset, clip) pairs."""
    hits, tt, k = [], 0.0, 0
    while tt < dur:
        frac = tt / dur
        step = 0.25 * (0.125 / 0.25) ** min(frac * 1.4, 1.0)
        hits.append((tt, clap(vel=0.25 + 0.75 * frac, key=("roll", k, *key))))
        tt += step
        k += 1
    return hits


def reverb_ir(seconds: float = 1.4, key=()) -> np.ndarray:
    n = int(seconds * SR)
    t = np.arange(n) / SR
    r = rng_for("ir", *key)
    ir = r.standard_normal((n, 2)) * np.exp(-t / (seconds / 5))[:, None]
    ir = np.stack([signal.sosfilt(butter("lowpass", 6000), ir[:, c]) for c in (0, 1)], axis=1)
    return ir / np.sqrt(np.sum(ir ** 2, axis=0))


# ─────────────────────────────── samples ─────────────────────────────────

_SAMPLE_CACHE: dict[str, np.ndarray] = {}


def load_sample(path: Path) -> np.ndarray:
    """Any format ffmpeg reads -> float stereo at SR (cached per path)."""
    key = str(path.resolve())
    if key not in _SAMPLE_CACHE:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", key, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
            check=True, capture_output=True).stdout
        _SAMPLE_CACHE[key] = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    return _SAMPLE_CACHE[key]


def sample_clip(ev: dict, base: Path) -> np.ndarray:
    x = load_sample(base / ev["file"])
    s = int(ev.get("src", 0.0) * SR)
    length = ev.get("len")
    e = len(x) if length is None else min(len(x), s + int(length * SR))
    clip = x[s:e].copy()
    n = len(clip)
    fi, fo = int(ev.get("fade_in", 0.004) * SR), int(ev.get("fade_out", 0.012) * SR)
    if fi > 0:
        clip[:min(fi, n)] *= np.linspace(0, 1, min(fi, n))[:, None]
    if fo > 0:
        clip[max(n - fo, 0):] *= np.linspace(1, 0, n - max(n - fo, 0))[:, None]
    if "pan" in ev:
        mono = clip.mean(axis=1)
        clip = pan_stereo(mono, ev["pan"])
    return clip * db(ev.get("gain_db", 0.0))


# ─────────────────────────────── arrangement ─────────────────────────────

def beat_time(v, spb: float, marks: dict | None = None) -> float:
    """A time given as seconds, {'beat': n}, or {'mark': name, 'dt': offset} -> seconds.
    Marks let a sound follow the EDIT: a reel's word times move every time the cut changes, and
    hard-coded seconds went stale silently (Cal Hacks reel, 2026-09-25)."""
    if isinstance(v, dict):
        if "mark" in v:
            if not marks or v["mark"] not in marks:
                raise KeyError(f"fx references unknown mark {v['mark']!r}")
            return float(marks[v["mark"]]) + float(v.get("dt", 0.0))
        return v["beat"] * spb
    return float(v)


def render_music(cues: dict, n: int, spb: float) -> tuple[np.ndarray, np.ndarray, list[float]]:
    """Returns (music bus, drums bus, kick times). Steps are 16ths; a bar has 16 steps."""
    music = np.zeros((n, 2))
    drums = np.zeros((n, 2))
    kicks: list[float] = []
    step = spb / 4
    chords = cues.get("chords", ["Fm"])
    for li, layer in enumerate(cues.get("layers", [])):
        inst = layer["inst"]
        b0, b1 = layer.get("from_bar", 0), layer.get("to_bar", 999)
        # a section can start/end on a story MARK (snapped to the nearest bar), so the music arc
        # follows the edit when a reel's cut changes — the breakdown stays under the vulnerable line
        marks, bar_s = cues.get("marks", {}), spb * 4
        if "from_mark" in layer:
            b0 = int(round(marks[layer["from_mark"]] / bar_s))
        if "to_mark" in layer:
            b1 = int(round(marks[layer["to_mark"]] / bar_s))
        pattern = layer.get("pattern", "x...............")
        vel = db(layer.get("gain_db", 0.0))
        total_bars = int(math.ceil(n / SR / (spb * 4)))
        for bar in range(max(b0, 0), min(b1, total_bars)):
            chord = chords[bar % len(chords)]
            notes = chord_notes(chord, octave=layer.get("octave", 3))
            bar_t = bar * spb * 4
            if inst == "pad":
                cutoff = layer.get("cutoff", 1800)
                if "cutoff_to" in layer:
                    frac = (bar - b0) / max(b1 - b0 - 1, 1)
                    cutoff = cutoff * (layer["cutoff_to"] / cutoff) ** frac
                place(music, pad_chord(notes, spb * 4 + 0.2, cutoff, vel, key=(li, bar)), bar_t)
                continue
            for si, ch in enumerate(pattern[:16]):
                if ch == ".":
                    continue
                accent = {"X": 1.0, "x": 0.75}.get(ch, 0.5)
                t = bar_t + si * step
                if inst == "kick":
                    place(drums, kick(vel * accent, key=(li, bar, si)), t)
                    kicks.append(t)
                elif inst == "clap":
                    place(drums, clap(vel * accent, key=(li, bar, si)), t)
                elif inst == "hat":
                    place(drums, hat(vel * accent, key=(li, bar, si)), t)
                elif inst == "ohat":
                    place(drums, hat(vel * accent, open_=True, key=(li, bar, si)), t)
                elif inst == "tick":
                    place(drums, tick(vel * accent, layer.get("freq", 2400.0)), t)
                elif inst == "sub":
                    place(music, sub_note(notes[0] - 12, step * layer.get("len_steps", 2) * 0.95,
                                          vel * accent), t)
                elif inst == "pluck":
                    arp = notes + [notes[0] + 12]
                    m = arp[si % len(arp)] + 12
                    place(music, pluck(m, vel * accent, pan=0.35 * math.sin(si)), t)
                else:
                    raise ValueError(f"unknown instrument {inst!r}")
    return music, drums, kicks


def render_fx(cues: dict, n: int, spb: float, base: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (sfx bus, voice bus, reverb send)."""
    sfx = np.zeros((n, 2))
    voice = np.zeros((n, 2))
    send = np.zeros((n, 2))
    for i, ev in enumerate(cues.get("fx", [])):
        kind = ev["type"]
        at = beat_time(ev["at"], spb, cues.get("marks", {}))
        vel = db(ev.get("gain_db", 0.0))
        rv = ev.get("reverb", 0.0)
        if kind == "sample":
            clip = sample_clip(ev, base)
            target = voice if ev.get("bus") == "voice" else sfx
            place(target, clip, at)
            if rv:
                place(send, clip * rv, at)
            continue
        if kind == "riser":
            clip = riser(beat_time(ev["len"], spb), key=(i,)) * vel
        elif kind == "downlifter":
            clip = downlifter(beat_time(ev["len"], spb), key=(i,)) * vel
        elif kind == "impact":
            clip = impact(vel, key=(i,))
        elif kind == "whoosh":
            clip = whoosh(beat_time(ev.get("len", 0.4), spb), ev.get("pan_from", -0.8),
                          ev.get("pan_to", 0.8), vel, key=(i,))
        elif kind == "tick":
            clip = tick(vel, ev.get("freq", 2400.0), ev.get("pan", 0.0))
        elif kind == "kick":
            clip = kick(vel, key=("fx", i))
        elif kind == "clap":
            clip = clap(vel, key=("fx", i))
        elif kind == "ping":
            clip = ping(vel, ev.get("freq", 1320.0), ev.get("pan", 0.0))
        elif kind == "pop":
            clip = pop(vel, ev.get("pan", 0.0))
        elif kind == "blip":
            clip = blip(vel, ev.get("freq", 1568.0), ev.get("notes"), ev.get("step", 0.055), ev.get("pan", 0.0))
        elif kind == "shimmer":
            clip = shimmer(beat_time(ev.get("len", 0.5), spb), vel, ev.get("pan_from", -0.4),
                           ev.get("pan_to", 0.4), key=(i,))
        elif kind in ("typing", "ratchet"):
            gen = typing if kind == "typing" else ratchet
            for off, c in gen(beat_time(ev["len"], spb), vel, ev.get("pan", 0.0), key=(i,)):
                place(sfx, c, at + off)
                if rv:
                    place(send, c * rv, at + off)
            continue
        elif kind == "snare_roll":
            for off, c in snare_roll(beat_time(ev["len"], spb), key=(i,)):
                place(sfx, c * vel, at + off)
                if rv:
                    place(send, c * vel * rv, at + off)
            continue
        else:
            raise ValueError(f"unknown fx type {kind!r}")
        place(sfx, clip, at)
        if rv:
            place(send, clip * rv, at)
    return sfx, voice, send


def follower(x: np.ndarray, attack: float, release: float) -> np.ndarray:
    """Peak envelope follower (mono), deterministic, vectorised in blocks."""
    mono = np.abs(x).max(axis=1)
    hop = 64
    frames = np.array([mono[i:i + hop].max() for i in range(0, len(mono), hop)])
    a, r = math.exp(-hop / (attack * SR)), math.exp(-hop / (release * SR))
    env = np.zeros_like(frames)
    e = 0.0
    for i, v in enumerate(frames):
        e = a * e + (1 - a) * v if v > e else r * e + (1 - r) * v
        env[i] = e
    return np.repeat(env, hop)[:len(mono)]


def pump_curve(n: int, kicks: list[float], depth_db: float, recover: float) -> np.ndarray:
    g = np.ones(n)
    if not kicks or depth_db <= 0:
        return g
    t = np.arange(n) / SR
    floor = db(-depth_db)
    for k in kicks:
        i = int(k * SR)
        j = min(n, i + int(recover * SR * 1.2))
        seg = (t[i:j] - k) / recover
        g[i:j] = np.minimum(g[i:j], floor + (1 - floor) * np.clip(seg, 0, 1) ** 1.5)
    return g


def true_peak_db(x: np.ndarray) -> float:
    up = signal.resample_poly(x, 4, 1, axis=0)
    return 20 * math.log10(max(np.abs(up).max(), 1e-12))


def limit(x: np.ndarray, ceiling_db: float) -> np.ndarray:
    """Lookahead-free soft-knee limiter: gain computed on the 4x-oversampled peak envelope."""
    ceil = db(ceiling_db)
    up = np.abs(signal.resample_poly(x, 4, 1, axis=0)).max(axis=1)
    up = up[:len(x) * 4].reshape(len(x), 4).max(axis=1)
    need = np.minimum(1.0, ceil / np.maximum(up, 1e-12))
    # 2 ms lookahead: the gain is already down when the peak arrives, then an 80 ms release
    win = int(0.002 * SR)
    need = ndimage.minimum_filter1d(need, size=2 * win + 1, origin=0)
    rel = math.exp(-1 / (0.08 * SR))
    g = np.empty_like(need)
    cur = 1.0
    for i, v in enumerate(need):
        cur = v if v < cur else rel * cur + (1 - rel) * v
        g[i] = cur
    return x * g[:, None]


def master(mix: np.ndarray, lufs: float, tp: float) -> tuple[np.ndarray, float, float]:
    meter = pyln.Meter(SR)
    for _ in range(4):
        loud = meter.integrated_loudness(mix)
        mix = mix * db(lufs - loud)
        mix = limit(mix, tp - 0.3)
        if abs(meter.integrated_loudness(mix) - lufs) < 0.3 and true_peak_db(mix) <= tp:
            break
    return mix, meter.integrated_loudness(mix), true_peak_db(mix)


# ─────────────────────────────── main ────────────────────────────────────

def build(cues: dict, base: Path) -> tuple[np.ndarray, dict]:
    spb = 60.0 / cues["bpm"]
    dur = float(cues["duration"])
    n = int(round(dur * SR))
    tail = int(2.5 * SR)  # render tails past the end, then cut, so nothing clicks off mid-note
    music, drums, kicks = render_music(cues, n + tail, spb)
    sfx, voice, send = render_fx(cues, n + tail, spb, base)

    mixcfg = cues.get("mix", {})
    music *= pump_curve(len(music), kicks, mixcfg.get("pump_db", 5.0), mixcfg.get("pump_recover", 0.16))[:, None]
    duck = mixcfg.get("voice_duck_db", 9.0)
    if np.abs(voice).max() > 0 and duck > 0:
        env = follower(voice, 0.01, 0.25)
        env = np.clip(env / (np.percentile(env[env > 1e-4], 90) if (env > 1e-4).any() else 1), 0, 1)
        g = db(-duck * 1.0) ** env  # multiplicative: full duck when the voice is at level
        music *= g[:, None]
        drums *= (g ** 0.5)[:, None]

    wet = np.stack([signal.fftconvolve(send[:, c], reverb_ir(key=("main",))[:, c])[:len(send)] for c in (0, 1)], axis=1)
    mix = (music * db(mixcfg.get("music_db", 0.0)) + drums * db(mixcfg.get("drums_db", 0.0))
           + sfx * db(mixcfg.get("sfx_db", 0.0)) + voice * db(mixcfg.get("voice_db", 0.0))
           + wet * db(mixcfg.get("reverb_db", -8.0)))
    mix = mix[:n]
    fade = int(cues.get("tail_fade", 0.004) * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    mix, loud, peak = master(mix, cues.get("lufs", -14.0), cues.get("true_peak", -1.0))
    report = {"duration_s": round(n / SR, 4), "lufs": round(loud, 2), "true_peak_dbtp": round(peak, 2),
              "kicks": len(kicks), "fx_events": len(cues.get("fx", [])), "sr": SR,
              "bar_lufs": bar_loudness(mix, spb * 4)}
    hook = report["bar_lufs"][0] if report["bar_lufs"] else None
    if hook is not None and hook < loud - 6:
        report["warning"] = (f"hook bar is {loud - hook:.1f} LU under the integrated level — the first "
                             "second is the one that decides the scroll; bring the hook up")
    return mix, report


def bar_loudness(mix: np.ndarray, bar_s: float) -> list[float]:
    """Short-term loudness per bar (LUFS). Makes a quiet hook or a flat drop visible as numbers."""
    meter = pyln.Meter(SR, block_size=0.4)
    step = int(bar_s * SR)
    out = []
    for s in range(0, len(mix) - int(0.4 * SR), step):
        v = meter.integrated_loudness(mix[s:s + step])
        out.append(round(v, 1) if math.isfinite(v) else -70.0)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cues", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--emit-js", type=Path, help="also write the cue sheet as `window.CUES = {...}` "
                    "so the composition reads the SAME marks the score was built from")
    args = ap.parse_args(argv)
    cues = json.loads(args.cues.read_text())
    if args.emit_js:
        args.emit_js.write_text("// GENERATED by score.py from cues.json. Edit cues.json, never this file.\n"
                                f"window.CUES = {json.dumps(cues, separators=(',', ':'))};\n")
    mix, report = build(cues, args.cues.parent)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.out, mix.astype(np.float32), SR, subtype="PCM_24")
    report["sha256"] = hashlib.sha256(args.out.read_bytes()).hexdigest()[:16]
    args.out.with_suffix(".report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
