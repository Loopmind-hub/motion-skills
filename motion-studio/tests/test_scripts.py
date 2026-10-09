"""Tests for the motion-studio scripts.

Run:
    uv run --with pytest --with numpy --with scipy --with soundfile --with pyloudnorm --with pillow \
        pytest ~/.claude/skills/motion-studio/tests -q
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import beatgrid  # noqa: E402
import review  # noqa: E402
import score  # noqa: E402


# ───────────────────────────── score.py ─────────────────────────────

def base_cues(**over) -> dict:
    c = {
        "bpm": 120, "duration": 4.0, "lufs": -14.0, "true_peak": -1.0,
        "chords": ["Fm", "Db"],
        "layers": [
            {"inst": "kick", "from_bar": 0, "to_bar": 2, "pattern": "X...x...X...x..."},
            {"inst": "clap", "from_bar": 0, "to_bar": 2, "pattern": "....X.......X..."},
            {"inst": "pad", "from_bar": 0, "to_bar": 2, "cutoff": 900},
            {"inst": "sub", "from_bar": 0, "to_bar": 2, "pattern": "..x...x...x...x.", "len_steps": 2},
        ],
        "fx": [{"type": "riser", "at": 0.5, "len": 1.0}, {"type": "impact", "at": 2.0}],
    }
    c.update(over)
    return c


def test_score_hits_loudness_and_peak_targets(tmp_path):
    mix, rep = score.build(base_cues(), tmp_path)
    assert abs(rep["lufs"] - (-14.0)) <= 0.5
    assert rep["true_peak_dbtp"] <= -0.9
    assert len(mix) == int(4.0 * score.SR)
    assert rep["duration_s"] == 4.0


def test_score_is_deterministic(tmp_path):
    a, _ = score.build(base_cues(), tmp_path)
    b, _ = score.build(base_cues(), tmp_path)
    assert np.array_equal(a, b)


def test_score_places_a_sample_on_time(tmp_path):
    # a 10 ms click; with no music the only energy is the sample, so its onset must be at 1.5 s
    click = np.zeros(int(0.2 * score.SR)); click[:480] = 0.8
    sf.write(tmp_path / "click.wav", click, score.SR)
    cues = base_cues(layers=[], fx=[{"type": "sample", "file": "click.wav", "at": 1.5, "fade_in": 0}])
    mix, _ = score.build(cues, tmp_path)
    onset = np.argmax(np.abs(mix).max(axis=1) > 0.05) / score.SR
    assert abs(onset - 1.5) < 0.005


def test_score_beat_times_accept_beats(tmp_path):
    assert score.beat_time({"beat": 3}, 0.5) == 1.5
    assert score.beat_time(2.25, 0.5) == 2.25


def test_score_fx_can_follow_a_mark(tmp_path):
    assert score.beat_time({"mark": "w:hit", "dt": 0.04}, 0.5, {"w:hit": 16.66}) == pytest.approx(16.7)
    with pytest.raises(KeyError):
        score.beat_time({"mark": "missing"}, 0.5, {"w:hit": 1.0})
    # end to end: a ping placed on a mark lands where the mark is
    cues = base_cues(layers=[], fx=[{"type": "ping", "at": {"mark": "w:hit"}}], marks={"w:hit": 1.25})
    mix, _ = score.build(cues, tmp_path)
    onset = np.argmax(np.abs(mix).max(axis=1) > 0.02) / score.SR
    assert abs(onset - 1.25) < 0.01


def test_score_warns_on_a_quiet_hook(tmp_path):
    cues = base_cues(duration=8.0, layers=[
        {"inst": "tick", "from_bar": 0, "to_bar": 1, "pattern": "x...............", "gain_db": -30},
        {"inst": "kick", "from_bar": 1, "to_bar": 4, "pattern": "X.x.X.x.X.x.X.x."},
        {"inst": "pad", "from_bar": 1, "to_bar": 4, "cutoff": 2000},
    ], fx=[])
    _, rep = score.build(cues, tmp_path)
    assert "warning" in rep and "hook" in rep["warning"]
    assert len(rep["bar_lufs"]) == 4


def test_score_cli_emits_js_with_the_same_marks(tmp_path):
    cues = base_cues(marks={"drop": 2.0})
    (tmp_path / "cues.json").write_text(json.dumps(cues))
    score.main([str(tmp_path / "cues.json"), "-o", str(tmp_path / "mix.wav"), "--emit-js", str(tmp_path / "cues.js")])
    js = (tmp_path / "cues.js").read_text()
    assert js.splitlines()[1].startswith("window.CUES = ")
    assert json.loads(js.splitlines()[1][len("window.CUES = "):-1])["marks"]["drop"] == 2.0
    assert json.loads((tmp_path / "mix.report.json").read_text())["sha256"]


@pytest.mark.parametrize("fx", [
    {"type": "ping", "at": 1.0}, {"type": "pop", "at": 1.0}, {"type": "typing", "at": 1.0, "len": 0.6},
    {"type": "blip", "at": 1.0}, {"type": "blip", "at": 1.0, "notes": [12, 7, 3, 0]},
    {"type": "ratchet", "at": 1.0, "len": 0.4},
])
def test_score_ui_sounds_land_on_time(tmp_path, fx):
    mix, _ = score.build(base_cues(layers=[], fx=[fx]), tmp_path)
    onset = np.argmax(np.abs(mix).max(axis=1) > 0.02) / score.SR
    assert abs(onset - 1.0) < 0.01


def test_typing_is_seeded_but_irregular():
    a = score.typing(1.0, key=(3,))
    b = score.typing(1.0, key=(3,))
    assert [o for o, _ in a] == [o for o, _ in b]           # deterministic
    gaps = np.diff([o for o, _ in a])
    assert gaps.std() > 0.005                                # humanised, not a metronome


def test_blip_arpeggio_steps_down_in_pitch():
    # keynote-ui chime: pitched steps; notes [12, 7, 3, 0] must sound highest first
    clip = score.blip(notes=[12, 7, 3, 0], step=0.06)[:, 0]
    seg = int(0.06 * score.SR)
    def peak_hz(x):
        spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
        return np.fft.rfftfreq(len(x), 1 / score.SR)[spec.argmax()]
    first, last = peak_hz(clip[:seg]), peak_hz(clip[3 * seg:4 * seg])
    assert first > last * 1.8, (first, last)


def test_shimmer_swells_inside_its_window(tmp_path):
    mix, _ = score.build(base_cues(layers=[], fx=[{"type": "shimmer", "at": 1.0, "len": 0.5}]), tmp_path)
    env = np.abs(mix).max(axis=1)
    loud = np.nonzero(env > env.max() * 0.1)[0] / score.SR
    assert loud.min() >= 1.0 and loud.max() <= 1.55          # sounds only inside [at, at + len]
    peak = env.argmax() / score.SR
    assert 1.1 < peak < 1.45                                  # a swell, not a hit


def test_ratchet_accelerates_and_is_seeded():
    a, b = score.ratchet(0.5, key=(1,)), score.ratchet(0.5, key=(1,))
    offs = [o for o, _ in a]
    assert offs == [o for o, _ in b]
    gaps = np.diff(offs)
    assert len(offs) >= 6 and gaps[-1] < gaps[0] * 0.7      # ticks speed up into the hit


def test_camera_spec_names_resolve_in_engine_template():
    # the engine resolves "drop" etc. against CUES.marks — make sure the template still exports it
    src = (SCRIPTS.parent / "templates" / "engine.js").read_text()
    for api in ("MS.springStep", "MS.springEase", "MS.camera", "MS.shaderBg", "MS.grain", "MS.drive"):
        assert api in src


def test_chord_parsing():
    assert score.chord_notes("Fm", 3) == [53, 56, 60]
    assert score.chord_notes("Db", 3) == [49, 53, 56]
    with pytest.raises(ValueError):
        score.chord_notes("Fdim7")


# ─────────────────────────── beatgrid.py ────────────────────────────

def click_track(bpm: float, first: float, seconds: float = 12.0) -> np.ndarray:
    sr, spb = beatgrid.SR, 60 / bpm
    x = np.zeros(int(seconds * sr))
    t = np.arange(int(0.08 * sr)) / sr
    for k, b in enumerate(np.arange(first, seconds - 0.1, spb)):
        i = int(b * sr)
        if k % 4 == 0:   # downbeat: low thump + click
            s = 0.9 * np.sin(2 * np.pi * 60 * t) * np.exp(-t / 0.03) + 0.3 * np.sin(2 * np.pi * 2000 * t) * np.exp(-t / 0.004)
        else:
            s = 0.5 * np.sin(2 * np.pi * 2000 * t) * np.exp(-t / 0.004)
        x[i:i + len(s)] += s[:len(x) - i]
    return x


@pytest.mark.parametrize("bpm", [120.0, 100.0])
def test_beatgrid_finds_tempo_and_downbeat(bpm):
    res = beatgrid.analyse(click_track(bpm, first=0.25))
    assert abs(res["bpm"] - bpm) < 1.5
    spb = 60 / bpm
    # first downbeat is 0.25 s (or a whole bar later if the tracker's first beat lands after it)
    fd = res["first_downbeat_s"]
    assert min(abs(fd - 0.25), abs(fd - 0.25 - 4 * spb)) < 0.04


# ──────────────────────────── review.py ─────────────────────────────

def make_video(path: Path, fps: int = 30, seconds: float = 5.0, still=(2.0, 3.5)):
    w, h = 90, 160
    n = int(fps * seconds)
    frames = np.zeros((n, h, w, 3), np.uint8)
    for i in range(n):
        t = i / fps
        if still[0] <= t < still[1]:
            x = int((still[0] * 40) % (w - 20))
        else:
            x = int((t * 40) % (w - 20))
        frames[i, 60:100, x:x + 20] = 255
    frames[-1] = frames[0]   # a perfect loop seam
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                    "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "12", str(path)],
                   input=frames.tobytes(), check=True)


def test_review_detects_dead_time_and_loop(tmp_path):
    v = tmp_path / "v.mp4"
    make_video(v)
    review.main([str(v), "--bpm", "120", "-o", str(tmp_path / "rv"), "--floor", "0.5"])
    rep = json.loads((tmp_path / "rv" / "report.json").read_text())
    assert rep["dead_windows"], "the 1.5 s freeze must be flagged"
    a, b = rep["dead_windows"][0]
    assert abs(a - 2.0) < 0.15 and abs(b - 3.5) < 0.15
    assert rep["loop_first_last_delta"] < 3
    assert (tmp_path / "rv" / "beats.jpg").exists() and (tmp_path / "rv" / "energy.png").exists()


def test_beat_zero_uses_the_loop_tail_as_its_baseline():
    # a hit right at frame 0 (then quiet), with a quiet tail: beat 0 must count as a hit
    e = np.array([6.0, 6.0, 5.0] + [0.2] * 60)
    hits = review.beat_hits(e, fps=60, beats=[0.0], tol_s=0.05, floor=1.0)
    assert hits[0]["hit"]
    # and a genuinely still start stays a miss
    still = np.array([0.1] * 63)
    assert not review.beat_hits(still, fps=60, beats=[0.0], tol_s=0.05, floor=1.0)[0]["hit"]


def test_camera_budget_flags_a_heartbeat():
    # Servi v3 as it was: 36 punches + a per-beat pulse → the "heartbeat" Freddy felt
    heavy = {"marks": {"a": 8.0, "b": 13.0}, "camera": {
        "punches": [{"t": i * 0.5, "a": 0.01} for i in range(36)],
        "pulse": {"from": "a", "to": "b", "every": 0.5, "a": 0.008},
        "shakes": [{"t": 1}, {"t": 2}, {"t": 3}, {"t": 4}]}}
    r = review.camera_budget(heavy, 20.0)
    assert not r["ok"] and r["punches"] == 36 + 9 and len(r["problems"]) == 3
    # the fixed version: punctuation only
    light = {"camera": {"punches": [{"t": 4}, {"t": 8}, {"t": 17.75}], "shakes": [{"t": 8}]}}
    assert review.camera_budget(light, 20.0)["ok"]
    assert review.camera_budget({}, 15.0)["declared"] is False


def test_adaptive_floor_survives_one_extreme_section():
    # 70% gentle constant motion (0.6), 30% hyperspace (16): the gentle part must NOT read as dead
    e = np.concatenate([np.full(700, 0.6), np.full(300, 16.0)])
    f = review.adaptive_floor(e)
    assert f < 0.6
    assert review.dead_windows(e, fps=60, min_dead_s=0.6, floor=f) == []
    # a genuinely still stretch is still caught
    e2 = np.concatenate([np.full(120, 0.02), np.full(880, 2.0)])
    assert review.dead_windows(e2, fps=60, min_dead_s=0.6, floor=review.adaptive_floor(e2))


def test_dead_windows_respects_minimum_length():
    e = np.array([5.0] * 10 + [0.0] * 5 + [5.0] * 10)
    assert review.dead_windows(e, fps=10, min_dead_s=0.6, floor=1.0) == []
    assert review.dead_windows(e, fps=10, min_dead_s=0.5, floor=1.0) == [(1.0, 1.5)]
