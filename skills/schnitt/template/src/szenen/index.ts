// Von scripts/geruest.py geschrieben: Szenenname -> [Komponente, Cues]. Nicht von Hand pflegen.
import type React from 'react';

import type {Cue} from '../geteilt';
import type {Marken, SzenenName, SzenenProps} from '../reel';
import {BeispielCues, BeispielSzene} from './teil-beispiel';

export const BAUSTEIN: Record<SzenenName, [React.FC<SzenenProps>, (m: Marken, dauer: number) => Cue[]]> = {
	'beispiel': [BeispielSzene, BeispielCues],
};
