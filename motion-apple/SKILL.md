---
name: motion-apple
description: >
  Direct and produce PREMIUM, Apple-style motion videos on the HyperFrames engine, in two measured
  registers. FILM — calm, expensive launch films and product reveals: a locked brand system, a
  storyboard of stills approved before any animation, one idea per shot, critically damped springs,
  continuity transitions, deliberate stillness, sound by subtraction. KEYNOTE-UI — the Apple keynote
  UI explainer distilled frame by frame from real references: words rising word by word, iOS-style
  widgets that land on a measured spring (ζ 0.68, ω 17, ~5 % overshoot) with shutter motion blur,
  page-turn cuts that flip the field light↔dark, and morph chains (one box: dot → pill → card → icon).
  Both enforced in code by apple_audit.py. Use when the user wants a video that looks "expensive",
  "premium", "like Apple", "smooth", "clean", "elegant", shows an Apple-style reference to copy, or says
  "/motion-apple". For loud, every-beat social energy use /motion-studio instead. Triggers:
  "/motion-apple", "Apple-style video", "premium product video", "make it look expensive",
  "video estilo Apple", "video premium", "motion graphics como Apple", "keynote style", "morph".
---

# motion-apple — the premium director

**Same engine, opposite taste.** /motion-studio makes a feed video loud. This skill makes it
*expensive*. It reuses every /motion-studio script (scaffold, engine, score, snapbeats, review,
deliver) and replaces the director layer: doctrine, gates and critique questions. **Never copy a
/motion-studio script here. Improve it there.**

## Two registers — pick one first

| | **film** | **keynote-ui** |
|---|---|---|
| What it is | a calm launch film, the product alone | a narrated explainer: words + app widgets, one page per phrase |
| Cuts | continuity; one hard cut, on the reveal | every phrase is a **page turn that flips the field** (light ↔ dark), avg ≈ 2.3 s |
| Springs | ζ = 1, no overshoot | objects land on **`MS.SPRINGS.ui`** (ζ 0.68, ω 17, ≈ 5 % overshoot, settled 0.62 s); words on `settle` |
| Smoothness from | stillness + slow moves | **shutter blur** (720° at 60 fps) + springs + long settles — the reference is only 30 fps |
| Set pieces | push-through, match move, reveal | selection → card, **morph chain** (`MS.morph`), icon → lockup |
| Sound | pad + sparse pluck, ≤ 3 SFX / 10 s | UI sounds: `blip`, `ratchet`, `shimmer` (+ soft `whoosh`), ≤ 7 / 10 s, 4 types |
| Lock + cues | `templates/style.json` + `cues.apple.json` | `templates/style.keynote-ui.json` + `cues.keynote-ui.json` |
| Read | `references/doctrine.md` | `references/preset-keynote-ui.md` (every number, measured) |
| Worked example | — | **Servi AI, approved by Freddy 2026-10-08** — `loopmind/clients/servi-ai/marketing/motion/keynote-20s/` (README has every version and why) |

## Where everything is

| Piece | Where |
|---|---|
| Doctrine (film) with evidence tiers | `references/doctrine.md` · **read before designing** |
| keynote-ui preset: moves, springs, sound, morph chain, recipe, gaps | `references/preset-keynote-ui.md` · **read before a keynote-ui piece** |
| Premium critique questions + gates | `references/critique.md` · **read before the storyboard** |
| Restraint linter: palette, type, SFX, camera, tempo, shots, **fields**, **motion blur** | `scripts/apple_audit.py <dir> [--holds \| --json]` |
| Measure an object in a reference + fit its spring | `scripts/track_spring.py VIDEO T0 T1` · `--fit OVERSHOOT HALF_PERIOD` |
| Engine: `MS.springEase`, `MS.springDur`, `MS.SPRINGS`, **`MS.morph`**, camera, drive | `MS/templates/engine.js` (copied to `lib/` by scaffold; re-copy after an engine change) |
| Score + SFX (`blip` `ratchet` `shimmer` …), snapshots, review, delivery | `MS/scripts/` · cue schema `MS/references/cue-sheet.md` |
| **Traps that already cost a round** (shared by both skills; 29–34 came from keynote-ui) | `MS/references/gotchas.md` · **read before writing composition code** |

