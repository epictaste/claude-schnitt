// The shared building blocks every part uses. Import them, never copy them:
// that is what keeps the look identical across parts, so nothing jumps at a
// part boundary.
//
// There is deliberately no `Title` block. A headline that repeats the spoken
// sentence is the most common way these videos go wrong. Text on screen is for
// what the voice does not say: a number, a date, a name, a measured value.
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';

import {ZONE} from './timing';

/**
 * The single accent color. Change this one line to rebrand the whole zone.
 * Default is the terracotta used by the reference build.
 */
export const ACCENT = '#D97757';

export const COLORS = {
	bg: '#0A0A0A',
	white: '#FFFFFF',
	gray: '#9C9C9C',
	grayDark: '#3A3A3A',
	card: '#161616',
	accent: ACCENT,
	/** Only for check marks inside mock interfaces, never as a second accent. */
	green: '#5FB37A',
} as const;

/** Hard drop shadow. No blur, no glow, no gradient anywhere in this look. */
export const HARD_SHADOW = '5px 6px 0 #000000';

/** Inter Black for headlines and emphasis words. */
export const INTER_BLACK = loadInter('normal', {
	weights: ['900'],
	subsets: ['latin'],
	ignoreTooManyRequestsWarning: true,
}).fontFamily;

/** Inter regular weights for mock interface text. */
export const UI_FONT = loadInter('normal', {
	weights: ['400', '500', '600'],
	subsets: ['latin'],
	ignoreTooManyRequestsWarning: true,
}).fontFamily;

/** The top strip is covered by the platform header. Keep it empty. */
export const HEADER_SAFE = 180;

/** Widest a core graphic may be, centered, so it never crowds the edges. */
export const MAX_GRAPHIC_WIDTH = 760;

/** Vertical band a graphic lives in when there is no poster above it. */
export const CONTENT_Y = 290;
export const CONTENT_H = 500;

/** Text hook poster: the headline sits here, the animation starts below it. */
export const POSTER_Y = 200;
export const POSTER_CONTENT_Y = 450;

/** Seconds to frames at 30 fps. */
export const S = (seconds: number) => Math.round(seconds * 30);

/** Centered left offset for a box of a given width. */
export const centerX = (width: number) => Math.round((ZONE.width - width) / 2);

/**
 * Scene background: solid black plus a very slow push in. The drift is there so
 * a scene is never fully static, even while a reveal waits for the next word.
 */
export const Scene: React.FC<{children: React.ReactNode}> = ({children}) => {
	const frame = useCurrentFrame();
	return (
		<AbsoluteFill style={{overflow: 'hidden', backgroundColor: COLORS.bg}}>
			<div
				style={{
					position: 'absolute',
					inset: 0,
					transform: `scale(${1 + frame * 0.0004})`,
					transformOrigin: 'center 45%',
				}}
			>
				{children}
			</div>
		</AbsoluteFill>
	);
};

/**
 * A single huge word or number, centered. Use it for numbers: a count, a
 * percentage, a factor. Not for adjectives, and not for words the voice is
 * already saying with emphasis.
 */
export const Emphasis: React.FC<{
	text: string;
	from?: number;
	to?: number;
	size?: number;
	color?: string;
	y?: number;
}> = ({text, from = 0, to, size = 190, color = COLORS.white, y = CONTENT_Y}) => {
	const frame = useCurrentFrame();
	if (frame < from || (to !== undefined && frame >= to)) {
		return null;
	}
	const settle = interpolate(frame - from, [0, 3], [1.08, 1], {extrapolateRight: 'clamp'});
	return (
		<div
			style={{
				position: 'absolute',
				left: 40,
				right: 40,
				top: y,
				height: CONTENT_H,
				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',
				textAlign: 'center',
				fontFamily: INTER_BLACK,
				fontWeight: 900,
				fontSize: size,
				lineHeight: 1,
				letterSpacing: -2,
				textTransform: 'uppercase',
				color,
				textShadow: '7px 8px 0 #000000',
				transform: `scale(${settle})`,
			}}
		>
			{text}
		</div>
	);
};

/**
 * A small pill label. Three frames of settle instead of a spring, so it lands
 * hard like a stamp.
 */
export const Badge: React.FC<{
	text: string;
	from?: number;
	to?: number;
	color?: string;
	size?: number;
}> = ({text, from = 0, to, color = COLORS.accent, size = 40}) => {
	const frame = useCurrentFrame();
	if (frame < from || (to !== undefined && frame >= to)) {
		return null;
	}
	const settle = interpolate(frame - from, [0, 3], [1.08, 1], {extrapolateRight: 'clamp'});
	return (
		<div
			style={{
				display: 'inline-block',
				padding: `${size * 0.36}px ${size * 0.7}px`,
				borderRadius: size * 0.32,
				border: `3px solid ${color}`,
				backgroundColor: color === COLORS.accent ? COLORS.accent : 'transparent',
				boxShadow: '4px 5px 0 #000000',
				transform: `scale(${settle})`,
				fontFamily: INTER_BLACK,
				fontWeight: 900,
				fontSize: size,
				letterSpacing: 1,
				textTransform: 'uppercase',
				color: COLORS.white,
				whiteSpace: 'nowrap',
			}}
		>
			{text}
		</div>
	);
};

