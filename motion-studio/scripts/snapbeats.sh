#!/usr/bin/env bash
# snapbeats.sh — the cheap critique loop in one command: one frame per beat (+offset),
# plus frame 0 and the last frame (the loop seam), straight from cues.json.
#
#   bash ~/.claude/skills/motion-studio/scripts/snapbeats.sh <project-dir> <label> [offset=0.2] [--only "t1,t2"]
#
# Writes <project>/snapshots/<label>/ with HyperFrames' contact sheets, then prints their paths:
# Read EVERY sheet before writing the gap list (references/critique.md).
set -euo pipefail
dir="${1:?usage: snapbeats.sh <project-dir> <label> [offset] [--only t1,t2]}"
label="${2:?label, e.g. v1}"
offset="${3:-0.2}"
only=""
[ "${4:-}" = "--only" ] && only="${5:-}"

cd "$dir"
if [ -n "$only" ]; then
  times="$only"
else
  times="$(node -e '
    const c = require("./cues.json"), off = +process.argv[1], spb = 60 / c.bpm, d = c.duration;
    const ts = [0];
    for (let b = 0; b * spb < d - 1e-6; b++) ts.push(Math.min(b * spb + off, d - 0.02));
    ts.push(d - 0.02);
    console.log([...new Set(ts.map(t => t.toFixed(2)))].join(","));
  ' "$offset")"
fi
pin="$(node -e 'const s=require("./package.json").scripts.render||"";const m=s.match(/hyperframes@[\d.]+/);console.log(m?m[0]:"hyperframes@latest")')"
npx --yes "$pin" snapshot . --at "$times" --no-end -o "snapshots/$label" --describe false >/dev/null
ls "snapshots/$label"/contact-sheet*.jpg
