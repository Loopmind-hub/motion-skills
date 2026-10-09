#!/usr/bin/env bash
# deliver.sh — encode a rendered master for Instagram Reels / TikTok, ENFORCE loudness, and prove it.
#
#   deliver.sh renders/master.mp4 renders/final-social.mp4
#
# H.264 High, yuv420p, faststart, AAC 48k stereo 192k, fps kept (IG/TikTok accept up to 60).
# Audio gets a two-pass EBU R128 loudnorm to −14 LUFS / −1.5 dBTP IN the encode: the renderer's
# audio mux can shift level (Servi/Reely v4 came out at −14.9 LUFS from a −14.1 mix), so the
# final file is normalised here instead of trusting upstream. Then it prints the proof.
set -euo pipefail

in="${1:?usage: deliver.sh <master.mp4> <out.mp4>}"
out="${2:?usage: deliver.sh <master.mp4> <out.mp4>}"
I=-14; TP=-1.5; LRA=11

# pass 1 — measure the master's audio
m="$(ffmpeg -hide_banner -nostats -i "$in" -af "loudnorm=I=$I:TP=$TP:LRA=$LRA:print_format=json" -f null - 2>&1 \
     | awk '/^\{/{f=1} f{print} /^\}/{f=0}')"
get() { printf '%s' "$m" | sed -n "s/.*\"$1\" : \"\\([^\"]*\\)\".*/\\1/p"; }
mi="$(get input_i)"; mtp="$(get input_tp)"; mlra="$(get input_lra)"; mth="$(get input_thresh)"; off="$(get target_offset)"

# pass 2 — encode with the measured values (linear normalisation: no pumping). Linear loudnorm
# cannot hold the peak ceiling on its own (Cal Hacks reel: −0.4 dBFS), and the AAC encoder adds
# ~0.6 dB of overshoot AFTER any limiter — so a 4×-oversampled limiter sits at 0.76 (≈ −2.4 dB)
# to land the encoded file under −1 dBTP (measured: −1.6).
ffmpeg -v error -y -i "$in" \
  -c:v libx264 -profile:v high -preset slow -crf 16 -maxrate 16M -bufsize 24M \
  -pix_fmt yuv420p -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -af "loudnorm=I=$I:TP=$TP:LRA=$LRA:measured_I=$mi:measured_TP=$mtp:measured_LRA=$mlra:measured_thresh=$mth:offset=$off:linear=true,aresample=192000,alimiter=limit=0.76:attack=3:release=60:level=false,aresample=48000" \
  -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -movflags +faststart "$out"

echo "── verify: $out"
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,profile,width,height,pix_fmt,r_frame_rate -of default=nw=1 "$out"
ffprobe -v error -show_entries format=duration,size,bit_rate -of default=nw=1 "$out"
echo "── loudness (target −14 LUFS ±0.5 integrated, true peak ≤ −1 dBTP) · master measured $mi LUFS"
ffmpeg -hide_banner -nostats -i "$out" -af ebur128=peak=true -f null - 2>&1 \
  | awk '/Summary:/{s=1} s && /I:|Peak:/{print "  " $0}'
