/**
 * The NVIDIA results page (`/pl/nvidia/`, `/en/nvidia/`).
 *
 * Single source of the numbers: `product/SITE-NVIDIA.md` (branch `nvidia-2026-11`). Every value
 * carries the `file:line` it comes from, so each one can be checked against the repo. Nothing here
 * is invented: a missing value is `null` and the page prints an en dash.
 *
 * Measurement conditions (SITE-NVIDIA.md:29): t/s = median of 6 PL/EN prompts at T=1 (sampling as
 * in the chat app). "Dziś" = the model Enigma picked earlier on plain llama.cpp; "Enigma" = the
 * current pick; "z silnikiem Enigmy" = our CUDA engines (SITE-NVIDIA.md:88 — Linux x64 only).
 */

/** One row of the per-card table, exactly as in the source (SITE-NVIDIA.md:31-43). */
export interface NvidiaCard {
	/** Card id used by the cards explorer, for the internal link. */
	readonly id: string;
	/** Marketing-free card name: "RTX 5090". */
	readonly name: string;
	readonly vramGB: number;
	/** Model cell: name as the source spells it, plus a note when the row mixes two models. */
	readonly model: string;
	/** True for the 12 GB rows: the "Enigma" cell is Saluki and the engine cell is Bonsai 2 + MTP. */
	readonly mix?: boolean;
	/** Context cell: what "dziś" gave and what Enigma gives now, in tokens. */
	readonly ctxToday: number;
	readonly ctxNow: number;
	/**
	 * The three speeds. `null` = the source prints "–" (the row had no such measurement).
	 * `engineNote` replaces the plain number for the two Saluki/Bonsai rows, whose "engine"
	 * column is a different model (SITE-NVIDIA.md:39-41).
	 */
	readonly today: number | null;
	readonly enigma: number | null;
	readonly engine: number | null;
	/** Percent strings as the source prints them ("+63%"); empty when the row has no comparison. */
	readonly enigmaGain: string;
	readonly engineGain: string;
	/** Where each cell comes from. */
	readonly src: string;
}