`MS` = `~/.claude/skills/motion-studio`, `MA` = `~/.claude/skills/motion-apple`.
Python runs with uv: `uv run --with numpy --with scipy --with soundfile --with pyloudnorm --with pillow <script>`
(apple_audit.py needs nothing: `uv run MA/scripts/apple_audit.py`).
Tests: `uv run --with pytest --with numpy --with scipy --with soundfile --with pyloudnorm pytest MA/tests -q` (32) ·
`node --test MS/tests/engine.test.mjs` (13) · MS python tests (26).
⚠ Run a command that names a `skills/…` path and later another `…claude…` path as TWO commands — the global
deny rule `*kill*claude*` matches "skills…claude" and blocks it.

## Procedure

```yaml
steps:
  - id: 0_distill   # only when Freddy hands over a reference video ("mira este video, cópialo")
    do:
      - "/watch:watch the file for the transcript; then 6 fps contact sheets per 10 s (ffmpeg fps=6,tile=6x10) — scene-cut sampling misses smooth motion."
      - "zsh personal-branding/shared/systems/edit-distill/run.sh <file> <name>  (zsh, not bash) → stems, voice vs bed dB, onsets, BPM, cuts."
      - "Per key move: 12 consecutive frames (ffmpeg tile, no select) to SEE blur, tilt, layering; track_spring.py T0 T1 to MEASURE it; --fit for ζ/ω."
      - "Spectrogram around each cut (showspectrumpic) to name the SFX; an SFX counts only if it lines up with a visual event."
      - "Write what's new into references/preset-*.md with M/S tiers; new primitives go in MS (engine/score) with tests."
    rule: "Copy the grammar, never their graphics, music or footage."

  - id: 1_brief
    do:
      - Identify the subject + workspace (client → loopmind/clients/<slug>/marketing/motion/<name>/).
      - Read the brand system verbatim. Hunt REAL material (product UI, real chats, logo, approved copy).
      - "Verify every feature claim against the product's state file, not the landing (MS doctrine §9)."
      - "Ask only what you can't find: length/aspect (default 15–20 s, 9:16 1080×1920, 60 fps), CTA."
    gate: no invented claims, numbers or UI states

  - id: 2_brand_lock
    do:
      - "Pick the REGISTER (table above). Copy its style template → <dir>/style.json and fill it from the brand: 3 colours, 1 family (never SF Pro), 2 weights, field rule, BPM band from the FEEL, SFX budget."
      - "If the brand already has a premium video, REUSE its style.json."
    output: "the lock in 5 lines in chat. Freddy can veto a colour or the feel here."

  - id: 3_shot_list
    do:
      - "Write the ONE-sentence idea of the film."
      - "Copy the register's cues template → <dir>/cues.json. `shots`: at (a mark), in (open|match|morph|push|mask|dissolve|cut), idea (ONE idea, no 'and'); keynote-ui shots also declare `field`."
      - "Adaptive rhythm: quick middle, the closing page longest (the audit rejects a metronome, cv < 0.12–0.15)."
      - "Show the shot table (time · page · idea · transition · sound) before building."
    gate: "apple_audit.py <dir> → shots + fields + tempo + camera + sfx PASS"

  - id: 4_scaffold
    run: "bash MS/scripts/scaffold.sh <dir> --fonts \"<fontsource id>\"   # then put style.json + cues.json back"

  - id: 5_storyboard
    reads: [MA/references/doctrine.md or preset-keynote-ui.md, MA/references/critique.md, MS/references/gotchas.md]
    do:
      - "Build every shot as a STILL at its hold pose. bash MS/scripts/snapbeats.sh <dir> board 0 --only \"$(uv run MA/scripts/apple_audit.py <dir> --holds)\""
      - "Critique Pass 1: one idea, centred, ≥ half empty, one accent, same film, poster test. Accent never as text on a light field unless it passes 3:1 — use a highlighter bar or ink on an accent fill."
    gate: "no CRITICAL/HIGH gap. On a brand's first premium piece, Freddy OKs the storyboard."

  - id: 6_score
    run: "uv run … MS/scripts/score.py cues.json -o assets/audio/mix.wav --emit-js cues.js"
    gate: "LUFS −14 ±0.5 · true peak ≤ −1 · no hook warning · apple_audit sfx PASS"
    then: "Subtraction pass: each SFX names the understanding it serves or goes."

  - id: 7_animate
    do:
      - "Animate BETWEEN the approved stills. Never linear except a hold drift. Overlap sequences 30–50 %."
      - "film: MS.springEase(1), continuity transitions, the one cut on the reveal, camera ≤ 1 tiny punch."
      - "keynote-ui: objects `ease: MS.springEase(UI.zeta), duration: MS.springDur(UI.zeta, UI.omega)`; exits power3.in 0.25 s; content reveals AFTER the container lands; a box that changes size is ONE MS.morph on an SVG rect (never two tweens on one property — gotcha 33)."
      - "Shutter blur (`data-hf-motion-blur` 720°/16) ONLY on things whose subtree never changes; a widget that changes inside flies as a static flyer (gotcha 32)."
      - "Frame 0 is a poster: its state in CSS, the first element already mid-spring (gotcha 34)."
    gate: "npx hyperframes lint . && npx hyperframes check . → 0 errors · apple_audit.py <dir> → PASSED"

  - id: 8_critique_loop
    do: "snapbeats.sh <dir> vN at entries, mid-moves and holds → critique Pass 2 + 3 → gap list → fix"
    until: "no CRITICAL/HIGH, max 3 rounds"

  - id: 9_render_measure
    run:
      - "PRODUCER_BROWSER_GPU_MODE=hardware npx hyperframes render . --fps 60 --quality delivery -o renders/<name>-vN.mp4"
      - "uv run … MS/scripts/review.py renders/<name>-vN.mp4 --cues cues.json --dead 2.5 -o review/vN"
      - "REAL-FRAME CHECK: 12 consecutive frames from the render at every flight, cut and morph (ffmpeg -ss T -vf tile). Snapshots don't run the shutter — ghosts, stale smears and late exits only show here (they did, three times, on Servi)."
    gate: "no dead window > 2.5 s · real frames clean at every transition · frame 0 is not blank. Beat hits are NOT a gate."

  - id: 10_deliver
    run: "bash MS/scripts/deliver.sh renders/<name>-vN.mp4 renders/<name>-social.mp4"
    then:
      - "Open it so Freddy SEES it: close stale QuickTime docs, `open -a 'QuickTime Player' <file>`, activate + play, `open -R <file>`."
      - "README in the project: what each page is, where each fact comes from, every version and why."
    report: [path · duration · LUFS, the brand lock used, what was verified by eye vs numbers, the SFX list for Freddy's ears, every assumption]
    learn: "A trap that cost a round → MS/references/gotchas.md (one shared list). A new move → the preset."
```

## Non-negotiables

1. **The register and the brand lock are decided first and never broken.** `apple_audit.py` must PASS.
2. **Design before motion.** No tween before the storyboard of stills passes.
3. **One shot = one idea**, key object centred, at least half the frame empty, one accent per shot.
4. **Measured motion, never eyeballed.** film: ζ = 1, continuity, one cut. keynote-ui: `MS.SPRINGS.ui` for
   objects, page-turn cuts that flip the field, one box per morph chain.
5. **Smoothness = shutter + springs + long settles**, not frame rate. Blur only static subtrees.
6. **Stillness is designed, never accidental.** Rhythm changes by act; frame 0 is never empty.
7. **Sound by subtraction.** Within the register's budget; no rescue-by-effect.
8. **Verify on real rendered frames before delivering.** The snapshot is a storyboard, not the film.
9. Everything else from /motion-studio still holds: real material, a pure function of time, one cue
   sheet for picture and sound, v1 → critique → v2.
