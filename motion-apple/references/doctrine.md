# Apple doctrine — premium is what you leave out

Sources: leo (@leomeethewoo), "Make your product videos look expensive (Apple Framework)", X, 2026-09-25
(his studio has made 50+ product videos for Trust Wallet, fomo, PrizePicks, **D**: one practitioner),
plus a research pass the same day (sources at the bottom). **Apple has never published a craft
guide for its marketing films.** Only its UI motion rules are primary (HIG, WWDC). Everything else here
is practitioner convention. Each rule says which it is.

**How this differs from /motion-studio.** /motion-studio makes a feed video loud: something happens on
every beat and holds are dead time. /motion-apple makes it *expensive*. One idea per shot, room to
breathe, stillness used on purpose, one sound where ten would fit. Pick the skill for the brand, not
for the mood of the day.

---

**Two registers.** This doctrine is the **film** register (calm launch film). The **keynote-ui** register
(the narrated UI explainer: kinetic words + widgets, page-turn cuts that flip the field, UI springs with ~5 %
overshoot, shutter blur) was measured on a reference on 2026-10-08 and lives in
`preset-keynote-ui.md`. Where the two disagree (cuts, overshoot, SFX budget), the preset wins for that
register. §1, §2, §8 and §9 hold for both.

## 1 · Intention is everything (the rule the others come from)

*Nothing happens by accident. Every choice needs a purpose (the font, the background, the music, the
colours).* To the viewer, a rule followed everywhere reads as a decision, and a decision reads as
premium. **leo, D. Consistent with HIG restraint, S.**

- **Lock the brand before the first frame.** Write `style.json` (3 colours, 1 family, 2 weights, a
  background rule, a BPM band, an SFX budget), then never break it inside the piece. `apple_audit.py`
  enforces it.
- **The cheapest way to look premium is to not look cheap.** Most amateur product videos fail by
  *adding*: effects, swooshes on everything, trap stems, glows. The default answer to "should I add…"
  is no.
- **Same type of video → same rules.** A brand's second launch video reuses the first one's `style.json`.
  Consistency across videos is where "that's so *them*" comes from.

## 2 · Design first, animation second

*Every great video starts with a great design.* Apple's product designers own the look and motion
comes after. leo's team storyboards every shot frame by frame in Figma before anyone animates. **D.**

- **Storyboard gate.** Build every shot as a still, the composition at its hold pose with no motion yet.
  Snapshot those holds and get them right (and approved) before writing a single tween. If a still is
  not beautiful, no animation will save it.
- **One shot = one idea.** If the idea needs "and", it's two shots. **Convention, C.** The audit
  flags "and" or ";" in a shot's idea.
