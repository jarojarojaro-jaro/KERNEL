/**
 * Numbers the home page shows, picked from the registries (measurements.ts, estimator.ts).
 * Nothing is typed in here: this module only selects runs and variants and formats them.
 */
import { CARDS, findCard, MODEL_INFO, variantOf, XTX_BOARD, type CardView, type ModelKey, type RunView, type Variant, type VariantKey } from '$lib/data/measurements';
import { findModel, GPUS } from '$lib/estimator';
import { fmtRatio } from '$lib/format';
import { nb } from '$lib/site/copy';

const must = <T>(v: T | null | undefined, what: string): T => {
	if (v === null || v === undefined) throw new Error(`home data: missing ${what}`);
	return v;
};

/** The hero card and run: RTX 3090 × Qwen3.8-27B UD-Q4_K_XL (same script in every column). */
export const HERO_CARD = must(findCard('rtx-3090'), 'rtx-3090');
export const HERO_RUN = must(
	HERO_CARD.runs.find((r) => r.model === 'qwen38'),
	'rtx-3090 qwen38'
);
export const HERO_V = {
	a0: must(variantOf(HERO_RUN, 'a0'), 'a0'),
	a1: must(variantOf(HERO_RUN, 'a1'), 'a1'),
	a2: must(variantOf(HERO_RUN, 'a2'), 'a2')
};

/** The scan scene reads our lab card: Sapphire PULSE RX 7900 XTX (board spec + registry entry). */
export const SCAN_CARD = must(findCard(XTX_BOARD.card), XTX_BOARD.card);
export const SCAN_BOARD = XTX_BOARD;
export const HERO_MODEL = MODEL_INFO[HERO_RUN.model].name;
export const HERO_GAIN = must(HERO_RUN.gain, 'gain');
export const HERO_KERNELS = must(HERO_RUN.kernels, 'kernels');

/** The Q8_0 build of the same model: too big for 24 GB (estimator registry, report 04). */
export const Q8 = must(findModel('qwen38-27b-q8'), 'qwen38-27b-q8');
export const MODELS_SRC = 'app/landing/src/lib/data/models.json (raport 04 §2.3.1)';

/** GPUs waiting in the lab queue. */
export const PLANNED = GPUS.filter((g) => g.lab === 'planned');

export { CARDS };

/**
 * The hero race cycles through these measured pairs: the run's "before" vs our engine, and only
 * runs where both come from the same script (`sameHarness`). XTX × Qwen (different scripts) and the
 * 3060 runs (Saluki ≈ even, Bonsai: Prism beats us) are never raced.
 */
const PAIR_IDS: [string, ModelKey][] = [
	// first: a pair whose whole gain is our engine (no speculation), then alternate models
	['rtx-3090', 'lfm25'],
	['rtx-3090', 'qwen38'],
	['rx-7900-xtx', 'lfm25'],
	['rtx-5060-ti-16', 'qwen38'],
	['rtx-5060-ti-16', 'lfm25'],
	['rtx-3090', 'nemotron']
];
export interface HeroPair {
	id: string;
	card: CardView;
	run: RunView;
	before: Variant;
	ours: Variant;
}
export const HERO_PAIRS: HeroPair[] = PAIR_IDS.map(([cardId, model]) => {
	const card = must(findCard(cardId), cardId);
	const run = must(
		card.runs.find((r) => r.model === model && r.sameHarness),
		`${cardId} ${model} same-script run`
	);
	return { id: `${cardId}:${model}`, card, run, before: must(variantOf(run, run.before), 'before'), ours: must(variantOf(run, run.ours), 'ours') };
});

export { nb };

/** `{key}` placeholders in copy are filled with formatted numbers from the registries. */
export function fill(s: string, vars: Record<string, string | number>): string {
	return nb(s.replace(/\{(\w+)\}/g, (m, k: string) => (k in vars ? String(vars[k]) : m)));
}

export { fmtRatio };

/**
 * One redline for the page (design/REDESIGN.md §6): every dial and bar for dense models runs to
 * 100 t/s with the red zone from 70 t/s, so the 3090 Qwen run (78,0) visibly crosses it.
 */
export const REDLINE = 70;
export const DIAL_MAX = 100;

/**
 * Dial scale for a run: the page-wide 0–100 / 70 dial whenever its fastest lane fits; fast MoE runs
 * (LFM, Nemotron, well above 100 t/s) get a longer scale with the red zone at the same 70% of it.
 */
export function dialFor(fastest: number): { max: number; redline: number } {
	if (fastest * 1.12 <= DIAL_MAX) return { max: DIAL_MAX, redline: REDLINE };
	const max = Math.ceil((fastest * 1.25) / 50) * 50;
	return { max, redline: Math.round((max * REDLINE) / DIAL_MAX) };
}

/**
 * Hero dial for one pair: the scale ends so that our measured value sits at ~80% of it, and the
 * red zone is always the top 30% of the dial (same fraction as the page-wide 70 of 100). Every tick
 * is a real t/s value; only the scale length changes with the pair.
 */
export function heroDial(fastest: number): { max: number; redline: number } {
	const raw = fastest / 0.8;
	const step = raw <= 120 ? 10 : raw <= 200 ? 20 : 50;
	const max = Math.ceil(raw / step) * step;
	return { max, redline: Math.round(max * 0.7) };
}

export function decode(v: Variant | undefined): number {
	return v?.decode?.v ?? 0;
}

/**
 * Columns shown for a run, in order: the "before", competing forks, the best flags and ours.
 * Duplicates (e.g. flags === before) are dropped.
 */
export function columns(run: RunView): VariantKey[] {
	const keys: VariantKey[] = [run.before];
	if (run.variants.some((v) => v.key === 'alt')) keys.push('alt');
	keys.push(run.flags, run.ours);
	return [...new Set(keys)].filter((k) => run.variants.some((v) => v.key === k && v.decode));
}

/**
 * The "cold" lane of a race: the default setup, unless our engine is not faster than it
 * (Bonsai: the Prism default beats us), in which case the honest pair is the same file on
 * upstream vs. ours.
 */
export function raceCold(run: RunView): VariantKey {
	const before = decode(variantOf(run, run.before));
	const ours = decode(variantOf(run, run.ours));
	return ours > before ? run.before : run.flags;
}