/** SITE-NVIDIA.md:31-43 — the per-card table, one row per measured card. */
export const NVIDIA_CARDS: readonly NvidiaCard[] = [
	{
		id: 'rtx-5090',
		name: 'RTX 5090',
		vramGB: 32,
		model: 'Qwen3.8-27B UD-Q6_K',
		ctxToday: 262144,
		ctxNow: 262144,
		today: 62.5,
		enigma: 102.2,
		engine: 148.6,
		enigmaGain: '+63%',
		engineGain: '+138%',
		src: 'product/SITE-NVIDIA.md:33 · product/research/67-nvidia-vast-kampania.md:13'
	},
	{
		id: 'rtx-4090',
		name: 'RTX 4090',
		vramGB: 24,
		model: 'Qwen3.8-27B UD-Q4_K_XL',
		ctxToday: 262144,
		ctxNow: 262144,
		today: 46.9,
		enigma: 76.4,
		engine: 101.3,
		enigmaGain: '+63%',
		engineGain: '+116%',
		src: 'product/SITE-NVIDIA.md:34 · product/research/67-nvidia-vast-kampania.md:14'
	},
	{
		id: 'rtx-3090',
		name: 'RTX 3090',
		vramGB: 24,
		model: 'Qwen3.8-27B UD-Q4_K_XL',
		ctxToday: 245760,
		ctxNow: 262144,
		today: 40.9,
		enigma: 61.5,
		engine: 80.0,
		enigmaGain: '+50%',
		engineGain: '+95%',
		src: 'product/SITE-NVIDIA.md:35 · product/research/67-nvidia-vast-kampania.md:15'
	},
	{
		id: 'rtx-5080',
		name: 'RTX 5080',
		vramGB: 16,
		model: 'Qwen3.8-27B ISTA IQ3_XXS',
		ctxToday: 208896,
		ctxNow: 217088,
		today: 52.1,
		enigma: 58.8,
		engine: 81.6,
		enigmaGain: '+13%',
		engineGain: '+57%',
		src: 'product/SITE-NVIDIA.md:36 · product/research/67-nvidia-vast-kampania.md:16'
	},
	{
		id: 'rtx-5060-ti-16',
		name: 'RTX 5060 Ti',
		vramGB: 16,
		model: 'Qwen3.8-27B ISTA IQ3_XXS',
		ctxToday: 200704,
		ctxNow: 229376,
		today: 27.5,
		enigma: 31.4,
		engine: 43.4,
		enigmaGain: '+14%',
		engineGain: '+58%',
		src: 'product/SITE-NVIDIA.md:37 · product/research/67-nvidia-vast-kampania.md:17'
	},
	{
		id: 'rtx-4060-ti-16',
		name: 'RTX 4060 Ti',
		vramGB: 16,
		model: 'Qwen3.8-27B ISTA IQ3_XXS',
		ctxToday: 217088,
		ctxNow: 229376,
		today: 19.8,
		enigma: 24.0,
		engine: 36.3,
		enigmaGain: '+21%',
		engineGain: '+84%',
		src: 'product/SITE-NVIDIA.md:38 · product/research/67-nvidia-vast-kampania.md:18'
	},
	{
		id: 'rtx-4070',
		name: 'RTX 4070',
		vramGB: 12,
		model: 'Qwen3.8-27B (Bonsai 2 / Saluki)',
		ctxToday: 151552,
		ctxNow: 208896,
		today: null,
		enigma: 44.4,
		engine: 94.7,
		enigmaGain: '',
		engineGain: '',
		mix: true,
		src: 'product/SITE-NVIDIA.md:39 · product/research/67-nvidia-vast-kampania.md:19'
	},
	{
		id: 'rtx-3060-12',
		name: 'RTX 3060',
		vramGB: 12,
		model: 'Qwen3.8-27B (Bonsai 2 / Saluki)',
		ctxToday: 135168,
		ctxNow: 204800,
		today: null,
		enigma: 22.2,
		engine: 58.3,
		enigmaGain: '',
		engineGain: '×2,6',
		mix: true,
		src: 'product/SITE-NVIDIA.md:40 · product/research/67-nvidia-vast-kampania.md:20'
	},
	{
		id: 'rtx-2080-ti',
		name: 'RTX 2080 Ti',
		vramGB: 11,
		model: 'Qwen3.8-27B Bonsai 2',
		ctxToday: 131072,
		ctxNow: 155648,
		today: null,
		enigma: 39.6,
		engine: 78.0,
		enigmaGain: '',
		engineGain: '×2,0',
		src: 'product/SITE-NVIDIA.md:41 · product/research/67-nvidia-vast-kampania.md:21'
	},
	{
		id: 'rtx-3080',
		name: 'RTX 3080',
		vramGB: 10,
		model: 'Qwen3.5-9B Q6_K',
		ctxToday: 192512,
		ctxNow: 192512,
		today: null,
		enigma: 85.2,
		engine: null,
		enigmaGain: '',
		engineGain: '',
		src: 'product/SITE-NVIDIA.md:42 · product/research/67-nvidia-vast-kampania.md:22'
	},
	{
		id: 'rtx-3070',
		name: 'RTX 3070',
		vramGB: 8,
		model: 'Qwen3.5-9B Q4_K_M',
		ctxToday: 151552,
		ctxNow: 151552,
		today: null,
		enigma: 66.9,
		engine: null,
		enigmaGain: '',
		engineGain: '',
		src: 'product/SITE-NVIDIA.md:43 · product/research/67-nvidia-vast-kampania.md:23'
	}
] as const;

/** SITE-NVIDIA.md:39-41 — the two model names in the 12 GB rows, for the Saluki footnote. */
export const MODEL_MIX = { saluki: 'Saluki 27B', bonsai: 'Bonsai 2 27B' } as const;

/**
 * SITE-NVIDIA.md:17-25 — the numbers called out under the headline, in the source order.
 * Numeric on purpose: the page formats them per locale ("148,6" / "148.6"). `key` picks the
 * translation in the copy file.
 */
export type HeroStat =
	| { readonly key: 'r5090' | 'r4090'; readonly kind: 'tps'; readonly v: number; readonly model: string; readonly ctx: number }
	| { readonly key: 'vsllama'; readonly kind: 'pct'; readonly v: number; readonly model: string }
	| { readonly key: 'r3060'; readonly kind: 'x'; readonly v: number; readonly model: string }
	| { readonly key: 'ctx'; readonly kind: 'ctx'; readonly v: number; readonly model: string };

