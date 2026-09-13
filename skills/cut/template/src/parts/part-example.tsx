// Part "example": a small mock terminal, built the way every part should be.
//
// What it demonstrates:
//   - every change sits on wordFrame(...), never on a guessed frame
//   - a mock interface instead of a row of text chips
//   - a reveal that keeps moving (typing, then a check mark, then a hard cut)
//   - Mosaic over the part of the command that should stay unreadable
//   - Emphasis used for a number, which is the only thing it is for
//
// Delete this file once your own parts exist.
import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';

import {
	Badge,
	COLORS,
	Card,
	Emphasis,
	MAX_GRAPHIC_WIDTH,
	Mosaic,
	Scene,
	Typing,
	UI_FONT,
} from '../blocks';
import type {Cue} from '../sfx';
import {typeTicks} from '../sfx';
import {wordFrame} from '../timing';

const at = (word: string, from = 0) => wordFrame('example', word, from);

const CARD_WIDTH = MAX_GRAPHIC_WIDTH;
const CARD_HEIGHT = 300;
const CARD_Y = 280;

const COMMAND = 'npx create-thing';

export const ExampleCues: Cue[] = [
	{frame: 0, sound: 'pop'},
	...typeTicks(at('run'), 8),
	{frame: at('installs'), sound: 'ding'},
	{frame: at('five'), sound: 'click'},
	{frame: at('done'), sound: 'pop'},
];

const Check: React.FC<{from: number}> = ({from}) => {
	const frame = useCurrentFrame();
	if (frame < from) {
		return null;
	}
	const settle = interpolate(frame - from, [0, 3], [1.2, 1], {extrapolateRight: 'clamp'});
	return (
		<span style={{color: COLORS.green, fontSize: 34, transform: `scale(${settle})`, display: 'inline-block'}}>
			✓
		</span>
	);
};

export const ExamplePart: React.FC = () => {
	const frame = useCurrentFrame();
	const switchFrame = at('five');
	const mosaicFrom = at('command');

	if (frame >= switchFrame) {
		return (
			<Scene>
				<Emphasis text="5 SEC" from={switchFrame} y={CARD_Y} />
				<div style={{position: 'absolute', left: 0, right: 0, top: 700, textAlign: 'center'}}>
					<Badge text="installed" from={at('done')} />
				</div>
			</Scene>
		);
	}

	return (
		<Scene>
			<Card width={CARD_WIDTH} height={CARD_HEIGHT} y={CARD_Y}>
				<div
					style={{
						display: 'flex',
						alignItems: 'center',
						gap: 12,
						padding: '20px 28px',
						borderBottom: '1px solid rgba(255,255,255,0.10)',
						fontFamily: UI_FONT,
						fontSize: 26,
						color: COLORS.gray,
					}}
				>
					<span style={{width: 14, height: 14, borderRadius: 7, backgroundColor: COLORS.grayDark}} />
					<span style={{width: 14, height: 14, borderRadius: 7, backgroundColor: COLORS.grayDark}} />
					<span style={{width: 14, height: 14, borderRadius: 7, backgroundColor: COLORS.grayDark}} />
					<span style={{marginLeft: 10}}>terminal</span>
				</div>
				<div style={{padding: '30px 28px', fontFamily: UI_FONT, fontSize: 34, lineHeight: 1.5}}>
					<div>
						<span style={{color: COLORS.accent}}>$ </span>
						<Typing text={COMMAND} from={at('run')} />
						{frame >= mosaicFrom ? (
							<span style={{display: 'inline-block', verticalAlign: '-6px', marginLeft: 10}}>
								<Mosaic width={190} height={30} cell={10} />
							</span>
						) : null}
					</div>
					<div style={{marginTop: 22, color: COLORS.gray}}>
						<Check from={at('installs')} />
						{frame >= at('installs') ? <span style={{marginLeft: 12}}>ready</span> : null}
					</div>
				</div>
			</Card>
		</Scene>
	);
};
