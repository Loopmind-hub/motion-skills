---
name: motion-studio
description: >
  Direct and produce studio-grade motion graphics videos — launch videos, product reels, showreels,
  kinetic-type spots, UI-motion loops — that look like a senior motion designer / FX artist made
  them. A director layer on top of HeyGen's HyperFrames (HTML → deterministic MP4): one-idea concept
  from the client's REAL material, a beat-grid cue sheet that times picture AND sound, spring-based
  seekable motion with a pure-function camera, a synthesized score + sound design mastered to −14
  LUFS, and a mandatory visual critique loop (per-beat contact sheets, dead-time and beat-hit
  metrics) that turns v1 into v2 before anything ships. ALWAYS invoke when the user wants a motion
  graphics / animated / launch / promo / showreel / kinetic-type video, or says the result must be
  "astonishing", "professional", "exciting", "like a real motion designer", "more energetic",
  "5x more exciting". Triggers: "/motion-studio", "motion graphics video", "launch video",
  "video de lanzamiento", "promo video", "showreel", "reel animado", "motion design",
  "animated video for", "make it more exciting", "haz un video motion graphics".
---

# motion-studio — the director layer

**HyperFrames is the engine; this skill is the director.** HyperFrames already knows how to render
HTML to video, with ~40 motion rules, 200+ registry blocks and a strict lint. What it doesn't
supply is *taste under a deadline*: one idea, a beat map, restraint, sound designed to picture,
and the discipline to watch v1 and fix it. That's this skill. **Do not copy HyperFrames' docs into
here — read them from the clone when a step needs them.**

| Piece | Where |
|---|---|
| Engine (pinned clone, source of truth for the HF contract) | `~/tools/hyperframes/` — skills in `skills/`, registry in `registry/` |
| CLI | `npx --yes hyperframes@<pinned> …` (project `package.json` pins it) |
| Craft rules, with the why | `references/doctrine.md` — **read before designing** |
| Critique loop + gap-list format | `references/critique.md` — **read before the first snapshot** |
| Cue sheet schema | `references/cue-sheet.md` |
| Traps that already cost a round | `references/gotchas.md` — **read before writing composition code** |
| One-command project setup (HF init, engine, motion blur, brand fonts, .gitignore, cues starter) | `scripts/scaffold.sh <dir> --fonts "outfit,space-grotesk"` |
| Shared runtime: springs, camera-as-data, shader field, grain, drive | `templates/engine.js` → copied to `lib/engine.js` (improve the template, never the copy) |
| Per-beat snapshots from cues.json in one command | `scripts/snapbeats.sh <dir> <label> [offset] [--only t1,t2]` |
| Score + SFX + mix engine (music, impacts, risers, whooshes, **ping / pop / typing** for UI & chat) | `scripts/score.py` |
| Render review (dead time, beat hits, per-beat sheet, loop seam) | `scripts/review.py` |
| Real-song beat grid | `scripts/beatgrid.py` |
| Social encode + loudness proof | `scripts/deliver.sh` |
| Worked examples | Reely 15 s — dark, real footage, voice chops: `loopmind/clients/reely/marketing/motion/launch-15s/` · Servi AI 20 s — light brand, real chat rebuilt, logo-as-story loop, **built on engine.js**: `loopmind/clients/servi-ai/marketing/motion/launch-20s/` |

Tests: `uv run --with pytest --with numpy --with scipy --with soundfile --with pyloudnorm --with pillow pytest tests -q` and `node --test tests/engine.test.mjs`.

Python scripts run with **uv**, never bare `python3` (no numpy there):
`uv run --with numpy --with scipy --with soundfile --with pyloudnorm --with pillow <script>`

## Procedure

