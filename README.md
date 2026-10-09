# motion-skills

Two Claude Code skills that direct motion-graphics videos on [HyperFrames](https://github.com/heygen-com/hyperframes)
(HTML → deterministic MP4), built by Freddy Ñañez / Loopmind.

| Skill | What it makes |
|---|---|
| **`motion-studio/`** | Loud, every-beat social videos: launch reels, kinetic type, product promos. Owns the shared engine (`templates/engine.js`: springs, `MS.morph`, camera-as-data, shader field, grain), the synthesized score + sound design (`scripts/score.py`), snapshots, the render review (dead time, beat hits) and delivery at −14 LUFS. |
| **`motion-apple/`** | Premium, Apple-style videos in two measured registers. **film**: the calm launch film. **keynote-ui**: the Apple keynote UI explainer, distilled frame by frame from real references: widgets landing on a measured spring (ζ 0.68, ω 17), shutter motion blur, page-turn cuts that flip the field, morph chains. `apple_audit.py` enforces the brand lock in code; `track_spring.py` measures a new reference's spring instead of guessing it. |

`motion-apple` reuses `motion-studio`'s engine and scripts. Keep them together.

## Install

```bash
git clone git@github.com:Loopmind-hub/motion-skills.git ~/projects/motion-skills
ln -s ~/projects/motion-skills/motion-studio ~/.claude/skills/motion-studio
ln -s ~/projects/motion-skills/motion-apple  ~/.claude/skills/motion-apple
gh repo clone heygen-com/hyperframes ~/tools/hyperframes -- --depth 1   # the engine's registry (motion blur)
```

Python runs with `uv`; HyperFrames runs with `npx` (Chrome + FFmpeg).

## Tests

```bash
node --test motion-studio/tests/engine.test.mjs
uv run --with pytest --with numpy --with scipy --with soundfile --with pyloudnorm --with pillow \
  pytest motion-studio/tests motion-apple/tests -q
```

## Start here

- `motion-apple/SKILL.md` — the two registers, the procedure, including step 0 (distill a reference video).
- `motion-apple/references/preset-keynote-ui.md` — every measured number, with its evidence tier.
- `motion-studio/references/gotchas.md` — 34 traps, each one paid for in a real build.

Worked example (approved 2026-10-08): the Servi AI keynote-ui film, `loopmind/clients/servi-ai/marketing/motion/keynote-20s/`.
