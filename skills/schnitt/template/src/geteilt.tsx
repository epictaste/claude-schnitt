// Kleine Helfer, die jede Szene braucht: Marken nachschlagen, Werte klemmen, Sound-Cues.
import {interpolate} from 'remotion';

import type {Marken} from './reel';

/** Frame eines gesprochenen Wortes, relativ zum Szenenstart. Wirft, wenn es das Wort in der Szene nicht gibt:
 * dann heißt es im Transkript anders (in reel.ts nachsehen) oder es wird in dieser Szene gar nicht gesagt. */
export const marke = (m: Marken, schluessel: string): number => {
	const f = m[schluessel];
	if (f === undefined) throw new Error(`Marke „${schluessel}“ fehlt. Vorhanden: ${Object.keys(m).join(', ')}`);
	return f;
};

/** interpolate mit Klemme auf beiden Seiten. */
export const klemm = (x: number, ein: number[], aus: number[], easing?: (t: number) => number): number =>
	interpolate(x, ein, aus, {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing});

export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

/** Sekunden in Frames bei 30 fps. */
export const S = (sekunden: number): number => Math.round(sekunden * 30);

/** Effekte, die scripts/sfx.py erzeugt. Riser und Whoosh am Hook setzt sfx_mix.py selbst, die gehören nicht in die Cues. */
export type Sound = 'click' | 'tick' | 'pop' | 'whoosh' | 'type';

/** Ein Sound-Einsatz, Frame relativ zur Szene. */
export type Cue = {frame: number; sound: Sound};

/** Tastenanschläge für eine Tipp-Animation, höchstens 12 pro Stelle. */
export const tippTicks = (von: number, anzahl: number, schritt = 4): Cue[] =>
	Array.from({length: Math.min(anzahl, 12)}, (_, i) => ({frame: von + i * schritt, sound: 'type' as Sound}));
