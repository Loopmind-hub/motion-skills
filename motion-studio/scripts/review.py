#!/usr/bin/env python3
"""review.py — the objective half of the critique loop.

Watches a render the way an editor scrubs it, and turns "feels slow in places"
into numbers you can act on:

  • motion energy per frame (mean abs luma change) → an energy strip PNG
  • DEAD TIME: windows ≥ --dead seconds where nothing moves enough to see
  • BEAT HITS: for every beat on the grid, did something visibly happen near it?
  • a labelled contact sheet, one frame per beat, with the social safe zone drawn on
  • report.md + report.json with all of the above

Run:
    uv run --with numpy --with pillow ~/.claude/skills/motion-studio/scripts/review.py \
        renders/video.mp4 --cues cues.json -o review/v2

It never judges taste. It tells you WHERE to look; the critique pass decides WHAT to fix.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SMALL_W, SMALL_H = 90, 160          # analysis resolution (9:16); enough to see motion, cheap to diff
FONT_CANDIDATES = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                   "/System/Library/Fonts/Supplemental/Arial.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
# Conservative 9:16 safe zone that satisfies every published variant for Reels + TikTok
# (top UI ~250px, right action column ~120px, bottom caption block ~370px, left ~60px).
SAFE = {"left": 60, "top": 250, "right": 120, "bottom": 370}


def probe(video: Path) -> tuple[float, float, int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=r_frame_rate,width,height:format=duration", "-of", "json", str(video)],
                         check=True, capture_output=True, text=True).stdout
    j = json.loads(out)
    num, den = j["streams"][0]["r_frame_rate"].split("/")
    return (float(num) / float(den), float(j["format"]["duration"]),
            int(j["streams"][0]["width"]), int(j["streams"][0]["height"]))


def luma_frames(video: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf",
                          f"scale={SMALL_W}:{SMALL_H}:flags=area,format=gray", "-f", "rawvideo", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, SMALL_H, SMALL_W).astype(np.float32)


def motion_energy(frames: np.ndarray) -> np.ndarray:
    """Mean |Δluma| between consecutive frames (0..255). energy[0] = energy[1]."""
    if len(frames) < 2:
        return np.zeros(len(frames))
    e = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    return np.concatenate([[e[0]], e])


def adaptive_floor(energy: np.ndarray) -> float:
    """Energy below which a frame counts as still. 12% of p90, but never above 30% of the median:
    one extreme section (a full-frame hyperspace, energy ~16) inflated p90 so much that a constantly
    scrolling grid (0.57) read as 'dead' (future-of-AI v2: 13.9 s of false dead time). Never under
    0.35 grey levels (sensor-noise territory)."""
    p90, p50 = float(np.percentile(energy, 90)), float(np.percentile(energy, 50))
    return max(0.35, min(0.12 * p90, 0.3 * p50))


def dead_windows(energy: np.ndarray, fps: float, min_dead_s: float, floor: float) -> list[tuple[float, float]]:
    """Runs of consecutive frames whose energy stays under `floor` for ≥ min_dead_s."""
    quiet = energy < floor
    out, start = [], None
    for i, q in enumerate(np.append(quiet, False)):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if (i - start) / fps >= min_dead_s:
                out.append((round(start / fps, 2), round(i / fps, 2)))
            start = None
    return out


def beat_hits(energy: np.ndarray, fps: float, beats: list[float], tol_s: float, floor: float) -> list[dict]:
    """A beat 'hits' when the energy near it rises above the floor AND above what came just before it."""
    res = []
    tol = max(1, int(round(tol_s * fps)))
    for b in beats:
        i = int(round(b * fps))
        if i >= len(energy):
            continue
        win = energy[max(i - tol, 0):min(i + tol + 1, len(energy))]
        if i - tol <= 0:
            # no history before the first beat: the video loops, so the frames before beat 0 are
            # the END of the video (without this, beat 0's baseline was its own peak → always "missed")
            before = energy[len(energy) - 2 * tol:]
        else:
            before = energy[max(i - 3 * tol, 0):i - tol]
        peak = float(win.max()) if len(win) else 0.0
        base = float(np.median(before)) if len(before) else 0.0
        res.append({"t": round(b, 3), "peak": round(peak, 2),
                    "hit": bool(peak >= floor and peak >= base * 1.15)})
    return res


def camera_budget(cues: dict, dur: float) -> dict:
    """Camera hits are punctuation, not rhythm (doctrine §5). A punch moves every pixel, so it also
    games the beat-hit metric — this is the check that stops that. Budget: punches ≤ max(4, dur/5),
    shakes ≤ 2, no per-beat pulse unless the brief is a hype/music edit."""
    cam = cues.get("camera")
    if cam is None:
        return {"declared": False, "ok": None,
                "note": "camera not declared in cues.json — budget not checked (legacy composition)"}
    punches = len(cam.get("punches", []))
    pulse = cam.get("pulse")
    pulse_hits = 0
    if pulse:
        marks = cues.get("marks", {})
        at = lambda v: marks.get(v, 0.0) if isinstance(v, str) else float(v)
        pulse_hits = max(0, int((at(pulse["to"]) - at(pulse["from"])) / float(pulse["every"])) - 1)
    shakes = len(cam.get("shakes", []))
    budget = max(4, round(dur / 5))
    problems = []
    if punches + pulse_hits > budget:
        problems.append(f"{punches + pulse_hits} camera punches (budget {budget}) — it will read as a heartbeat")
    if pulse:
        problems.append("per-beat camera pulse is on — opt-in only for hype/music edits")
    if shakes > 2:
        problems.append(f"{shakes} shakes (budget 2)")
    return {"declared": True, "punches": punches + pulse_hits, "shakes": shakes, "budget": budget,
            "ok": not problems, "problems": problems}


def load_font(size: int):
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def frame_at(video: Path, t: float, w: int) -> Image.Image:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                          "-vf", f"scale={w}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
                         check=True, capture_output=True).stdout
    from io import BytesIO
    return Image.open(BytesIO(raw)).convert("RGB")


def contact_sheet(video: Path, times: list[float], labels: list[str], full_w: int, full_h: int,
                  out: Path, cols: int = 6, tile_w: int = 270) -> None:
    scale = tile_w / full_w
    tile_h = int(round(full_h * scale))
    rows = (len(times) + cols - 1) // cols
    head = 34
    sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + head)), (20, 20, 22))
    font = load_font(20)
    for k, (t, lab) in enumerate(zip(times, labels)):
        im = frame_at(video, t, tile_w)
        d = ImageDraw.Draw(im)
        # SAFE margins are defined on the 1080×1920 reference frame, whatever the render size
        sx, sy = tile_w / 1080, tile_h / 1920
        l, tp = SAFE["left"] * sx, SAFE["top"] * sy
        r, b = tile_w - SAFE["right"] * sx, tile_h - SAFE["bottom"] * sy
        d.rectangle([l, tp, r, b], outline=(0, 220, 255), width=1)
        x, y = (k % cols) * tile_w, (k // cols) * (tile_h + head)
        sheet.paste(im, (x, y + head))
        ImageDraw.Draw(sheet).text((x + 8, y + 6), lab, fill=(240, 240, 240), font=font)
    sheet.save(out, quality=88)


def energy_strip(energy: np.ndarray, fps: float, beats: list[float], dead: list[tuple[float, float]],
                 hits: list[dict], floor: float, out: Path, w: int = 1800, h: int = 260) -> None:
    im = Image.new("RGB", (w, h), (16, 16, 18))
    d = ImageDraw.Draw(im)
    dur = len(energy) / fps
    top = max(float(np.percentile(energy, 99)), floor * 3, 1e-6)
    for a, b in dead:
        d.rectangle([a / dur * w, 0, b / dur * w, h], fill=(90, 20, 20))
    for hb in hits:
        x = hb["t"] / dur * w
        d.line([x, 0, x, h], fill=(60, 60, 70) if hb["hit"] else (220, 60, 60), width=1)
    fy = h - floor / top * (h - 10)
    d.line([0, fy, w, fy], fill=(0, 160, 200), width=1)
    pts = [(i / len(energy) * w, h - min(e / top, 1) * (h - 10)) for i, e in enumerate(energy)]
    d.line(pts, fill=(255, 176, 32), width=2)
    font = load_font(16)
    for s in range(int(dur) + 1):
        d.text((s / dur * w + 3, 4), f"{s}s", fill=(150, 150, 150), font=font)
    im.save(out)


def camera_line(c: dict) -> str:
    if not c.get("declared"):
        return "- Camera budget: not checked (camera not declared in cues.json)"
    if c["ok"]:
        return f"- Camera budget OK: {c['punches']} punches (≤ {c['budget']}), {c['shakes']} shakes (≤ 2)"
    return "- ⚠ **Camera over budget:** " + "; ".join(c["problems"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video", type=Path)
    ap.add_argument("--cues", type=Path, help="cue sheet (bpm + marks); without it --bpm is used")
    ap.add_argument("--bpm", type=float, default=120.0)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--dead", type=float, default=0.6, help="seconds of stillness that count as dead time")
    ap.add_argument("--floor", type=float, default=None,
                    help="energy below which a frame counts as still (default: adaptive)")
    args = ap.parse_args(argv)

    fps, dur, W, H = probe(args.video)
    frames = luma_frames(args.video)
    energy = motion_energy(frames)
    floor = args.floor if args.floor is not None else adaptive_floor(energy)

    bpm, marks, cues = args.bpm, {}, {}
    if args.cues:
        cues = json.loads(args.cues.read_text())
        bpm, marks = float(cues["bpm"]), cues.get("marks", {})
    spb = 60.0 / bpm
    beats = [round(k * spb, 4) for k in range(int(dur / spb) + 1) if k * spb < dur - 1e-3]

    dead = dead_windows(energy, fps, args.dead, floor)
    hits = beat_hits(energy, fps, beats, tol_s=0.06, floor=floor)
    missed = [h["t"] for h in hits if not h["hit"]]

    args.out.mkdir(parents=True, exist_ok=True)
    energy_strip(energy, fps, beats, dead, hits, floor, args.out / "energy.png")
    # one still per beat, taken just after the hit so the landed state is what you judge
    times = [min(b + 0.12, dur - 0.02) for b in beats]
    labels = []
    for b in beats:
        tag = next((k for k, v in marks.items() if abs(float(v) - b) < 1e-3), "")
        labels.append(f"{b:.2f}s {tag}".strip())
    contact_sheet(args.video, times, labels, W, H, args.out / "beats.jpg")
    # loop check: first frame vs last frame
    loop_delta = float(np.abs(frames[0] - frames[-1]).mean()) if len(frames) > 1 else 0.0

    report = {
        "video": str(args.video), "fps": fps, "duration_s": round(dur, 3), "bpm": bpm,
        "energy_floor": round(floor, 3), "mean_energy": round(float(energy.mean()), 3),
        "dead_windows": dead, "dead_time_s": round(sum(b - a for a, b in dead), 2),
        "beats": len(hits), "beats_hit": sum(h["hit"] for h in hits), "beats_missed": missed,
        "loop_first_last_delta": round(loop_delta, 2),
        "camera": camera_budget(cues, dur) if args.cues else {"declared": False, "ok": None},
    }
    (args.out / "report.json").write_text(json.dumps(report, indent=2))
    lines = [f"# Review — {args.video.name}", "",
             f"- **{report['beats_hit']}/{report['beats']} beats** carry a visible event"
             + (f" — missed: {', '.join(f'{m:.2f}s' for m in missed)}" if missed else ""),
             f"- **Dead time: {report['dead_time_s']} s** in {len(dead)} window(s) ≥ {args.dead}s"
             + (": " + ", ".join(f"{a}–{b}s" for a, b in dead) if dead else ""),
             f"- Loop seam (mean |first−last| luma): **{report['loop_first_last_delta']}** "
             "(under ~3 reads as seamless)",
             f"- Mean motion energy {report['mean_energy']} · still-floor {report['energy_floor']}",
             camera_line(report["camera"]), "",
             "Files: `energy.png` (amber = motion, red bands = dead time, red lines = missed beats), "
             "`beats.jpg` (one frame per beat, cyan box = social safe zone)."]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
