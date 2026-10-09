#!/usr/bin/env python3
"""apple_audit — lint a HyperFrames project for Apple-grade restraint.

The premium look is mostly what you DON'T do, and a rule that only lives in a doc drifts. This
script checks the project against its brand lock (`style.json`) and its cue sheet (`cues.json`):

  • PALETTE   every colour in index.html is one of the ≤3 palette colours (alpha variants allowed)
  • TYPE      every font-family is a declared family (generic fallbacks ignored)
  • SFX       ≤ max_per_10s sound effects in any 10 s window, ≤ max_types distinct types, none banned
  • CAMERA    punches ≤ budget, shakes ≤ budget (default 1 and 0)
  • TEMPO     bpm inside the chosen feel band
  • SHOTS     each shot names ONE idea, holds ≥ min_s to breathe, hard cuts ≤ max_cuts,
              and shot lengths VARY (adaptive rhythm, not a metronome)
  • FIELDS    (keynote-ui) every hard cut flips the background field
  • MOTION    (keynote-ui) fast movers carry shutter motion blur

Usage:
  apple_audit.py <project_dir>            → report + exit 1 on any failure
  apple_audit.py <project_dir> --holds    → comma list of each shot's hold time (for snapbeats --only)
  apple_audit.py <project_dir> --json     → machine-readable report
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

GENERIC_FONTS = {"sans-serif", "serif", "monospace", "system-ui", "inherit", "initial", "cursive",
                 "ui-sans-serif", "ui-monospace", "-apple-system", "unset"}
DEFAULTS = {
    "sfx": {"max_per_10s": 3, "max_types": 3, "banned": ["snare_roll", "typing", "clap"]},
    "camera": {"punches": 1, "shakes": 0},
    "shots": {"min_s": 1.2, "max_cuts": 1, "min_rhythm_cv": 0.15},
}
TRANSITIONS = {"cut", "match", "morph", "push", "mask", "dissolve", "open"}


# ── colours ────────────────────────────────────────────────────────────────────────────────
def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h[:3])
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def colours_in(html: str) -> list[tuple[str, tuple[int, int, int]]]:
    """Every literal colour in the page (hex + rgb/rgba), skipping #tokens that are element ids."""
    ids = set(re.findall(r'\bid\s*=\s*["\']([^"\']+)["\']', html))
    found = []
    for m in re.finditer(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])", html):
        if m.group(1) in ids:
            continue
        found.append((m.group(0), hex_to_rgb(m.group(1))))
    for m in re.finditer(r"rgba?\(\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})", html):
        found.append((m.group(0) + ")", (int(m.group(1)), int(m.group(2)), int(m.group(3)))))
    return found


def check_palette(html: str, style: dict) -> dict:
    palette = style.get("palette", {})
    allowed = {hex_to_rgb(v) for v in palette.values()}
    allowed |= {hex_to_rgb(v) for v in style.get("extra_allowed", [])}
    off = sorted({lit for lit, rgb in colours_in(html) if rgb not in allowed})
    problems = []
    if len(palette) > 3:
        problems.append(f"palette has {len(palette)} colours — the lock is 3")
    if off:
        problems.append(f"{len(off)} colour(s) outside the palette: {', '.join(off[:8])}")
    return {"ok": not problems, "palette": palette, "off_palette": off, "problems": problems}


# ── type ───────────────────────────────────────────────────────────────────────────────────
def families_in(html: str) -> set[str]:
    fams = set()
    for m in re.finditer(r"font-family\s*:\s*([^;}\"]+)", html):
        for f in m.group(1).split(","):
            f = f.strip().strip("'\"").strip()
            if f and f.lower() not in GENERIC_FONTS and not f.startswith("var("):
                fams.add(f)
    return fams


def check_type(html: str, style: dict) -> dict:
    declared = set(style.get("type", {}).get("families", []))
    used = families_in(html)
    extra = sorted(used - declared)
    problems = [f"undeclared typeface(s): {', '.join(extra)}"] if extra else []
    if len(declared) > 2:
        problems.append(f"{len(declared)} families declared — premium pieces use 1 (2 at most)")
    return {"ok": not problems, "declared": sorted(declared), "used": sorted(used), "problems": problems}


