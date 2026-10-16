/**
 * Data layer of the cards explorer. Numbers come only from `measurements.ts` (measured) and
 * `estimator.ts` (estimates, always labelled as such). Nothing here invents a value.
 *
 * Card ids (also used for the prerender entries in svelte.config.js, same rule): every measured
 * card in `CARDS`, plus every GPU with a lab status in gpus.json that has no measurements yet
 * (the measurement queue).
 */
import { CARDS, variantOf, type CardView, type ModelKey, type RunView, type Variant } from '$lib/data/measurements';
import { decodeRange, findModel, fit, GPUS, memoryNeed, recommend, type Gpu, type Model, type Range } from '$lib/estimator';

export type MeasuredEntry = { kind: 'measured'; id: string; card: CardView; gpu: Gpu | null };
export type QueuedEntry = { kind: 'queued'; id: string; gpu: Gpu };
export type Entry = MeasuredEntry | QueuedEntry;

export const MEASURED: MeasuredEntry[] = CARDS.map((card) => ({ kind: 'measured', id: card.id, card, gpu: GPUS.find((g) => g.id === card.id) ?? null }));
export const QUEUED: QueuedEntry[] = GPUS.filter((g) => g.lab && !CARDS.some((c) => c.id === g.id)).map((gpu) => ({ kind: 'queued', id: gpu.id, gpu }));
export const ENTRIES: Entry[] = [...MEASURED, ...QUEUED];

/** "GeForce RTX 4090" → { prefix: "GeForce RTX", short: "4090" }; Apple/Intel keep the vendor as prefix. */
export function splitName(name: string, vendor: string): { prefix: string; short: string } {
	const short = name.replace(/^(GeForce|Radeon) (RTX |RX )?/, '');
	return { prefix: name.slice(0, name.length - short.length).trim() || vendor.toUpperCase(), short };
}

export const findEntry = (id: string) => ENTRIES.find((e) => e.id === id) ?? null;

/** Where the estimator's inputs live (for SourceTips next to estimates). */
export const EST_SRC = 'app/landing/src/lib/estimator.ts: decodeRange (η·BW/B, raport 04 §2.2.4), memoryNeed (raport 04 §2.2.4)';
export const GPU_SRC = 'app/landing/src/lib/data/gpus.json';

/* ---------------- measured cards ---------------- */

export interface Duel {
	run: RunView;
	before: Variant;
	flags: Variant | undefined;
	ours: Variant;
	/** ours / before decode, only when both come from the same script. */
	ratio: number | null;
}

export function duel(run: RunView): Duel | null {
	const before = variantOf(run, run.before);
	const ours = variantOf(run, run.ours);
	if (!before?.decode || !ours?.decode) return null;
	const flags = run.flags !== run.before ? variantOf(run, run.flags) : undefined;
	// The sheet's own total (computed from unrounded medians) wins over re-dividing rounded values.
	const ratio = run.sameHarness ? (run.gain?.total?.v ?? ours.decode.v / before.decode.v) : null;
	return { run, before, flags, ours, ratio };
}

/** Heat of a card's render = its measured speed-up on the ramp (×1 cold … ×2 white-hot; not measured = 0). */
export const heatOf = (ratio: number | null | undefined) => (ratio ? Math.max(0.12, Math.min(1, (ratio - 1) / 1.05)) : 0);

/** A value rounded to the digits it is shown with (rolling counters must come to rest on a whole digit). */
export const roundTo = (v: number, digits: number) => Math.round(v * 10 ** digits) / 10 ** digits;

/** Kept here for callers that import it from the explorer; the one definition lives in format.ts. */
export { ratioDigits } from '$lib/format';

export const runOf = (card: CardView, model: ModelKey) => card.runs.find((r) => r.model === model) ?? null;

/**
 * The headline comparison of a card: its editorial pick, unless that pick has no same-script
 * before/after (RX 7900 XTX Qwen); then the first run that has one.
 */
export function headline(card: CardView): Duel | null {
	const pick = runOf(card, card.pick.model);
	const pd = pick ? duel(pick) : null;
	if (pd?.ratio) return pd;
	for (const r of card.runs) {
		const d = duel(r);
		if (d?.ratio) return d;
	}
	return pd;
}

/** Models both cards measured; the compare view falls back to each card's pick when empty. */
/**
 * Models whose output we have not yet checked against upstream with KLD (the run's note says so,
 * e.g. Nemotron: KERNEL/product/research/14-nemotron-3090.md). The honesty panel names them.
 */
