// The animation zone, assembled from the parts of one version, plus the check
// composite.
//
// `Top` is what gets rendered and laid over the cut: zone sized, nothing else.
// `Check` puts the same zone over the cut at full frame size, for stills that
// answer the only question that matters at the end: does the edge sit right and
// does the graphic match the sentence being spoken.
//
// Versions do not share a timeline. Each one has its own layout in timing.ts, so
// a version with a shorter hook shifts everything after it by exactly that
// difference and nothing else has to be touched.
import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, staticFile} from 'remotion';

import {VERSIONS, ZONE, versionLayout} from './timing';
import type {PartName} from './timing';
import {SfxTrack} from './sfx';
import type {Cue} from './sfx';
import {HookCues, HookPart} from './parts/part-texthook';
import {ExampleCues, ExamplePart} from './parts/part-example';

type PartEntry = {component: React.FC; cues: Cue[]};

/**
 * One entry per part that exists in words.json. A version picks its parts from
 * here by name; a hook that differs between versions is its own part with its
 * own file, not a variant of a shared one.
 */
const COMPONENTS: Record<PartName, PartEntry> = {
	hook: {component: HookPart, cues: HookCues},
	example: {component: ExamplePart, cues: ExampleCues},
};

export const Top: React.FC<{version: number}> = ({version}) => {
	const layout = versionLayout(version);
	return (
		<AbsoluteFill
			style={{
				width: ZONE.width,
				height: ZONE.height,
				overflow: 'hidden',
				backgroundColor: '#050505',
			}}
		>
			{layout.map(({part, from, frames}) => {
				const Part = COMPONENTS[part].component;
				return (
					<Sequence key={part} from={from} durationInFrames={frames}>
						<Part />
					</Sequence>
				);
			})}
			<SfxTrack
				tracks={layout.map(({part, from}) => ({offset: from, cues: COMPONENTS[part].cues}))}
			/>
		</AbsoluteFill>
	);
};

/** Zone over the cut, full frame. Stills only, this is slow to render. */
export const Check: React.FC<{version: number}> = ({version}) => {
	const entry = VERSIONS[version];
	if (!entry) {
		throw new Error(`version ${version} is not in VERSIONS`);
	}
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
