#!/usr/bin/env bash
# scaffold.sh — start a motion-studio project in one command.
#
#   bash ~/.claude/skills/motion-studio/scripts/scaffold.sh <project-dir> [--fonts "outfit,space-grotesk"]
#
# Does: HyperFrames init (skills NOT installed — gotcha 12) · lib/engine.js + lib/motion-blur.js ·
# assets/{fonts,audio,video,img} · fonts from Fontsource (OFL) with their licence · .gitignore for
# heavy/derived files · a cues.json starter. Idempotent: never overwrites an existing file.
set -euo pipefail

SKILL="$(cd "$(dirname "$0")/.." && pwd)"
dir="${1:?usage: scaffold.sh <project-dir> [--fonts a,b]}"; shift || true
fonts="inter"
while [ $# -gt 0 ]; do case "$1" in --fonts) fonts="$2"; shift 2 ;; *) echo "unknown arg $1" >&2; exit 2 ;; esac; done

if [ ! -f "$dir/hyperframes.json" ]; then
  mkdir -p "$(dirname "$dir")"
  HYPERFRAMES_SKIP_SKILLS=1 npx --yes hyperframes@latest init "$dir" --non-interactive --example=blank >/dev/null
  echo "✓ hyperframes project at $dir"
fi
mkdir -p "$dir"/lib "$dir"/assets/{fonts,audio,video,img}

cp -n "$SKILL/templates/engine.js" "$dir/lib/engine.js" 2>/dev/null || true
if [ ! -f "$dir/lib/motion-blur.js" ]; then
  src="$HOME/tools/hyperframes/registry/components/motion-blur/motion-blur.html"
  # the runtime is the <script> body between the SHUTTER_SNIPPET markers' enclosing IIFE
  awk '/^<script>/{f=1;next} /^<\/script>/{if(f){exit}} f' "$src" > "$dir/lib/motion-blur.js"
  node --check "$dir/lib/motion-blur.js"
fi
echo "✓ lib/engine.js + lib/motion-blur.js"

tmp="$(mktemp -d)"
IFS=',' read -ra F <<< "$fonts"
for f in "${F[@]}"; do
  f="$(echo "$f" | xargs)"
  out="$dir/assets/fonts/${f}-variable.woff2"
  [ -f "$out" ] && continue
  (cd "$tmp" && npm pack "@fontsource-variable/$f" >/dev/null 2>&1 && tar xzf fontsource-variable-*.tgz && rm fontsource-variable-*.tgz)
  cp "$tmp/package/files/${f}-latin-wght-normal.woff2" "$out"
  cp "$tmp/package/LICENSE" "$dir/assets/fonts/${f}-LICENSE.txt"
  rm -rf "$tmp/package"
  echo "✓ font $f → assets/fonts/${f}-variable.woff2"
done
rm -rf "$tmp"

[ -f "$dir/.gitignore" ] || cat > "$dir/.gitignore" <<'EOF'
# derived / heavy — rebuild with the steps in README.md
renders/
snapshots/
review/
assets/video/
assets/audio/*.wav
.hyperframes/
EOF

[ -f "$dir/cues.json" ] || cat > "$dir/cues.json" <<'EOF'
{
  "title": "",
  "bpm": 120,
  "duration": 15.0,
  "lufs": -14.0,
  "true_peak": -1.0,
  "chords": ["Fm", "Db", "Ab", "Eb"],
  "marks": {},
  "camera": { "moves": [], "punches": [], "shakes": [] },
  "layers": [],
  "fx": [],
  "mix": { "pump_db": 4.0, "voice_duck_db": 10.0 }
}
EOF
echo "✓ ready. Next: write cues.json, then score.py --emit-js cues.js, then index.html"
