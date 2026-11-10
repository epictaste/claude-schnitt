// Das fertige Hochkant-Video, eine Komposition je Version (Root.tsx). Heißt nicht Reel.tsx, weil reel.ts daneben liegt und macOS Groß- und Kleinschreibung nicht unterscheidet.
// Satz 1: Plakat steht ab Frame 0, die Kamera zoomt weich hinein. Ab SATZ2 harter Schnitt, mit Hook-Szene ins Vollbild bis Hook-Ende.
// Body: der Zoom wechselt an jedem Take-Schnitt zwischen weit und nah, Vollbild-Passagen (VOLLBILD) zeigen nur die Grafik,
// sonst liegt die Grafik auf der Wand über dem Kopf. Die Augen stehen bei jedem Schnitt auf derselben Höhe (augen.json).
// Ton: kein Audio-Element in diesem Projekt. Effekte mischt scripts/sfx_mix.py, bauen.sh nimmt den Ton aus --ton-video.
import React from 'react';
import {AbsoluteFill, Easing, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';

import AUGEN from './augen.json';
import {Plakat} from './Plakat';
import {AUGEN_Y, BODY_SCHNITTE, GESAMT, GESICHT_X, HOOK, HOOK_SZENEN, PLAKAT, SATZ2, SZENEN, VOLLBILD, ZOOM, type Version} from './reel';
import {STIL} from './stil';
import {BAUSTEIN} from './szenen';
import {UntertitelBild, Untertitel, probeHaeppchen, untertitelY} from './Untertitel';

const inPassage = (x: number, liste: [number, number][]): [number, number] | undefined => liste.find(([a, b]) => x >= a && x < b);
const clipVon = (bf: number): number => BODY_SCHNITTE.filter((s) => s <= bf).pop() ?? 0;

/** Weit und nah im Wechsel über die Clips mit Person. Im weiten Clip schiebt die Kamera langsam rein. */
const rhythmusZoom = (weit: number, bf: number): number => {
	const von = clipVon(bf);
	const nr = BODY_SCHNITTE.filter((s) => s <= von && !inPassage(s, VOLLBILD)).length - 1;
	if (nr % 2 === 1) return weit + STIL.zoom.nahPlus;
	const bis = BODY_SCHNITTE.find((s) => s > von) ?? von + 150;
	return interpolate(bf, [von, bis], [weit, weit + 0.04], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
};

const hatHookSzene = (version: Version): boolean => HOOK_SZENEN[version].length > 0;

/** Läuft bei Body-Frame bf eine Szene über dem Kopf? Nur dann liegt der dunkle Hof auf der Wand, sonst bleibt sie frei. */
const grafikUeberKopf = (bf: number): boolean =>
	bf >= 0 && SZENEN.some((s) => bf >= s.von && bf < s.bis && !inPassage(s.von, VOLLBILD));

/** Liegt Frame f einer Version in einer Vollbild-Passage (nur Grafik, keine Person)? */
export const imVollbild = (version: Version, f: number): boolean => {
	const bf = f - HOOK[version];
	if (bf >= 0) return Boolean(inPassage(bf, VOLLBILD));
	return hatHookSzene(version) && f >= SATZ2[version];
};

const zoomBei = (version: Version, f: number): number => {
	const w = ZOOM[version];
	if (f < SATZ2[version]) return interpolate(f, [0, SATZ2[version]], [w, w + STIL.zoom.hookPlus], {easing: Easing.inOut(Easing.quad), extrapolateRight: 'clamp'});
	if (f < HOOK[version]) return w;
	return rhythmusZoom(w, f - HOOK[version]);
};

/** Augen je Take-Clip (augen.json: {version: [[startFrame, augenY, augenX], ...]}), sonst die Werte aus reel.ts. */
const augenBei = (version: Version, f: number): [number, number] => {
	const liste = (AUGEN as Record<string, number[][]>)[version] ?? [];
	const c = liste.filter((e) => e[0] <= f).pop() ?? liste[0];
	return c ? [c[1], c[2]] : [AUGEN_Y, GESICHT_X];
};
const klemm = (x: number, a: number, b: number): number => Math.max(a, Math.min(b, x));

/** Verschiebung, damit die Augen auf STIL.zoom.augenZielY und das Gesicht auf x 540 landen, ohne schwarzen Rand. */
const versatz = (zoom: number, ay: number, ax: number): [number, number] => [
	klemm(540 - ax, -(1080 - ax) * (zoom - 1), ax * (zoom - 1)),
	klemm(STIL.zoom.augenZielY - ay, -(1920 - ay) * (zoom - 1), ay * (zoom - 1)),
];

const PlakatHook: React.FC<{version: Version}> = ({version}) => {
	const f = useCurrentFrame();
	const spann = Math.pow(Math.min(1, f / Math.max(1, SATZ2[version])), 3);
	const zitter = Math.sin(f * 1.9) * 2.5 * spann;
	return (
		<div style={{position: 'absolute', inset: 0, transform: `translateX(${zitter}px) scale(${1 + 0.05 * spann})`, transformOrigin: `540px ${STIL.plakat.y}px`}}>
			<Plakat zeilen={PLAKAT[version]} />
		</div>
	);
};

/** Dunkler Hof hinter der Bühne, damit helle Grafiken auf heller Wand tragen. Nur solange eine Grafik über dem Kopf steht. */
const Hof: React.FC = () => (
	<div style={{position: 'absolute', left: 0, right: 0, top: 0, height: 1000,
		background: 'radial-gradient(ellipse 660px 460px at 540px 470px, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.34) 55%, rgba(0,0,0,0) 100%)'}} />
);
const VollbildGrund: React.FC = () => (
	<div style={{position: 'absolute', inset: 0, background: `radial-gradient(ellipse 760px 900px at 540px 900px, ${STIL.farben.grundLicht} 0%, ${STIL.farben.grund} 100%)`}} />
);

export const Reel: React.FC<{version: Version; mitVideo?: boolean}> = ({version, mitVideo = true}) => {
	const f = useCurrentFrame();
	const hook = HOOK[version];
	const voll = imVollbild(version, f);
	const zoom = zoomBei(version, f);
	const [ay, ax] = augenBei(version, f);
	const [dx, dy] = versatz(zoom, ay, ax);
	return (
		<AbsoluteFill style={{background: '#000'}}>
			{voll && <VollbildGrund />}
			{mitVideo && (
				<AbsoluteFill style={{opacity: voll ? 0 : 1, transform: `translate(${dx}px, ${dy}px) scale(${zoom})`, transformOrigin: `${ax}px ${ay}px`}}>
					<OffthreadVideo src={staticFile(`video/${version}-hd.mp4`)} style={{width: 1080, height: 1920}} />
				</AbsoluteFill>
			)}
			{!voll && grafikUeberKopf(f - hook) && <Hof />}
			{HOOK_SZENEN[version].filter((s) => s.bis > s.von).map((s) => {
				const [Szene] = BAUSTEIN[s.name];
				return (
					<Sequence key={`h-${s.name}`} from={s.von} durationInFrames={s.bis - s.von}>
						<Szene m={s.m} dauer={s.bis - s.von} version={version} />
					</Sequence>
				);
			})}
			<Sequence from={hook} durationInFrames={GESAMT[version] - hook}>
				{SZENEN.map((s) => {
					const [Szene] = BAUSTEIN[s.name];
					return (
						<Sequence key={`${s.name}-${s.von}`} from={s.von} durationInFrames={s.bis - s.von}>
							<Szene m={s.m} dauer={s.bis - s.von} version={version} />
						</Sequence>
					);
				})}
			</Sequence>
			{PLAKAT[version].length > 0 && SATZ2[version] > 0 && (
				<Sequence from={0} durationInFrames={SATZ2[version]}><PlakatHook version={version} /></Sequence>
			)}
			<Untertitel version={version} zoom={zoom} anker={ay} versatz={dy} y={voll ? STIL.untertitel.vollbildY : undefined} />
		</AbsoluteFill>
	);
};

/** Props der Stilprobe (Schritt 4). `bild` liegt in public/, z. B. stilprobe/hook.png (ein Frame aus dem echten Video). */
export type StilprobeProps = {
	bild: string;
	modus: 'plakat' | 'weit' | 'nah';
	plakat: string[];
	untertitel: string;
	zoom: number;
	augenY: number;
	gesichtX: number;
};

/** Standbild mit echtem Frame, Zoom, Plakat und Untertitel im Stil von stil.json. Keine Wortzeiten nötig. */
export const Stilprobe: React.FC<StilprobeProps> = ({bild, modus, plakat, untertitel, zoom, augenY, gesichtX}) => {
	const z = modus === 'nah' ? zoom + STIL.zoom.nahPlus : modus === 'plakat' ? zoom + STIL.zoom.hookPlus : zoom;
	const [dx, dy] = versatz(z, augenY, gesichtX);
	return (
		<AbsoluteFill style={{background: '#000'}}>
			{bild ? (
				<AbsoluteFill style={{transform: `translate(${dx}px, ${dy}px) scale(${z})`, transformOrigin: `${gesichtX}px ${augenY}px`}}>
					<Img src={staticFile(bild)} style={{width: 1080, height: 1920, objectFit: 'cover'}} />
				</AbsoluteFill>
			) : <VollbildGrund />}
			{modus === 'plakat' && plakat.length > 0 && <Plakat zeilen={plakat} />}
			{untertitel && <UntertitelBild woerter={probeHaeppchen(untertitel)} frame={0} y={untertitelY(z, augenY, dy)} />}
		</AbsoluteFill>
	);
};
