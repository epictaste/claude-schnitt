# Part briefing

Template for the sub-agent that builds one part of the animation zone. Fill in
every `<placeholder>` before sending it. One agent per part, one file per part.

---

You are building part **`<part>`** of the animation zone for `<slug>`.

**Canvas:** `<width>` x `<height>` px, 30 fps.
**File:** `src/parts/part-<part>.tsx` in `<project-path>`.
**Exports:** `export const <Name>Part: React.FC` and `export const <Name>Cues: Cue[]`.
**Length:** `PARTS.<part>` frames. Frame 0 is the start of the part, not of the video.

Touch only this one file. Import the blocks from `../blocks`, do not copy them.
`src/timing.ts`, `src/blocks.tsx`, `src/Top.tsx`, and `src/sfx.tsx` belong to
someone else.

## What is spoken in this part

```
<the transcript of this part, verbatim>
```

Word timings are in `src/words.json`. Look them up in code with
`wordFrame('<part>', 'word')`. Do not calculate frames by hand and do not edit
`words.json`. If speech recognition spelled a word its own way, use that
spelling in the code.

## Facts this part may show

<the facts, numbers, names, dates this part is allowed to put on screen. Nothing
beyond this list. No invented numbers, no made-up benchmarks, no screenshots of
things that do not exist.>

## Rules

1. **The video is the truth.** Every change lands on `wordFrame('<part>',
   'word')`. No guessed times.
2. **No headline that repeats what is said.** Text on screen is for what the
   voice does not carry: a number, a date, a name, a measured value. `Emphasis`
   is for numbers only.
3. **Hard changes.** No fades, no springs at the start of a scene, nothing
   floating. Allowed: the slow drift `Scene` already does, typing reveals, lines
   flying in, bars filling, arrows drawing, counters running up.
4. **Never standing still.** No scene sits finished for 1.5 seconds. Keep scenes
   short or keep revealing inside them. A list item appears when it is spoken.
5. **Mock interfaces instead of text chips.** A terminal with a typed command
   and a check mark, a chat window with bubbles, a file card, a notification.
   One core graphic per scene plus at most three keywords. Keep text short.
6. **Type and color.** `INTER_BLACK` with `HARD_SHADOW` for headline-weight
   text, `UI_FONT` inside mock interfaces. Only `COLORS.bg / white / gray /
   grayDark / card / accent`, plus `COLORS.green` for check marks. One accent
   element per scene. No glow, no blur, no gradient, no colored shadow.
7. **Room.** Core graphic vertically centered, at most `MAX_GRAPHIC_WIDTH`
   (760 px) wide, the top `HEADER_SAFE` (180 px) empty. Inter Black is wide:
   check sizes after every text change, nothing may touch an edge.
8. **Blur out secrets.** Full prompts, keys, and private paths go under `Mosaic`
   with the first line left readable.
9. **Frame 0 already shows something.** The first frame of the part must not be
   empty. SVG arrows: `markerEnd` only above `draw > 0.85`, `opacity: 0` at
   `draw === 0`.
10. **Sound cues.** Export 4 to 12 cues, frames relative to the part, exactly on
    the frames where something visible happens: `click` for a hard scene change
    or a stamp, `pop` for a card or badge appearing, `tick` for list rows and
    check marks, `whoosh` for something flying in, `ding` for success,
    `typeTicks(from, count)` for typing. At most one cue per 8 frames, except
    inside `typeTicks`.

## Self test, mandatory before you report back

```bash
cd "<project-path>"
npx tsc --noEmit
npx remotion still Top-V<version> out/<part>-f<N>.png --frame=<N>
```

`<N>` is an **absolute** frame in the composition: `START.<part>` plus the frame
inside the part. Render at least four stills and **Read every one of them**:

- the first frame of the part
- the middle
- one point in the middle of a reveal
- the last frame

Fix clipped text, an empty frame, a jumping element, or a scene that stands
still before you report. Redirect render output to a log file, never into a
pipe: a closing pipe kills the render with SIGPIPE.

Report back: what the part shows scene by scene with its frame ranges, which
words each change hangs on, and anything you could not resolve.
