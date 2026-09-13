# Security

`/cut` runs `ffmpeg`, `ffprobe`, and Remotion on your machine. Here is exactly
what leaves it and what does not.

## What goes out

- **The audio track, to Deepgram.** To place scene changes on spoken words, the
  skill extracts a mono 16 kHz mp3 and posts it to `api.deepgram.com/v1/listen`.
  That is the only outbound call that carries your content.
- **npm and a headless browser, on first render.** Remotion installs its
  dependencies and a Chromium build the first time a project renders.
- **The Inter font, from Google Fonts, at render time.** Remotion fetches it
  when the zone is rendered.

## What stays local

- **The video itself.** It is never uploaded. Cutting, measuring, compositing,
  and the contact sheet all happen with local ffmpeg calls.
- **The finished files.** They are written next to your video and nowhere else.
- **Your API key.** It lives in `~/.config/cut/.env` (mode `0600`), or in
  `~/.config/watch/.env` if you already use the `watch` skill. It is never
  printed, logged, or written into an output file.

## Rules of thumb

- **Never commit `.env`.** It is already in `.gitignore`.
- **Blur what should not be read.** The `Mosaic` block exists for full prompts,
  keys, and private paths that appear in a screen recording. Use it.
- **The skill sends nothing to anyone.** It does not post, upload, or message.
  The last thing it does is print file paths.

## Reporting a vulnerability

Please report security issues privately through
[GitHub Security Advisories](https://github.com/epictaste/claude-cut/security/advisories/new)
rather than in a public issue.
