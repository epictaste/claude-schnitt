# Changelog

All notable changes to `/cut` are documented here.

## [1.0.1] — 2026-09-13

Review fixes. The version layout is the substantial one: before this, all
versions shared one timeline, so two hooks of different lengths could not be
expressed at all.

### Changed
- **Every version has its own layout.** `VERSIONS` in `timing.ts` now carries
  the parts of that version in order with their lengths, and `versionLayout()`
  turns them into start frames as a running sum. A version with a 103 frame hook
  and one with a 135 frame hook now shift everything after them correctly. The
  old global `PARTS` and `START` are gone, and `Top.tsx` builds its sequences
  from the layout. A part whose length disagrees with `words.json` throws
  instead of drifting.
- **One source for the layout.** `cut.py` prints the `VERSIONS` block, including
  the part names, and is the only script that does. `words.py` now prints what
  it wrote to `words.json` and nothing else, instead of a second, take-absolute
  block that contradicted it.
- **Named cut segments.** `cut.py --version "v1=hookA:0-103,body:370-600"` ties
  the cut, `words.json`, and the part files together through one name.
- **Transcribe once, split often.** SKILL.md now runs `words.py --raw-out` in
  step 3 and re-splits with `--from-json --parts` after the structure is
  settled, so deciding on parts no longer costs a second upload.
- **Scaffolding uses `rsync --exclude node_modules`**, so a development checkout
  no longer copies a few hundred megabytes into every project.
- **Hard card shadow.** The `Card` block had a soft, blurred shadow, which the
  skill's own rule 6 forbids. It is an offset block of black now.

### Added
- **Frame rate preflight.** `config.require_supported_frame_rate()` rejects any
  take that is not constant 30 fps, including variable frame rate recordings,
  and prints the `ffmpeg` command to convert it. `words.py`, `cut.py`, and
  `build.py` check before doing anything. The half-wired `--fps` flags are gone,
  30 fps is one constant in one place.

### Fixed
- **A frame count mismatch now fails the build.** `build.py` warned and carried
  on with `shortest=1`, which produced a file that was subtly wrong rather than
  an error, and the README claimed it aborted. It aborts.
- **The contact sheet no longer dies on the last frame.** Seek positions are
  computed with half a frame of headroom, every grabbed still is checked, and
  the temporary frame directory is removed even when a step fails.
- **The example part stopped standing still.** Its closing scene held a finished
  graphic for more than two seconds, breaking the rule the same file is supposed
  to demonstrate. The number counts up and a bar fills while the sentence runs.

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