- **Key object centred.** The product sits on the centre axis. Everything else is subordinate.
  **Directionally true, D (no measured ratio exists; don't invent one).**
- **Background serves, never competes.** A flat field or one slow light falloff. It never moves faster
  than the product and never carries its own idea.
- **Negative space is a material.** At least half of every frame is empty. Space is what makes the
  object look important.
- **One accent per shot.** The accent colour marks the ONE thing the shot is about.

## 3 · Motion: smooth, overlapped, interruptible

| Rule | Evidence |
|---|---|
| **Springs start at 100% damping (ζ = 1, no overshoot).** Add bounce only where the object has physical mass and a reason. `MS.springEase(1)` | WWDC 2018 "Designing Fluid Interfaces", **S** |
| **Velocity-preserving.** A move that changes target keeps its speed. Never restart from zero mid-motion. Use summed spring retargets (`MS.camera` moves). | WWDC 2018, **S** |
| **Never linear** except a constant drift (a slow camera float, a rotating product). Linear starts and stops look mechanical and cheap. | leo, **D** + universal motion practice |
| **Overlap.** The next element starts before the last one lands (≈30–50% overlap), so a sequence reads as one gesture, not a queue. | leo, **D** |
| **Avoid motion that makes people wait.** No move exists only to fill time. | HIG Motion, **S** |
| **Transforms and opacity only.** Same reason as /motion-studio: layout properties snap. | HF lint, **S** |

## 4 · Transitions carry the eye; cuts are a choice

- **Default = continuity.** A match move (the shape in shot A becomes the shape in shot B), a morph, a
  push-through (the camera travels into the object and out into the next scene), a mask wipe that
  follows the product's own geometry, or a soft dissolve. When one scene flows into the next, the
  viewer believes it belongs there. **Grasso via 9to5mac, B.** Apple hides cuts inside camera modules and
  surfaces.
- **One hard cut is allowed, and it is on the dramatic turn.** Apple keeps its abrupt cuts for the reveal
  beat, where the abruptness IS the message. **B.** Budget `max_cuts: 1`.
- Declare each shot's entry in `cues.json` (`"in": "open|match|morph|push|mask|dissolve|cut"`) so the
  audit can count them.

## 5 · Adaptive rhythm

The rhythm is not a metronome. It **speeds up, slows down, or holds** by act. **leo, D. Apple keynote
reveal videos build slower → faster → reveal, B.**

- A typical arc: slow open (long shots, the object alone) → quickening middle (features, shorter shots)
  → **stillness before the reveal** → the reveal lands and HOLDS → a calm name card.
- The audit rejects shot lengths that barely vary (`min_rhythm_cv`).
- **Stillness is allowed, but it has to be deliberate.** A hold after an arrival is breathing, not dead time.
  Gate: no *unplanned* hold. Every hold longer than ~1.2 s is a shot's declared hold, and even a hold
  keeps a trace of life (a slow push ≤ 2%, a light moving across the surface). There is no source for a
  maximum hold length, so tune it per piece and default to ≤ 2.5 s.

## 6 · Music sets the price

- **Choose the BPM from the feel, then stay in the band.** leo's bands: **60–80** regal, cinematic,
  heritage · **90–110** smooth, cool, effortless · **115–123** elite, kinetic, sophisticated · above
  that, hype (fits some projects, destroys others). **⚠ Convention only. No source beyond leo's article
  exists (research pass, 2026-09-25).** Use it as a starting point, not a law.
- **Minimal arrangement.** A pad or a sustained chord that builds, one melodic voice (pluck or piano), a
  soft sub. Add a kick only in the kinetic act. No claps, no snare rolls, no trap hats. **C.**
- The music's arc follows the rhythm arc. The drop, if there is one, IS the reveal.

## 7 · Sound design is subtraction

*Great sound design is the cherry on top.* The same psychology as §1 applies. **leo, D.**

- A sound effect has to help the viewer **understand the product or stay with it**. Decoration is out.
- Budget: **≤ 3 SFX per 10 s, ≤ 3 types in the whole piece** (for example a soft whoosh for the
  push-through, one tick for a UI state, one low impact for the reveal). `style.json` holds the budget
  and the audit counts it.
- **Subtraction pass after the mix.** Go through every SFX and ask whether it's too loud, out of place,
  or not helping. If so, remove it. You can't hear, so do this pass on the list of events and their
  gains, and hand the listening pass to Freddy.

## 8 · Type

- **SF Pro is off-limits.** Its licence restricts it to UI mock-ups running on Apple's own OSs and bars
  artwork and any other work product. **Apple Fonts licence, S.** Use Inter, General Sans or the
  brand's own family.
- One family, two weights. Large type sits a little tight (−0.01 to −0.03 em; convention, **C**).
- Text enters calmly: fade plus a short rise (16–30 px) with the same ζ = 1 spring, one line at a time.
  It stays long enough to read twice.

## 9 · Honesty (same as /motion-studio §9)

Real product, real UI, real claims. Premium polish makes an invented claim worse, not better.

---

**Sources.** [Apple HIG, Motion](https://developer.apple.com/design/human-interface-guidelines/motion) (S) ·
[WWDC 2018 #803 "Designing Fluid Interfaces"](https://developer.apple.com/videos/play/wwdc2018/803/) (S) ·
[Apple Fonts licence](https://developer.apple.com/fonts/) (S) ·
[9to5mac, Adam Grasso on Apple keynote editing](https://9to5mac.com/2023/06/21/apple-keynote-videos-transitions-and-editing/) (B) ·
leo @leomeethewoo on X, 2026-09-25 (D) · practitioner blogs on negative space and tracking (C/D).
**Weak or convention only:** hold durations, the BPM-to-feel bands, tracking values, "one idea per shot",
the negative-space ratio.
