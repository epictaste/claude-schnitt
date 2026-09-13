// The animation zone, assembled from the parts, plus the check composite.
//
// `Top` is what gets rendered and laid over the cut: zone sized, nothing else.
// `Check` puts the same zone over the cut at full frame size, for stills that
// answer the only question that matters at the end: does the edge sit right and
// does the graphic match the sentence being spoken.
import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, staticFile} from 'remotion';

import {PARTS, START, VERSIONS, ZONE} from './timing';
import type {PartName} from './timing';
import {SfxTrack} from './sfx';
import type {Cue} from './sfx';
import {HookCues, HookPart} from './parts/part-texthook';
import {ExampleCues, ExamplePart} from './parts/part-example';

export type VersionNumber = keyof typeof VERSIONS;

type PartEntry = {component: React.FC; cues: Cue[]};

/** One entry per part, in any order: START decides where each one lands. */
const DEFAULT_PARTS: Record<PartName, PartEntry> = {
	hook: {component: HookPart, cues: HookCues},
	example: {component: ExamplePart, cues: ExampleCues},
};

/**
 * Versions usually differ in one part only, most often the hook. Override just
 * that part here and leave the rest shared:
 *
 *   const VERSION_PARTS = {2: {hook: {component: HookPartB, cues: HookBCues}}};
 */
const VERSION_PARTS: Partial<Record<number, Partial<Record<PartName, PartEntry>>>> = {};

const partsFor = (version: number): Record<PartName, PartEntry> => ({
	...DEFAULT_PARTS,
	...(VERSION_PARTS[version] ?? {}),
});

export const Top: React.FC<{version: number}> = ({version}) => {
	const parts = partsFor(version);
	const names = Object.keys(PARTS) as PartName[];
	return (
		<AbsoluteFill
			style={{
				width: ZONE.width,
				height: ZONE.height,
				overflow: 'hidden',
				backgroundColor: '#050505',
			}}
		>
			{names.map((name) => {
				const Part = parts[name].component;
				return (
					<Sequence key={name} from={START[name]} durationInFrames={PARTS[name]}>
						<Part />
					</Sequence>
				);
			})}
			<SfxTrack tracks={names.map((name) => ({offset: START[name], cues: parts[name].cues}))} />
		</AbsoluteFill>
	);
};

/** Zone over the cut, full frame. Stills only, this is slow to render. */
export const Check: React.FC<{version: number}> = ({version}) => {
	const entry = VERSIONS[version as VersionNumber];
	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			<OffthreadVideo src={staticFile(entry.cut)} muted style={{width: '100%', height: '100%'}} />
			<div
				style={{
					position: 'absolute',
					left: 0,
					top: 0,
					width: ZONE.width,
					height: ZONE.height,
					overflow: 'hidden',
				}}
			>
				<Top version={version} />
			</div>
		</AbsoluteFill>
	);
};
