# Motion doctrine — what makes it look like a senior motion designer made it

Condensed from: Freddy's reference prompts (Dribbble-level UI motion, "5x more exciting" v2 critique,
the 15s showreel brief), two research passes (2026-09-25, sources at the bottom), and the Reely
launch build. Every rule has a **why**. Where evidence is weak it says so.

---

## 1 · The idea comes before the motion

**One idea, stated in one sentence, that a 10-year-old would get with the sound off.**
"The takes stutter until Reely picks the best one" is an idea. "A cool product video with
kinetic type" is not. If you cannot say it, you will decorate instead of direct.

- **Build the idea from the client's REAL material.** Their footage, their UI, their words. Reely's
  hook worked because the four takes were Freddy actually fumbling the same line. Stock
  footage and invented UI read as template on sight.
- **The product's mechanism IS the storyboard.** Show the thing doing its job, in order, as spectacle.
- **The 10-year-old test** (from Freddy's v2 prompt): would a kid with no idea what it's about
  watch to the end because it's fun? Fun = surprise every beat, cause→effect you can see,
  one moment that makes you go "oh!".

## 2 · Rhythm is the skeleton

- **Pick the BPM first; derive every time from the grid.** 120 BPM → 0.5 s/beat, 2 s/bar,
  30 frames/beat at 60 fps. Author times as marks in `cues.json`, never as loose numbers in code.
- **Something happens on every beat — carried by CONTENT.** A word, a card, a tap, a row lighting
  up, a caret blink. Never by throbbing the whole frame: a camera punch changes every pixel, so it
  *passes* the beat metric while making the video feel like a **heartbeat** (Freddy, 2026-09-25,
  on both Reely and Servi — "I feel a lot of heartbeats"). Target ≥ 90% of beats hit by content.
- **Space the emphasis.** Not every beat is equal: most beats get a small local event, a few get a
  medium one, and only the 2–4 story turns get the big hit (camera + impact). If every beat is
  loud, none is — rhythm needs rests.
  Calibration from Freddy's feedback (2026-09-25): ~85% of beats with a content event and the
  rest as named rests felt right; 100% driven by camera punches felt like a heartbeat.
- **Accelerate into the turn.** Quarter notes → 8ths → 16ths before a reveal (the Reely stutter).
- **Silence before the drop.** A ¼-beat gap (7.75→8.0 s) makes the drop land twice as hard.
- **No hold longer than ~2 s without internal motion** (convention, not measured science —
  but dead time is the #1 thing Freddy flags). Holds get a slow push, a float, a blink.
- **Structure for 15 s:** hook ≤1 s (open *on* motion, never a slow logo build) · problem ·
  turn · payoff on the drop · product · name in the last 2–3 s · **last frame = first frame**.

## 3 · Continuity beats cuts

- **One hero object, never cut.** The same element morphs through every state (card → row
  thumbnail → full screen → phone slot). Shared-element transitions read as designed; wipes read
  as template.
- **Match cuts on shape, colour or motion vector.** The amber seam is frame 0, the card's birth,
  the cut line, the caret, and the loop.
- **Text that swaps inside a container needs its own exit and entry timing** or the two overlap
  (Reely v1 bug at 7.2 s). Exit fast (`power2.in`, ~0.16 s), enter after.

## 4 · Motion quality

| Rule | Why |
|---|---|
| **Springs, tiny overshoot at most** (ζ ≈ 0.74 → ~3.5%; UI surfaces ζ ≈ 0.86) | Real mass settles; big bounce reads cheap and fights legibility |
| **Closed-form spring step response**, retargets summed: `v(t) = base + Σ Δᵢ·step(t − tᵢ)` | Pure function of time → seekable, deterministic, no state between frames |
| Enter `expo.out`/spring, exit `power2/3.in`, on-screen moves `inOut` | Fast start/soft land in, soft start/fast leave out |
| Slams: scale 1.4–1.9 → 1 in 0.2–0.34 s on the ELEMENT; camera punch/shake only if it is a story turn | Weight comes from the object; the camera is reserved punctuation |
| **Each repeat of a move varies** (direction, angle, size) | Identical slams = template. Reely v1 flaw |
| Staggers cap at ~0.5 s total per group | Arrival reads as one beat |
| **Transforms and opacity only.** Never `letter-spacing`, `width`, `top` | Layout properties snap to whole pixels and stutter (HF lint `gsap_non_transform_motion`) |
| Motion blur only on things that SNAP (slams, whips) — 1–3 per piece | Blur on slow motion reads as a soft render, not speed |
| Per-glyph `x` for tracking animation | See above — letter-spacing snaps |
| Read-heads, cursors, taps drive changes | Cause → effect is what makes UI motion feel alive |

## 5 · Camera

- The whole scene lives in a `#cam` wrapper driven ONLY by `frame(t)`: summed springs for moves,
  exponential punches (+3–7% scale, 12 ms attack, ~140 ms decay), decaying sinusoid shake
  (8–14 px, 17–21 Hz, τ≈85 ms).
- **Camera punches are punctuation, not rhythm. Budget: 3–4 per 15–20 s piece**, only on the
  story turns (the reveal, the drop, the name). **Shakes: 1–2 per piece.** `review.py` reports the
  budget from `cues.json` and flags an overspend.
- **No per-beat pulse by default** (no `camera.pulse`, no beat-synced shader glow, no four-on-the-
  floor thump under a quiet section). It reads as a heartbeat. Opt in only when the brief is a
  hype/music edit and say so.
- **Lean in before the payoff** (slow spring toward the winner), **release on the drop** — slow
  camera *moves* are fine; it is the rapid repeated *hits* that tire the eye.
- Never let tweens and `frame(t)` fight over the same element.

## 6 · Look

- **Brand tokens verbatim** — colours, type, radii from the client's design system. One accent,
  used as a highlighter, never as a background wash.
- **Light has a story:** an ambient shader whose intensity follows the acts (brighter hook,
  darker focused middle, full on the drop). Keep it dark and warm; it is atmosphere, not content.
- **Grain** hashed per frame (never a looping texture), ~5–8% overlay. **Vignette** gentle.
- **Grade the footage** lightly (contrast +8%, brightness −5%) so it sits in the palette.
- Banned (Freddy's list + research): bouncy/elastic easing as default, particle bursts, glows on
  UI chrome, gradients on UI chrome, stacked grain+CA+flare+vignette, mismatched icon strokes,
  dead time, uniform content-agnostic transitions, perfect symmetry in every frame,
  anything that looks like a template.

- **Light brands are not dark brands with the colours swapped.** On a bright field (Servi's
  celeste) the ambient shader adds a white halo instead of a warm glow, grain drops to ~5%, the
  vignette is a faint ink tint, and depth comes from edges and colour steps — some brands ban
  blurred shadows outright (Servi §2.3). Read the brand's material rules before styling a card.
- **The end card is not exempt from "something every beat".** Reely v3 failed the dead-time gate
  only on its logo hold. Give each beat of the hold an event: lockup, tagline, URL/CTA,
  a highlighter swipe, a caret blink, a slow push.
- **Build the video around the logo's own geometry when it has a story.** Servi's symbol IS a
  message bubble with a check: the bubble leaves the logo as the first message, and the whole
  conversation folds back into it as the check. Concept, transition and loop in one move.

## 7 · Type

- One UI face, local `@font-face` (HF lint requires it). Inter/Geist; SF Pro only inside
  Apple-UI mockups (licence).
- Hook type huge (130–160 px on 1080 w), **with contrast guaranteed**: dim what's behind it
  (≥0.65 black) or give it its own zone. Reely v1: white on dimmed-grey failed.
- Every word readable ≥ 0.5 s after it lands; captions pop per word on the *measured* audio.
- Keep critical text inside the safe zone (review sheet draws it).

## 8 · Sound is half the video

- **Score to picture** with `score.py`: the music's structure is the story's structure
  (tension pad → build → gap → drop → tail). Every visual hit has a sound: slam=impact+kick,
  UI=tick, move=whoosh, turn=riser+snare roll.
- **Use real voice when it exists** — chopped on the grid it becomes the hook.
- **Measure onsets from the waveform, never trust Whisper word times** (they were 1.1–1.7 s off).
- Master **−14 LUFS integrated, ≤ −1 dBTP**. Read `bar_lufs`: **the hook bar must not be more
  than ~6 LU under the mix** (score.py warns). A quiet first second loses the scroll.
- You cannot hear. Verify by numbers (LUFS per bar, true peak) and by looking at the
  waveform/spectrogram — and tell Freddy to listen, because taste in sound needs ears.

## 9 · Honesty

- **"Features in production" is a claim — verify it against the account/state file, not the
  landing.** The Servi landing advertised a phone channel ("Nuevo · el teléfono") that was still
  on a branch; it stayed out of the video. Marketing pages run ahead of production.
- **Reuse approved copy before writing new copy.** The landing's feature titles and the brand's
  "what we don't do" list are already on-voice and already approved — lift them verbatim.
- **A real conversation beats a scripted one.** Rebuild real messages as animated bubbles (exact
  text), never paste low-res screenshots and never invent the exchange. Swap a real client's
  name for the demo tenant's when the video is public, and say so in the handoff.
- No invented numbers on screen. Real durations, real takes, real UI copy.
- Don't claim what isn't live ("Coming soon" until the App Store listing exists).
- Reordering real clips for the story is fine; say so in the handoff.

---

**Sources** — Material Design 2 motion (S), MDN easing (S), HyperFrames docs + motion-blur
component measurements vs After Effects (S), Figma spring blog (A), Emil Kowalski UI-motion rules (B),
Josh Comeau spring physics (B), School of Motion match cuts (B), Ryan Juckett damped springs (A),
Replit "lying to the browser" render engine (A), librosa beat tracking (S), ProVideo Coalition
shutter angle (C). Weak evidence, treat as convention: the "2-second hold" rule, per-letter stagger
ms ranges, exact safe-zone pixels, 3-second-hook percentages.
