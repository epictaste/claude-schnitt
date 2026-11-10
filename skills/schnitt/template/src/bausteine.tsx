// Bausteine für Szenen. Farben und Schrift kommen aus stil.json, nie fest in eine Szene schreiben.
// Regeln für den Einsatz: referenz/regeln-grafiken.md im Skill-Ordner.
import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';

import {SCHRIFT, STIL} from './stil';

export const FARBE = {
	...STIL.farben,
	linie: 'rgba(255,255,255,0.16)',
	glas: 'rgba(0,0,0,0.42)',
	grau: '#8E8A84', // nur in nachgebauten Oberflächen (Fensterleisten, Eingabefelder)
} as const;

export const GRAFIK_FONT = SCHRIFT.grafik;

/** Weiches Licht um Text und Lichtpunkte. */
export const LICHT = '0 0 18px rgba(255,255,255,0.55), 0 0 42px rgba(255,255,255,0.25)';

/** 0..1 zwischen von und von + dauer, geklemmt. */
export const ein = (frame: number, von: number, dauer = 10): number =>
	interpolate(frame, [von, von + dauer], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

/** Ausklingend (kubisch). */
export const weich = (t: number): number => 1 - Math.pow(1 - t, 3);

/** Mit kleinem Überschwinger, für Dinge, die einrasten. */
export const einrasten = (t: number): number => 1 + 2.2 * Math.pow(t - 1, 3) + 1.2 * Math.pow(t - 1, 2);

/** Erscheint ab `von` aus der Unschärfe. Vorher ist nichts da, ab `von` ist schon etwas zu sehen. */
export const Scharf: React.FC<{von?: number; dauer?: number; blur?: number; children: React.ReactNode; style?: React.CSSProperties}> = ({von = 0, dauer = 8, blur = 22, children, style}) => {
	const frame = useCurrentFrame();
	if (frame < von) return null;
	const b = interpolate(frame - von, [0, dauer], [blur, 0], {extrapolateRight: 'clamp'});
	return <div style={{...style, filter: b < 0.3 ? undefined : `blur(${b}px)`, opacity: ein(frame, von, dauer * 0.6) * 0.5 + 0.5}}>{children}</div>;
};

/** Fläche über dem Kopf (STIL.buehne), Inhalt mittig. Für Szenen, in denen die Person zu sehen ist. */
export const Buehne: React.FC<{children: React.ReactNode}> = ({children}) => (
	<AbsoluteFill style={{top: STIL.buehne.y, height: STIL.buehne.hoehe, alignItems: 'center', justifyContent: 'center'}}>
		<div style={{maxWidth: STIL.buehne.maxBreite, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{children}</div>
	</AbsoluteFill>
);

/** Fläche für Vollbild-Szenen ohne Person (STIL.voll). Darunter liegen die Untertitel. */
export const Voll: React.FC<{children: React.ReactNode}> = ({children}) => (
	<div style={{position: 'absolute', left: STIL.voll.x, top: STIL.voll.y, width: STIL.voll.breite, height: STIL.voll.hoehe, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
		{children}
	</div>
);

/** Gesperrtes Label in Versalien. */
export const Gesperrt: React.FC<{children: React.ReactNode; groesse?: number; style?: React.CSSProperties}> = ({children, groesse = 32, style}) => (
	<span style={{fontFamily: GRAFIK_FONT, fontWeight: 300, fontSize: groesse, letterSpacing: '0.45em', paddingLeft: '0.45em', color: FARBE.textGedimmt, whiteSpace: 'nowrap', ...style}}>{children}</span>
);

/** Großes Wort oder große Zahl. */
export const Gross: React.FC<{children: React.ReactNode; groesse?: number; akzent?: boolean; style?: React.CSSProperties}> = ({children, groesse = 120, akzent = false, style}) => (
	<span style={{fontFamily: GRAFIK_FONT, fontWeight: 800, fontSize: groesse, lineHeight: 1, color: akzent ? FARBE.akzent : FARBE.text, whiteSpace: 'nowrap', textShadow: '0 4px 24px rgba(0,0,0,0.5)', ...style}}>{children}</span>
);

/** Dunkle Glaskarte, trägt sich auf heller Wand und auf dunklem Grund. */
export const GlasKarte: React.FC<{children: React.ReactNode; breite?: number; polster?: number; style?: React.CSSProperties}> = ({children, breite, polster = 36, style}) => (
	<div style={{width: breite, padding: polster, boxSizing: 'border-box', borderRadius: 28, background: FARBE.glas, border: `1px solid ${FARBE.linie}`,
		backdropFilter: 'blur(14px)', boxShadow: '0 30px 80px rgba(0,0,0,0.55)', ...style}}>{children}</div>
);

/** Schräger Lichtstreifen über ein Element, `p` 0..1. Elternteil braucht position: relative. */
export const LichtWisch: React.FC<{p: number; staerke?: number}> = ({p, staerke = 0.5}) => (
	<div style={{position: 'absolute', inset: 0, mixBlendMode: 'screen', pointerEvents: 'none', opacity: p <= 0 || p >= 1 ? 0 : 1,
		background: `linear-gradient(110deg, transparent ${p * 160 - 45}%, rgba(255,255,255,${staerke}) ${p * 160 - 30}%, transparent ${p * 160 - 15}%)`}} />
);

/** Leuchtender Punkt für Verbindungen und Marker. */
export const Lichtpunkt: React.FC<{x: number; y: number; r?: number; staerke?: number}> = ({x, y, r = 8, staerke = 1}) => (
	<div style={{position: 'absolute', left: x - r, top: y - r, width: 2 * r, height: 2 * r, borderRadius: r, background: '#fff', opacity: staerke,
		boxShadow: `0 0 ${2 * r}px ${r / 2}px rgba(255,255,255,0.7), 0 0 ${5 * r}px rgba(255,255,255,0.35)`}} />
);

/** Echtes Logo aus public/logos/. Nie ein nachgebautes Kästchen mit Namen. */
export const Logo: React.FC<{datei: string; groesse: number; rund?: boolean; style?: React.CSSProperties}> = ({datei, groesse, rund = true, style}) => (
	<Img src={staticFile(`logos/${datei}`)} style={{width: groesse, height: groesse, objectFit: 'contain', borderRadius: rund ? groesse * 0.22 : 0, display: 'block', ...style}} />
);

/** Häkchen, `p` 0..1 zeichnet es. */
export const Haekchen: React.FC<{groesse: number; p: number}> = ({groesse, p}) => (
	<svg width={groesse} height={groesse} viewBox="0 0 24 24" style={{display: 'block', overflow: 'visible', filter: `drop-shadow(0 0 8px ${FARBE.haken})`}}>
		<path d="M4 12.5 L9.5 18 L20 6.5" fill="none" stroke={FARBE.haken} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round"
			pathLength={1} strokeDasharray="1" strokeDashoffset={1 - p} opacity={p > 0 ? 1 : 0} />
	</svg>
);

/** Pfeil, der sich zeichnet. Die Spitze kommt erst kurz vor Schluss dazu, sonst steht sie allein im Bild. */
export const Pfeil: React.FC<{von: [number, number]; nach: [number, number]; p: number; dicke?: number}> = ({von, nach, p, dicke = 5}) => {
	const [x1, y1] = von;
	const [x2, y2] = nach;
	const w = Math.atan2(y2 - y1, x2 - x1);
	const sx = x1 + (x2 - x1) * p;
	const sy = y1 + (y2 - y1) * p;
	const k = 22;
	return (
		<svg style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', pointerEvents: 'none'}} width={1} height={1}>
			{p > 0 && <line x1={x1} y1={y1} x2={sx} y2={sy} stroke={FARBE.text} strokeWidth={dicke} strokeLinecap="round" />}
			{p > 0.85 && (
				<polyline points={`${x2 - k * Math.cos(w - 0.5)},${y2 - k * Math.sin(w - 0.5)} ${x2},${y2} ${x2 - k * Math.cos(w + 0.5)},${y2 - k * Math.sin(w + 0.5)}`}
					fill="none" stroke={FARBE.text} strokeWidth={dicke} strokeLinecap="round" strokeLinejoin="round" />
			)}
		</svg>
	);
};

export type DateiTyp = 'pdf' | 'folie' | 'tabelle' | 'text' | 'bild' | 'video' | 'mail' | 'ordner';
const DATEI: Record<DateiTyp, {farbe: string; kurz: string}> = {
	pdf: {farbe: '#E5322D', kurz: 'PDF'},
	folie: {farbe: '#D24726', kurz: 'PPT'},
	tabelle: {farbe: '#1D6F42', kurz: 'XLS'},
	text: {farbe: '#2B579A', kurz: 'DOC'},
	bild: {farbe: '#8E5CD9', kurz: 'JPG'},
	video: {farbe: '#E0A100', kurz: 'MP4'},
	mail: {farbe: '#3D8BFD', kurz: '@'},
	ordner: {farbe: '#C9A227', kurz: ''},
};

/** Datei als erkennbares Icon: Typ auf einen Blick, Typfarbe ist erlaubt. Der Name darf klein drunter, trägt aber nicht die Aussage. */
export const DateiIcon: React.FC<{typ: DateiTyp; groesse?: number; name?: string}> = ({typ, groesse = 120, name}) => {
	const d = DATEI[typ];
	const b = groesse * 0.78;
	return (
		<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: groesse * 0.08}}>
			{typ === 'ordner' ? (
				<svg width={groesse} height={groesse * 0.8} viewBox="0 0 100 80">
					<path d="M4 14 Q4 8 10 8 L36 8 L44 16 L90 16 Q96 16 96 22 L96 70 Q96 76 90 76 L10 76 Q4 76 4 70 Z" fill={d.farbe} />
					<path d="M4 28 L96 28 L96 70 Q96 76 90 76 L10 76 Q4 76 4 70 Z" fill="#E8C547" />
				</svg>
			) : (
				<div style={{position: 'relative', width: b, height: groesse, borderRadius: groesse * 0.08, background: '#F4F4F2', boxShadow: '0 10px 30px rgba(0,0,0,0.45)', overflow: 'hidden'}}>
					<div style={{position: 'absolute', right: 0, top: 0, width: b * 0.3, height: b * 0.3, background: '#D6D6D2', borderBottomLeftRadius: groesse * 0.06}} />
					<div style={{position: 'absolute', left: 0, right: 0, bottom: groesse * 0.14, height: groesse * 0.3, background: d.farbe, display: 'flex', alignItems: 'center', justifyContent: 'center',
						fontFamily: GRAFIK_FONT, fontWeight: 800, fontSize: groesse * 0.17, color: '#fff', letterSpacing: '0.04em'}}>{d.kurz}</div>
				</div>
			)}
			{name && <span style={{fontFamily: GRAFIK_FONT, fontWeight: 500, fontSize: Math.max(32, groesse * 0.2), color: FARBE.textGedimmt, whiteSpace: 'nowrap'}}>{name}</span>}
		</div>
	);
};

/** Verpixelt Inhalte, die niemand lesen soll (ganze Prompts, Schlüssel, private Pfade). Die erste Zeile darüber darf lesbar bleiben. */
export const Mosaik: React.FC<{breite: number; hoehe: number; zelle?: number; saat?: number}> = ({breite, hoehe, zelle = 22, saat = 1}) => {
	const spalten = Math.ceil(breite / zelle);
	const zeilen = Math.ceil(hoehe / zelle);
	const felder: React.ReactNode[] = [];
	for (let r = 0; r < zeilen; r++) {
		for (let s = 0; s < spalten; s++) {
			const ton = ((r * 31 + s * 17 + saat * 7) % 23) / 23;
			felder.push(<div key={`${r}-${s}`} style={{position: 'absolute', left: s * zelle, top: r * zelle, width: zelle, height: zelle, background: `rgba(200,200,215,${0.12 + ton * 0.4})`}} />);
		}
	}
	return <div style={{position: 'relative', width: breite, height: hoehe, overflow: 'hidden', borderRadius: 8}}>{felder}</div>;
};
