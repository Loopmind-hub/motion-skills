# Preset `keynote-ui` — the Apple keynote UI explainer, measured

**Source.** TikTok @beingmayy, "Apple Style Motion Graphics" tutorial intro (1024×576, **30 fps**, 50.5 s), at
`~/Movies/videos-iPhone/6-pantallas/v1c044g50000d99uqa7og65h40itt5qg.mp4`. Measured 2026-10-08 with
`/edit-distill` (`personal-branding/shared/research/edit-distill/apple-kinetic/`) plus a per-frame
element tracker and dense 30 fps strips. **We copy the grammar, never their graphics, music or footage.**
Every value is **M** (measured from a file) or **S** (seen on frame strips). Unknown stays unknown.

## When to use it

`film` (doctrine §1–9) is the calm launch film: continuity, one cut, ζ = 1. **`keynote-ui` is the narrated
explainer**: words and iOS-style widgets carry an idea per phrase, the page turns on every phrase. Pick it for
"explain the product in 20 s", tutorials and feature walk-throughs. Lock it with
`templates/style.keynote-ui.json` + `templates/cues.keynote-ui.json`. `apple_audit.py` enforces the two rules
that make it this style and not a busy one, **cuts flip the field** and **fast movers carry shutter blur**.

## 1 · The smoothness is shutter + springs, not frame rate

The reference is **30 fps** (M) and still reads as "almost 60". Three causes, all measured:

| Cause | Number | Tier |
|---|---|---|
| **Shutter motion blur** on every fast move. Edge sharpness (p95 gradient) drops 60 → 16 while a pill flies in and recovers as it lands | p95 grad 16 → 68 over 0.5 s | M |
| **Long tails.** Almost all movement happens in the first ~0.3 s, then a slow settle, then near-stillness. The frame-difference curve is spikes over a flat floor, and a few drifts decay exponentially (29–32 s) | motion energy ≈ 0 between events | M |
| **Holds that drift.** A held page keeps scaling or sliding very slowly (the profile mock-up grows; the "Apple" logo creeps 2.5 px in 0.5 s at 512 px) | ≈ 1 %/s | M |

