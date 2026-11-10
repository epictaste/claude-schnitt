// Der Look des Projekts. Die Werte stehen in stil.json: Schritt 3 schreibt sie aus den
// Referenzvideos, ohne Referenzen bleibt der Standard aus referenz/stil-standard.md.
// Hier wird nur geprüft und die Schrift geladen, Werte ändert man in stil.json.
import {loadFont as ladeArimo} from '@remotion/google-fonts/Arimo';
import {loadFont as ladeInter} from '@remotion/google-fonts/Inter';
import {loadFont as ladeMontserrat} from '@remotion/google-fonts/Montserrat';
import {loadFont as ladePoppins} from '@remotion/google-fonts/Poppins';

import ROH from './stil.json';

export type Schrift = 'Inter' | 'Montserrat' | 'Poppins' | 'Arimo';

export type Stil = {
	name: string;
	beschreibung: string;
	schrift: {plakat: Schrift; untertitel: Schrift; grafik: Schrift};
	farben: {plakat: string; plakatKontur: string; text: string; textGedimmt: string; akzent: string; grund: string; grundLicht: string; haken: string};
	plakat: {y: number; groesse: number; versalien: boolean; kontur: number; maxBreite: number};
	untertitel: {modus: 'springend' | 'einheitlich'; groessen: [number, number, number, number]; einheitlich: number; abstandKinn: number; vollbildY: number};
	zoom: {hookPlus: number; nahPlus: number; augenZielY: number};
	buehne: {y: number; hoehe: number; maxBreite: number};
	voll: {x: number; y: number; breite: number; hoehe: number};
};

export const STIL = ROH as Stil;

// Plakat-Oberkante nie über y 300: darüber liegt auf dem Handy die Kopfzeile der Plattform.
if (STIL.plakat.y < 300) throw new Error(`stil.json: plakat.y ${STIL.plakat.y} liegt unter der Kopfzeile, mindestens 300`);

const LADER: Record<Schrift, () => string> = {
	Inter: () => ladeInter('normal', {weights: ['200', '300', '500', '600', '700', '800', '900'], subsets: ['latin', 'latin-ext'], ignoreTooManyRequestsWarning: true}).fontFamily,
	Montserrat: () => ladeMontserrat('normal', {weights: ['700', '800', '900'], subsets: ['latin', 'latin-ext'], ignoreTooManyRequestsWarning: true}).fontFamily,
	Poppins: () => ladePoppins('normal', {weights: ['500', '700', '800', '900'], subsets: ['latin', 'latin-ext'], ignoreTooManyRequestsWarning: true}).fontFamily,
	Arimo: () => ladeArimo('normal', {weights: ['400', '700'], subsets: ['latin', 'latin-ext'], ignoreTooManyRequestsWarning: true}).fontFamily,
};
const geladen: Partial<Record<Schrift, string>> = {};
const schrift = (s: Schrift): string => {
	if (!LADER[s]) throw new Error(`stil.json: Schrift „${s}“ gibt es in der Vorlage nicht (${Object.keys(LADER).join(', ')})`);
	return (geladen[s] ??= LADER[s]());
};

/** Schriftfamilien, nur die geladen, die stil.json wirklich nutzt. */
export const SCHRIFT = {
	plakat: schrift(STIL.schrift.plakat),
	untertitel: schrift(STIL.schrift.untertitel),
	grafik: schrift(STIL.schrift.grafik),
};
