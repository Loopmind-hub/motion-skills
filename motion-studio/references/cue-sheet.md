# cues.json — one file times the picture AND the sound

`score.py cues.json -o assets/audio/mix.wav --emit-js cues.js` builds the soundtrack and writes
`cues.js` (`window.CUES`) so the composition reads the **same marks**. Change a time once, both move.

```jsonc
{
  "bpm": 120, "duration": 15.0,
  "lufs": -14.0, "true_peak": -1.0,
  "chords": ["Fm", "Fm", "Db", "Eb", "Fm", "Db", "Ab", "Eb"],   // one per bar, cycles
  "marks": { "drop": 8.0, "brand": 13.0 },                        // named story beats, seconds

  "layers": [                                                     // the music, 16 steps per bar
    {"inst": "kick", "from_bar": 4, "to_bar": 8, "pattern": "X...x...X...x..."},
    {"inst": "pad",  "from_bar": 0, "to_bar": 4, "cutoff": 420, "cutoff_to": 1500, "gain_db": -1}
  ],
  "fx": [                                                          // designed sound + samples
    {"type": "impact", "at": 8.0, "reverb": 0.35},
    {"type": "sample", "bus": "voice", "file": "assets/audio/take2.wav", "at": 7.98, "src": 1.15, "len": 2.3}
  ],
  "mix": {"pump_db": 4, "voice_duck_db": 10, "music_db": -3.5, "voice_db": 2}
}
```

**Pattern chars:** `X` accent (1.0) · `x` normal (0.75) · `o` ghost (0.5) · `.` rest.
**Instruments:** `kick clap hat ohat tick sub pluck pad` (sub/pluck/pad follow the bar's chord;
`sub.len_steps`, `pad.cutoff[_to]`, `tick.freq`, `octave`).
**FX types:** `sample riser downlifter impact whoosh tick kick clap snare_roll ping pop typing blip ratchet shimmer`.
keynote-ui sounds (measured on an Apple-style reference, 2026-10-08): `blip` = soft pitched UI note, `notes` in
semitones (`[0]` one landing, `[12,7,3,0]` the falling turn chime), `freq`, `step` · `ratchet` = tick train that
speeds up into its end (`len`) · `shimmer` = granular sparkle swell for a morph (`len`). `at`
takes seconds, `{"beat": n}`, or **`{"mark": "name", "dt": offset}`** — prefer marks: a sound placed
on a mark follows the edit when times change (hard-coded seconds went stale silently in a reel).
`len` takes seconds or `{"beat": n}`. **Layers** take `from_bar`/`to_bar` OR `from_mark`/`to_mark`
(snapped to the nearest bar) so a music section stays under its story beat. Any fx takes `gain_db`, `reverb` (send 0–1). Samples take `bus`
(`voice` ducks the music), `src`, `len`, `fade_in`, `fade_out`, `pan`.
**Chords:** root + `"" m 7 m7 maj7 sus2 sus4 5`.

**Report** (`mix.report.json`): integrated LUFS, true peak, `bar_lufs` (loudness per bar — read it,
the hook bar must not sag), a `warning` when it does, and a sha256 (same cues → same bytes).

**Using a real song instead** (Mixkit/Pixabay, commercial-safe): drop the `layers`, add the song
as a `sample` on the music bus, and set `bpm`/marks from `beatgrid` analysis — keep SFX + voice.
