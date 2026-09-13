// Everything the animation zone needs to stay in sync with the take.
//
// Fill this in from the script output:
//   zone.py  -> ZONE
//   words.py -> words.json
//   cut.py   -> VERSIONS
//
// The placeholder values below belong to the example parts and exist so the
// template compiles and renders before you have touched anything.
import words from './words.json';

/** Size of the animation zone. Width is the video width, height comes from zone.py. */
export const ZONE = {width: 1080, height: 855} as const;

/**
 * Frames per second. The scripts refuse any take that is not constant 30 fps,
 * so this is a constant, not a setting.
 */
export const FPS = 30;

export type PartName = keyof typeof words;
export type Word = {word: string; frame: number; frameEnd: number};

/** Word level timestamps per part, frames relative to the start of the part. */
export const WORDS = words as Record<PartName, {durationFrames: number; words: Word[]}>;

/** One part inside a version: which part, and how many frames it runs. */
export type LayoutEntry = {part: PartName; frames: number};

export type Version = {cut: string; layout: readonly LayoutEntry[]};

/**
 * One entry per cut version, straight out of cut.py.
 *
 * `cut` is the file name inside public/. `layout` lists the parts of that
 * version in order, so versions can differ in structure and not just in
 * content: a shorter hook, an extra beat, a part left out.
 *
 *   2: {cut: 'v2.mp4', layout: [{part: 'hookB', frames: 135}, {part: 'body', frames: 230}]},
 */
export const VERSIONS: Record<number, Version> = {
	1: {
		cut: 'cut.mp4',
		layout: [
			{part: 'hook', frames: 90},
			{part: 'example', frames: 180},
		],
	},
};

/** Set to true once sfx.py has written public/sfx/*.wav. */
export const SFX_READY = false;

/** A part placed on the timeline of one version. */
export type PlacedPart = {part: PartName; from: number; frames: number};

/**
 * The parts of a version with their start frames, as a running sum.
 *
 * Also where a drifting project gets caught: a part length that does not match
 * `words.json` throws here, instead of silently shifting every animation after
 * it by a few frames.
 */
export const versionLayout = (version: number): PlacedPart[] => {
	const entry = VERSIONS[version];
	if (!entry) {
		throw new Error(`version ${version} is not in VERSIONS`);
	}
	let from = 0;
	return entry.layout.map((item) => {
		const known = WORDS[item.part];
		if (!known) {
			throw new Error(`part "${item.part}" of version ${version} is not in words.json`);
		}
		if (known.durationFrames !== item.frames) {
			throw new Error(
				`part "${item.part}" is ${item.frames} frames in VERSIONS but ${known.durationFrames} ` +
					`in words.json. Re-run words.py and cut.py with the same ranges.`,
			);
		}
		const placed: PlacedPart = {part: item.part, from, frames: item.frames};
		from += item.frames;
		return placed;
	});
};

/** Total length of a version, which has to match the frame count of its cut. */
export const versionDuration = (version: number): number =>
	versionLayout(version).reduce((total, placed) => total + placed.frames, 0);

/** Start frame of a part inside a version, for rendering stills at absolute frames. */
export const partStart = (version: number, part: PartName): number => {
	const placed = versionLayout(version).find((item) => item.part === part);
	if (!placed) {
		throw new Error(`part "${part}" is not in version ${version}`);
	}
	return placed.from;
};

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