export const HERO_STATS: readonly HeroStat[] = [
	{ key: 'r5090', kind: 'tps', v: 148.6, model: 'RTX 5090 · Qwen3.8-27B (Q6_K)', ctx: 262144 /* SITE-NVIDIA.md:21 */ },
	{ key: 'r4090', kind: 'tps', v: 101.3, model: 'RTX 4090 · Qwen3.8-27B (Q4_K_XL)', ctx: 262144 /* SITE-NVIDIA.md:22 */ },
	{ key: 'vsllama', kind: 'pct', v: 47, model: 'RTX 5090 · Qwen3.8-27B · MTP' /* SITE-NVIDIA.md:23 */ },
	{ key: 'r3060', kind: 'x', v: 2.6, model: 'RTX 3060 · 12 GB · 22.2 → 58.3' /* SITE-NVIDIA.md:24 */ },
	{ key: 'ctx', kind: 'ctx', v: 262144, model: 'Qwen3.8-27B' /* SITE-NVIDIA.md:25 */ }
] as const;

/** SITE-NVIDIA.md:47 — the MoE row, whole model in VRAM, context 131 072. */
export const MOE = {
	model: 'LFM2.5-24B-A2B',
	ctx: 131072,
	src: 'product/SITE-NVIDIA.md:47 · product/research/67-nvidia-vast-kampania.md:114',
	rows: [
		{ id: 'rtx-4070', name: 'RTX 4070', tps: 179.3, src: 'product/SITE-NVIDIA.md:47' },
		{ id: 'rtx-5060-ti-16', name: 'RTX 5060 Ti', tps: 139.5, src: 'product/SITE-NVIDIA.md:47' },
		{ id: 'rtx-3060-12', name: 'RTX 3060', tps: 102.5, src: 'product/SITE-NVIDIA.md:47' }
	]
} as const;

/** SITE-NVIDIA.md:53-61 — model files and licences; licences re-checked on Hugging Face 2026-11-08. */
export interface NvidiaModel {
	readonly name: string;
	/** One or two Hugging Face links (the source sometimes lists a mirror). */
	readonly urls: readonly string[];
	/** Licence as printed on the page, per language (the Saluki row must say "non-commercial only"). */
	readonly licence: { readonly pl: string; readonly en: string };
	/** `nc` rows get the "non-commercial only" emphasis. */
	readonly nc: boolean;
	/** Extra sentence under the table, when the licence needs it. */
	readonly note?: 'lfm' | 'saluki';
	readonly src: string;
}

export const NVIDIA_MODELS: readonly NvidiaModel[] = [
	{
		name: 'Qwen3.8-27B (Unsloth UD)',
		urls: ['https://huggingface.co/unsloth/Qwen3.8-27B-GGUF'],
		licence: { pl: 'Apache-2.0', en: 'Apache-2.0' },
		nc: false,
		src: 'product/SITE-NVIDIA.md:55 · research/out/licencje.md:19'
	},
	{
		name: 'Qwen3.8-27B ISTA GSQ-RCO IQ3_XXS-mtp',
		urls: ['https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF'],
		licence: { pl: 'Apache-2.0', en: 'Apache-2.0' },
		nc: false,
		src: 'product/SITE-NVIDIA.md:56 · research/out/licencje.md:20'
	},
	{
		name: 'Ternary Bonsai 2 27B (PrismML), Q2_0',
		urls: ['https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf'],
		licence: { pl: 'Apache-2.0', en: 'Apache-2.0' },
		nc: false,
		src: 'product/SITE-NVIDIA.md:57 · research/out/licencje.md:21'
	},
	{
		name: 'Bonsai 2 27B PTQ1_0 + MTP head',
		urls: ['https://huggingface.co/sudoingx/Ternary-Bonsai-2-27B-PTQ1_0-MTP-GGUF'],
		licence: { pl: 'Apache-2.0', en: 'Apache-2.0' },
		nc: false,
		src: 'product/SITE-NVIDIA.md:58 · research/out/licencje.md:22'
	},
	{
		name: 'Underdog Saluki 27B + MTP',
		urls: ['https://huggingface.co/Kujira/Underdog-Saluki-27B-1.0-MTP-GGUF'],
		/* research/out/licencje.md:61-63 — the graft card says Apache-2.0, the weights' owner
		   switched the base to CC BY-NC 4.0 on 2026-11-05; the owner wins. */
		licence: { pl: 'CC BY-NC 4.0 — tylko niekomercyjnie (od 2026-11-05)', en: 'CC BY-NC 4.0 — non-commercial only (since 2026-11-05)' },
		nc: true,
		note: 'saluki',
		src: 'product/SITE-NVIDIA.md:59 · research/out/licencje.md:23'
	},
	{
		name: 'Qwen3.5-9B',
		urls: ['https://huggingface.co/unsloth/Qwen3.5-9B-GGUF'],
		licence: { pl: 'Apache-2.0', en: 'Apache-2.0' },
		nc: false,
		src: 'product/SITE-NVIDIA.md:60 · research/out/licencje.md:24'
	},
	{
		name: 'LFM2.5-24B-A2B',
		urls: ['https://huggingface.co/LiquidAI/LFM2.5-24B-A2B-GGUF', 'https://huggingface.co/unsloth/LFM2.5-24B-A2B-GGUF'],
		licence: { pl: 'LFM Open 1.0 (firmy poniżej 10 mln USD przychodu)', en: 'LFM Open 1.0 (companies under $10M revenue)' },
		nc: false,
		note: 'lfm',
		src: 'product/SITE-NVIDIA.md:61 · research/out/licencje.md:25'
	}
] as const;

