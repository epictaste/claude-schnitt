// Projekt „Beispiel der Vorlage“. Von scripts/geruest.py aus schnitt/meta.json und spec.json geschrieben, nicht von Hand ändern:
// beim nächsten Lauf wird die Datei neu erzeugt. Wortzeiten in Frames, relativ zum Teil-Start.
// Marken = Startframe jedes Wortes ab 3 Zeichen (Umlaute als ae/oe/ue/ss, Zahlen mit n davor, doppelte Wörter mit 2/3 dahinter), relativ zum Szenenstart.
import D from './woerter.json';
import {STIL} from './stil';

export const FPS = 30;
export type Version = 'v1';
export const VERSIONEN: Version[] = ["v1"];
export type Wort = {w: string; von: number; bis: number};
export type Marken = Record<string, number>;

/** Hook-Länge je Version (= Body-Start im Video). */
export const HOOK: Record<Version, number> = {"v1": 90};
/** Erster harter Schnitt nach Satz 1: bis hier Plakat und weicher Zoom. */
export const SATZ2: Record<Version, number> = {"v1": 45};
/** Take-Schnitte je Version (Video-Frames): Untertitel wechseln mit dem Schnitt. */
export const TAKE_SCHNITTE: Record<Version, number[]> = {"v1": [45, 90, 150]};
/** Clip-Grenzen im Body (Body-Frames): hier wechselt der Zoom zwischen weit und nah. */
export const BODY_SCHNITTE = [0, 60];
export const BODY = 210;
export const GESAMT: Record<Version, number> = {v1: HOOK['v1'] + BODY};

export const HOOK_WOERTER: Record<Version, Wort[]> = {v1: D.hook['v1']};
export const BODY_WOERTER: Wort[] = D.body;

/** Fläche über dem Kopf und Fläche für Vollbild-Szenen, Werte aus stil.json. */
export const BUEHNE = STIL.buehne;
export const VOLL = STIL.voll;
export const KOPF_Y = 860;
export const AUGEN_Y = 1000;
export const GESICHT_X = 540;
/** Body-Zoom (weit) je Version, jede Version ein eigenes Level. Nah = weit + STIL.zoom.nahPlus. */
export const ZOOM: Record<Version, number> = {"v1": 1.1};
/** Text-Hook je Version, eine Zeile pro Eintrag, Logo als [logo:datei.png]. */
export const PLAKAT: Record<Version, string[]> = {"v1": ["Claude schneidet", "mein Video"]};

export type SzenenName = 'beispiel';
export type SzenenEintrag = {name: SzenenName; von: number; bis: number; m: Marken};
export type SzenenProps = {m: Marken; dauer: number; version?: Version};

/** Hook-Szene je Version: Vollbild ab SATZ2 bis Hook-Ende. Frames relativ zum Videostart. */
export const HOOK_SZENEN: Record<Version, SzenenEintrag[]> = {
	v1: [],
};

/** Body-Szenen, Frames relativ zum Body-Start (in allen Versionen gleich). */
export const SZENEN: SzenenEintrag[] = [
	// beispiel (VOLLBILD): „Ich gebe ihm das Rohmaterial, er sucht die besten Takes, baut Grafiken und Untertitel und am Ende liegt das fertige Video im Ordner.“
	{name: 'beispiel', von: 0, bis: 210, m: {"ich": 2, "gebe": 11, "ihm": 20, "das": 29, "rohmaterial": 38, "sucht": 56, "die": 65, "besten": 74, "takes": 83, "baut": 92, "grafiken": 101, "und": 110, "untertitel": 119, "und2": 128, "ende": 146, "liegt": 155, "das2": 164, "fertige": 173, "video": 182, "ordner": 200}},
];

/** Vollbild-Passagen (Body-Frames): nur Grafik, keine Person. Im Hook: SATZ2 bis HOOK, wenn es eine Hook-Szene gibt. */
export const VOLLBILD: [number, number][] = [[0, 210]];
