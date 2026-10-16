/**
 * Shapes of the generated cards registry (`cards.json`, written by `scripts/cards.ts`).
 * Shared by the build script and the site; pure types, no runtime code.
 */

/** One sourced number. `src` is `file:line`; nothing without a source is ever rendered. */
export interface Num {
	v: number;
	src: string;
	/** Per-prompt range printed as [lo–hi] next to the median. */
	lo?: number;
	hi?: number;
	/** Figure printed in parentheses next to the value (e.g. the Ollama measurement). */
	paren?: number;
	unit?: string;
}

/**
 * Columns of the benchmark sheet:
 * a0 = upstream llama.cpp with defaults ("typical app"), a1 = upstream with the best flags,
 * a2 = our fork with the a1 flags, profile = a2 + per-architecture settings,
 * ours = our fork (3060 tables), alt = a competing fork (Bonsai: Prism PTQ1_0).
 */
export type VariantKey = 'a0' | 'a1' | 'a2' | 'profile' | 'ours' | 'alt';

export interface Variant {
	key: VariantKey;
	decode?: Num;
	msStep?: Num;
	tokStep?: Num;
	pp512?: Num;
	pp4096?: Num;
	/** Time to first token, seconds (~2k-token prompt). */
	ttft?: Num;
	/** Seconds for a 500-word answer. */
	words500en?: Num;
	words500pl?: Num;
	vram?: Num;
	tg128?: Num;
	ppl?: Num;
	tg8k?: Num;
	tg32k?: Num;
	scorecard?: { file: string; variant: string; decode: number };
}

export type ModelKey = 'qwen38' | 'lfm25' | 'saluki' | 'bonsai' | 'nemotron';

export interface LongCtx {
	depths: number[];
	up: Num[];
	ours: Num[];
	kv: string;
}

export interface Kernels {
	up: Num;
	ours: Num;
	gpuMs: [Num, Num];
	gapMs: [Num, Num];
}

export interface Gain {
	flags: Num | null;
	engine: Num | null;
	total: Num | null;
	/** Cell texts as printed in the sheet (PL), for the small print. */
	text: [string, string, string];
	src: string;
}

export interface Run {
	model: ModelKey;
	title: string;
	quant: string;
	file?: Num;
	src: string;
	variants: Variant[];
	before: VariantKey;
	flags: VariantKey;
	ours: VariantKey;
	longCtx?: LongCtx;
	kernels?: Kernels;
	gain?: Gain;
}

export interface CardHw {
	powerW: Num;
	bwGBs: Num;
	pcie: string;
	/** The sheet's hardware line (PL), shown as small print. */
	line: string;
	src: string;
}

export interface NvidiaCard {
	id: string;
	heading: string;
	src: string;
	scorecard: string;
	hw: CardHw;
	runs: Run[];
}

export interface CardsFile {
	source: string;
	generated: string;
	method: { decode: string };
	correctness: {
		md5Diff: string;
		tbo3090: string;
		tbo5060: string;
		quality: Record<'saluki' | 'bonsai', { ours: Num; noise: Num }>;
	};
	lfmFormats5060: { file: string; gb: Num; up: Num | null; ours: Num | null; kld: Num; md5Same: boolean | null }[];
	/** Sheet values that disagree with the cloud scorecard beyond rounding. */
	checks: { card: string; model: string; variant: string; sheet: number; scorecard: number; file: string }[];
	cards: NvidiaCard[];
}
