# Install — for coding agents (Claude Code, Codex, Cursor, Gemini CLI)

You are an agent installing **motion-apple** (Apple-style motion graphics) and **motion-studio** (its engine) for
the user. Do every step, check each one, and tell the user the exact command when something needs their password.

## 1 · Prerequisites (check, install what's missing)

| Tool | Check | macOS | Windows | Linux |
|---|---|---|---|---|
| Node.js ≥ 22 | `node -v` | `brew install node` | `winget install OpenJS.NodeJS.LTS` | nodejs.org |
| FFmpeg | `ffmpeg -version` | `brew install ffmpeg` | `winget install Gyan.FFmpeg` | distro package |
| uv (Python) | `uv --version` | `brew install uv` | `winget install astral-sh.uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| git + GitHub CLI | `git --version` · `gh --version` | `brew install git gh` | `winget install Git.Git GitHub.cli` | distro package |

HyperFrames itself runs through `npx` (no global install). It renders in headless Chrome, which npx fetches.

## 2 · The skills

```bash
git clone https://github.com/Loopmind-hub/motion-skills.git ~/motion-skills
mkdir -p ~/.claude/skills
ln -s ~/motion-skills/motion-studio ~/.claude/skills/motion-studio
ln -s ~/motion-skills/motion-apple  ~/.claude/skills/motion-apple
```

On Windows without symlink rights, copy the two folders into `%USERPROFILE%\.claude\skills\` instead.
For agents that don't read `~/.claude/skills`, point them at the two `SKILL.md` files.

## 3 · The HyperFrames engine clone (the motion-blur component and the docs the skills read)

```bash
mkdir -p ~/tools && git clone --depth 1 https://github.com/heygen-com/hyperframes.git ~/tools/hyperframes
```

## 4 · Voice — pick one

- **ElevenLabs (best results).** Create an API key at elevenlabs.io and store it as `ELEVENLABS_API_KEY` in the
  user's shell profile or OS keychain. Never print it and never ask the user to paste it into the chat.
  Use the text-to-speech endpoint with timestamps, so every word gets its onset.
- **Qwen3-TTS (free, local, open source).**
  - Mac with Apple Silicon: `uv tool install mlx-audio`, then
    `mlx_audio.tts.generate --model mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit --text "Hola" --voice Vivian --output_path ./vo`
  - Windows/Linux with an NVIDIA GPU: `pip install -U qwen-tts` (see github.com/QwenLM/Qwen3-TTS).
  - Get word timings by transcribing the result (whisper.cpp or any Whisper).

## 5 · Verify

```bash
node --test ~/motion-skills/motion-studio/tests/engine.test.mjs
uv run --with pytest --with numpy --with scipy --with soundfile --with pyloudnorm --with pillow \
  pytest ~/motion-skills/motion-studio/tests ~/motion-skills/motion-apple/tests -q
npx --yes hyperframes doctor
```

## 6 · First render

Read `motion-apple/SKILL.md`, then make a 15-second test video on a topic the user picks, in the **keynote-ui**
register, and open it for them. Paths inside the skills use `~/.claude/skills/...`; they work as installed above.
