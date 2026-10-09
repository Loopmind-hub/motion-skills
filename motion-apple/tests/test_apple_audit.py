"""Tests for apple_audit. Run: uv run --with pytest pytest ~/.claude/skills/motion-apple/tests -q"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import apple_audit as A  # noqa: E402

STYLE = {
    "palette": {"bg": "#0B0B0C", "ink": "#F5F5F7", "accent": "#2997FF"},
    "type": {"families": ["Inter"]},
    "music": {"bpm": [90, 110]},
}


def cues(**over):
    base = {
        "bpm": 100, "duration": 12.0,
        "marks": {"reveal": 0.0, "detail": 2.4, "name": 8.4},
        "shots": [
            {"id": "reveal", "at": "reveal", "in": "open", "idea": "the phone appears"},
            {"id": "detail", "at": {"mark": "detail"}, "in": "match", "idea": "the camera finds the button"},
            {"id": "name", "at": "name", "in": "morph", "idea": "the product is named"},
        ],
        "fx": [{"type": "whoosh", "at": {"mark": "detail", "dt": -0.1}},
               {"type": "tick", "at": {"mark": "name"}}],
        "camera": {"moves": [{"t": "detail", "s": 1.04}], "punches": [], "shakes": []},
    }
    base.update(over)
    return base


# palette ───────────────────────────────────────────────────────────────────────────────────
def test_palette_accepts_palette_colours_and_alpha_variants():
    html = '<style>body{background:#0b0b0c;color:#F5F5F7} .a{fill:rgba(41,151,255,.4)}</style>'
    assert A.check_palette(html, STYLE)["ok"]


def test_palette_flags_off_palette_colour():
    r = A.check_palette("<style>.x{color:#ff0000}</style>", STYLE)
    assert not r["ok"] and "#ff0000" in r["off_palette"]


def test_palette_ignores_element_ids_that_look_like_hex():
    html = '<div id="fade"></div><style>#fade{color:#F5F5F7}</style>'
    assert A.check_palette(html, STYLE)["ok"]


def test_palette_rejects_more_than_three_colours():
    style = {**STYLE, "palette": {**STYLE["palette"], "extra": "#FFFFFF"}}
    assert not A.check_palette("", style)["ok"]


def test_palette_extra_allowed():
    style = {**STYLE, "extra_allowed": ["#000000"]}
    assert A.check_palette("<style>.s{box-shadow:0 0 4px rgba(0,0,0,.2)}</style>", style)["ok"]


# type ──────────────────────────────────────────────────────────────────────────────────────
def test_type_ignores_generic_fallbacks():
    assert A.check_type('<style>h1{font-family:"Inter", system-ui, sans-serif}</style>', STYLE)["ok"]


def test_type_flags_second_family():
    r = A.check_type("<style>h1{font-family:Inter} p{font-family:'Comic Sans MS'}</style>", STYLE)
    assert not r["ok"] and r["problems"]


# sfx ───────────────────────────────────────────────────────────────────────────────────────
def test_sfx_within_budget():
    assert A.check_sfx(cues(), STYLE)["ok"]


def test_sfx_window_overflow():
    fx = [{"type": "tick", "at": t} for t in (1, 2, 3, 4)]
    r = A.check_sfx(cues(fx=fx), STYLE)
    assert not r["ok"] and r["worst_10s"] == 4


def test_sfx_too_many_types_and_banned():
    fx = [{"type": t, "at": i * 5.0} for i, t in enumerate(["tick", "whoosh", "ping", "snare_roll"])]
    r = A.check_sfx(cues(fx=fx, duration=30), STYLE)
    assert not r["ok"]
    assert any("types" in p for p in r["problems"]) and any("banned" in p for p in r["problems"])


def test_sfx_ignores_samples():
    fx = [{"type": "sample", "at": t, "file": "x.wav"} for t in range(8)]
    assert A.check_sfx(cues(fx=fx), STYLE)["ok"]


# camera / tempo ────────────────────────────────────────────────────────────────────────────
def test_camera_budget():
    cam = {"punches": [{"t": "name"}, {"t": "detail"}], "shakes": [{"t": "name"}]}
    r = A.check_camera(cues(camera=cam), STYLE)
    assert not r["ok"] and len(r["problems"]) == 2


def test_tempo_band():
    assert A.check_tempo(cues(bpm=100), STYLE)["ok"]
    assert not A.check_tempo(cues(bpm=128), STYLE)["ok"]
    assert not A.check_tempo(cues(), {})["ok"]


# shots ─────────────────────────────────────────────────────────────────────────────────────
def test_shots_pass_and_durations():
    r = A.check_shots(cues(), STYLE)
    assert r["ok"], r["problems"]
    assert [s["dur"] for s in r["shots"]] == [2.4, 6.0, 3.6]


def test_shots_too_short_to_breathe():
    c = cues(marks={"reveal": 0.0, "detail": 0.6, "name": 8.4})
    assert any("breathe" in p for p in A.check_shots(c, STYLE)["problems"])


def test_shots_two_ideas_and_missing_idea():
    c = cues()
    c["shots"][1]["idea"] = "the button glows and the price appears"
    c["shots"][2]["idea"] = ""
    probs = A.check_shots(c, STYLE)["problems"]
    assert any("two ideas" in p for p in probs) and any("no idea" in p for p in probs)


def test_shots_cut_budget():
    c = cues()
    for s in c["shots"][1:]:
        s["in"] = "cut"
    assert any("hard cuts" in p for p in A.check_shots(c, STYLE)["problems"])


def test_shots_metronome_rhythm():
    c = cues(duration=12.0, marks={"reveal": 0.0, "detail": 4.0, "name": 8.0})
    assert any("metronome" in p for p in A.check_shots(c, STYLE)["problems"])


def test_shots_missing_is_a_failure():
    assert not A.check_shots(cues(shots=[]), STYLE)["ok"]


def test_hold_defaults_and_override():
    c = cues()
    c["shots"][0]["hold"] = 1.0
    holds = [s["hold"] for s in A.shot_table(c)]
    assert holds == [1.0, round(2.4 + 0.7 * 6.0, 3), round(8.4 + 0.7 * 3.6, 3)]


# keynote-ui register: cuts flip the field, motion blur is required ───────────────────────
KEYNOTE = {**STYLE, "shots": {"max_cuts": 6, "cut_flips_field": True}, "motion": {"blur_required": True}}


def keynote_cues(fields):
    marks = {f"s{i}": i * 2.5 for i in range(len(fields))}
    shots = [{"id": f"s{i}", "at": f"s{i}", "in": "open" if i == 0 else "cut", "field": f,
              "idea": f"idea {i}"} for i, f in enumerate(fields)]
    return cues(marks=marks, shots=shots, duration=2.5 * len(fields) + 1.0)


def test_fields_pass_when_every_cut_flips_the_field():
    assert A.check_fields(keynote_cues(["light", "dark", "light", "dark"]), KEYNOTE)["ok"]


def test_fields_flag_a_cut_that_keeps_the_field():
    r = A.check_fields(keynote_cues(["light", "dark", "dark"]), KEYNOTE)
    assert not r["ok"] and "s2" in r["problems"][0]


def test_fields_flag_a_cut_with_no_declared_field():
    c = keynote_cues(["light", "dark"])
    del c["shots"][1]["field"]
    assert not A.check_fields(c, KEYNOTE)["ok"]


def test_fields_rule_is_off_in_the_film_register():
    assert A.check_fields(keynote_cues(["light", "light"]), STYLE)["ok"]


def test_motion_blur_required_in_keynote_register():
    assert not A.check_motion('<div id="a"></div>', KEYNOTE)["ok"]
    assert A.check_motion("<span data-hf-motion-blur='{\"shutterAngle\":360}'>x</span>", KEYNOTE)["ok"]
    assert A.check_motion("<div></div>", STYLE)["ok"]


def test_keynote_template_passes_its_own_audit(tmp_path):
    (tmp_path / "style.json").write_text((TEMPLATES / "style.keynote-ui.json").read_text())
    (tmp_path / "cues.json").write_text((TEMPLATES / "cues.keynote-ui.json").read_text())
    (tmp_path / "index.html").write_text("<span data-hf-motion-blur>x</span>")
    report = A.audit(tmp_path)
    failing = {k: c["problems"] for k, c in report["checks"].items() if not c["ok"]}
    assert report["ok"], failing


# track_spring: the fit that produced MS.SPRINGS.ui ────────────────────────────────────────
import track_spring as TS  # noqa: E402


def test_fit_spring_reproduces_the_measured_ui_spring():
    zeta, omega = TS.fit_spring(0.054, 0.25)       # ~5 % overshoot, 0.25 s peak→trough (the "19:25" pill)
    assert abs(zeta - 0.68) < 0.02 and abs(omega - 17) < 1.5


def test_fit_spring_round_trips_and_rejects_nonsense():
    z, w = 0.5, 20.0
    os_ = math.exp(-z * math.pi / math.sqrt(1 - z * z))
    half = math.pi / (w * math.sqrt(1 - z * z))
    fz, fw = TS.fit_spring(os_, half)
    assert abs(fz - z) < 1e-9 and abs(fw - w) < 1e-9
    import pytest
    with pytest.raises(ValueError):
        TS.fit_spring(0.0, 0.2)


# the shipped templates must pass their own audit and build a valid score ─────────────────
TEMPLATES = Path(__file__).resolve().parents[1] / "templates"


def test_templates_pass_their_own_audit(tmp_path):
    (tmp_path / "style.json").write_text((TEMPLATES / "style.json").read_text())
    (tmp_path / "cues.json").write_text((TEMPLATES / "cues.apple.json").read_text())
    report = A.audit(tmp_path)
    failing = {k: c["problems"] for k, c in report["checks"].items() if not c["ok"]}
    assert report["ok"], failing


import pytest  # noqa: E402


@pytest.mark.parametrize("template", ["cues.apple.json", "cues.keynote-ui.json"])
def test_template_cues_build_with_score_py(tmp_path, template):
    import importlib.util
    import subprocess
    for mod in ("numpy", "scipy", "soundfile", "pyloudnorm"):
        if importlib.util.find_spec(mod) is None:
            import pytest
            pytest.skip(f"{mod} not installed")
    score = Path.home() / ".claude/skills/motion-studio/scripts/score.py"
    cues_path = tmp_path / "cues.json"
    cues_path.write_text((TEMPLATES / template).read_text())
    out = tmp_path / "mix.wav"
    r = subprocess.run([sys.executable, str(score), str(cues_path), "-o", str(out)],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr[-800:]
    assert out.exists() and out.stat().st_size > 100_000


# end to end ────────────────────────────────────────────────────────────────────────────────
def test_main_end_to_end(tmp_path, capsys):
    (tmp_path / "style.json").write_text(json.dumps(STYLE))
    (tmp_path / "cues.json").write_text(json.dumps(cues()))
    (tmp_path / "index.html").write_text('<style>body{background:#0B0B0C;font-family:Inter}</style>')
    assert A.main([str(tmp_path)]) == 0
    assert "PASSED" in capsys.readouterr().out
    assert A.main([str(tmp_path), "--holds"]) == 0
    assert capsys.readouterr().out.strip().count(",") == 2
    (tmp_path / "index.html").write_text('<style>body{background:#123456}</style>')
    assert A.main([str(tmp_path)]) == 1