/** Dark panel: the base for a terminal, a chat window, a file card. */
export const Card: React.FC<{
	width: number;
	height: number;
	x?: number;
	y?: number;
	from?: number;
	to?: number;
	border?: string;
	children: React.ReactNode;
}> = ({
	width,
	height,
	x,
	y = CONTENT_Y,
	from = 0,
	to,
	border = 'rgba(255,255,255,0.12)',
	children,
}) => {
	const frame = useCurrentFrame();
	if (frame < from || (to !== undefined && frame >= to)) {
		return null;
	}
	const settle = interpolate(frame - from, [0, 3], [1.04, 1], {extrapolateRight: 'clamp'});
	return (
		<div
			style={{
				position: 'absolute',
				left: x ?? centerX(width),
				top: y,
				width,
				height,
				borderRadius: 26,
				border: `1.5px solid ${border}`,
				backgroundColor: COLORS.card,
				boxShadow: '0 30px 80px rgba(0,0,0,0.6)',
				overflow: 'hidden',
				transform: `scale(${settle})`,
				fontFamily: UI_FONT,
				color: '#F3F1EA',
			}}
		>
			{children}
		</div>
	);
};

/** Text that types itself in, character by character. */
export const Typing: React.FC<{
	text: string;
	from: number;
	perCharacter?: number;
	style?: React.CSSProperties;
}> = ({text, from, perCharacter = 1.2, style}) => {
	const frame = useCurrentFrame();
	const shown = Math.max(0, Math.min(text.length, Math.floor((frame - from) / perCharacter)));
	return <span style={style}>{text.slice(0, shown)}</span>;
};

/**
 * Pixel mosaic. Put this over anything that should stay unreadable: a full
 * prompt, a key, a private path. Leave the first line readable so the viewer
 * still understands what kind of text it is.
 */
export const Mosaic: React.FC<{width: number; height: number; cell?: number; seed?: number}> = ({
	width,
	height,
	cell = 22,
	seed = 1,
}) => {
	const columns = Math.ceil(width / cell);
	const rows = Math.ceil(height / cell);
	const tiles: React.ReactNode[] = [];
	for (let row = 0; row < rows; row++) {
		for (let column = 0; column < columns; column++) {
			const shade = ((row * 31 + column * 17 + seed * 7) % 23) / 23;
			tiles.push(
				<div
					key={`${row}-${column}`}
					style={{
						position: 'absolute',
						left: column * cell,
						top: row * cell,
						width: cell,
						height: cell,
						backgroundColor: `rgba(200,200,215,${0.12 + shade * 0.4})`,
					}}
				/>,
			);
		}
	}
	return <div style={{position: 'relative', width, height, overflow: 'hidden'}}>{tiles}</div>;
};

/**
 * Text hook poster: two lines, complete from frame 0, standing at least three
 * seconds. Building it word by word looks livelier and reads worse, because the
 * full sentence is only on screen for a moment.
 *
 * `accent` is the one substring that turns accent colored. It has to appear in
 * one of the two lines, otherwise the line renders plain.
 */
export const TextHook: React.FC<{
	line1: string;
	line2: string;
	accent?: string;
	size?: number;
}> = ({line1, line2, accent, size = 84}) => {
	const frame = useCurrentFrame();
	const settle = interpolate(frame, [0, 3], [1.06, 1], {extrapolateRight: 'clamp'});

	const paint = (line: string) => {
		if (!accent || !line.includes(accent)) {
			return line;
		}
		const [before, after] = line.split(accent);
		return (
			<>
				{before}
				<span style={{color: COLORS.accent}}>{accent}</span>
				{after}
			</>
		);
	};

	return (
		<div
			style={{
				position: 'absolute',
				left: 70,
				right: 70,
				top: POSTER_Y,
				textAlign: 'center',
				fontFamily: INTER_BLACK,
				fontWeight: 900,
				fontSize: size,
				textTransform: 'uppercase',
				letterSpacing: -2,
				lineHeight: 1.1,
				color: COLORS.white,
				textShadow: HARD_SHADOW,
				whiteSpace: 'nowrap',
				transform: `scale(${settle})`,
			}}
		>
			<div>{paint(line1)}</div>
			<div>{paint(line2)}</div>
		</div>
	);
};