# ── time resolution (same semantics as score.py) ──────────────────────────────────────────
def resolve_at(at, marks: dict, bpm: float) -> float:
    spb = 60.0 / bpm
    if isinstance(at, (int, float)):
        return float(at)
    if isinstance(at, str):
        return float(marks[at])
    if isinstance(at, dict):
        if "mark" in at:
            return float(marks[at["mark"]]) + float(at.get("dt", 0.0))
        if "beat" in at:
            return float(at["beat"]) * spb
    raise ValueError(f"cannot resolve time {at!r}")


# ── sound ──────────────────────────────────────────────────────────────────────────────────
def check_sfx(cues: dict, style: dict) -> dict:
    cfg = {**DEFAULTS["sfx"], **style.get("sfx", {})}
    marks, bpm = cues.get("marks", {}), float(cues.get("bpm", 120))
    events = [(resolve_at(f["at"], marks, bpm), f["type"]) for f in cues.get("fx", [])
              if f.get("type") != "sample"]  # voice / licensed music are not sound effects
    events.sort()
    types = sorted({t for _, t in events})
    worst, worst_at = 0, 0.0
    for i, (t0, _) in enumerate(events):
        n = sum(1 for t, _ in events[i:] if t < t0 + 10.0)
        if n > worst:
            worst, worst_at = n, t0
    problems = []
    if worst > cfg["max_per_10s"]:
        problems.append(f"{worst} SFX in the 10 s from {worst_at:.1f}s — budget {cfg['max_per_10s']}")
    if len(types) > cfg["max_types"]:
        problems.append(f"{len(types)} SFX types ({', '.join(types)}) — budget {cfg['max_types']}")
    banned = sorted(set(types) & set(cfg["banned"]))
    if banned:
        problems.append(f"banned SFX: {', '.join(banned)}")
    return {"ok": not problems, "count": len(events), "types": types,
            "worst_10s": worst, "problems": problems}


def check_camera(cues: dict, style: dict) -> dict:
    cfg = {**DEFAULTS["camera"], **style.get("camera", {})}
    cam = cues.get("camera", {}) or {}
    punches, shakes = len(cam.get("punches", [])), len(cam.get("shakes", []))
    problems = []
    if punches > cfg["punches"]:
        problems.append(f"{punches} camera punches — budget {cfg['punches']} (premium = the object moves, not the frame)")
    if shakes > cfg["shakes"]:
        problems.append(f"{shakes} camera shakes — budget {cfg['shakes']}")
    if cam.get("pulse"):
        problems.append("camera pulse present — never in a premium piece")
    return {"ok": not problems, "punches": punches, "shakes": shakes, "problems": problems}


def check_tempo(cues: dict, style: dict) -> dict:
    band = style.get("music", {}).get("bpm")
    bpm = float(cues.get("bpm", 120))
    if not band:
        return {"ok": False, "bpm": bpm, "problems": ["style.json has no music.bpm band — choose the feel first"]}
    lo, hi = band
    ok = lo <= bpm <= hi
    return {"ok": ok, "bpm": bpm, "band": band,
            "problems": [] if ok else [f"bpm {bpm:g} outside the chosen band {lo}–{hi}"]}


# ── shots ──────────────────────────────────────────────────────────────────────────────────
def shot_table(cues: dict) -> list[dict]:
    marks, bpm = cues.get("marks", {}), float(cues.get("bpm", 120))
    dur_total = float(cues["duration"])
    shots = []
    for s in cues.get("shots", []):
        shots.append({**s, "start": resolve_at(s["at"], marks, bpm)})
    shots.sort(key=lambda s: s["start"])
    for i, s in enumerate(shots):
        end = shots[i + 1]["start"] if i + 1 < len(shots) else dur_total
        s["dur"] = round(end - s["start"], 3)
        s["hold"] = round(resolve_at(s["hold"], marks, bpm), 3) if "hold" in s else round(s["start"] + 0.7 * s["dur"], 3)
    return shots


