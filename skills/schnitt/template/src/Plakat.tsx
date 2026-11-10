// Text-Hook als Plakat: steht ab Frame 0 komplett, bis zum ersten harten Schnitt (SATZ2).
// Zeilen sind einfache Texte. Ein Logo aus public/logos/ kommt mit [logo:datei.png] in die Zeile,
// es steht auf der Schreiblinie und ist etwas höher als die Versalien.
import React from 'react';
import {Img, staticFile} from 'remotion';

import {SCHRIFT, STIL} from './stil';

type Teil = {text: string} | {logo: string};

const zerlege = (zeile: string): Teil[] =>
	zeile.split(/(\[logo:[^\]]+\])/).filter(Boolean).map((t) => {
		const m = t.match(/^\[logo:([^\]]+)\]$/);
		return m ? {logo: m[1].trim()} : {text: t};
	});

/** Kontur über Schatten in 16 Richtungen, frisst die Buchstaben nicht an wie text-stroke. */
const kontur = (px: number, farbe: string): string =>
	Array.from({length: 16}, (_, i) => {
		const w = (i / 16) * Math.PI * 2;
		return `${(Math.cos(w) * px).toFixed(2)}px ${(Math.sin(w) * px).toFixed(2)}px 0 ${farbe}`;
	}).join(', ');

// Grobe Breite einer Zeile in Schriftgrößen-Einheiten (breite Versalien-Schrift), damit nichts über den Rand läuft.
const breite = (teile: Teil[]): number =>
	teile.reduce((b, t) => b + ('text' in t ? t.text.length * (STIL.plakat.versalien ? 0.78 : 0.6) : 1.3), 0);

/** Schriftgröße je Zeile: höchstens STIL.plakat.groesse, kleiner, wenn die Zeile sonst breiter als maxBreite wäre. */
export const plakatGroesse = (zeile: string): number => Math.min(STIL.plakat.groesse, Math.floor(STIL.plakat.maxBreite / Math.max(1, breite(zerlege(zeile)))));

export const Plakat: React.FC<{zeilen: string[]; y?: number}> = ({zeilen, y = STIL.plakat.y}) => {
	const schatten = `${kontur(STIL.plakat.kontur, STIL.farben.plakatKontur)}, 0 6px 0 rgba(0,0,0,0.35)`;
	const cap = 0.7;
	return (
		<div style={{position: 'absolute', top: y, left: 0, right: 0, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
			{zeilen.map((zeile, i) => {
				const gr = plakatGroesse(zeile);
				return (
					<div key={i} style={{fontFamily: SCHRIFT.plakat, fontWeight: 900, fontSize: gr, lineHeight: 1.04, letterSpacing: '-0.01em', whiteSpace: 'nowrap',
						textAlign: 'center', color: STIL.farben.plakat, textShadow: schatten, textTransform: STIL.plakat.versalien ? 'uppercase' : 'none'}}>
						{zerlege(zeile).map((t, k) => {
							if ('text' in t) return <span key={k}>{t.text}</span>;
							const h = gr * cap * 1.3;
							return (
								<Img key={k} src={staticFile(`logos/${t.logo}`)} style={{display: 'inline-block', width: h, height: h, objectFit: 'contain', verticalAlign: 'baseline',
									marginBottom: -gr * cap * 0.15, marginRight: gr * 0.08, borderRadius: h * 0.22, boxShadow: `0 0 0 3px ${STIL.farben.plakatKontur}, 0 6px 0 rgba(0,0,0,0.3)`}} />
							);
						})}
					</div>
				);
			})}
		</div>
	);
};
