// Kompositionen:
//   Reel-<v>    das fertige Video einer Version mit Take, 1080x1920. Das rendert bauen.sh.
//   Zone-<v>    dasselbe ohne Video, für schnelle Standbilder der Grafiken (Szenen-Agents).
//   Stilprobe   ein Standbild aus einem echten Frame mit Plakat, Zoom und Untertitel (Schritt 4), Props siehe Komposition.tsx.
// Alle Versionen kommen aus VERSIONEN in reel.ts, das geruest.py schreibt.
import React from 'react';
import {Composition} from 'remotion';

import {FPS, GESAMT, VERSIONEN} from './reel';
import {Reel, Stilprobe, type StilprobeProps} from './Komposition';

const STILPROBE: StilprobeProps = {
	bild: '',
	modus: 'weit',
	plakat: ['Dein Hook', 'in zwei Zeilen'],
	untertitel: 'Beispiel',
	zoom: 1.1,
	augenY: 1000,
	gesichtX: 540,
};

export const RemotionRoot: React.FC = () => (
	<>
		{VERSIONEN.map((v) => (
			<React.Fragment key={v}>
				<Composition id={`Reel-${v}`} component={Reel} defaultProps={{version: v, mitVideo: true}} durationInFrames={GESAMT[v]} fps={FPS} width={1080} height={1920} />
				<Composition id={`Zone-${v}`} component={Reel} defaultProps={{version: v, mitVideo: false}} durationInFrames={GESAMT[v]} fps={FPS} width={1080} height={1920} />
			</React.Fragment>
		))}
		<Composition id="Stilprobe" component={Stilprobe} defaultProps={STILPROBE} durationInFrames={1} fps={FPS} width={1080} height={1920} />
	</>
);