/** The measured model family an estimator file belongs to (for its identity colour), if any. */
export const familyOf = (modelId: string): ModelKey | null => (modelId.startsWith('qwen38') ? 'qwen38' : modelId.startsWith('lfm25') ? 'lfm25' : null);

export const KLD_PENDING: ModelKey[] = ['nemotron'];


export const sharedModels = (a: CardView, b: CardView): ModelKey[] => a.runs.map((r) => r.model).filter((m) => b.runs.some((r) => r.model === m));

/* ---------------- estimates (labelled) ---------------- */

/** Model families we measured that also exist in the estimator's model list, best quality first. */
const FAMILIES: string[][] = [
	['qwen38-27b-q8', 'qwen38-27b-q6k', 'qwen38-27b-q4kxl', 'qwen38-27b-q3kxl'],
	['lfm25-24b-q5km', 'lfm25-24b-q4km']
];
const CTX = 32768;

/**
 * "Does not fit" ghosts for a card's VRAM bar: per family, the smallest file that would not fit
 * at a 32k context according to the estimator's memory formula (an ESTIMATE, labelled in the UI).
 */
export function ghosts(vramGiB: number): { model: Model; need: Range }[] {
	const out: { model: Model; need: Range }[] = [];
	for (const fam of FAMILIES) {
		const over = fam
			.map((id) => findModel(id)!)
			.filter((m) => memoryNeed(m, CTX).lo > vramGiB)
			.sort((a, b) => a.sizeGB - b.sizeGB)[0];
		if (over) out.push({ model: over, need: memoryNeed(over, CTX) });
	}
	return out;
}

export interface QueueEstimate {
	model: Model;
	need: Range;
	decode: Range;
}

/**
 * Estimates for a card in the measurement queue: the best Qwen and LFM file that fits at a 32k
 * context (or, if none does, the estimator's recommendation), with the stock decode range
 * η·BW/B. Unified-memory machines have no fixed VRAM → no estimate ("soon").
 */
export function queueEstimate(gpu: Gpu): QueueEstimate[] {
	if (!gpu.vram || gpu.unified || gpu.cpuOnly) return [];
	const hw = { gpu, vramGiB: gpu.vram, ramGiB: 0, os: 'linux' as const };
	const out: QueueEstimate[] = [];
	for (const fam of FAMILIES) {
		const m = fam.map((id) => findModel(id)!).find((x) => fit(x, hw, CTX) === 'fits');
		if (m) out.push({ model: m, need: memoryNeed(m, CTX), decode: decodeRange(m, gpu)! });
	}
	if (!out.length) {
		const m = recommend(hw, CTX).primary;
		if (fit(m, hw, CTX) === 'fits') out.push({ model: m, need: memoryNeed(m, CTX), decode: decodeRange(m, gpu)! });
	}
	return out;
}

/* ---------------- search ---------------- */

export type VramBand = 'all' | 'le12' | '16' | 'ge20';
export const VRAM_BANDS: VramBand[] = ['all', 'le12', '16', 'ge20'];

export const entryVram = (e: Entry): number | null => (e.kind === 'measured' ? e.card.vramGB : (e.gpu.vram ?? null));
export const entryName = (e: Entry) => (e.kind === 'measured' ? e.card.name : e.gpu.name);

export function inBand(e: Entry, band: VramBand): boolean {
	const v = entryVram(e);
	if (band === 'all') return true;
	if (v == null) return false;
	if (band === 'le12') return v <= 12;
	if (band === '16') return v > 12 && v < 20;
	return v >= 20;
}

const norm = (s: string) => s.toLowerCase().replace(/geforce|radeon|nvidia|amd|intel/g, '').replace(/[^a-z0-9]+/g, '');

/** Every query token must appear in the name ("3090", "rtx 5060 ti", "xtx", "24"). Numbers also match the VRAM size. */
export function matches(e: Entry, q: string): boolean {
	const name = norm(entryName(e));
	const v = entryVram(e);
	return q
		.toLowerCase()
		.split(/\s+/)
		.filter(Boolean)
		.every((tok) => {
			const t = tok.replace(/gb$/, '');
			if (/^\d+$/.test(t) && v != null && Number(t) === v) return true;
			const n = norm(tok);
			return !n || name.includes(n);
		});
}
