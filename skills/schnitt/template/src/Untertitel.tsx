// Untertitel wortgenau aus den Wortzeiten. Höchstens zwei Wörter pro Bild, immer eine Zeile, Satzzeichen sind eine Grenze.
// Ein langes Wort (ab 9 Buchstaben) und ein Schlüsselwort stehen allein. Nichts steht über einen Take-Schnitt hinweg.
// Die Lage folgt dem Zoom: unter dem Kinn, im Vollbild fest auf STIL.untertitel.vollbildY.
import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';

import K from './korrektur.json';
import {BODY_WOERTER, HOOK, HOOK_WOERTER, KOPF_Y, TAKE_SCHNITTE, type Version, type Wort} from './reel';
import {SCHRIFT, STIL} from './stil';

type Gr = 's' | 'm' | 'l' | 'xl';
const STUFEN: Gr[] = ['s', 'm', 'l', 'xl'];
const MAX_BREITE = 900;
const KORREKTUR = K.korrektur as Record<string, string>;
const GROSS = K.gross as Record<string, Gr>;

/** Kinn liegt rund 330 px unter der Kopf-Oberkante. `anker` = Höhe, von der aus der Zoom wächst, `versatz` = Verschiebung der Videoebene. */
export const untertitelY = (zoom: number, anker = 0, versatz = 0): number => Math.round(anker + versatz + (KOPF_Y + 330 - anker) * zoom + STIL.untertitel.abstandKinn);

export type HWort = {t: string; von: number; gr: Gr};
const kern = (w: string): string => {
	const m = w.match(/^(.*?)([.,!?:;]*)$/);
	const k = m ? m[1] : w;
	return KORREKTUR[k] ?? k;
};
const stufe = (t: string): Gr => GROSS[t] ?? (t.length <= 3 ? 's' : t.length >= 8 ? 'l' : 'm');
const gross = (x: HWort): boolean => STIL.untertitel.modus === 'springend' && (x.gr === 'l' || x.gr === 'xl');
const px = (x: HWort): number => (STIL.untertitel.modus === 'springend' ? STIL.untertitel.groessen[STUFEN.indexOf(x.gr)] : STIL.untertitel.einheitlich);

/** Ein Wortanfang bis 3 Frames vor einem Take-Schnitt gehört schon zum neuen Clip (Anlaute werden oft etwas früh erkannt). */
const aufSchnitt = (von: number, schnitte: number[]): number => schnitte.find((c) => c - von > 0 && c - von <= 3) ?? von;
const schnittDazwischen = (a: number, b: number, schnitte: number[]): boolean => schnitte.some((c) => c > a && c <= b);

export const haeppchen = (W: Wort[], o: number, schnitte: number[] = []): HWort[][] => {
	const aus: HWort[][] = [];
	let i = 0;
	while (i < W.length) {
		const ta = kern(W[i].w);
		const a: HWort = {t: ta, von: aufSchnitt(W[i].von + o, schnitte), gr: stufe(ta)};
		const tb = W[i + 1] ? kern(W[i + 1].w) : '';
		const b: HWort | null = W[i + 1] ? {t: tb, von: aufSchnitt(W[i + 1].von + o, schnitte), gr: stufe(tb)} : null;
		const satzEnde = /[.,!?:;]$/.test(W[i].w);
		const paar = !!b && !satzEnde && !schnittDazwischen(a.von, b.von, schnitte) && !(gross(a) && gross(b)) && a.t.length < 9 && b.t.length < 9 && a.t.length + b.t.length <= 14;
		aus.push(paar && b ? [a, b] : [a]);
		i += paar ? 2 : 1;
	}
	return aus;
};

/** Alle Häppchen einer Version auf Reel-Frames: Hook ab 0, Body ab HOOK[version]. */
export const liste = (version: Version): HWort[][] => {
	const sch = TAKE_SCHNITTE[version];
	return [...haeppchen(HOOK_WOERTER[version], 0, sch), ...haeppchen(BODY_WOERTER, HOOK[version], sch)];
};

/** Ein Untertitel-Bild. `frame` zählt ab dem ersten Wort, damit jedes Wort kurz aus der Unschärfe kommt. */
export const UntertitelBild: React.FC<{woerter: HWort[]; frame: number; y: number}> = ({woerter, frame, y}) => {
	const b0 = woerter.reduce((sum, w) => sum + px(w) * (w.t.length * (gross(w) ? 0.74 : 0.56) + 0.3), 0);
	const k = Math.min(1, MAX_BREITE / b0);
	return (
		<div style={{position: 'absolute', top: y, left: 40, right: 40, display: 'flex', justifyContent: 'center'}}>
			<div style={{display: 'flex', alignItems: 'baseline', gap: 22 * k, lineHeight: 1.02, whiteSpace: 'nowrap'}}>
				{woerter.map((w, i) => {
					const g = gross(w);
					const d = frame - w.von;
					const groesse = px(w) * k;
					const gewicht = g ? 900 : w.gr === 'm' ? 700 : 600;
					if (d < 0) return <span key={i} style={{visibility: 'hidden', fontSize: groesse, fontFamily: SCHRIFT.untertitel, fontWeight: gewicht}}>{g ? w.t.toUpperCase() : w.t}</span>;
					const blur = interpolate(d, [0, 4], [12, 0], {extrapolateRight: 'clamp'});
					const s = interpolate(d, [0, 5], [g ? 1.14 : 1.08, 1], {extrapolateRight: 'clamp'});
					return (
						<span key={i} style={{fontFamily: SCHRIFT.untertitel, fontWeight: gewicht, fontSize: groesse, color: STIL.farben.text, textTransform: g ? 'uppercase' : undefined,
							opacity: g ? 1 : 0.94, filter: blur < 0.3 ? undefined : `blur(${blur}px)`, transform: `scale(${s})`, display: 'inline-block', textShadow: '0 3px 18px rgba(0,0,0,0.7)'}}>{w.t}</span>
					);
				})}
			</div>
		</div>
	);
};

export const Untertitel: React.FC<{version: Version; zoom: number; anker?: number; versatz?: number; y?: number}> = ({version, zoom, anker = 0, versatz = 0, y}) => {
	const frame = useCurrentFrame();
	const alle = liste(version);
	const hi = alle.findIndex((h, i) => frame >= h[0].von && (i === alle.length - 1 || frame < alle[i + 1][0].von));
	if (hi < 0) return null;
	// Untertitel wechseln mit dem Schnitt, nichts steht über einen Take-Schnitt hinweg
	if (schnittDazwischen(alle[hi][0].von, frame, TAKE_SCHNITTE[version])) return null;
	return <UntertitelBild woerter={alle[hi]} frame={frame} y={y ?? untertitelY(zoom, anker, versatz)} />;
};

/** Für Standbilder (Stilprobe): ein fester Text als fertig eingeblendetes Untertitel-Bild. */
export const probeHaeppchen = (text: string): HWort[] => {
	const w = text.split(/\s+/).filter(Boolean).map((t, i) => ({w: t, von: i, bis: i + 1}));
	return (haeppchen(w, -100)[0] ?? []);
};