/** SITE-NVIDIA.md:65 — the flags every recipe shares. */
export const RECIPE_BASE = 'llama-server -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c <context> -ub <batch> --jinja';

/** SITE-NVIDIA.md:67-74 — ready-made settings per memory class. */
export interface Recipe {
	readonly memClass: string;
	readonly engine: string;
	readonly flags: string;
	readonly env?: string;
	readonly batch: string;
	readonly src: string;
}

export const RECIPES: readonly Recipe[] = [
	{
		memClass: '32 GB, 24 GB',
		engine: 'llama.cpp b11856',
		flags: '--spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-n-ubatch 64',
		batch: '5090: 1024 · 4090/3090: 256',
		src: 'product/SITE-NVIDIA.md:69'
	},
	{
		memClass: '24–32 GB',
		engine: 'our fork + kvq + lean',
		flags:
			'--spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs',
		env: 'GGML_CUDA_KVQ=1 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1',
		batch: '5090: 512 · 4090/3090: 256',
		src: 'product/SITE-NVIDIA.md:70'
	},
	{
		memClass: '16 GB',
		engine: 'llama.cpp b11856',
		flags: 'no MTP',
		batch: '256',
		src: 'product/SITE-NVIDIA.md:71'
	},
	{
		memClass: '16 GB',
		engine: 'b12110 + lean',
		flags: '--spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-ubatch 64 -ctkd q4_0 -ctvd q4_0',
		batch: '256',
		src: 'product/SITE-NVIDIA.md:72'
	},
	{
		memClass: '11–12 GB',
		engine: 'PrismML b12128',
		flags: '--spec-type draft-mtp --spec-draft-n-max 2',
		batch: '4070/3060: 256 · 2080 Ti: 512',
		src: 'product/SITE-NVIDIA.md:73'
	},
	{
		memClass: 'LFM2.5',
		engine: 'llama.cpp',
		flags: '-ctk q8_0 -ctv q8_0 · 8–10 GB: --n-cpu-moe 20 (10 GB) / 26 (8 GB)',
		batch: '512',
		src: 'product/SITE-NVIDIA.md:74'
	}
] as const;

/** SITE-NVIDIA.md:88 — the engine release the "with our engine" column refers to. */
export const ENGINE_RELEASE = {
	url: 'https://github.com/jarojarojaro-jaro/KERNEL/releases/tag/enigma-engines-cuda-2026-11-07',
	tag: 'enigma-engines-cuda-2026-11-07',
	src: 'product/SITE-NVIDIA.md:88'
} as const;

/**
 * SITE-NVIDIA.md:86-93 — all six caveats. The page prints every one of them; do not shorten
 * the meaning, the numbers depend on them.
 */
export const CAVEATS = ['linux', 'power', 'seeds', 'fork16', 'saluki', 'bonsai'] as const;
export type CaveatKey = (typeof CAVEATS)[number];

/** SITE-NVIDIA.md:78-84 — the five method points. */
export const METHOD = ['mtp', 'ctx', 'kvq', 'model', 'real'] as const;
export type MethodKey = (typeof METHOD)[number];