**For us.** Render at **60 fps** anyway (it doubles the smoothness we get for free) **and** put
`data-hf-motion-blur='{"shutterAngle":720,"samplesPerFrame":16}'` on every element that moves fast
(720° at 60 fps = the reference's 33 ms exposure at 30 fps, gotcha 31). A
CSS `filter: blur()` on a moving element is NOT motion blur. It is isotropic and doesn't follow the path.

## 2 · Springs — two of them

| Spring | Use | Params | Measured on |
|---|---|---|---|
| `MS.SPRINGS.ui` | objects landing: cards, pills, icons, widgets | **ζ 0.68, ω 17** → peak at ~0.25 s, **overshoot ≈ 5 %**, settled by **0.62 s** | the "19:25" pill: position overshoot 4.3 %, scale overshoot 8.5 %, half-period 0.25 s; the heart icon: area overshoot ≈ 20 % (≈ 10 % linear) | M |
| `MS.SPRINGS.settle` | words, lines, camera drift | ζ 1, ω 14 (no overshoot) | words settle without a visible bounce | S |

```js
var UI = MS.SPRINGS.ui, UI_EASE = MS.springEase(UI.zeta), UI_DUR = MS.springDur(UI.zeta, UI.omega); // 0.62 s
tl.fromTo(pill, { y: 360, scale: 0.35, rotation: -12, opacity: 0 },
               { y: 0, scale: 1, rotation: 0, opacity: 1, ease: UI_EASE, duration: UI_DUR, immediateRender: false }, t);
```

The film register's "ζ = 1, no overshoot" still holds for **type** here. The overshoot is reserved for things
with mass.

## 3 · The moves, one by one

| Move | What happens | Numbers | Tier |
|---|---|---|---|
| **Word rise** | Each word enters from ~1.4× its cap height below, vertically smeared, and lands on `settle`. Words are staggered and **overlap**: the next one starts before the last lands, so mid-flight they sit on different baselines | stagger **≈ 0.07–0.1 s** per word; each word ≈ 0.3 s to land; driven by the VO onset (word appears 0–80 ms after it's spoken) | M (words.json vs captions) + S |
| **Line drift** | After the line lands it keeps shrinking slowly (≈ 6 % over 1.5 s), a hold with life | ≈ 4 %/s | S |
| **UI land** | A card/pill flies in from below, starts at ~0.3× scale and **tilted ±10–12°**, rotating to 0 while it lands, with heavy blur, on `ui` | 0.32 s to target, 37 % of frame height travelled | M |
| **Layered reveal** | Container lands first, then its content (the ring, the number), then the secondary label fades in last | content +0.15 s, label +0.35 s | S |
| **Pill morph** | The pill **changes width** to fit the next word ("Under 20 minutes" → "Well") and its fill colour changes to the accent on the answer ("Yes" turns green). Same object, new state, no cut | width on `ui`; fill 0.2 s | S |
| **Exit** | Objects leave **accelerating** (ease-in) downward or scaling down, smeared more each frame | 0.25–0.35 s, `power3.in` | S |
| **Selection highlight** | A text-selection box (accent fill at ~40 % + two round handles) grows word by word behind the text, then the whole box **detaches**, squashes, tilts, glows and flies into the next shot as a card, the background crossfading dark → light under it (≈ 6 frames) | the morph-transition, 0.4 s | S |
| **Icon → widget** | A dot grows into an app-icon tile (`ui`, overshoot), holds, then the tile **expands** into a wide widget (title, value, progress bar that fills), and later collapses back into the icon, which gets a soft glow pulse | expand 0.35 s, bar fill 0.6 s | S |
| **Logo → lockup** | The logo holds big, then shrinks and slides left as the wordmark reveals to its right (letters fade in left → right with a short blur) | 0.3 s with blur | S |
| **Letter type** | On a dark navy field, letters appear one by one, each fading in from blur, the colour shifting from a cool tint to the accent as it settles, with a soft glow | ≈ 1 letter / 2 frames | S |
| **Word replace** | One word fills the frame; the next replaces it in place with no move (a "beat" of the VO) | cut on the word | S |

## 4 · Cuts are page turns

- **14 scene changes in 50 s, average shot 2.29 s, 34.5 visual changes/min** (M). This is NOT the
  film register's "one cut".
- **Every scene cut flips the field.** Light grey #E9E9E9 ↔ near-black #141414 ↔ navy #10121F (S). That flip
  is why the cuts read as page turns and not as jumps. `apple_audit` enforces it (`cut_flips_field`).
- The cut lands **on a VO phrase**, and the new page's object starts moving on the first frame (no empty frame).

## 5 · Sound (Demucs split of voice vs bed)

| | Value | Tier |
|---|---|---|
| Integrated loudness | −20.6 LUFS (a tutorial; deliver ours at −14) | M |
| Voice vs bed | −24.9 vs −25.2 dB. **The bed is as loud as the voice and never ducks** (−24.5 in pauses) | M |
| Music | calm electronic: strong sub (20–160 Hz), a sustained pad note, plucked **arpeggios** 0.7–2 kHz; ≈ 83 BPM, weakly on grid | M (spec-bed.png, beat grid) |
| SFX on events | 77 of 230 bed onsets fall on a visual event | M |
| The turn chime | at two big turns (10.1 s, 33.6 s): a **tick train** then **descending pitched blips** | S on spectrogram → `ratchet` + `blip notes:[12,7,3,0]` |
| The morph | dense granular sparkle during the selection → card morph | S → `shimmer` |
| Landings | small clicks/pops (centroid 2.5–5.4 kHz) as objects land | M → `blip` / `pop` |

No impacts, no risers of note, no whoosh on every cut. **UI sounds, not cinema.**

## 6 · The recipe for a 20 s piece (9:16)

1. 6–8 pages, each ONE idea, each its own field (alternate light/dark; a morph may keep or crossfade the field).
2. Per page: a word line (rise), or a widget (land → layered reveal → morph state), never both fighting.
3. Exactly one **selection → card** morph and one icon set piece (**icon → widget** or **icon → lockup**).
4. **The accent never sets body text on a light page** unless it passes 3:1. On lienzo-type fields use a
   highlighter bar under the word, or ink text on an accent fill (Servi v1: celeste text was 2.49:1).
5. End on **logo → lockup**, then a tagline word rise, then a calm hold with drift.
6. **Shutter blur only on static subtrees** (gotcha 32): a widget that changes inside flies as a static
   flyer and the live one takes over on landing. **Frame 0 is a poster**, never a blank page (gotcha 34).
7. Label swaps inside a morphing pill: the old label leaves in 0.1 s, the new one enters 0.13 s after the
   morph starts. Overlapping them ghosts two texts (gotcha 5).
8. Score: pad + sub + pluck arpeggio at 84–92 BPM; SFX from `blip / ratchet / shimmer / whoosh` only.

## 8 · The morph chain — reference 2 (same creator, `…/6-pantallas/v1c044g50000d83kfvvog65h79b6qqg0.mp4`, 37 s, 30 fps)

The second reference's set piece: **one container** goes dot → `>` button → "iPhone 17 Pro" pill → product
card with a Pay button → "Track Order" pill → dot, twice, then ends as a black pill. Measured with the
element tracker at 512 px wide (M):

| Transition | Change | Time | Character |
|---|---|---|---|
| dot → button | 18 → 41 px | 0.2 s | the whole widget keeps drifting down ≈ 30 px/s |
| button → pill | **width only** 44 → 228 | ≈ 0.5 s, 60 % in the first 0.13 s | no overshoot on width |
| pill → card | **height only** 41 → 200 | 0.33 s | **≈ 7 % overshoot**, sharpness 92 → 20 (blur) |
| card → pill | both axes | 0.27 s | ≈ 4 px vertical bounce on landing |

Rules that come out of it:
- **One box, many states.** Never cross-dissolve two boxes. Drive it with `MS.morph(states)` (engine) on an
  SVG `<rect>` (attr width/height/rx). Each state is a retarget, so a change mid-flight keeps its velocity.
- **Open one axis at a time.** A pill opens its width, holds a beat, then opens its height (`lead: "w"`).
  Collapses go both axes at once, faster (≈ 0.27 s).
- **A shared element survives the morph.** The phone thumbnail is in every state (pill icon → card photo →
  Track-Order icon), only resizing. The viewer's eye rides it through the change. Pick one per chain.
- **Content swaps with a blur crossfade** inside the box, the old content leaving in ≈ 0.1 s.
- **The chain loops**: ending on the dot it started from makes the whole thing read as one object with moods.

Other moves seen in reference 2 (S):

| Move | What happens |
|---|---|
| **Conveyor line** | words keep being added at the right while the whole line slides left to keep the writing head near centre; the last word gets pushed out by the next object (the Apple logo) |
| **Logo → chip → widget** | the logo lands, a label pill grows to its right (logo + "Motion Graphics"), then the chip morphs into a dark timer widget with the logo kept in its corner (shared element) |
| **Picker wheel** | an iOS time picker column rolls (19 · 20 · 21 min) before settling |
| **Push-in on a widget** | a small Notes card scales toward the camera until it fills the frame while text types into it, then pulls back and blurs out |
| **Squash & stretch on a fast bubble** | an iMessage bubble enters so fast it's a stretched streak for 2 frames, then lands round; older bubbles shift up (the chat stacks) |
| **Cursor interaction** | a hand cursor glides in, clicks, the card's text changes on the click |
| **Tilt-out exit** | a card leaves by rotating in 3D and falling (perspective), not just dropping |

## 9 · Gaps we closed / still open (2026-10-08)

| Element | Engine today | Status |
|---|---|---|
| Measured UI spring | `MS.springDur` + `MS.SPRINGS` (motion-studio engine) | ✅ built, tested |
| Measuring a new reference's spring | `MA/scripts/track_spring.py VIDEO T0 T1` + `--fit OVERSHOOT HALF_PERIOD` | ✅ built, tested (reproduces ζ 0.68 / ω 17) |
| Shutter blur | HyperFrames `motion-blur` component (`lib/motion-blur.js`, scaffolded) | ✅ exists, now required by the audit |
| Turn chime, ratchet, shimmer | `score.py` `blip` / `ratchet` / `shimmer` | ✅ built, tested |
| Field-flip cuts | `apple_audit` `fields` check | ✅ built, tested |
| Morph chain (one box, many states, lead axis) | `MS.morph` (motion-studio engine) | ✅ built, tested; used in the Servi example v4 |
| Blur on a SIZE morph (the reference blurs while the card opens) | the shutter component reads transforms, not rect sizes | ⏳ open — size morphs render sharp |
| Conveyor line, picker wheel, cursor, 3D tilt-out, squash & stretch | composition patterns, no engine piece needed | ⏳ not yet used in an example |
| Word-onset sync to a real VO | `/edit-distill` words.json gives the onsets; no voice in our first example | ⏳ when a piece has VO, drive the word rise from the onsets (gotcha 3: RMS, not Whisper) |
| 3D objects on a grid (the reference's 23–28 s) | no 3D in the engine | ⏳ skip, or use a rendered still |