```yaml
steps:
  - id: 0_setup
    do:
      - "If ~/tools/hyperframes is missing: gh repo clone heygen-com/hyperframes ~/tools/hyperframes -- --depth 1"
      - "npx --yes hyperframes@latest doctor   # Chrome + FFmpeg must pass"
    never: "npx hyperframes skills update / npx skills add — they dump 20+ skills into ~/.claude/skills (gotcha 12)"

  - id: 1_brief
    do:
      - Identify the subject and the workspace (a client → loopmind/clients/<slug>/marketing/motion/<name>/).
      - Read the client's brand system (tokens, type, voice, positioning) — verbatim, not from memory.
      - "Hunt REAL material first: footage (raw takes!), screenshots, UI designs, voice, logo, real conversations, approved landing copy. List it."
      - "Feature claims: verify each one against the product's state/account file, NOT the landing — marketing runs ahead of production (doctrine §9)."
      - Ask ONLY what you cannot find: length/aspect (default 15 s, 9:16 1080×1920, 60 fps), CTA, music preference.
    gate: "no invented numbers, claims, or UI states — honesty rules in doctrine §9"

  - id: 2_concept
    do:
      - Write the ONE-sentence idea. Apply the 10-year-old test (doctrine §1).
      - "Pick the hero object that never cuts, and the frame-0 motif the video loops back to."
    output: "3–5 lines in chat. For a first-time client or a big-budget piece, get Freddy's OK here."

  - id: 3_beat_sheet
    do:
      - Choose BPM (120 default). Write cues.json — marks for every story beat, on the grid.
      - "Acts for 15 s: hook ≤1 s · problem · turn (accelerate + ¼-beat silence) · DROP payoff · product · name · loop."
      - Show Freddy the beat sheet as a table (time · beat · picture · sound) before building.
    reads: references/cue-sheet.md, references/doctrine.md §2

  - id: 4_scaffold
    run: "bash ~/.claude/skills/motion-studio/scripts/scaffold.sh <dir> --fonts \"<brand fonts, fontsource ids>\""
    then:
      - "Prep media: transcode footage to H.264 at the target size (ffmpeg, -an, -g 15); extract voice wav; measure speech onsets by RMS (gotcha 3)."
      - "Local fonts in assets/fonts with licence; derive data (waveforms etc.) from the real media into a generated .js."

  - id: 5_score
    run: "score.py cues.json -o assets/audio/mix.wav --emit-js cues.js"
    gate: "LUFS −14 ±0.5 · true peak ≤ −1 · no hook warning in bar_lufs"
    verify: "ffmpeg showwavespic+showspectrumpic → look at it. You cannot hear; say so in the handoff."

  - id: 6_compose
    reads: [references/gotchas.md, "~/tools/hyperframes/skills/hyperframes-core/SKILL.md", "~/tools/hyperframes/skills/hyperframes-animation/rules-index.md (pick rules as needed)"]
    do:
      - "One paused GSAP timeline on window.__timelines, built inside document.fonts.ready."
      - "Load lib/engine.js. Camera = MS.camera(CUES.camera, CUES.marks) — moves/punches/shakes/pulse are DATA in cues.json, by mark name."
      - "MS.drive(tl, D, frame) runs frame(t) every seek: cam transform, MS.shaderBg draw, MS.grain draw, any per-frame bounce."
      - "Every mark comes from window.CUES. Springs via MS.springEase(ζ); ζ≈0.74 max overshoot, 0.86 for UI surfaces."
      - "Registry before hand-building a named effect: npx hyperframes add <name>, read the file."
    gate: "npx hyperframes lint . && npx hyperframes check .  → 0 errors"

  - id: 7_critique_loop
    reads: references/critique.md
    do:
      - "bash scripts/snapbeats.sh <dir> vN  → read EVERY sheet, write the v1→v2 gap list, fix."
      - "Re-check only what changed: snapbeats.sh <dir> vNspot 0 --only \"t1,t2,…\" (seconds, not a full pass)."
    until: "no CRITICAL/HIGH gaps, max 3 rounds"
    rule: "v1 is never shipped. At least one full critique round, always."

  - id: 8_render
    run: "PRODUCER_BROWSER_GPU_MODE=hardware npx hyperframes render . --fps 60 --quality delivery -o renders/<name>-vN.mp4"
    note: "Run in background; ~minutes. Snapshot iteration is the cheap loop; renders are the expensive one."

  - id: 9_measure
    run: "review.py renders/<name>-vN.mp4 --cues cues.json -o review/vN"
    gate: "beats_hit ≥ 80% by content · no dead window ≥ 0.6 s except one named end-card hold ≤ 1.5 s · loop < 3 · camera budget OK — name every miss as a rest or a weak event"
    then: "Read energy.png + beats.jpg. A failed gate → back to step 7."

  - id: 10_deliver
    run: "deliver.sh renders/<name>-vN.mp4 renders/<name>-social.mp4"
    report:
      - the file path + duration + LUFS
      - "what was verified by eye vs by numbers; what still needs Freddy's ears (sound)"
      - "every assumption (reordered clips, placeholder wordmark, 'coming soon' copy)"
      - "open with /watch or `open` so Freddy sees it"
    then: "Anything learned that cost a round → add a row to references/gotchas.md (coldest layer that works)."
```

## Non-negotiables

1. **Real material over invented** — footage, UI, voice, numbers.
2. **Every value is a pure function of time.** No CSS transitions, timers, `Math.random`, `Date.now`.
3. **Picture and sound share one cue sheet.**
4. **v1 → critique → v2**, by looking at every beat, before any full render.
5. **Beats are carried by content, emphasis is spaced; nothing holds dead for > 0.6 s** (one named
   end-card hold ≤ 1.5 s is allowed). **The camera is punctuation: 3–4 punches per piece, no
   per-beat pulse** — it reads as a heartbeat (Freddy, 2026-09-25).
6. **The last frame is the first frame.**
