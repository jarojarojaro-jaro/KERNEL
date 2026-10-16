/**
 * Hardware → model recommendation and the honest before/after estimate.
 *
 * Memory (report 04 §2.2.4, §3.2; PLAN §4.2):
 *   M = W + KV(ctx) + logits + β·ctx + O_rt,  plus a 1 GiB margin like llama.cpp `--fit`
 *   W      = GGUF size (decimal GB → GiB), all layers on the GPU
 *   KV     = kvKiB/token (KV q8_0) · ctx
 *   logits = n_vocab · n_ubatch · 4 B ≈ 0.25–0.5 GiB (Qwen 485 MiB, LFM 250 MiB); we take 0.5 GiB
 *   β      = 3 KiB per token of context (ub = 512)
 *   O_rt   = 0.25–0.6 GiB runtime/driver overhead → the range lo/hi
 *
 * Decode speed before any optimisation (report 04 §2.2.4, measured η table):
 *   t/s ≈ η · BW / B_tok,  η ∈ [0.55, 0.67] dense/hybrid, [0.31, 0.55] MoE
 * The two-term model (bandwidth + kernel gaps) needs per-model kernel counts we only have for
 * Qwen and LFM, so the web estimate uses the measured η band and always shows a RANGE.
 *
 * After: only what is measured is shown as a number. For models with a measured MTP head the
 * L1 band is PLAN §2 "×1.5–2.2" (measured ×2.2 on RX 7900 XTX: 38.8 → 85.6 t/s) and is labelled
 * as an estimate for every other card. L3 recipes exist only for the RX 7900 XTX.
 */
import gpuData from '$lib/data/gpus.json';
import modelData from '$lib/data/models.json';
import { M, type Measurement } from '$lib/data/measurements';

export type Gpu = (typeof gpuData.gpus)[number] & {
	vram?: number;
	unified?: boolean;
	cpuOnly?: boolean;
	bwMax?: number;
	labDir?: string;
	laptop?: boolean;
	share?: string;
};
export type Model = (typeof modelData.models)[number] & {
	activeB?: number;
	activeSource?: string;
	flagship?: boolean;
	fast?: boolean;
	use?: string;
};
export type Os = 'windows' | 'linux' | 'macos';
export type FitLabel = 'fits' | 'tight' | 'slow' | 'no';

export const GPUS = gpuData.gpus as Gpu[];
export const MODELS = modelData.models as Model[];
export const LICENSES = modelData.licenses;

export interface Hw {
	gpu: Gpu | null;
	/** GiB; for unified memory this is the system RAM. */
	vramGiB: number | null;
	ramGiB: number;
	os: Os;
}

export interface Range {
	lo: number;
	hi: number;
}

const GIB = 2 ** 30;
const LOGITS_GIB = 0.5;
const BETA_KIB = 3;
const MARGIN_GIB = 1;
/** Apple: recommendedMaxWorkingSetSize ≈ 66–75% of RAM (report 04 §2.1.3). */
const UNIFIED_BUDGET: Range = { lo: 0.66, hi: 0.75 };
/** CPU-only: leave room for the OS and apps [SZACUNEK]. */
const CPU_BUDGET = 0.7;
export const ETA: Record<'dense' | 'moe', Range> = { dense: { lo: 0.55, hi: 0.67 }, moe: { lo: 0.31, hi: 0.55 } };
/** PLAN §2, layer L1 (speculation + configuration) against a naive install. */
export const L1_MTP_BAND: Range = { lo: 1.5, hi: 2.2 };
/** Tokens per word (report 06 §2.1.2, Qwen3 tokenizer). */
export const TOK_PER_WORD = { pl: 2.69, en: 1.17 } as const;
export const CTX_OPTIONS = [8192, 32768, 131072] as const;

export const findGpu = (id: string | null | undefined) => GPUS.find((g) => g.id === id) ?? null;
export const findModel = (id: string) => MODELS.find((m) => m.id === id) ?? null;

/** GiB the model needs on the GPU at a given context length. */
export function memoryNeed(model: Model, ctx: number): Range {
	const w = (model.sizeGB * 1e9) / GIB;
	const kv = (model.kvKiB * 1024 * ctx) / GIB;
	const scratch = (BETA_KIB * 1024 * ctx) / GIB;
	const base = w + kv + LOGITS_GIB + scratch;
	return { lo: base + 0.25, hi: base + 0.6 };
}

