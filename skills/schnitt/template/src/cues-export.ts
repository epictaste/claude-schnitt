// Gibt die Sound-Cues aller Szenen einer Version als JSON aus, für scripts/sfx_mix.py: [{t, rolle, gain}], t in Sekunden.
// Aufruf im Projekt: npm run -s cues -- v1 > ../schnitt/v1-cues.json
// Der Pegel ist für alle Effekte gleich (EFFEKT_PEGEL). Was eine Szene sonst als Lautstärke vorschlägt, zählt nicht:
// einzeln gesetzte Pegel lagen in der Praxis lauter als die Stimme.
import {FPS, HOOK, HOOK_SZENEN, SZENEN, VERSIONEN, type Version} from './reel';
import {BAUSTEIN} from './szenen';

const EFFEKT_PEGEL = 0.25;
const v = (process.argv[2] ?? VERSIONEN[0]) as Version;
if (!VERSIONEN.includes(v)) throw new Error(`Version ${v} gibt es nicht (${VERSIONEN.join(', ')})`);
const aus: {t: number; rolle: string; gain: number}[] = [];
for (const s of HOOK_SZENEN[v]) for (const c of BAUSTEIN[s.name][1](s.m, s.bis - s.von)) aus.push({t: (s.von + c.frame) / FPS, rolle: c.sound, gain: EFFEKT_PEGEL});
for (const s of SZENEN) for (const c of BAUSTEIN[s.name][1](s.m, s.bis - s.von)) aus.push({t: (HOOK[v] + s.von + c.frame) / FPS, rolle: c.sound, gain: EFFEKT_PEGEL});
console.log(JSON.stringify(aus.sort((a, b) => a.t - b.t)));
