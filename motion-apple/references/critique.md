# Premium critique — what to look for on every sheet

The loop mechanics (snapshot → gap list → fix → repeat, severity scale, gap-list format) are
/motion-studio's: `~/.claude/skills/motion-studio/references/critique.md`. This file only replaces
**the questions**, because premium fails differently. A loud video fails by being boring. A premium
one fails by being **busy** or **cheap**.

## Pass 1 · Storyboard (stills, before any tween)

`snapbeats.sh <dir> board 0 --only "$(apple_audit.py <dir> --holds)"` → one frame per shot hold.

| # | Question | Typical fix |
|---|---|---|
| 1 | Can you say each shot's ONE idea from the still alone, sound off? | Cut whatever belongs to another idea. Split the shot |
| 2 | Is the key object on the centre axis, and is it the brightest or most contrasted thing? | Move it, dim the rest |
| 3 | Is at least half the frame empty? | Remove elements. Scale the object down before scaling it up |
| 4 | Is the accent colour used on exactly one thing? | Put everything else back to ink |
| 5 | Do all the stills look like the SAME film (type, field, light, margins)? | Go back to style.json. One of them broke the lock |
| 6 | Would this still work as a poster? | If not, redesign before animating. Motion won't save it |

**Show Freddy the storyboard sheet and get an OK before animating** on a first piece for a brand.

## Pass 2 · Motion (per-shot snapshots at entry, mid, hold)

| # | Question | Typical fix |
|---|---|---|
| 7 | Does anything overshoot or bounce without a physical reason? | ζ = 1 |
| 8 | Do sequences read as one gesture (overlapped) or as a queue? | Start the next element at 30–50% of the previous |
| 9 | Is every transition carried by something (shape, motion vector, the object itself)? | Match move / morph / push-through. A plain cut only on the turn |
| 10 | Does the rhythm change between acts? Is there stillness before the reveal? | Lengthen the open, shorten the middle, hold before and after the reveal |
| 11 | Is anything moving that doesn't need to? | Freeze it |
| 12 | Does a hold have a trace of life (≤ 2% push, a light drift), or is it a frozen frame? | Add the slow push. Never add a new element to fill a hold |

## Pass 3 · Sound (on the event list, then Freddy's ears)

| # | Question | Typical fix |
|---|---|---|
| 13 | For every SFX, which viewer understanding does it serve? | No answer → remove it |
| 14 | Is the reveal the only moment with an impact? | Remove the others |
| 15 | Does the music's arc match the rhythm arc (build → breath → reveal → calm)? | Move the layer marks |

## Gates (replace /motion-studio's)

- `apple_audit.py <dir>` → **PASSED** (palette, type, SFX, camera, tempo, shots)
- `review.py … --dead 2.5` → no dead window except the declared holds. **Beat hits are NOT a gate
  here.** Stillness on a beat is often correct. Read the number, don't chase it.
- LUFS −14 ±0.5, true peak ≤ −1 (deliver.sh proves it)
- Zero CRITICAL/HIGH gaps after at most 3 rounds

**Never** rescue a quiet stretch by adding an effect. In this style, adding is the failure.
