// Beispielszene der Vorlage, zeigt die Regeln aus referenz/regeln-grafiken.md im Kleinen:
// ein Vorgang statt Text (Dateien wandern in einen Ordner, Häkchen), bekannte Dinge statt Kästchen,
// jeder Schritt hängt an einem gesprochenen Wort, ab Frame 0 ist etwas zu sehen, nichts steht lange still.
// Im echten Projekt löschen oder überschreiben. Neue Szenen schreibt Claude als szenen/teil-<name>.tsx.
import React from 'react';
import {useCurrentFrame} from 'remotion';

import {DateiIcon, type DateiTyp, Haekchen, Scharf, Voll, ein, weich} from '../bausteine';
import {type Cue, klemm} from '../geteilt';
import type {Marken, SzenenProps} from '../reel';

const DATEIEN: DateiTyp[] = ['video', 'bild', 'text', 'tabelle'];

/** Die Wortmarken der Szene in zeitlicher Reihenfolge, damit das Beispiel mit jedem Transkript läuft. */
const takte = (m: Marken): number[] => Object.values(m).sort((a, b) => a - b);

export const BeispielSzene: React.FC<SzenenProps> = ({m, dauer}) => {
	const f = useCurrentFrame();
	const t = takte(m);
	const flug = (i: number): number => t[Math.min(t.length - 1, i * 2 + 1)] ?? i * 12;
	const fertig = Math.min(dauer - 15, (t[t.length - 1] ?? dauer) - 5);
	return (
		<Voll>
			<div style={{position: 'relative', width: 900, height: 900}}>
				<div style={{position: 'absolute', left: 290, top: 520, transform: `scale(${1 + 0.06 * Math.sin(ein(f, fertig, 10) * Math.PI)})`}}>
					<DateiIcon typ="ordner" groesse={320} />
				</div>
				{DATEIEN.map((typ, i) => {
					const p = weich(klemm(f, [flug(i), flug(i) + 14], [0, 1]));
					const x = 60 + i * 200;
					return (
						<div key={typ} style={{position: 'absolute', left: x + (390 - x) * p, top: 120 + 460 * p, transform: `scale(${1 - 0.5 * p})`, opacity: p >= 1 ? 0 : 1}}>
							<DateiIcon typ={typ} groesse={150} />
						</div>
					);
				})}
				<Scharf von={fertig} style={{position: 'absolute', left: 560, top: 470}}>
					<Haekchen groesse={140} p={klemm(f, [fertig, fertig + 12], [0, 1])} />
				</Scharf>
			</div>
		</Voll>
	);
};

export const BeispielCues = (m: Marken, dauer: number): Cue[] => {
	const t = takte(m);
	const fluege = DATEIEN.map((_, i) => ({frame: (t[Math.min(t.length - 1, i * 2 + 1)] ?? i * 12) + 12, sound: 'whoosh' as const}));
	// Bei wenigen Wortmarken fliegen mehrere Dateien auf derselben Marke los: dann ein Whoosh, nicht mehrere übereinander.
	const einzeln = fluege.filter((c, i) => fluege.findIndex((x) => x.frame === c.frame) === i);
	return [...einzeln, {frame: Math.min(dauer - 15, (t[t.length - 1] ?? dauer) - 5), sound: 'click'}];
};