/** Memory budget the GPU can give a model, GiB. */
export function budget(hw: Hw): Range {
	if (hw.gpu?.cpuOnly || (!hw.gpu && !hw.vramGiB)) return { lo: hw.ramGiB * CPU_BUDGET, hi: hw.ramGiB * CPU_BUDGET };
	if (hw.gpu?.unified) return { lo: hw.ramGiB * UNIFIED_BUDGET.lo, hi: hw.ramGiB * UNIFIED_BUDGET.hi };
	const v = hw.vramGiB ?? hw.gpu?.vram ?? 0;
	return { lo: v, hi: v };
}

export function fit(model: Model, hw: Hw, ctx: number): FitLabel {
	const need = memoryNeed(model, ctx);
	const b = budget(hw);
	if (need.hi + MARGIN_GIB <= b.lo) return 'fits';
	if (need.lo <= b.hi) return 'tight';
	const discrete = !!hw.gpu && !hw.gpu.unified && !hw.gpu.cpuOnly;
	// Partial offload: the rest of the weights live in system RAM (keep ~6 GiB for the OS).
	if (discrete && need.hi <= b.hi + Math.max(0, hw.ramGiB - 6)) return 'slow';
	return 'no';
}

/** Stock decode speed range (t/s), no speculation, model fully in GPU memory. */
export function decodeRange(model: Model, gpu: Gpu | null): Range | null {
	if (!gpu) return null;
	const eta = model.kind === 'moe' ? ETA.moe : ETA.dense;
	const bwHi = gpu.bwMax ?? gpu.bw;
	return { lo: (eta.lo * gpu.bw) / model.bTok, hi: (eta.hi * bwHi) / model.bTok };
}

export function l1Range(model: Model, before: Range): Range | null {
	if (model.mtp !== 'measured') return null;
	return { lo: before.lo * L1_MTP_BAND.lo, hi: before.hi * L1_MTP_BAND.hi };
}

export interface MeasuredPath {
	before: Measurement;
	l1?: Measurement;
	after: Measurement;
	sameHarness: boolean;
}

/** Before/after pairs we actually measured. Only the RX 7900 XTX has them today. */
export function measuredFor(gpuId: string | null | undefined, modelId: string): MeasuredPath | null {
	if (gpuId !== 'rx-7900-xtx') return null;
	if (modelId === 'qwen38-27b-q4kxl')
		return { before: M.qwenUpstreamVulkanPlain, l1: M.qwenUpstreamVulkanMtp, after: M.qwenOursMtp, sameHarness: false };
	if (modelId === 'lfm25-24b-q5km') return { before: M.lfmUpstreamTg128, after: M.lfmOursTg128, sameHarness: true };
	return null;
}

/** Candidate lists per tier, best first (report 04 §2.3.2). The first one that fits wins. */
const TIERS: { minGiB: number; primary: string[]; fast?: string; polish?: string; code?: string }[] = [
	{ minGiB: 28, primary: ['qwen38-27b-q6k', 'qwen38-27b-q4kxl'], fast: 'lfm25-24b-q5km', polish: 'bielik-11b-q8', code: 'qwen36-35b-a3b-q4km' },
	{ minGiB: 20, primary: ['qwen38-27b-q4kxl', 'qwen38-27b-q3kxl'], fast: 'lfm25-24b-q5km', polish: 'bielik-11b-q8', code: 'qwen36-35b-a3b-q4km' },
	{ minGiB: 15, primary: ['qwen38-27b-q3kxl', 'gpt-oss-20b'], fast: 'gpt-oss-20b', polish: 'bielik-11b-q8', code: 'gpt-oss-20b' },
	{ minGiB: 11, primary: ['gemma4-12b-q4kxl'], fast: 'gpt-oss-20b', polish: 'bielik-11b-q6k', code: 'ministral3-14b-q4km' },
	{ minGiB: 6, primary: ['qwen35-9b-q4km'], fast: 'qwen35-4b-q4km', polish: 'bielik-11b-q4km' },
	{ minGiB: 0, primary: ['qwen35-4b-q4km'], polish: 'bielik-minitron-7b-q4km' }
];
/** Apple tiers by RAM (report 04 §2.3.2). */
const APPLE_TIERS: { minRam: number; primary: string[]; fast?: string; polish?: string }[] = [
	{ minRam: 96, primary: ['gpt-oss-120b'], fast: 'gpt-oss-120b', polish: 'mistral-small4-q4km' },
	{ minRam: 48, primary: ['qwen38-27b-q8', 'qwen38-27b-q6k'], polish: 'bielik-11b-q8' },
	{ minRam: 32, primary: ['qwen38-27b-q4kxl', 'gemma4-26b-a4b-q3kxl'], fast: 'gpt-oss-20b', polish: 'bielik-11b-q8' },
	{ minRam: 24, primary: ['gemma4-26b-a4b-q3kxl', 'gemma4-12b-q4kxl'], fast: 'gpt-oss-20b', polish: 'bielik-11b-q8' },
	{ minRam: 16, primary: ['qwen35-9b-q4km'], polish: 'bielik-minitron-7b-q4km' },
	{ minRam: 0, primary: ['qwen35-4b-q4km'] }
];