def check_shots(cues: dict, style: dict) -> dict:
    cfg = {**DEFAULTS["shots"], **style.get("shots", {})}
    shots = shot_table(cues)
    problems = []
    if not shots:
        return {"ok": False, "shots": [], "problems": ["cues.json has no `shots` — storyboard the piece shot by shot first"]}
    for s in shots:
        idea = str(s.get("idea", "")).strip()
        if not idea:
            problems.append(f"shot {s.get('id', '?')} has no idea — one shot = one idea")
        elif " and " in idea.lower() or ";" in idea:
            problems.append(f"shot {s.get('id', '?')} carries two ideas ({idea!r}) — split it")
        if s["dur"] < cfg["min_s"]:
            problems.append(f"shot {s.get('id', '?')} lasts {s['dur']:.2f}s — under {cfg['min_s']}s it can't breathe")
        if s.get("in", "cut") not in TRANSITIONS:
            problems.append(f"shot {s.get('id', '?')}: unknown transition {s.get('in')!r} ({', '.join(sorted(TRANSITIONS))})")
    cuts = sum(1 for s in shots[1:] if s.get("in", "cut") == "cut")
    if cuts > cfg["max_cuts"]:
        problems.append(f"{cuts} hard cuts — budget {cfg['max_cuts']}; carry the eye with match/morph/push/mask")
    cv = 0.0
    if len(shots) >= 3:
        durs = [s["dur"] for s in shots]
        cv = statistics.pstdev(durs) / statistics.mean(durs)
        if cv < cfg["min_rhythm_cv"]:
            problems.append(f"shot lengths barely vary (cv {cv:.2f}) — the rhythm is a metronome; speed up or slow down by act")
    return {"ok": not problems, "cuts": cuts, "rhythm_cv": round(cv, 3),
            "shots": [{k: s.get(k) for k in ("id", "start", "dur", "hold", "in", "idea")} for s in shots],
            "problems": problems}


def check_fields(cues: dict, style: dict) -> dict:
    """keynote-ui register: a hard cut is only allowed when the FIELD flips (light ↔ dark, or another
    declared field). Measured on the reference: every one of its cuts changed the background, which is
    what makes a cut read as a page turn instead of a jump."""
    if not style.get("shots", {}).get("cut_flips_field"):
        return {"ok": True, "problems": []}
    shots = shot_table(cues)
    problems = []
    for prev, s in zip(shots, shots[1:]):
        if s.get("in", "cut") != "cut":
            continue
        if not s.get("field") or not prev.get("field"):
            problems.append(f"shot {s.get('id', '?')} is a cut but a `field` is missing — declare the background of every shot")
        elif s["field"] == prev["field"]:
            problems.append(f"shot {s.get('id', '?')} cuts without flipping the field ({s['field']}) — flip it or use a continuity transition")
    return {"ok": not problems, "problems": problems}


def check_motion(html: str, style: dict) -> dict:
    """keynote-ui register: the smoothness is shutter blur, not frame rate (the reference is 30 fps).
    Every fast-moving element must carry data-hf-motion-blur."""
    if not style.get("motion", {}).get("blur_required"):
        return {"ok": True, "problems": []}
    ok = "data-hf-motion-blur" in html or "attachMotionBlur" in html
    return {"ok": ok, "problems": [] if ok else
            ["no motion blur — put data-hf-motion-blur on every element that moves fast (cards, pills, words)"]}


# ── entry ──────────────────────────────────────────────────────────────────────────────────
def audit(project: Path) -> dict:
    style = json.loads((project / "style.json").read_text())
    cues = json.loads((project / "cues.json").read_text())
    html = (project / "index.html").read_text() if (project / "index.html").exists() else ""
    checks = {
        "palette": check_palette(html, style),
        "type": check_type(html, style),
        "sfx": check_sfx(cues, style),
        "camera": check_camera(cues, style),
        "tempo": check_tempo(cues, style),
        "shots": check_shots(cues, style),
        "fields": check_fields(cues, style),
        "motion": check_motion(html, style),
    }
    return {"ok": all(c["ok"] for c in checks.values()), "checks": checks}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project", type=Path)
    ap.add_argument("--holds", action="store_true", help="print shot hold times for snapbeats --only")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.holds:
        cues = json.loads((args.project / "cues.json").read_text())
        print(",".join(f"{s['hold']:g}" for s in shot_table(cues)))
        return 0

    report = audit(args.project)
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        for name, c in report["checks"].items():
            print(f"{'PASS' if c['ok'] else 'FAIL'}  {name}")
            for p in c["problems"]:
                print(f"      · {p}")
        print("\nAPPLE AUDIT", "PASSED" if report["ok"] else "FAILED")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
