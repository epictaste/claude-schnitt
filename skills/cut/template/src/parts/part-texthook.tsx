// Part "hook": the text hook poster.
//
// The poster is complete from frame 0 and stays. Underneath it, three slots
// fill in on the words that are actually spoken, so the part is never static
// but also never spoils what the video is about to reveal.
//
// Replace the two poster lines with your own. Everything else can stay.
import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';

import {COLORS, INTER_BLACK, POSTER_CONTENT_Y, Scene, TextHook, centerX} from '../blocks';
import type {Cue} from '../sfx';
import {wordFrame} from '../timing';

const at = (word: string, from = 0) => wordFrame('hook', word, from);

const SLOT_SIZE = 150;
const SLOT_GAP = 40;
const SLOT_COUNT = 3;

/** The words the three slots land on. */
const SLOT_WORDS = ['goes', 'here', 'Replace'] as const;

export const HookCues: Cue[] = [
	{frame: 0, sound: 'whoosh'},
	...SLOT_WORDS.map((word) => ({frame: at(word), sound: 'tick' as const})),
	{frame: at('file'), sound: 'pop'},
];

const Slot: React.FC<{index: number; filledFrom: number}> = ({index, filledFrom}) => {
	const frame = useCurrentFrame();
	const filled = frame >= filledFrom;
	const settle = interpolate(frame - filledFrom, [0, 3], [1.1, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const rowWidth = SLOT_COUNT * SLOT_SIZE + (SLOT_COUNT - 1) * SLOT_GAP;
	return (
		<div
			style={{
				position: 'absolute',
				left: centerX(rowWidth) + index * (SLOT_SIZE + SLOT_GAP),
				top: POSTER_CONTENT_Y,
				width: SLOT_SIZE,
				height: SLOT_SIZE,
				borderRadius: 18,
				border: `4px solid ${filled ? COLORS.accent : COLORS.grayDark}`,
				backgroundColor: filled ? COLORS.accent : 'transparent',
				boxShadow: '4px 5px 0 #000000',
				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',
				fontFamily: INTER_BLACK,
				fontWeight: 900,
				fontSize: 74,
				color: COLORS.white,
				transform: filled ? `scale(${settle})` : 'none',
			}}
		>
			{filled ? index + 1 : ''}
		</div>
	);
};

export const HookPart: React.FC = () => (
	<Scene>
		<TextHook line1="YOUR TEXT HOOK" line2="GOES RIGHT HERE" accent="HOOK" />
		{SLOT_WORDS.map((word, index) => (
			<Slot key={word} index={index} filledFrom={at(word)} />
		))}
	</Scene>
);