export interface Recommendation {
	primary: Model;
	alternatives: { role: 'fast' | 'polish' | 'code'; model: Model }[];
	ctx: number;
}

export function recommend(hw: Hw, ctx = 32768): Recommendation {
	const pick = (ids: string[]) =>
		ids.map((id) => findModel(id)!).find((m) => fit(m, hw, ctx) === 'fits') ?? findModel(ids[ids.length - 1])!;
	let tier: { primary: string[]; fast?: string; polish?: string; code?: string };
	if (hw.gpu?.unified && hw.gpu.vendor === 'apple') tier = APPLE_TIERS.find((t) => hw.ramGiB >= t.minRam)!;
	else {
		const b = budget(hw).lo;
		tier = TIERS.find((t) => b >= t.minGiB)!;
	}
	const primary = pick(tier.primary);
	const alternatives: Recommendation['alternatives'] = [];
	for (const role of ['fast', 'polish', 'code'] as const) {
		const id = tier[role];
		const m = id ? findModel(id) : null;
		if (m && m.id !== primary.id && fit(m, hw, ctx) !== 'no') alternatives.push({ role, model: m });
	}
	return { primary, alternatives, ctx };
}

/** Seconds for an answer of `words` words at `tps` tokens/s. */
export function answerSeconds(words: number, tps: number, lang: 'pl' | 'en'): number {
	return (words * TOK_PER_WORD[lang]) / tps;
}

/**
 * Match a GPU name from a scan code or free text. Token-subset matching handles lspci's
 * ambiguous names ("Navi 31 [Radeon RX 7900 XT/7900 XTX/7900M]"); VRAM breaks the tie.
 */
export function matchGpu(name: string, vramGiB?: number | null): Gpu | null {
	const tokens = (s: string) =>
		new Set(
			s
				.toLowerCase()
				.replace(/\((tm|r)\)|nvidia|geforce|amd|ati|radeon|intel|graphics|laptop gpu|series|apple/g, ' ')
				.split(/[^a-z0-9+]+/)
				.filter(Boolean)
		);
	const q = tokens(name);
	if (q.size === 0) return null;
	const subset = (a: Set<string>, b: Set<string>) => [...a].every((t) => b.has(t));
	const hits = GPUS.filter((g) => {
		const n = tokens(g.name);
		return subset(n, q) || subset(q, n);
	});
	if (hits.length === 0) return null;
	const byVram = vramGiB ? hits.filter((g) => g.vram && Math.abs(g.vram - vramGiB) < 1.5) : [];
	const pool = byVram.length ? byVram : hits;
	// Rank: exact token match, then names fully contained in the query (most tokens = most
	// specific, "rtx 4070 ti super" over "rtx 4070"), then partial queries ("m4" → "Apple M4").
	const rank = (g: Gpu) => {
		const n = tokens(g.name);
		if (n.size === q.size && subset(n, q)) return 1e6;
		return subset(n, q) ? 1e3 + n.size : -n.size;
	};
	return pool.sort((a, b) => rank(b) - rank(a))[0];
}
