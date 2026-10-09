# The critique loop — v1 is a draft, never the deliverable

Freddy's standing instruction (from his v2 prompt): *"examine your result visually… the rhythm,
the speed, everything… find the gap between what I described and what you currently have."*
This file is that pass, made mechanical so it happens every time.

## Order of operations (cheap → expensive)

```yaml
loop:
  - step: snapshot_every_beat
    run: npx hyperframes snapshot . --at "<beat+0.2 for every beat>,0,<end-0.02>" --no-end -o snapshots/vN --describe false
    why: ~40 s. Catches 80% of problems before any full render.
  - step: look
    do: Read EVERY contact sheet. Write the gap list BEFORE touching code (format below).
  - step: fix
    do: One edit batch per gap list. Re-run `npx hyperframes check .` (must be 0 errors).
  - step: repeat
    until: the gap list has no CRITICAL/HIGH items, or 3 rounds (then report what remains)
  - step: render
    run: npx hyperframes render . --fps 60 --quality delivery -o renders/<name>-vN.mp4
  - step: measure
    run: review.py renders/<name>-vN.mp4 --cues cues.json -o review/vN
    gate: beats_hit ≥ 80% by CONTENT · no dead window ≥ 0.6 s except ONE named end-card hold ≤ 1.5 s · loop_first_last_delta < 3 · camera budget OK
    misses: list every missed beat and name it — a deliberate rest (fine, rhythm needs rests) or a weak event (fix with content)
    never: add a camera punch to rescue a missed beat — that games the metric (Reely + Servi, 2026-09-25)
  - step: watch_the_motion
    do: Read review/vN/energy.png + beats.jpg. Energy dips that are not deliberate = slow spots.
```

## What to look for on every sheet

| # | Question | Typical fix |
|---|---|---|
| 1 | Does frame 0 already say something? Is the first second loud (audio) and moving (picture)? | Open on the slam, not a build-up; raise the hook bar LUFS |
| 2 | Could two consecutive beats be swapped without anyone noticing? | Vary direction, angle, scale, framing |
| 3 | Is every word readable at phone size against what's behind it? | Dim/scrim behind, bigger, own zone |
| 4 | Any text overlapping other text mid-transition? | Sequence exit before entry |
| 5 | Is anything washed out, muddy, or off-palette? | Look for a leaking overlay first (see gotchas) — then grade |
| 6 | Does the eye know where to look in each frame? | One focal point per beat; dim the rest |
| 7 | Any hold > 2 s with no internal motion? | Slow push, float, blink on the beat |
| 8 | Is the payoff (drop) the biggest visual AND audio moment? | Flash, punch, shake, full groove, impact — and nothing else in the piece gets all of those |
| 11 | Does the frame throb? (camera hits on consecutive beats, a pulse, a thumping quiet section) | Cut to the story turns only; carry the beat with content |
| 9 | Would a 10-year-old keep watching? Where would they get bored? | That's the next thing to fix |
| 10 | Does the last frame equal the first? | Fold everything back into the frame-0 motif |

## Gap list format (write it, don't just think it)

```
v1 → v2 gaps
1. CRITICAL  <what's wrong>  — <where, seconds>  — <fix>
2. HIGH      ...
3. MEDIUM    ...
```

Severity: **CRITICAL** broken/unwatchable · **HIGH** a viewer would notice · **MEDIUM** a
designer would notice · **LOW** polish. Ship with zero CRITICAL/HIGH.

## The "5x more exciting" lever list — when it's correct but boring

Reach for these in order; each is cheap in this stack:
1. Shorter holds, more events per bar (8ths instead of quarters)
2. Camera: a lean-in before the payoff and ONE punch on the drop — never punches on every hit (heartbeat)
3. Vary every repeated move
4. A gap of silence + stillness right before the drop
5. Real motion blur on the 1–3 snappiest moves
6. A bigger local event on a weak beat (a row flash, a word slam, a tap ripple) — NOT a camera punch
7. A shader/WebGL moment for the hero beat (registry: `vfx-*`, `domain-warp-dissolve`,
   `glass-shard-title`, `sdf-iris` — install with `npx hyperframes add <name>`, read its file first)
8. A playful cause→effect: a cursor/tap/read-head that *makes* things happen
