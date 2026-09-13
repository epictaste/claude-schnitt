// Sound effect track. Each part exports its own cues with frames relative to
// the part; this file shifts them onto the timeline of the whole version.
//
// The sounds are synthesized by scripts/sfx.py into public/sfx/. Until that has
// run, SFX_READY in timing.ts stays false and this renders nothing, so a render
// never fails over a missing wav file.
import React from 'react';
import {Audio, Sequence, staticFile} from 'remotion';

import {SFX_READY} from './timing';

export type Sound = 'click' | 'tick' | 'pop' | 'whoosh' | 'ding' | 'type';

/** One hit. `frame` is relative to the part, `gain` scales the base volume. */
export type Cue = {frame: number; sound: Sound; gain?: number};

/** Base volume per sound. The wav files are already normalized to fixed peaks. */
const VOLUME: Record<Sound, number> = {
	click: 1,
	tick: 1,
	pop: 1,
	whoosh: 1,
	ding: 0.9,
	type: 1,
};

/** How long each cue stays mounted, in frames. */
const LENGTH: Record<Sound, number> = {
	click: 3,
	tick: 3,
	pop: 4,
	whoosh: 10,
	ding: 8,
	type: 2,
};

/** A row of keystrokes for a typing reveal. Capped, because it gets noisy fast. */
export const typeTicks = (from: number, count: number, step = 4): Cue[] =>
	Array.from({length: Math.min(count, 12)}, (_, index) => ({
		frame: from + index * step,
		sound: 'type' as Sound,
	}));

export const SfxTrack: React.FC<{tracks: {offset: number; cues: Cue[]}[]}> = ({tracks}) => {
	if (!SFX_READY) {
		return null;
	}
	return (
		<>
			{tracks.flatMap(({offset, cues}) =>
				cues.map((cue, index) => (
					<Sequence
						key={`${offset}-${index}-${cue.frame}`}
						from={offset + cue.frame}
						durationInFrames={LENGTH[cue.sound]}
					>
						<Audio src={staticFile(`sfx/${cue.sound}.wav`)} volume={VOLUME[cue.sound] * (cue.gain ?? 1)} />
					</Sequence>
				)),
			)}
		</>
	);
};
