# cut skill

Agent Skills package that lets an agent edit a vertical talking-head video:
measure the free zone above the speaker, get word-level timestamps, cut
frame-exact hook versions, build a word-synced animation zone with Remotion, and
render finished MP4s. Installable in Claude Code, Codex, Cursor, GitHub Copilot,
and other [Agent Skills](https://agentskills.io) hosts. The Python side is pure
stdlib and orchestrates `ffmpeg`, `ffprobe`, Remotion, and the Deepgram API.

## Structure

- `skills/cut/SKILL.md` — the skill contract. Source of truth for behavior on
  every host.
- `skills/cut/scripts/` — `setup.py` (preflight and installer), `words.py`
  (Deepgram word timings to frames), `zone.py` (subtitle-box measurement),
  `cut.py` (frame-exact cuts with ffprobe verification), `sfx.py` (six
  ffmpeg-synthesized UI sounds), `build.py` (render, composite, contact sheet),
  `config.py` (shared config plus the ffmpeg and ffprobe wrappers).
- `skills/cut/template/` — the Remotion project that gets copied next to the
  user's video. `src/timing.ts` holds zone, parts, word timings, and versions;
  `src/blocks.tsx` holds the shared visual blocks; `src/parts/` holds one file
  per part.
- `skills/cut/PART_BRIEF.md` — the briefing handed to a sub-agent that builds one
  part.
- `hooks/` — Claude Code SessionStart status hook.
- `.claude-plugin/`, `.codex-plugin/`, `.agents/plugins/` — host manifests.
- `tests/` — pytest suite. Videos are synthesized with ffmpeg, the Deepgram path
  runs against a fixture. No network.

## Orientation

- **The product is the skill, not a CLI.** The scripts are implementation. They
  have to work on every host the skill installs into.
- **The skill is one self-contained folder: `skills/cut/`.** SKILL.md,
  `scripts/`, and `template/` are siblings inside it. That is what lets
  `npx skills add` copy a working skill as a unit. Do not move them apart.
- **Path resolution is harness-agnostic.** SKILL.md resolves `SKILL_DIR` as the
  directory of the SKILL.md the model just Read. Do not reintroduce
  `${CLAUDE_SKILL_DIR}`, which is unset outside Claude Code.
- **No `commands/` wrapper.** `/cut` comes from the SKILL.md frontmatter
  (`name: cut` plus `user-invocable: true`).
- **The design rules are the product.** The value of this skill is not the
  scripting, it is the list of rules in SKILL.md and PART_BRIEF.md that keep an
  animation readable: changes on spoken words, no headline repeating the voice,
  hard cuts, never standing still. Changes there matter more than refactors.

## Commands

```bash
# Tests (ffmpeg required for the media tests, no network)
python3 -m pytest -q

# Template typecheck
cd skills/cut/template && npm ci && npx tsc --noEmit

# A still from the template, to see the look without a video
cd skills/cut/template && npx remotion still Top-V1 /tmp/cut-still.png --frame=10
```

## Rules

- Keep the version in sync across `skills/cut/SKILL.md` (frontmatter),
  `.claude-plugin/plugin.json`, and `.codex-plugin/plugin.json` when releasing.
- Never commit an API key, an `.env`, or a rendered video.
- Renders log to a file, never to a pipe. A pipe that closes kills Remotion with
  SIGPIPE mid-render.
- A project keeps its own `public/` directory. Pointing a render at a large
  shared one copies it on every single run.
