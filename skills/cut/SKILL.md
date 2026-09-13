---
name: cut
version: "1.0.1"
description: Edit a talking-head video. Measures the free zone above the speaker, gets word-level timestamps, cuts frame-exact hook versions, builds a word-synced animation zone with Remotion, and renders finished MP4s. Use when the user says "edit my video", "cut this reel", "animate the top half", "put graphics over my video", "three hook versions", or hands over a local video file to edit.
argument-hint: "<video-path> [notes]"
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion, Task
homepage: https://github.com/epictaste/claude-cut
repository: https://github.com/epictaste/claude-cut
author: epictaste
license: MIT
user-invocable: true
---

# /cut

The user hands you a vertical talking-head video they already shot. You give back
finished MP4s: the lower part stays their footage, the upper part becomes a
graphics zone that is animated in sync with the words they speak, cut into as
many hook versions as they recorded.

You are the editor here. Python scripts do the measuring, cutting, and
rendering; the part files you write are the actual editing work.

## Resolve `SKILL_DIR` (do this before any command)

Every command below runs a bundled script under `SKILL_DIR/scripts/`. Set
`SKILL_DIR` to the **absolute path of the directory containing THIS SKILL.md you
just Read** — your harness printed that path in the Read result. The scripts are
always a direct sibling of this file, in every install layout:

```
Read ~/.claude/plugins/cache/epictaste/cut/<ver>/skills/cut/SKILL.md → SKILL_DIR=…/skills/cut
Read ~/.codex/skills/cut/SKILL.md                                    → SKILL_DIR=~/.codex/skills/cut
Read ~/.agents/skills/cut/SKILL.md                                   → SKILL_DIR=~/.agents/skills/cut
```

Substitute that literal path for `${SKILL_DIR}` everywhere. Guard once:

```bash
SKILL_DIR="<absolute path of the directory containing the SKILL.md you Read>"
if [ ! -f "$SKILL_DIR/scripts/build.py" ]; then
  echo "ERROR: scripts/build.py not found under SKILL_DIR=$SKILL_DIR" >&2
  exit 1
fi
```

On Windows, substitute `python` for `python3` in every command.

## Step 1 — Preflight

```bash
python3 "${SKILL_DIR}/scripts/setup.py" --check
```

Exit 0 means everything is in place; say nothing and continue. Otherwise:

| Exit | Meaning | Action |
|------|---------|--------|
| `2` | `ffmpeg`, `ffprobe`, `node`, or `npm` missing, or node older than 20 | run the installer |
| `3` | no Deepgram API key | run the installer, then ask for a key |
| `4` | both | installer, then key |

```bash
python3 "${SKILL_DIR}/scripts/setup.py"
```

The installer uses `brew` on macOS and prints exact commands elsewhere. It
scaffolds `~/.config/cut/.env` (mode 0600). A key in `~/.config/watch/.env` is
picked up automatically, so users of the `watch` skill have nothing to
configure. Without a key there are no word timings, and the whole premise of
this skill falls apart. Say that plainly instead of building something out of
guessed times.

Use `--json` instead of `--check` when you want the full picture (`status`,
`can_proceed`, `missing_binaries`, `node_version`, `api_key_source`).

## Step 2 — Watch the take

