// Everything the animation zone needs to stay in sync with the take.
//
// Fill this in from the script output:
//   zone.py  -> ZONE
//   words.py -> words.json, PARTS, START
//   cut.py   -> VERSIONS
//
// The placeholder values below belong to the example part and exist so the
// template compiles and renders before you have touched anything.
import words from './words.json';

/** Size of the animation zone. Width is the video width, height comes from zone.py. */
export const ZONE = {width: 1080, height: 855} as const;

export const FPS = 30;

/** Length of each part in frames. Parts run back to back and cover the whole cut. */
export const PARTS = {
	hook: 90,
	example: 180,
} as const;

/** Absolute start frame of each part inside the cut (the running sum of PARTS). */
export const START = {
	hook: 0,
	example: 90,
} as const;

/**
 * One entry per cut version. `cut` is the file name inside public/, used by the
 * Check composition and by build.py.
 */
export const VERSIONS = {
	1: {durationInFrames: 270, cut: 'cut.mp4'},
} as const;

/** Set to true once sfx.py has written public/sfx/*.wav. */
export const SFX_READY = false;

export type PartName = keyof typeof PARTS;
export type Word = {word: string; frame: number; frameEnd: number};

/** Word level timestamps per part, frames relative to the start of the part. */
export const WORDS = words as Record<PartName, {durationFrames: number; words: Word[]}>;

/**
 * The frame a word is spoken on, inside its part.
 *
 * This is the only way a part should pick a frame. Guessed times drift against
 * the take; a word does not. `from` skips ahead when a word occurs more than
 * once ("and" in the middle of a sentence, for example).
 *
 * Throws when the word is not in the transcript, which is deliberate: a silent
 * fallback to frame 0 would look like a working animation and be wrong.
 */
export const wordFrame = (part: PartName, word: string, from = 0): number => {
	const wanted = word.toLowerCase().replace(/[.,?!:;]/g, '');
	const hit = WORDS[part].words.find(
		(entry) => entry.frame >= from && entry.word.toLowerCase().replace(/[.,?!:;]/g, '') === wanted,
	);
	if (!hit) {
		throw new Error(
			`word "${word}" not found in part "${part}" at or after frame ${from}. ` +
				`Check words.json for how the transcript actually spells it.`,
		);
	}
	return hit.frame;
};

/** Last frame of a word, for animations that should end when a word ends. */
export const wordEnd = (part: PartName, word: string, from = 0): number => {
	const start = wordFrame(part, word, from);
	const hit = WORDS[part].words.find((entry) => entry.frame === start);
	return hit ? hit.frameEnd : start;
};
