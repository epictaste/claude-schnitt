# Changelog

All notable changes to `/cut` are documented here.

## [1.0.0] — 2026-09-13

Initial release.

### Added
- **`/cut <video> [notes]`** — edits a vertical talking-head video end to end:
  preflight, word timings, zone measurement, cuts, scaffold, parts, render,
  contact sheet.
- **Word-level timing (`words.py`).** Deepgram `nova-3` with `punctuate=true`
  and `utterances=true`, written to `words.json` as per-part frame numbers at
  30 fps, so every scene change can sit on a word that was actually spoken.
  `--from-json` reparses a saved response without calling the API.
- **Zone measurement (`zone.py`).** Scans several frames for the top edge of a
  burned-in subtitle box using raw grayscale bytes from ffmpeg, no image
  library, and falls back to half the frame height when there is no box.
- **Frame-exact cuts (`cut.py`).** ffmpeg trim and concat per version, then a
  frame count check with ffprobe. A mismatch fails the run instead of silently
  shifting every animation.
- **Sound (`sfx.py`).** Six UI sounds (click, tick, pop, whoosh, ding, type)
  synthesized with ffmpeg and normalized to fixed peaks. No sound library, no
  external assets, no music.
- **Render and composite (`build.py`).** Remotion render with the log going to a
  file, ffmpeg overlay, sound effects mixed under the voice, and a contact sheet
  of seven frames.
- **Remotion template.** `timing.ts` (zone, parts, words, versions, `wordFrame`),
  `blocks.tsx` (Scene, Emphasis, Badge, Card, Typing, Mosaic, TextHook, one
  configurable accent color), `Top.tsx` with per-version part overrides, and a
  `Check-V<N>` composition that lays the zone over the cut for stills.
- **`PART_BRIEF.md`** — the briefing for a sub-agent that builds one part, with
  the ten design rules and a mandatory still-rendering self test.
- **Config shared with [`watch`](https://github.com/epictaste/claude-eyes).**
  `~/.config/cut/.env` first, `~/.config/watch/.env` as a fallback, so existing
  `watch` users have nothing to configure.
- **SessionStart hook** for Claude Code, silent when everything is in place.
- **CI**: pytest against ffmpeg-synthesized clips and a fixture Deepgram
  response, plus a typecheck of the Remotion template.