Play the video or step through frames before you plan anything. You need to know
what is on screen, where the speaker looks, and whether subtitles are burned in.
If the [`watch` skill](https://github.com/epictaste/claude-eyes) is installed,
use it. Otherwise pull a handful of frames and Read them:

```bash
for t in 1 5 10 20 30; do
  ffmpeg -v error -y -ss $t -i "<video>" -frames:v 1 "/tmp/cut-frame-$t.jpg"
done
```

## Step 3 — Words

Transcribe once and keep the raw response. The part ranges are not known yet,
they come out of step 5, and nothing is gained by uploading the audio twice:

```bash
python3 "${SKILL_DIR}/scripts/words.py" "<video>" --raw-out "<video-dir>/raw-deepgram.json"
```

This extracts the audio, sends it to Deepgram (`nova-3`, `punctuate=true`,
`utterances=true`), and writes `words.json` next to the video. Without `--parts`
everything lands in a single part called `main`, which is all you need in order
to read the transcript and plan the structure.

After step 5, when you know the frame ranges, split it again from the saved
response. This runs offline and takes a second:

```bash
python3 "${SKILL_DIR}/scripts/words.py" "<video>" \
  --from-json "<video-dir>/raw-deepgram.json" \
  --parts hookA:0-103,hookB:103-238,body:370-600
```

Parts are ranges in **frames of the take**, they must not overlap, and they do
not have to cover the whole take. Name them the way the parts are named in the
cut, because those names show up again in `VERSIONS` and in the part files.
Frames inside `words.json` are relative to the start of each part.

`words.py` writes `words.json` and nothing else. The layout of a version, which
parts in which order, comes from `cut.py` in step 6.

**The video is the truth.** Every scene change you build later sits on
`wordFrame(part, 'word')`, never on a time you estimated. Read `words.json`
before writing part files: speech recognition spells things its own way, and the
code has to match the transcript, not the script. Never rewrite `words.json` to
fix a spelling.

**Constant 30 fps only.** The scripts refuse anything else, including variable
frame rate recordings, and print the `ffmpeg` command to convert the file. Run
that command, then start again from step 3 with the converted take.

## Step 4 — Zone

```bash
python3 "${SKILL_DIR}/scripts/zone.py" "<video>"
```

With burned-in subtitles, this scans several frames for the top edge of the
subtitle box and reports the zone height as that edge minus 23 px, so the box
stays free. Without subtitles it falls back to half the frame height. Pass
`--samples`, `--threshold`, or `--margin` if the measurement looks off, and
check it against a frame you have actually seen.

## Step 5 — Structure, asked once

Ask the user **one bundled block** of questions before building anything. Do not
drip-feed these one at a time:

1. **Hook versions.** Were several hooks recorded back to back, and which
   versions should come out of them? You need the frame ranges.
2. **Hook treatment.** A text hook poster from frame 0 (the default, a two-line
   headline that stands at least three seconds) or a word-by-word animation.
3. **Zone style.** A dark zone with a hard edge (the default) or floating
   elements over the footage.
4. **Zone from second 0**, over the hook as well? Default yes.
5. **Accent color.** Default is terracotta `#D97757`, one line in `blocks.tsx`.

## Step 6 — Cuts

Name every segment after the part it becomes. That name is what ties the cut,
`words.json`, and the part files together:

```bash
python3 "${SKILL_DIR}/scripts/cut.py" "<video>" \
  --version "v1=hookA:0-103,body:370-600" \
  --version "v2=hookB:103-238,body:370-600"
```

Segments are frames of the take, half open, so `0-103` ends before frame 103 and
the next segment can start there. Versions may have different lengths, which is
the normal case with hooks: `v1` is 333 frames here, `v2` is 365.

Each version is cut with ffmpeg and its frame count is then verified with
ffprobe. The script fails on a mismatch, because a cut that is one frame off
drags every word timing with it.

It prints the `VERSIONS` block for `src/timing.ts`. That block is the single
source for the layout, the lengths, and the file names. Paste it as it is.

## Step 7 — Scaffold the project

Copy the template next to the video, never into a shared directory: the render
copies `public/` on every run, so the project needs its own small one. Exclude
`node_modules`, a development checkout has a few hundred megabytes sitting
there:

```bash
SLUG="<short-slug>"
VIDEO_DIR="$(cd "$(dirname "<video>")" && pwd)"
PROJECT="$VIDEO_DIR/cut-$SLUG"
mkdir -p "$PROJECT"
rsync -a --exclude node_modules --exclude out "${SKILL_DIR}/template/" "$PROJECT/"
cp "<words.json>" "$PROJECT/src/words.json"
cp "<cuts>/v1.mp4" "$PROJECT/public/v1.mp4"      # one cut file per version
python3 "${SKILL_DIR}/scripts/sfx.py" "$PROJECT/public"
(cd "$PROJECT" && npm install --no-audit --no-fund)
```

Without `rsync`, copy and clean up afterwards:
`cp -R "${SKILL_DIR}/template" "$PROJECT" && rm -rf "$PROJECT/node_modules" "$PROJECT/out"`.

The `npm install` takes a minute on the first project and is needed before any
still renders. `build.py` runs it for you if you skip it, but the sub-agents in
step 8 render stills directly and need the dependencies in place.

Then edit `src/timing.ts`:

- `ZONE` from step 4.
- `VERSIONS` exactly as `cut.py` printed it. Each entry names the cut file in
  `public/` and lists its parts in order with their lengths.
- `SFX_READY = true` now that the sounds exist.

Nothing else in that file is filled in by hand. `versionLayout()` turns the
layout into start frames as a running sum, and it throws if a length disagrees
with `words.json`, which is the check that catches a project drifting apart.

Delete `src/parts/part-example.tsx` and write one file per part instead. Each
part file exports a component and its sound cues:

```
src/parts/part-<name>.tsx  →  export const <Name>Part: React.FC
                              export const <Name>Cues: Cue[]
```

Register every part in the `COMPONENTS` map in `src/Top.tsx`, keyed by the part
name from `words.json`. A hook that differs between versions is its own part
with its own file, `hookA` and `hookB`, not a variant of one shared part. That is
what lets versions have hooks of different lengths.

Frame 0 inside a part file is the start of that part, because `Top.tsx` wraps
each part in a `Sequence` at the offset its version gives it.

## Step 8 — Build the parts

One part per sub-agent, all at once if your harness can run them in parallel,
otherwise one after another. Brief each agent with `PART_BRIEF.md` from this
skill directory, filled in with the part name, the zone size, the part length,
and the facts that part is allowed to show.

Every agent has to render at least four stills, Read them, and fix clipped text,
empty frames, or a scene that stands still before reporting back:

```bash
cd "$PROJECT" && npx remotion still Top-V1 out/<part>-f<N>.png --frame=<N>
```

`<N>` is absolute in that version's composition, so it is the part's start plus
the frame inside the part. The start is the sum of the lengths of the parts
before it in that version's layout, which differs per version. Work it out once
per part and hand it to the agent in the briefing.

Do not take an agent's word for it. Spot-check a few stills yourself.

## Step 9 — Render and composite

```bash
python3 "${SKILL_DIR}/scripts/build.py" "$PROJECT" 1
```

This renders `Top-V<N>`, overlays it onto the matching cut at 0:0, mixes the
sound effects about 10 dB under the voice, and writes
`out/<slug>-v<N>.mp4` plus a contact sheet of seven frames.

The render log goes to `out/render-v<N>.log`. Never pipe a Remotion render into
`head` or any other command that closes the pipe early; the render dies from
SIGPIPE halfway through.

## Step 10 — Check

`Read` the contact sheet `out/contact-v<N>.jpg` and answer three questions:

- Does the hard edge sit where it should, with the subtitle box untouched?
- Does the graphic match the sentence being spoken at that moment?
- Is anything clipped at an edge, and is any scene standing still?

For a closer look, render a still of the `Check-V<N>` composition: same zone,
laid over the cut at full frame size. It takes 20 to 40 seconds per still
because it decodes the video, so use it for the final look, not for iteration.

Fix what you find, rebuild, look again.

## Step 11 — Deliver

Print the paths of the finished MP4s and their contact sheets, and say in one
line what differs between the versions. That is the end of the skill. It does
not post, upload, message anyone, or write into a note system.

## Design rules

These are the actual craft of this skill. They also go into every sub-agent
briefing.

1. **The video is the truth.** Every change lands on `wordFrame(part, 'word')`.
   No guessed times.
2. **No headline that repeats what is said.** On-screen text is for what the
   voice does not carry: a number, a date, a name, a measured value, a word to
   comment. Emphasis is for numbers.
3. **Hard changes.** No fades, no springs at the start of a scene, nothing
   floating. Allowed: slow drift, typing reveals, lines flying in, bars filling,
   arrows drawing.
4. **Never standing still.** No scene sits finished for 1.5 seconds. List items
   appear when they are spoken, not before.
5. **Mock interfaces instead of text chips.** A chat window, a terminal with a
   check mark, a phone notification, a file card. One core graphic per scene
   plus at most three keywords.
6. **Type and color.** Inter Black with a hard shadow `5px 6px 0 #000`. Black
   `#0A0A0A`, white, gray `#9C9C9C`, card `#161616`, one accent (default
   terracotta `#D97757`), green only for check marks. No glow, no blur, no
   gradient.
7. **Room.** Core graphic vertically centered, at most 760 px wide, the top
   180 px empty for the platform header.
8. **Text hook.** A poster from frame 0, two lines, large, standing at least
   three seconds, with the hook animation below it.
9. **Blur out secrets.** Full prompts, keys, private paths go under `Mosaic`
   with the first line left readable.
10. **Frame 0 of every scene already shows something.** SVG arrows get their
    `markerEnd` only above `draw > 0.85`.

## Acceptance checklist

- [ ] Zone measured, subtitle box free, hard edge sits right
- [ ] Frame counts of the cuts match their `VERSIONS` layout exactly, per version
- [ ] Every scene change hangs on `wordFrame`, nothing guessed
- [ ] No headline repeating the spoken sentence, emphasis only on numbers
- [ ] No scene standing finished for more than about 1.5 seconds
- [ ] Prompts and keys blurred, everything spoken stays readable
- [ ] `npx tsc --noEmit` clean in the project
- [ ] Contact sheet of every version looked at

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Render dies halfway with no error | output was piped into a command that closed the pipe | log to a file, `build.py` already does |
| Every render copies gigabytes | the project points at a large shared `public/` | give the project its own `public/`, as in step 7 |
| `wordFrame` throws | speech recognition spelled the word differently | look it up in `words.json` and use that spelling, never edit the JSON |
| `build.py` stops with a frame count mismatch | the layout in `timing.ts` and the cut disagree | re-run `cut.py` and paste the `VERSIONS` block it prints, do not hand-edit lengths |
| `versionLayout` throws about a length | a part length in `VERSIONS` differs from `words.json` | re-run `words.py` and `cut.py` with the same ranges |
| A script refuses the file over frame rate | the take is not constant 30 fps | run the `ffmpeg` command it printed, then start again at step 3 with the converted file |
| Text clipped at the edge | Inter Black is wide | lower the font size or shorten the text, do not narrow the margins |
| Zone covers the subtitles | measurement hit a dark shirt, not the box | re-run `zone.py --samples 10`, or pass the height you measured yourself |

## Security and permissions

**What this skill does**

- Runs `ffmpeg` and `ffprobe` locally to cut, measure, composite, and to
  synthesize the six sound effects
- Sends the extracted audio track, and only that, to Deepgram
  (`api.deepgram.com/v1/listen`) for word-level timestamps
- Runs Remotion locally, which downloads npm packages and a headless browser on
  first use, and fetches the Inter font from Google Fonts at render time
- Writes into a `cut-<slug>` project directory next to the video
- Reads `~/.config/cut/.env` and, as a fallback, `~/.config/watch/.env`

**What it does not do**

- Never uploads the video itself, only the audio
- Never posts, sends, or publishes anything
- Never writes the API key to stdout, to a log, or into an output file

**Bundled scripts:** `scripts/setup.py` (preflight and installer),
`scripts/words.py` (Deepgram word timings), `scripts/zone.py` (zone
measurement), `scripts/cut.py` (frame-exact cuts), `scripts/sfx.py` (sound
synthesis), `scripts/build.py` (render, composite, contact sheet),
`scripts/config.py` (shared config and media helpers).

Review the scripts before first use to verify what they do.
