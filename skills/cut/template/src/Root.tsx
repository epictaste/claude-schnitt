// Compositions, one pair per version:
//   Top-V<N>    the zone itself, zone sized, this is what gets rendered
//   Check-V<N>  the zone over the cut, full frame, for stills
//
// Both are generated from VERSIONS in timing.ts, so adding a version there is
// all it takes.
import React from 'react';
import {Composition} from 'remotion';

import {Check, Top} from './Top';
import {FPS, VERSIONS, ZONE} from './timing';

const FULL_FRAME = {width: 1080, height: 1920};

export const RemotionRoot: React.FC = () => (
	<>
		{Object.entries(VERSIONS).map(([key, entry]) => {
			const version = Number(key);
			return (
				<React.Fragment key={key}>
					<Composition
						id={`Top-V${version}`}
						component={Top}
						durationInFrames={entry.durationInFrames}
						fps={FPS}
						width={ZONE.width}
						height={ZONE.height}
						defaultProps={{version}}
					/>
					<Composition
						id={`Check-V${version}`}
						component={Check}
						durationInFrames={entry.durationInFrames}
						fps={FPS}
						width={FULL_FRAME.width}
						height={FULL_FRAME.height}
						defaultProps={{version}}
					/>
				</React.Fragment>
			);
		})}
	</>
);
