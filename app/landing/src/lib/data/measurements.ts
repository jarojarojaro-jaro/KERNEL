/**
 * Every performance number the site shows comes from this registry. Each entry names the file
 * and line it was copied from and the harness that produced it. Nothing here is rounded up,
 * extrapolated or invented; when two numbers come from different harnesses, `harness` says so
 * and the UI shows the warning next to the comparison.
 *
 * `M`: AMD Radeon RX 7900 XTX (gfx1100, 24 GB), Ryzen 7 5700X, Linux, our lab server.
 * `CARDS` (bottom): every measured GPU × model, NVIDIA from the generated cards.json, plus the XTX from `M`.
 */

import { TOK_PER_WORD } from '$lib/estimator';
import cardsFile from './cards.json';
import type { CardsFile, ModelKey, Num, Run, Variant, VariantKey } from './card-types';

export type Harness = 'serve_bench' | 'spec_sweep' | 'llama-bench' | 'long_ctx_bench' | 'unspecified';

export interface Measurement {
	id: string;
	model: string;
	quant: string;
	gpu: string;
	backend: string;
	build: string;
	config: { pl: string; en: string };
	value: number;
	unit: 't/s' | 'ms/step';
	harness: Harness;
	method: { pl: string; en: string };
	source: string;
	date: string;
}

const XTX = 'RX 7900 XTX';
const QWEN = 'Qwen3.8-27B';
const LFM = 'LFM2.5-24B-A2B';

export const M = {
	qwenUpstreamVulkanPlain: {
		id: 'qwenUpstreamVulkanPlain',
		model: QWEN,
		quant: 'UD-Q4_K_XL',
		gpu: XTX,
		backend: 'Vulkan (RADV)',
		build: 'upstream llama.cpp e60eff95f',
		config: { pl: 'bez spekulacji', en: 'no speculation' },
		value: 38.8,
		unit: 't/s',
		harness: 'serve_bench',
		method: {
			pl: 'serve_bench.py: llama-server, czat, temp 0, 256 tokenów, 3 przebiegi na prompt, mediana, z rozgrzewką; KV q4_0, flash attention',
			en: 'serve_bench.py: llama-server, chat, temp 0, 256 tokens, 3 runs per prompt, median, with warm-up; KV q4_0, flash attention'
		},
		source: 'KERNEL/qwen-opt/NOTES.md:48 (metoda: NOTES.md:3-4)',
		date: '2026-10'
	},
	qwenUpstreamVulkanMtp: {
		id: 'qwenUpstreamVulkanMtp',
		model: QWEN,
		quant: 'UD-Q4_K_XL',
		gpu: XTX,
		backend: 'Vulkan (RADV)',
		build: 'upstream llama.cpp e60eff95f',
		config: { pl: 'spekulacja MTP n=4, mieszanka promptów EN+PL', en: 'MTP speculation n=4, mixed EN+PL prompts' },
		value: 85.6,
		unit: 't/s',
		harness: 'serve_bench',
		method: {
			pl: 'serve_bench.py jak wyżej; prompty EN+PL',
			en: 'serve_bench.py as above; EN+PL prompts'
		},
		source: 'KERNEL/qwen-opt/NOTES.md:48-50',
		date: '2026-10'
	},
	qwenUpstreamRocmMtp: {
		id: 'qwenUpstreamRocmMtp',
		model: QWEN,
		quant: 'UD-Q4_K_XL',
		gpu: XTX,
		backend: 'ROCm (HIP)',
		build: 'upstream llama.cpp e60eff95f',
		config: { pl: 'spekulacja MTP n=3, prompty EN', en: 'MTP speculation n=3, EN prompts' },
		value: 68.6,
		unit: 't/s',
		harness: 'serve_bench',
		method: {
			pl: 'serve_bench.py jak wyżej; prompty angielskie',
			en: 'serve_bench.py as above; English prompts'
		},
		source: 'KERNEL/qwen-opt/NOTES.md:43',
		date: '2026-10'
	},
	qwenOursMtp: {
		id: 'qwenOursMtp',
		model: QWEN,
		quant: 'UD-Q4_K_XL',
		gpu: XTX,
		backend: 'ROCm (HIP)',
		build: 'amd-opt @ f61994f58 (70 łatek / 70 patches)',
		config: { pl: 'spekulacja MTP, KV q4_0', en: 'MTP speculation, KV q4_0' },
		value: 109.0,
		unit: 't/s',
		harness: 'spec_sweep',
		method: {
			pl: 'spec_sweep: 6 promptów × 3 seedy, T=1, świeży serwer (run-llm.sh), mediana',
			en: 'spec_sweep: 6 prompts × 3 seeds, T=1, fresh server (run-llm.sh), median'
		},
		source: 'KERNEL/qwen-opt/STATUS-NEXT.md:6,10',
		date: '2026-10-15'
	},
	qwenOursPlainTg128: {
		id: 'qwenOursPlainTg128',
		model: QWEN,
		quant: 'UD-Q4_K_XL',
		gpu: XTX,
		backend: 'ROCm (HIP)',
		build: 'amd-opt @ f61994f58',
		config: { pl: 'bez spekulacji', en: 'no speculation' },
		value: 43.2,
		unit: 't/s',
		harness: 'llama-bench',
		method: {
			pl: 'llama-bench -fa 1 -p 4096 -n 128 -r 2, KV jak w run-llm.sh',
			en: 'llama-bench -fa 1 -p 4096 -n 128 -r 2, KV as in run-llm.sh'
		},
		source: 'KERNEL/qwen-opt/STATUS-NEXT.md:7,10',
		date: '2026-10-15'
	},
	qwenOursPrefill: {
		id: 'qwenOursPrefill',
		model: QWEN,
		quant: 'UD-Q4_K_XL',
		gpu: XTX,
		backend: 'ROCm (HIP)',
		build: 'amd-opt @ f61994f58',
		config: { pl: 'prefill pp4096', en: 'prefill pp4096' },
		value: 1115,
		unit: 't/s',
		harness: 'llama-bench',
		method: {
			pl: 'llama-bench -fa 1 -p 4096 -n 128 -r 2',
			en: 'llama-bench -fa 1 -p 4096 -n 128 -r 2'
		},
		source: 'KERNEL/qwen-opt/STATUS-NEXT.md:10',
		date: '2026-10-15'
	},
	lfmUpstreamTg128: {
		id: 'lfmUpstreamTg128',
		model: LFM,
		quant: 'Q5_K_M',
		gpu: XTX,
		backend: 'ROCm (HIP)',
		build: 'upstream llama.cpp e60eff95f',
		config: { pl: 'bez spekulacji, KV q4_0', en: 'no speculation, KV q4_0' },
		value: 169.3,
		unit: 't/s',
		harness: 'llama-bench',
		method: {
			pl: 'llama-bench tg128, -fa 1, KV q4_0, 2 przeplatane rundy',
			en: 'llama-bench tg128, -fa 1, KV q4_0, 2 interleaved rounds'
		},
		source: 'KERNEL/qwen-opt/NOTES.md:339',
		date: '2026-10-14'
	},
	lfmOursTg128: {
		id: 'lfmOursTg128',
		model: LFM,
		quant: 'Q5_K_M',
		gpu: XTX,
		backend: 'ROCm (HIP)',
		build: 'amd-opt @ f61994f58',
		config: { pl: 'bez spekulacji, KV q8_0', en: 'no speculation, KV q8_0' },
		value: 289.7,
		unit: 't/s',
		harness: 'llama-bench',
		method: {
			pl: 'llama-bench -fa 1 -p 4096 -n 128 -r 2, KV q8_0 (wolniejszy od q4_0 o 2.6% przy głębokości 0, NOTES.md:354)',
			en: 'llama-bench -fa 1 -p 4096 -n 128 -r 2, KV q8_0 (2.6% slower than q4_0 at depth 0, NOTES.md:354)'
		},
		source: 'KERNEL/qwen-opt/STATUS-NEXT.md:12',
		date: '2026-10-15'
	},
	lfmOursServer: {
		id: 'lfmOursServer',
		model: LFM,
		quant: 'Q5_K_M',
		gpu: XTX,
		backend: 'ROCm (HIP)',
		build: 'amd-opt @ f61994f58',
		config: { pl: 'serwer, bez spekulacji, KV q8_0', en: 'server, no speculation, KV q8_0' },
		value: 293.7,
		unit: 't/s',
		harness: 'spec_sweep',
		method: {
			pl: 'spec_sweep: 6 promptów × 3 seedy, T=1, świeży serwer, mediana',
			en: 'spec_sweep: 6 prompts × 3 seeds, T=1, fresh server, median'
		},
		source: 'KERNEL/qwen-opt/STATUS-NEXT.md:6,12',
		date: '2026-10-15'
	},
	bacoAsleep: {
		id: 'bacoAsleep',
		model: QWEN,
		quant: 'UD-Q4_K_XL',
		gpu: XTX,
		backend: 'ROCm (HIP)',
		build: 'amd-opt',
		config: { pl: 'karta uśpiona (runtime PM / BACO), VRAM przeniesiona do RAM', en: 'card asleep (runtime PM / BACO), VRAM migrated to system RAM' },
		value: 4.4,
		unit: 't/s',
		harness: 'unspecified',
		method: {
			pl: 'NOTES nie podaje skryptu ani modelu tego pomiaru (plik dotyczy Qwen3.8-27B); traktujemy jako ilustrację skali awarii L0',
			en: 'NOTES does not name the script or model of this measurement (the file covers Qwen3.8-27B); shown only as an illustration of an L0 failure'
		},
		source: 'KERNEL/qwen-opt/NOTES.md:122-124',
		date: '2026-10-10'
	},
	bacoAwake: {
		id: 'bacoAwake',
		model: QWEN,
		quant: 'UD-Q4_K_XL',
		gpu: XTX,
		backend: 'ROCm (HIP)',
		build: 'amd-opt',
		config: { pl: 'ta sama konfiguracja, karta nie usypia', en: 'same configuration, card kept awake' },
		value: 92,
		unit: 't/s',
		harness: 'unspecified',
		method: { pl: 'jak wyżej', en: 'as above' },
		source: 'KERNEL/qwen-opt/NOTES.md:124',
		date: '2026-10-10'
	},
	/*
	 * Same script on all three sides (FinalBench, 2026-10-19): spec_sweep chat, 6 prompts × 3 seeds,
	 * T=1, fresh server each, ABBA order (two passes; the first pass is shown, the second agrees to
	 * ±0.2 t/s: 35.8 / 60.2 / 114.9). Logs on the lab server under ~/qwen-opt/queue/logs.
	 */
	qwenXtxDefault: {
		id: 'qwenXtxDefault',
		model: QWEN,
		quant: 'UD-Q4_K_XL',
		gpu: XTX,
		backend: 'ROCm (HIP)',
		build: 'upstream llama.cpp',
		config: { pl: 'ustawienia domyślne, bez spekulacji', en: 'default settings, no speculation' },
		value: 35.9,
		unit: 't/s',
		harness: 'spec_sweep',
		method: {
			pl: 'spec_sweep czat: 6 promptów × 3 seedy, T=1, świeży serwer, mediana; kolejność ABBA, pierwszy przebieg (drugi: 35,8)',
			en: 'spec_sweep chat: 6 prompts × 3 seeds, T=1, fresh server, median; ABBA order, first pass (second: 35.8)'
		},
		source: '~/qwen-opt/queue/logs/fb-qwen-U0-p1.log:2 (p2: fb-qwen-U0-p2.log:2)',
		date: '2026-10-19'
	},
	qwenXtxFlags: {
		id: 'qwenXtxFlags',
		model: QWEN,
		quant: 'UD-Q4_K_XL',
		gpu: XTX,
		backend: 'ROCm (HIP)',
		build: 'upstream llama.cpp',
		config: { pl: 'najlepsze flagi + spekulacja MTP', en: 'best flags + MTP speculation' },
		value: 60.0,
		unit: 't/s',
		harness: 'spec_sweep',
		method: {
			pl: 'spec_sweep czat jak wyżej; pierwszy przebieg (drugi: 60,2)',
			en: 'spec_sweep chat as above; first pass (second: 60.2)'
		},
		source: '~/qwen-opt/queue/logs/fb-qwen-U1-p1.log:2 (p2: fb-qwen-U1-p2.log:2)',
		date: '2026-10-19'
	},
	qwenXtxOurs: {
		id: 'qwenXtxOurs',
		model: QWEN,
		quant: 'UD-Q4_K_XL',
		gpu: XTX,
		backend: 'ROCm (HIP)',
		build: 'amd-opt (nasz silnik / our engine)',
		config: { pl: 'te same flagi + spekulacja MTP', en: 'the same flags + MTP speculation' },
		value: 114.8,
		unit: 't/s',
		harness: 'spec_sweep',
		method: {
			pl: 'spec_sweep czat jak wyżej; pierwszy przebieg (drugi: 114,9)',
			en: 'spec_sweep chat as above; first pass (second: 114.9)'
		},
		source: '~/qwen-opt/queue/logs/fb-qwen-T-p1.log:2 (p2: fb-qwen-T-p2.log:2)',
		date: '2026-10-19'
	}
} satisfies Record<string, Measurement>;

export type MeasurementId = keyof typeof M;

/** Numerics exceptions: changes that are NOT bit-identical, each with its KLD gate result. */
export const KLD_EXCEPTIONS = [
	{
		what: { pl: 'A4: prolog GDN w jednym kernelu (Qwen, ROCm)', en: 'A4: fused GDN prologue (Qwen, ROCm)' },
		result: { pl: 'KLD 0.0067 wobec szumu samej bazy 0.0098; PPL 6.182 vs 6.191', en: 'KLD 0.0067 vs base-only noise 0.0098; PPL 6.182 vs 6.191' },
		source: 'KERNEL/qwen-opt/NOTES.md:222-225'
	},
	{
		what: { pl: 'MMVQ Q6_K na Vulkanie (Qwen)', en: 'Q6_K MMVQ on Vulkan (Qwen)' },
		result: { pl: 'KLD 0.0042 wobec szumu batch 6 vs 512 0.0036; PPL 6.2226 → 6.2099', en: 'KLD 0.0042 vs batch 6 vs 512 noise 0.0036; PPL 6.2226 → 6.2099' },
		source: 'KERNEL/qwen-opt/NOTES.md:165-167'
	},
	{
		what: { pl: '0055: atencja kvq dla KV q8_0 (LFM)', en: '0055: kvq attention for q8_0 KV (LFM)' },
		result: { pl: 'KLD vs f16 KV 0.044196 (stary kernel 0.044171)', en: 'KLD vs f16 KV 0.044196 (old kernel 0.044171)' },
		source: 'KERNEL/qwen-opt/NOTES.md:363'
	}
] as const;

/** Greedy md5 prefixes after install (STATUS-NEXT.md:15). */
export const MD5 = { qwenPlain: 'c4708318', qwenMtp: '6f14e814', lfm: '894e56e4' } as const;


/* ======================================================================================
 * Cards registry (v2): every measured GPU × model with before / after, generated at build
 * time from KERNEL/product/BENCHMARKI-NVIDIA-2026-10-16.md (scripts/cards.ts) plus the
 * RX 7900 XTX entries above. The landing page and the cards explorer read ONLY this.
 * ==================================================================================== */


export type { CardsFile, ModelKey, Num, Run, Variant, VariantKey } from './card-types';

export const SHEET = cardsFile as unknown as CardsFile;

type L = { pl: string; en: string };

/** A registry entry as a sourced number. */
const n = (m: Measurement): Num => ({ v: m.value, src: m.source });
const SN = 'KERNEL/qwen-opt/STATUS-NEXT.md';

export interface RunView extends Run {
	/** What "decode" means for this run (script and conditions), small print. */
	metric: L;
	/** True when before and ours come from the same script and conditions. */
	sameHarness: boolean;
	/** Run conditions: context, KV cache, flags (small print). */
	conditions: L;
	conditionsSrc: string;
	note?: L;
	/** The sheet's "skąd zysk" cells (flags, engine, total) in both languages. */
	gainText?: { pl: [string, string, string]; en: [string, string, string] };
}

export interface CardView {
	id: string;
	name: string;
	/** Short label for tiles and pickers ("3090"). */
	short: string;
	vendor: 'nvidia' | 'amd';
	vramGB: number;
	arch: string;
	bwGBs: Num;
	powerW: Num;
	pcie?: string;
	hwLine?: L;
	hwSrc: string;
	runs: RunView[];
	/** Our editorial pick among the measured models, with the reason. */
	pick: { model: ModelKey; why: L };
}

const sheetCard = (id: string) => {
	const c = SHEET.cards.find((x) => x.id === id);
	if (!c) throw new Error(`cards.json has no ${id}; run bun scripts/sync-results.ts`);
	return c;
};
const SPEC_SWEEP: L = {
	pl: 'spec_sweep przez serwer: 6 promptów × 3 seedy, T=1, odpowiedź 400 tokenów, krótki kontekst, mediana',
	en: 'spec_sweep through the server: 6 prompts × 3 seeds, T=1, 400-token answers, short context, median'
};
const BS = 'KERNEL/product/BENCHMARKI-NVIDIA-2026-10-16.md';
const NR = 'KERNEL/product/research/14-nemotron-3090.md';

/**
 * English for the sheet's Polish prose cells (hardware line, gain notes). Word substitution only,
 * so every figure stays exactly as printed in the sheet; `.` decimals are already English.
 */
const SHEET_EN: [RegExp, string][] = [
	[/limit mocy/g, 'power limit'],
	[/pamięć/g, 'memory'],
	[/CPU hosta/g, 'host CPU'],
	[/sterownik/g, 'driver'],
	[/kontener z limitem/g, 'container limited to'],
	[/stale na limicie/g, 'constantly at the limit'],
	[/słownik draftu/g, 'draft vocabulary'],
	[/kod forka/g, 'fork code'],
	[/profil Ampere/g, 'Ampere profile'],
	[/profil/g, 'profile'],
	[/fuzje/g, 'fusions'],
	[/ na Q2_0/g, ' on Q2_0'],
	[/łatki/g, 'patches'],
	[/vs domyślny Prism/g, 'vs default Prism']
];
const toEn = (s: string) => SHEET_EN.reduce((t, [re, en]) => t.replace(re, en), s);

/**
 * A newer same-script session that replaces the sheet's run for one model completely (variants,
 * gain, long context); only fields of the sheet run that the session did not measure again and that
 * do not depend on the build (title, file, kernel profile) are kept.
 */
interface Final {
	variants: Variant[];
	before: VariantKey;
	flags: VariantKey;
	ours: VariantKey;
	src: string;
	metric: L;
	gain?: Run['gain'];
	longCtx?: Run['longCtx'];
	kernels?: Run['kernels'];
}

function nvidia(
	id: string,
	meta: Pick<CardView, 'name' | 'short' | 'vramGB' | 'arch' | 'pick'>,
	conditions: Partial<Record<ModelKey, { c: L; src: string; note?: L; final?: Final }>>
): CardView {
	const c = sheetCard(id);
	return {
		id,
		vendor: 'nvidia',
		...meta,
		bwGBs: c.hw.bwGBs,
		powerW: c.hw.powerW,
		pcie: c.hw.pcie,
		hwLine: { pl: c.hw.line, en: toEn(c.hw.line) },
		hwSrc: c.hw.src,
		runs: c.runs.filter((sheet) => conditions[sheet.model]).map((sheet) => {
			const k = conditions[sheet.model]!;
			const f = k.final;
			const r: Run = f ? { model: sheet.model, title: sheet.title, quant: sheet.quant, file: sheet.file, kernels: sheet.kernels, ...f } : sheet;
			return {
				...r,
				metric: f?.metric ?? SPEC_SWEEP,
				sameHarness: true,
				conditions: k.c,
				conditionsSrc: k.src,
				...(r.gain ? { gainText: { pl: r.gain.text, en: r.gain.text.map(toEn) as [string, string, string] } } : {}),
				...(k.note ? { note: k.note } : {})
			};
		})
	};
}

/*
 * RTX 3090 final session (2026-10-19/20, report 27): upstream default (U0), upstream
 * with production flags + its own MTP (U1) and our engine (T), fresh servers in ABBA order; values are
 * the mean of the two passes. Logs are copied into the repo under qwen-opt/cloud/results/nv-final-*.
 */
const R27 = 'KERNEL/product/research/27-3090-final.md';
const NV3090 = 'KERNEL/qwen-opt/cloud/results/nv-final-3090-qwen-20261019/logs';
const NV3090L = 'KERNEL/qwen-opt/cloud/results/nv-final-3090-qwen60k-20261020/logs';
const s3090 = (log: string, line: number) => `${NV3090}/${log}; ${R27}:${line}`;
/** nvidia-smi MiB after load as GiB (shown as GB with the site's GiB note). */
const mib = (v: number, src: string): Num => ({ v: Math.round((v / 1024) * 10) / 10, src: `${src} (${v} MiB)`, unit: 'GiB' });
const SPEC_SWEEP_ABBA: L = {
	pl: 'spec_sweep przez serwer, ten sam skrypt po obu stronach: czat, 6 promptów × 3 seedy, T=1, świeży serwer, mediana; kolejność ABBA, średnia z dwóch przebiegów',
	en: 'spec_sweep through the server, the same script on both sides: chat, 6 prompts × 3 seeds, T=1, fresh server, median; ABBA order, mean of the two passes'
};
const LB = (u: string, t: string) => `${NV3090}/${u} / ${t}`;
const FINAL_3090_QWEN: Final = {
	src: s3090('spec_sweep.jsonl', 59),
	before: 'a0',
	flags: 'a1',
	ours: 'a2',
	metric: SPEC_SWEEP_ABBA,
	variants: [
		{
			key: 'a0',
			decode: { v: 42.9, src: s3090('spec_sweep.jsonl (qwen.U0.p1/p2)', 59) },
			msStep: { v: 23.29, src: s3090('spec_sweep.jsonl', 60) },
			tokStep: { v: 1, src: s3090('spec_sweep.jsonl', 61) },
			pp512: { v: 1584.5, src: `${LB('lb.qwen.U.r1,r4.jsonl', 'lb.qwen.T.r2,r3.jsonl')}; ${R27}:98` },
			pp4096: { v: 1581.5, src: `${LB('lb.qwen.U.r1,r4.jsonl', 'lb.qwen.T.r2,r3.jsonl')}; ${R27}:99` },
			ttft: { v: 1.23, src: s3090('long.jsonl (prompt 1747 tok)', 90), unit: 's' },
			tg128: { v: 43.1, src: `${LB('lb.qwen.U.r1,r4.jsonl', 'lb.qwen.T.r2,r3.jsonl')}; ${R27}:100` },
			vram: mib(22545, s3090('vram.jsonl', 104))
		},
		{
			key: 'a1',
			decode: { v: 75.3, src: s3090('spec_sweep.jsonl (qwen.U1.p1/p2)', 59) },
			msStep: { v: 43.4, src: s3090('spec_sweep.jsonl', 60) },
			tokStep: { v: 3.27, src: s3090('spec_sweep.jsonl', 61) },
			pp512: { v: 1584.5, src: `${LB('lb.qwen.U.r1,r4.jsonl', 'lb.qwen.T.r2,r3.jsonl')}; ${R27}:98 (U1 = U0, the same binary)` },
			pp4096: { v: 1581.5, src: `${LB('lb.qwen.U.r1,r4.jsonl', 'lb.qwen.T.r2,r3.jsonl')}; ${R27}:99 (U1 = U0, the same binary)` },
			ttft: { v: 1.43, src: s3090('long.jsonl (prompt 1747 tok)', 90), unit: 's' },
			vram: mib(23129, s3090('vram.jsonl', 104))
		},
		{
			key: 'a2',
			decode: { v: 93.3, src: s3090('spec_sweep.jsonl (qwen.T.p1/p2)', 59) },
			msStep: { v: 32.36, src: s3090('spec_sweep.jsonl', 60) },
			tokStep: { v: 3.03, src: s3090('spec_sweep.jsonl', 61) },
			pp512: { v: 1540.4, src: `${LB('lb.qwen.U.r1,r4.jsonl', 'lb.qwen.T.r2,r3.jsonl')}; ${R27}:98` },
			pp4096: { v: 1542.5, src: `${LB('lb.qwen.U.r1,r4.jsonl', 'lb.qwen.T.r2,r3.jsonl')}; ${R27}:99` },
			ttft: { v: 1.6, src: s3090('long.jsonl (prompt 1747 tok)', 90), unit: 's' },
			tg128: { v: 45.9, src: `${LB('lb.qwen.U.r1,r4.jsonl', 'lb.qwen.T.r2,r3.jsonl')}; ${R27}:100` },
			vram: mib(23493, s3090('vram.jsonl', 104))
		}
	],
	gain: {
		flags: { v: 75.3 / 42.9, src: `${R27}:59 (75.3 / 42.9)` },
		engine: { v: 93.3 / 75.3, src: `${R27}:59 (93.3 / 75.3)` },
		total: { v: 93.3 / 42.9, src: `${R27}:59 (93.3 / 42.9)` },
		text: ['×1.76 (MTP)', '×1.24 (lookup W16, share, GPU verify)', '×2.17'],
		src: `${R27}:20,59`
	},
	/** llama-bench tg128 at a filled context, no speculation (upstream vs ours, the same binary as U0/U1). */
	longCtx: {
		depths: [0, 16384, 32768, 65536],
		up: [
			{ v: 43.1, src: `${NV3090}/lb.qwen.U.r1,r4.jsonl; ${R27}:100` },
			{ v: 39.1, src: `${NV3090}/lbd.qwen.U.r1,r4.jsonl; ${R27}:101` },
			{ v: 35.7, src: `${NV3090}/lbd.qwen.U.r1,r4.jsonl; ${R27}:102` },
			{ v: 30.4, src: `${NV3090}/lbd.qwen.U.r1,r4.jsonl; ${R27}:103` }
		],
		ours: [
			{ v: 45.9, src: `${NV3090}/lb.qwen.T.r2,r3.jsonl; ${R27}:100` },
			{ v: 41.4, src: `${NV3090}/lbd.qwen.T.r2,r3.jsonl; ${R27}:101` },
			{ v: 37.7, src: `${NV3090}/lbd.qwen.T.r2,r3.jsonl; ${R27}:102` },
			{ v: 31.9, src: `${NV3090}/lbd.qwen.T.r2,r3.jsonl; ${R27}:103` }
		],
		kv: 'KV q4_0'
	}
};
/*
 * RTX 4060 Ti 16 GB (report 29, 2026-10-20): the nv-final harness of report 27 on a rented card
 * (power limit 100 W set by the host, PCIe gen3 x8), U0 / U1 / T in ABBA order, mean of the two
 * passes; the same GGUF files as the 5060 Ti. Not in the 10-16 sheet, so the card is written out
 * here instead of going through nvidia().
 */
const R29 = 'KERNEL/product/research/29-4060ti.md';
const NV4060 = 'KERNEL/qwen-opt/cloud/results/nv-final-4060ti-20261020/logs';
const s4060 = (log: string, line: number) => `${NV4060}/${log}; ${R29}:${line}`;
const LB4060 = (m: string, line: number) => `${NV4060}/lb.${m}.U.r1,r4.jsonl / lb.${m}.T.r2,r3.jsonl; ${R29}:${line}`;
const COND_4060: L = {
	pl: 'najlepsze flagi i nasz silnik: kontekst 32k (-c 32768), KV q8_0, -fit off, -fa on; nasz dodatkowo GPU verify; A0: samo -m (domyślny -fit, KV f16); karta z limitem mocy 100 W, PCIe gen3 x8',
	en: 'best flags and our engine: 32k context (-c 32768), KV q8_0, -fit off, -fa on; ours adds GPU verify; A0: plain -m (default -fit, KV f16); card power-limited to 100 W, PCIe gen3 x8'
};
const RTX_4060TI: CardView = {
	id: 'rtx-4060-ti-16',
	name: 'GeForce RTX 4060 Ti 16 GB',
	short: '4060 Ti',
	vendor: 'nvidia',
	vramGB: 16,
	arch: 'Ada sm_89',
	bwGBs: { v: 288, src: `${R29}:25; app/landing/src/lib/data/gpus.json` },
	powerW: { v: 100, src: `${R29}:25-26` },
	pcie: 'gen3 x8',
	hwLine: {
		pl: 'limit mocy 100 W (host; domyślnie 165 W), PCIe gen3 x8, GDDR6 288 GB/s, CPU hosta Ryzen 9 3950X, sterownik 595.84',
		en: 'power limit 100 W (host; default 165 W), PCIe gen3 x8, GDDR6 288 GB/s, host CPU Ryzen 9 3950X, driver 595.84'
	},
	hwSrc: `${R29}:25-28`,
	pick: { model: 'qwen38', why: { pl: 'Qwen w Q3 mieści się w 16 GB z kontekstem 32k i jest tu 1,9× szybszy niż typowa aplikacja.', en: 'Qwen at Q3 fits in 16 GB with a 32k context and is 1.9× faster here than the typical app.' } },
	runs: [
		{
			model: 'qwen38',
			title: 'Qwen3.8-27B UD-Q3_K_XL (13.15 GB)',
			quant: 'UD-Q3_K_XL',
			file: { v: 13.15, src: `${R29}:52`, unit: 'GB' },
			src: s4060('spec_sweep.jsonl', 56),
			before: 'a0',
			flags: 'a1',
			ours: 'a2',
			variants: [
				{
					key: 'a0',
					decode: { v: 18.6, src: s4060('spec_sweep.jsonl (qwen.U0.p1/p2)', 56) },
					msStep: { v: 53.67, src: s4060('spec_sweep.jsonl', 57) },
					tokStep: { v: 1, src: s4060('spec_sweep.jsonl', 58) },
					pp512: { v: 793.7, src: LB4060('qwen', 66) },
					pp4096: { v: 788.4, src: LB4060('qwen', 67) },
					tg128: { v: 18.8, src: LB4060('qwen', 68) },
					vram: mib(14354, s4060('vram.jsonl', 70))
				},
				{
					key: 'a1',
					decode: { v: 30.6, src: s4060('spec_sweep.jsonl (qwen.U1.p1/p2)', 56) },
					msStep: { v: 97.74, src: s4060('spec_sweep.jsonl', 57) },
					tokStep: { v: 2.99, src: s4060('spec_sweep.jsonl', 58) },
					vram: mib(14570, s4060('vram.jsonl', 70))
				},
				{
					key: 'a2',
					decode: { v: 35.4, src: s4060('spec_sweep.jsonl (qwen.T.p1/p2)', 56) },
					msStep: { v: 81.56, src: s4060('spec_sweep.jsonl', 57) },
					tokStep: { v: 2.88, src: s4060('spec_sweep.jsonl', 58) },
					pp512: { v: 762.7, src: LB4060('qwen', 66) },
					pp4096: { v: 760.7, src: LB4060('qwen', 67) },
					tg128: { v: 18.7, src: LB4060('qwen', 68) },
					vram: mib(14848, s4060('vram.jsonl', 70))
				}
			],
			gain: {
				flags: { v: 30.6 / 18.6, src: `${R29}:56 (30.6 / 18.6)` },
				engine: { v: 35.4 / 30.6, src: `${R29}:56 (35.4 / 30.6)` },
				total: { v: 35.4 / 18.6, src: `${R29}:56 (35.4 / 18.6)` },
				text: ['×1.65 (MTP)', '×1.16 (słownik draftu 64k, lookup W16, GPU verify)', '×1.90'],
				src: `${R29}:9-11,56`
			},
			gainText: {
				pl: ['×1,65 (MTP)', '×1,16 (słownik draftu 64k, lookup W16, GPU verify)', '×1,90'],
				en: ['×1.65 (MTP)', '×1.16 (64k draft vocabulary, lookup W16, GPU verify)', '×1.90']
			},
			longCtx: {
				depths: [0, 16384],
				up: [
					{ v: 18.8, src: LB4060('qwen', 68) },
					{ v: 16.8, src: `${NV4060}/lbd.qwen.U.r1,r4.jsonl; ${R29}:69` }
				],
				ours: [
					{ v: 18.7, src: LB4060('qwen', 68) },
					{ v: 16.8, src: `${NV4060}/lbd.qwen.T.r2,r3.jsonl; ${R29}:69` }
				],
				kv: 'KV q8_0'
			},
			metric: SPEC_SWEEP_ABBA,
			sameHarness: true,
			conditions: {
				pl: `${COND_4060.pl}; MTP n=4, nasz: słownik draftu 64k, głowice IQ4_XS, lookup W16`,
				en: `${COND_4060.en}; MTP n=4, ours: 64k draft vocabulary, IQ4_XS heads, lookup W16`
			},
			conditionsSrc: `${R29}:37-47; ${NV4060}/vram.jsonl`,
			note: {
				pl: 'Ten sam skrypt, inne zadania: edycja kodu (T=0) 18,5 → 50,0 → 170,9 t/s; generowanie po 16k kontekstu (T=0) 17,6 → 33,3 → 40,1 t/s. Uczciwie: zysk nad najlepszymi flagami to krótszy krok (81,6 wobec 97,7 ms), nie więcej tokenów na krok; prefill jest u nas o 3,5–3,9% wolniejszy, a bez spekulacji (llama-bench tg128) tempo jest takie samo.',
				en: 'The same script, other tasks: code edits (T=0) 18.5 → 50.0 → 170.9 t/s; generation after a 16k context (T=0) 17.6 → 33.3 → 40.1 t/s. Honestly: the gain over the best flags is a shorter step (81.6 vs 97.7 ms), not more tokens per step; our prefill is 3.5–3.9% slower, and without speculation (llama-bench tg128) the pace is the same.'
			}
		},
		{
			model: 'lfm25',
			title: 'LFM2.5-24B-A2B QAD-Q4_0 (13.58 GB)',
			quant: 'QAD-Q4_0',
			file: { v: 13.58, src: `${R29}:73`, unit: 'GB' },
			src: s4060('spec_sweep.jsonl', 77),
			before: 'a0',
			flags: 'a1',
			ours: 'a2',
			variants: [
				{
					key: 'a0',
					decode: { v: 114.4, src: s4060('spec_sweep.jsonl (lfm.U0.p1/p2)', 77) },
					msStep: { v: 8.74, src: s4060('spec_sweep.jsonl', 78) },
					pp512: { v: 3286.3, src: LB4060('lfm', 79) },
					pp4096: { v: 3272.8, src: LB4060('lfm', 80) },
					tg128: { v: 143.0, src: LB4060('lfm', 81) },
					vram: mib(14944, s4060('vram.jsonl', 82))
				},
				{
					key: 'a1',
					decode: { v: 113.3, src: s4060('spec_sweep.jsonl (lfm.U1.p1/p2)', 77) },
					msStep: { v: 8.82, src: s4060('spec_sweep.jsonl', 78) },
					vram: mib(13914, s4060('vram.jsonl', 82))
				},
				{
					key: 'a2',
					decode: { v: 149.4, src: s4060('spec_sweep.jsonl (lfm.T.p1/p2)', 77) },
					msStep: { v: 6.69, src: s4060('spec_sweep.jsonl', 78) },
					pp512: { v: 3278.4, src: LB4060('lfm', 79) },
					pp4096: { v: 3267.8, src: LB4060('lfm', 80) },
					tg128: { v: 155.1, src: LB4060('lfm', 81) },
					vram: mib(13924, s4060('vram.jsonl', 82))
				}
			],
			gain: {
				flags: { v: 113.3 / 114.4, src: `${R29}:77 (113.3 / 114.4)` },
				engine: { v: 149.4 / 113.3, src: `${R29}:77 (149.4 / 113.3)` },
				total: { v: 149.4 / 114.4, src: `${R29}:77 (149.4 / 114.4)` },
				text: ['×0.99', '×1.32 (sampler + kernele)', '×1.31'],
				src: `${R29}:14-15,77`
			},
			gainText: {
				pl: ['×0,99', '×1,32 (sampler + kernele)', '×1,31'],
				en: ['×0.99', '×1.32 (sampler + kernels)', '×1.31']
			},
			metric: SPEC_SWEEP_ABBA,
			sameHarness: true,
			conditions: { pl: `${COND_4060.pl}; bez spekulacji, -b 2048 -ub 2048`, en: `${COND_4060.en}; no speculation, -b 2048 -ub 2048` },
			conditionsSrc: `${R29}:37-47; ${NV4060}/vram.jsonl`
		}
	]
};

/*
 * The NVIDIA campaign on rented cards (report 67, 2026-11-06/07): eleven cards, each with the
 * settings Enigma ships today. One seed per setting (6 PL/EN prompts × 400 tokens, T=1, median);
 * every final setting passed a full-context fill (prompt = context − 640 tokens) on that card.
 * "Typical app" = plain llama.cpp without speculation (the pick Enigma ran before the campaign),
 * "best flags" = plain llama.cpp with MTP, "our engine" = the CUDA engines of the
 * enigma-engines-cuda-2026-11-07 release (fork + kvq + lean, lean, Prism + MTP head; Linux x64).
 * Power limits are the rented hosts' (§2), so cards capped below default read low.
 */
const R67 = 'KERNEL/product/research/67-nvidia-vast-kampania.md';
const r67 = (lines: string) => `${R67}:${lines}`;
const SPEC_67: L = {
	pl: 'spec_sweep przez serwer, ten sam skrypt po obu stronach: czat, 6 promptów PL/EN, 1 seed, T=1, odpowiedź 400 tokenów, mediana; każde końcowe ustawienie przeszło test pełnego wypełnienia kontekstu',
	en: 'spec_sweep through the server, the same script on both sides: chat, 6 PL/EN prompts, 1 seed, T=1, 400-token answers, median; every final setting passed a full-context fill test'
};
const BONSAI_67_LABELS: Run['labels'] = {
	a1: { pl: 'Typowa aplikacja', en: 'Typical app' },
	alt: { pl: 'Fork Prism, plik PTQ1_0', en: 'Prism fork, PTQ1_0 file' },
	ours: { pl: 'Nasz silnik', en: 'Our engine' }
};
/** A ratio with its arithmetic as the source, the way the 4060 Ti card states its gain. */
const x = (a: number, b: number, line: string): Num => ({ v: a / b, src: `${r67(line)} (${a} / ${b})` });
/** Shared shape of a card measured only in report 67. */
function card67(meta: Omit<CardView, 'vendor' | 'hwSrc'> & { hwLines: string }): CardView {
	const { hwLines, ...rest } = meta;
	return { vendor: 'nvidia', hwSrc: r67(hwLines), ...rest };
}
/** One measured setting and nothing to compare it with (no engine of ours for this card yet). */
function single67(model: ModelKey, title: string, quant: string, decode: Num, vram: Num, c: L, line: string): RunView {
	return { model, title, quant, src: r67(line), variants: [{ key: 'a0', decode, vram }], before: 'a0', flags: 'a0', ours: 'a0', metric: SPEC_67, sameHarness: true, conditions: c, conditionsSrc: r67(line) };
}

const RTX_5090: CardView = card67({
	id: 'rtx-5090',
	name: 'GeForce RTX 5090',
	short: '5090',
	vramGB: 32,
	arch: 'Blackwell sm_120',
	bwGBs: { v: 1792, src: 'app/landing/src/lib/data/gpus.json (raport 04 §2.1.6)' },
	powerW: { v: 575, src: r67('46') },
	hwLine: { pl: 'limit mocy 575 W (domyślnie 575 W), wynajęta karta (Vast)', en: 'power limit 575 W (default 575 W), rented card (Vast)' },
	hwLines: '46',
	pick: { model: 'qwen38', why: { pl: 'Pełny kontekst 262 144 tokenów w najlepszej jakości (Q6_K): 2,4× szybciej niż typowa aplikacja.', en: 'The full 262,144-token context at the best quality (Q6_K): 2.4× faster than the typical app.' } },
	runs: [
		{
			model: 'qwen38',
			title: 'Qwen3.8-27B UD-Q6_K',
			quant: 'UD-Q6_K',
			src: r67('13'),
			before: 'a0',
			flags: 'a1',
			ours: 'ours',
			variants: [
				{ key: 'a0', decode: { v: 62.49, src: r67('13') } },
				{ key: 'a1', decode: { v: 102.19, src: r67('13') }, vram: mib(28592, r67('13')) },
				{ key: 'ours', decode: { v: 148.57, src: r67('13,97') }, vram: mib(28232, r67('13,97')) }
			],
			gain: { flags: x(102.19, 62.49, '13'), engine: x(148.57, 102.19, '13'), total: x(148.57, 62.49, '13'), text: ['×1,64 (MTP n=3)', '×1,45 (fork + kvq + lean)', '×2,38'], src: r67('13,97') },
			gainText: { pl: ['×1,64 (MTP n=3)', '×1,45 (fork + kvq + lean)', '×2,38'], en: ['×1.64 (MTP n=3)', '×1.45 (fork + kvq + lean)', '×2.38'] },
			metric: SPEC_67,
			sameHarness: true,
			conditions: {
				pl: 'kontekst 262 144, KV q4_0, -fa on; typowa aplikacja (llama.cpp bez spekulacji); najlepsze flagi (MTP n=3, -ub 1024); nasz silnik (fork CUDA + kvq + lean, -ub 512); karta 575 W',
				en: '262k context (-c 262144), KV q4_0, -fa on; typical app (llama.cpp without speculation); best flags (MTP n=3, -ub 1024); our engine (CUDA fork + kvq + lean, -ub 512); card at 575 W'
			},
			conditionsSrc: r67('13,31,46,97'),
			note: {
				pl: 'Na tym samym hoście, naprzemiennie (ABBA): najlepsze flagi 100,90 i 100,61 t/s, nasz silnik 148,57 t/s (+47%). Pełne wypełnienie 262 144 tokenów przeszło na obu ustawieniach. Jeden seed na pomiar.',
				en: 'On the same host, alternating (ABBA): best flags 100.90 and 100.61 t/s, our engine 148.57 t/s (+47%). A full 262,144-token fill passed on both settings. One seed per measurement.'
			}
		}
	]
});

const RTX_4090: CardView = card67({
	id: 'rtx-4090',
	name: 'GeForce RTX 4090',
	short: '4090',
	vramGB: 24,
	arch: 'Ada sm_89',
	bwGBs: { v: 1008, src: 'app/landing/src/lib/data/gpus.json (raport 04 §2.1.6)' },
	powerW: { v: 250, src: r67('46') },
	hwLine: { pl: 'limit mocy 250 W (domyślnie 450 W), wynajęta karta (Vast)', en: 'power limit 250 W (default 450 W), rented card (Vast)' },
	hwLines: '46',
	pick: { model: 'qwen38', why: { pl: 'Najlepsza jakość z pełnym kontekstem 262 144 tokenów na 24 GB: 2,2× szybciej niż typowa aplikacja.', en: 'The best quality with the full 262,144-token context on 24 GB: 2.2× faster than the typical app.' } },
	runs: [
		{
			model: 'qwen38',
			title: 'Qwen3.8-27B UD-Q4_K_XL',
			quant: 'UD-Q4_K_XL',
			src: r67('14'),
			before: 'a0',
			flags: 'a1',
			ours: 'ours',
			variants: [
				{ key: 'a0', decode: { v: 46.94, src: r67('14') } },
				{ key: 'a1', decode: { v: 76.44, src: r67('14') }, vram: mib(24028, r67('14')) },
				{ key: 'ours', decode: { v: 101.27, src: r67('14,95') }, vram: mib(23852, r67('14,95')) }
			],
			gain: { flags: x(76.44, 46.94, '14'), engine: x(101.27, 76.44, '14'), total: x(101.27, 46.94, '14'), text: ['×1,63 (MTP n=3)', '×1,32 (fork + kvq + lean)', '×2,16'], src: r67('14,95') },
			gainText: { pl: ['×1,63 (MTP n=3)', '×1,32 (fork + kvq + lean)', '×2,16'], en: ['×1.63 (MTP n=3)', '×1.32 (fork + kvq + lean)', '×2.16'] },
			metric: SPEC_67,
			sameHarness: true,
			conditions: {
				pl: 'kontekst 262 144, KV q4_0, -fa on, -ub 256; typowa aplikacja (llama.cpp bez spekulacji); najlepsze flagi (MTP n=3); nasz silnik (fork CUDA + kvq + lean, MTP n=4, KV draftu q4_0, słownik draftu 64k); karta przycięta do 250 W',
				en: '262k context (-c 262144), KV q4_0, -fa on, -ub 256; typical app (llama.cpp without speculation); best flags (MTP n=3); our engine (CUDA fork + kvq + lean, MTP n=4, draft KV q4_0, 64k draft vocabulary); card capped at 250 W'
			},
			conditionsSrc: r67('14,46,85,95'),
			note: {
				pl: 'Karta miała limit 250 W zamiast domyślnych 450 W, więc na pełnej mocy wyniki będą wyższe. Przy kontekście 65 536: najlepsze flagi 76,13 t/s, nasz silnik 100,56 t/s. Jeden seed na pomiar.',
				en: 'The card was capped at 250 W instead of the default 450 W, so at full power the results will be higher. At a 65,536 context: best flags 76.13 t/s, our engine 100.56 t/s. One seed per measurement.'
			}
		}
	]
});

const RTX_5080: CardView = card67({
	id: 'rtx-5080',
	name: 'GeForce RTX 5080',
	short: '5080',
	vramGB: 16,
	arch: 'Blackwell sm_120',
	bwGBs: { v: 960, src: 'app/landing/src/lib/data/gpus.json (specyfikacja producenta)' },
	powerW: { v: 250, src: r67('46') },
	hwLine: { pl: 'limit mocy 250 W (domyślnie 360 W), wynajęta karta (Vast)', en: 'power limit 250 W (default 360 W), rented card (Vast)' },
	hwLines: '46',
	pick: { model: 'qwen38', why: { pl: 'Qwen3.8-27B w 3 bitach mieści się w 16 GB z kontekstem ponad 200 000 tokenów: 1,6× szybciej niż wcześniej.', en: 'Qwen3.8-27B at 3 bits fits in 16 GB with a context above 200,000 tokens: 1.6× faster than before.' } },
	runs: [
		{
			model: 'qwen38',
			title: 'Qwen3.8-27B ISTA GSQ IQ3_XXS',
			quant: 'IQ3_XXS (ISTA)',
			src: r67('16'),
			before: 'a0',
			flags: 'a1',
			ours: 'ours',
			labels: {
				a0: { pl: 'Typowa aplikacja (plik UD-Q3_K_XL)', en: 'Typical app (UD-Q3_K_XL file)' },
				a1: { pl: 'Lepszy plik (ISTA), bez MTP', en: 'Better file (ISTA), no MTP' }
			},
			variants: [
				{ key: 'a0', decode: { v: 52.05, src: r67('16') } },
				{ key: 'a1', decode: { v: 58.81, src: r67('16') }, vram: mib(14562, r67('16')) },
				{ key: 'ours', decode: { v: 81.62, src: r67('16,71') }, vram: mib(15632, r67('16,71')) }
			],
			gain: { flags: x(58.81, 52.05, '16'), engine: x(81.62, 58.81, '16'), total: x(81.62, 52.05, '16'), text: ['×1,13 (plik ISTA)', '×1,39 (lean + MTP n=2)', '×1,57'], src: r67('16,71') },
			gainText: { pl: ['×1,13 (plik ISTA)', '×1,39 (lean + MTP n=2)', '×1,57'], en: ['×1.13 (ISTA file)', '×1.39 (lean + MTP n=2)', '×1.57'] },
			metric: SPEC_67,
			sameHarness: true,
			conditions: {
				pl: 'KV q4_0, -fa on, -ub 256; typowa aplikacja (plik UD-Q3_K_XL, kontekst 135 168, bez spekulacji); lepszy plik (ISTA IQ3_XXS, kontekst 208 896, bez spekulacji); nasz silnik (lean + MTP n=2, kontekst 217 088); karta 250 W',
				en: 'KV q4_0, -fa on, -ub 256; typical app (UD-Q3_K_XL file, -c 135168, no speculation); better file (ISTA IQ3_XXS, -c 208896, no speculation); our engine (lean + MTP n=2, -c 217088); card at 250 W'
			},
			conditionsSrc: r67('16,46,71'),
			note: {
				pl: 'Zwykły llama.cpp z MTP n=3 nie mieści się tu w 16 GB przy tym kontekście; nasz silnik (lean) zwalnia pamięć bufora spekulacji i mieści MTP przy 217 088 tokenach. Przy kontekście 65 536 nasz fork CUDA daje 93,94 t/s. Jeden seed na pomiar.',
				en: 'Plain llama.cpp with MTP n=3 does not fit in 16 GB at this context; our engine (lean) frees the speculation buffer and fits MTP at 217,088 tokens. At a 65,536 context our CUDA fork does 93.94 t/s. One seed per measurement.'
			}
		}
	]
});

const RTX_4070: CardView = card67({
	id: 'rtx-4070',
	name: 'GeForce RTX 4070',
	short: '4070',
	vramGB: 12,
	arch: 'Ada sm_89',
	bwGBs: { v: 504, src: 'app/landing/src/lib/data/gpus.json (specyfikacja producenta)' },
	powerW: { v: 200, src: r67('46') },
	hwLine: { pl: 'limit mocy 200 W (domyślnie 200 W), wynajęta karta (Vast)', en: 'power limit 200 W (default 200 W), rented card (Vast)' },
	hwLines: '46',
	pick: { model: 'bonsai', why: { pl: 'Model 27B na 12 GB: Bonsai 2 z głowicą MTP pisze 1,9× szybciej niż typowa aplikacja na tym samym modelu.', en: 'A 27B model on 12 GB: Bonsai 2 with an MTP head writes 1.9× faster than the typical app on the same model.' } },
	runs: [
		{
			model: 'bonsai',
			title: 'Ternary Bonsai 2 27B',
			quant: 'PTQ1_0 + MTP',
			src: r67('19,68'),
			before: 'a1',
			flags: 'alt',
			ours: 'ours',
			labels: BONSAI_67_LABELS,
			variants: [
				{ key: 'a1', decode: { v: 49.43, src: r67('68') } },
				{ key: 'alt', decode: { v: 66.34, src: r67('68') } },
				{ key: 'ours', decode: { v: 94.73, src: r67('19') }, vram: mib(11163, r67('19')) }
			],
			gain: { flags: x(66.34, 49.43, '68'), engine: x(94.73, 66.34, '19,68'), total: x(94.73, 49.43, '19,68'), text: ['×1,34 (fork Prism, PTQ1_0)', '×1,43 (głowica MTP n=2)', '×1,92'], src: r67('19,68') },
			gainText: { pl: ['×1,34 (fork Prism, PTQ1_0)', '×1,43 (głowica MTP n=2)', '×1,92'], en: ['×1.34 (Prism fork, PTQ1_0)', '×1.43 (MTP head n=2)', '×1.92'] },
			metric: SPEC_67,
			sameHarness: true,
			conditions: {
				pl: 'typowa aplikacja (llama.cpp, plik Q2_0, kontekst 65 536, -ub 256); fork Prism (plik PTQ1_0, kontekst 65 536); nasz silnik (Prism + głowica MTP n=2, kontekst 208 896); karta 200 W',
				en: 'typical app (llama.cpp, Q2_0 file, -c 65536, -ub 256); Prism fork (PTQ1_0 file, -c 65536); our engine (Prism + MTP head n=2, -c 208896); card at 200 W'
			},
			conditionsSrc: r67('19,46,68'),
			note: {
				pl: 'Nasz silnik mierzony przy ponad 3× dłuższym kontekście niż pozostałe dwa ustawienia; przy 65 536 daje 94,81 t/s. Bonsai 2 to 2-bitowa kwantyzacja Qwen3.8-27B, więc jakość jest niższa niż modelu 4-bitowego na kartach 24 GB. Jeden seed na pomiar.',
				en: 'Our engine was measured at over 3× the context of the other two settings; at 65,536 it does 94.81 t/s. Bonsai 2 is a 2-bit quantisation of Qwen3.8-27B, so its quality is below the 4-bit model on 24 GB cards. One seed per measurement.'
			}
		},
		single67(
			'lfm25',
			'LFM2.5-24B-A2B UD-IQ3_XXS',
			'UD-IQ3_XXS',
			{ v: 179.32, src: r67('114') },
			mib(10525, r67('114')),
			{ pl: 'cały model w pamięci karty, kontekst 131 072, KV q8_0, -ub 512, bez spekulacji', en: 'the whole model in card memory, 128k context (-c 131072), KV q8_0, -ub 512, no speculation' },
			'114'
		)
	]
});

const RTX_3060: CardView = card67({
	id: 'rtx-3060-12',
	name: 'GeForce RTX 3060 12 GB',
	short: '3060',
	vramGB: 12,
	arch: 'Ampere sm_86',
	bwGBs: { v: 360, src: 'app/landing/src/lib/data/gpus.json (raport 04 §2.1.6)' },
	powerW: { v: 140, src: r67('46') },
	hwLine: { pl: 'limit mocy 140 W (domyślnie 170 W), wynajęta karta (Vast)', en: 'power limit 140 W (default 170 W), rented card (Vast)' },
	hwLines: '46',
	pick: { model: 'bonsai', why: { pl: 'Model 27B na 12 GB: Bonsai 2 z głowicą MTP pisze 1,8× szybciej niż typowa aplikacja na tym samym modelu.', en: 'A 27B model on 12 GB: Bonsai 2 with an MTP head writes 1.8× faster than the typical app on the same model.' } },
	runs: [
		{
			model: 'bonsai',
			title: 'Ternary Bonsai 2 27B',
			quant: 'PTQ1_0 + MTP',
			src: r67('20,68'),
			before: 'a1',
			flags: 'alt',
			ours: 'ours',
			labels: BONSAI_67_LABELS,
			variants: [
				{ key: 'a1', decode: { v: 32.23, src: r67('68') } },
				{ key: 'alt', decode: { v: 46.87, src: r67('68') } },
				{ key: 'ours', decode: { v: 58.31, src: r67('20') }, vram: mib(11015, r67('20')) }
			],
			gain: { flags: x(46.87, 32.23, '68'), engine: x(58.31, 46.87, '20,68'), total: x(58.31, 32.23, '20,68'), text: ['×1,45 (fork Prism, PTQ1_0)', '×1,24 (głowica MTP n=2)', '×1,81'], src: r67('20,68') },
			gainText: { pl: ['×1,45 (fork Prism, PTQ1_0)', '×1,24 (głowica MTP n=2)', '×1,81'], en: ['×1.45 (Prism fork, PTQ1_0)', '×1.24 (MTP head n=2)', '×1.81'] },
			metric: SPEC_67,
			sameHarness: true,
			conditions: {
				pl: 'typowa aplikacja (llama.cpp, plik Q2_0, kontekst 65 536, -ub 256); fork Prism (plik PTQ1_0, kontekst 65 536); nasz silnik (Prism + głowica MTP n=2, kontekst 204 800); karta 140 W',
				en: 'typical app (llama.cpp, Q2_0 file, -c 65536, -ub 256); Prism fork (PTQ1_0 file, -c 65536); our engine (Prism + MTP head n=2, -c 204800); card at 140 W'
			},
			conditionsSrc: r67('20,46,68'),
			note: {
				pl: 'Nasz silnik mierzony przy ponad 3× dłuższym kontekście niż pozostałe dwa ustawienia; przy 65 536 daje 58,60 t/s. Bonsai 2 to 2-bitowa kwantyzacja Qwen3.8-27B, więc jakość jest niższa niż modelu 4-bitowego na kartach 24 GB. Jeden seed na pomiar.',
				en: 'Our engine was measured at over 3× the context of the other two settings; at 65,536 it does 58.60 t/s. Bonsai 2 is a 2-bit quantisation of Qwen3.8-27B, so its quality is below the 4-bit model on 24 GB cards. One seed per measurement.'
			}
		},
		single67(
			'lfm25',
			'LFM2.5-24B-A2B UD-IQ3_XXS',
			'UD-IQ3_XXS',
			{ v: 102.47, src: r67('114') },
			mib(10463, r67('114')),
			{ pl: 'cały model w pamięci karty, kontekst 131 072, KV q8_0, -ub 512, bez spekulacji; karta 140 W', en: 'the whole model in card memory, 128k context (-c 131072), KV q8_0, -ub 512, no speculation; card at 140 W' },
			'114'
		)
	]
});

const RTX_2080TI: CardView = card67({
	id: 'rtx-2080-ti',
	name: 'GeForce RTX 2080 Ti',
	short: '2080 Ti',
	vramGB: 11,
	arch: 'Turing sm_75',
	bwGBs: { v: 616, src: 'app/landing/src/lib/data/gpus.json (specyfikacja producenta)' },
	powerW: { v: 250, src: r67('46') },
	hwLine: { pl: 'limit mocy 250 W (domyślnie 250 W), wynajęta karta (Vast)', en: 'power limit 250 W (default 250 W), rented card (Vast)' },
	hwLines: '46',
	pick: { model: 'bonsai', why: { pl: 'Model 27B na 11 GB: Bonsai 2 z głowicą MTP pisze 2,0× szybciej niż typowa aplikacja na tym samym modelu.', en: 'A 27B model on 11 GB: Bonsai 2 with an MTP head writes 2.0× faster than the typical app on the same model.' } },
	runs: [
		{
			model: 'bonsai',
			title: 'Ternary Bonsai 2 27B',
			quant: 'PTQ1_0 + MTP',
			src: r67('21,68,73'),
			before: 'a1',
			flags: 'alt',
			ours: 'ours',
			labels: BONSAI_67_LABELS,
			variants: [
				{ key: 'a1', decode: { v: 39.57, src: r67('21') }, vram: mib(10243, r67('21')) },
				{ key: 'alt', decode: { v: 61.18, src: r67('68') } },
				{ key: 'ours', decode: { v: 77.96, src: r67('21') }, vram: mib(10151, r67('21')) }
			],
			gain: { flags: x(61.18, 39.57, '21,68'), engine: x(77.96, 61.18, '21,68'), total: x(77.96, 39.57, '21'), text: ['×1,55 (fork Prism, PTQ1_0)', '×1,27 (głowica MTP n=2)', '×1,97'], src: r67('21,68') },
			gainText: { pl: ['×1,55 (fork Prism, PTQ1_0)', '×1,27 (głowica MTP n=2)', '×1,97'], en: ['×1.55 (Prism fork, PTQ1_0)', '×1.27 (MTP head n=2)', '×1.97'] },
			metric: SPEC_67,
			sameHarness: true,
			conditions: {
				pl: 'typowa aplikacja (llama.cpp, plik Q2_0, kontekst 131 072, -ub 256); fork Prism (plik PTQ1_0, kontekst 65 536); nasz silnik (Prism + głowica MTP n=2, kontekst 155 648, -ub 512); karta 250 W',
				en: 'typical app (llama.cpp, Q2_0 file, -c 131072, -ub 256); Prism fork (PTQ1_0 file, -c 65536); our engine (Prism + MTP head n=2, -c 155648, -ub 512); card at 250 W'
			},
			conditionsSrc: r67('21,46,68,73'),
			note: {
				pl: 'Najstarsza karta w kampanii (Turing). Bonsai 2 to 2-bitowa kwantyzacja Qwen3.8-27B, więc jakość jest niższa niż modelu 4-bitowego na kartach 24 GB. Jeden seed na pomiar.',
				en: 'The oldest card in the campaign (Turing). Bonsai 2 is a 2-bit quantisation of Qwen3.8-27B, so its quality is below the 4-bit model on 24 GB cards. One seed per measurement.'
			}
		}
	]
});

const RTX_3080: CardView = card67({
	id: 'rtx-3080',
	name: 'GeForce RTX 3080',
	short: '3080',
	vramGB: 10,
	arch: 'Ampere sm_86',
	bwGBs: { v: 760, src: 'app/landing/src/lib/data/gpus.json (specyfikacja producenta)' },
	powerW: { v: 260, src: r67('46') },
	hwLine: { pl: 'limit mocy 260 W (domyślnie 320 W), wynajęta karta (Vast)', en: 'power limit 260 W (default 320 W), rented card (Vast)' },
	hwLines: '46',
	pick: { model: 'qwen35', why: { pl: 'Na 10 GB najlepiej działa Qwen3.5-9B: 85 t/s z kontekstem 192 512 tokenów. Naszego silnika na tej karcie jeszcze nie mierzyliśmy.', en: 'On 10 GB Qwen3.5-9B works best: 85 t/s with a 192,512-token context. We have not measured our engine on this card yet.' } },
	runs: [
		single67(
			'qwen35',
			'Qwen3.5-9B Q6_K',
			'Q6_K',
			{ v: 85.2, src: r67('22') },
			mib(9345, r67('22')),
			{ pl: 'llama.cpp, kontekst 192 512, KV q4_0, -fa on, -ub 512, bez spekulacji; karta 260 W', en: 'llama.cpp, 188k context (-c 192512), KV q4_0, -fa on, -ub 512, no speculation; card at 260 W' },
			'22'
		)
	]
});

const RTX_3070: CardView = card67({
	id: 'rtx-3070',
	name: 'GeForce RTX 3070',
	short: '3070',
	vramGB: 8,
	arch: 'Ampere sm_86',
	bwGBs: { v: 448, src: 'app/landing/src/lib/data/gpus.json (specyfikacja producenta)' },
	powerW: { v: 220, src: r67('46') },
	hwLine: { pl: 'limit mocy 220 W (domyślnie 220 W), wynajęta karta (Vast)', en: 'power limit 220 W (default 220 W), rented card (Vast)' },
	hwLines: '46',
	pick: { model: 'qwen35', why: { pl: 'Na 8 GB najlepiej działa Qwen3.5-9B: 67 t/s z kontekstem 151 552 tokenów. Naszego silnika na tej karcie jeszcze nie mierzyliśmy.', en: 'On 8 GB Qwen3.5-9B works best: 67 t/s with a 151,552-token context. We have not measured our engine on this card yet.' } },
	runs: [
		single67(
			'qwen35',
			'Qwen3.5-9B Q4_K_M',
			'Q4_K_M',
			{ v: 66.9, src: r67('23') },
			mib(7251, r67('23')),
			{ pl: 'llama.cpp, kontekst 151 552, KV q4_0, -fa on, -ub 512, bez spekulacji; karta 220 W', en: 'llama.cpp, 148k context (-c 151552), KV q4_0, -fa on, -ub 512, no speculation; card at 220 W' },
			'23'
		)
	]
});

const XTX_HW = 'KERNEL/qwen-opt/NOTES.md:110';
/** FinalBench same-script XTX logs (lab server, 2026-10-19). */
const FB = '~/qwen-opt/queue/logs';
const SPEC_SWEEP_XTX: L = {
	pl: 'spec_sweep przez serwer, ten sam skrypt po obu stronach: czat, 6 promptów × 3 seedy, T=1, świeży serwer, mediana; kolejność ABBA (drugi przebieg w granicach ±0,2 t/s)',
	en: 'spec_sweep through the server, the same script on both sides: chat, 6 prompts × 3 seeds, T=1, fresh server, median; ABBA order (the second pass within ±0.2 t/s)'
};

/** Vendor spec sheet of our lab card (Specification tab, read 2026-10-19). */
const PULSE_SPEC = 'sapphiretech.com/en/consumer/pulse-radeon-rx-7900-xtx-24g-gddr6 (Specification)';

/**
 * The physical board in our lab: Sapphire PULSE RX 7900 XTX. Board facts from the vendor spec sheet,
 * the chip name from `vulkaninfo` and the ROCm version from our notes on the lab machine. The home
 * scan scene draws and reads this card.
 */
export const XTX_BOARD = {
	card: 'rx-7900-xtx',
	maker: 'Sapphire',
	series: 'PULSE',
	chip: { v: 'Navi 31', src: 'KERNEL/product/research/16j-magnitude-vulkan-xtx.md:18 (vulkaninfo: RADV NAVI31)' },
	rocm: { v: '10.0', src: 'KERNEL/qwen-opt/NOTES.md:1' },
	memType: { v: 'GDDR6', src: PULSE_SPEC },
	busBits: { v: 384, src: PULSE_SPEC },
	gbps: { v: 20, src: PULSE_SPEC },
	pins8: { v: 3, src: PULSE_SPEC }
} as const;

export const CARDS: CardView[] = [
	RTX_5090,
	RTX_4090,
	nvidia(
		'rtx-3090',
		{ name: 'GeForce RTX 3090', short: '3090', vramGB: 24, arch: 'Ampere sm_86', pick: { model: 'qwen38', why: { pl: 'Najlepsza jakość, która mieści się w 24 GB: 2,2× szybciej niż typowa aplikacja.', en: 'The best quality that fits in 24 GB: 2.2× faster than the typical app.' } } },
		{
			qwen38: {
				c: {
					pl: 'najlepsze flagi i nasz silnik: kontekst 200k (-c 204800), KV q4_0, MTP n=4, -fa on; nasz dodatkowo słownik draftu 64k, lookup W16, GPU verify; A0: samo -m (-fit: kontekst 90k, KV f16); karta 335 W',
					en: 'best flags and our engine: 200k context (-c 204800), KV q4_0, MTP n=4, -fa on; ours adds the 64k draft vocabulary, lookup W16, GPU verify; A0: plain -m (-fit: 90k context, KV f16); card at 335 W'
				},
				src: `${R27}:10-14,62-79,109,207,211-212; ${NV3090}/vram.jsonl; ${NV3090L}/vram.jsonl`,
				note: {
					pl: 'Ten sam skrypt, inne zadania: czat zachłanny (T=0) 42,3 → 76,7 → 103,4 t/s; edycja kodu 42,0 → 109,5 → 348,9 t/s; kopiowanie 41,8 → 108,4 → 343,8 t/s; generowanie po 32k kontekstu 39,1 → 64,0 → 79,9 t/s. Uczciwie: nasz silnik z kontekstem 200k nie zmieścił promptu ~55,6k tokenów w 24 GB; na kartach NVIDIA 24 GB ustawiamy kontekst ≤ 131 072 (szczyt 22,2 GB przy 60k).',
					en: 'The same script, other tasks: greedy chat (T=0) 42.3 → 76.7 → 103.4 t/s; code edits 42.0 → 109.5 → 348.9 t/s; copying 41.8 → 108.4 → 343.8 t/s; generation after a 32k context 39.1 → 64.0 → 79.9 t/s. Honestly: with a 200k context our engine did not fit a ~55.6k-token prompt in 24 GB; on 24 GB NVIDIA cards we set the context to ≤ 131,072 (22.2 GB peak at 60k).'
				},
				final: FINAL_3090_QWEN
			},
			lfm25: { c: { pl: 'kontekst 64k (-c 65536), KV q8_0, bez spekulacji', en: '64k context (-c 65536), KV q8_0, no speculation' }, src: `${BS}:19-21` },
			nemotron: {
				c: {
					pl: 'kontekst 64k (-c 65536), KV q8_0, spekulacja DFlash n_max 5 (drafter NVFP4, 1 GB); A0: samo -m (-fit: 4 sloty × 104k, KV f16)',
					en: '64k context (-c 65536), KV q8_0, DFlash speculation n_max 5 (NVFP4 drafter, 1 GB); A0: plain -m (-fit: 4 slots × 104k, KV f16)'
				},
				src: `${NR}:73; ${NR}:224`,
				note: {
					pl: 'Uczciwie: sam nasz fork z tymi flagami (A2) dał 129,0 t/s, czyli mniej niż upstream (131,4): krok jest krótszy, ale draft trafia rzadziej. Wersja „nasz silnik” to fork z nowymi łatkami (141,1), która przywraca trafność draftu. KLD dla tego modelu jeszcze nie zmierzone; 500 słów liczone współczynnikiem tokenizera Qwena.',
					en: 'Honestly: our fork alone with these flags (A2) gave 129.0 t/s, less than upstream (131.4): the step is shorter but the draft hits less often. "Our engine" is the fork with new patches (141.1), which restores draft acceptance. KLD for this model is not measured yet; 500-word times use the Qwen tokenizer ratio.'
				}
			}
		}
	),
	RTX_5080,
	nvidia(
		'rtx-5060-ti-16',
		{ name: 'GeForce RTX 5060 Ti 16 GB', short: '5060 Ti', vramGB: 16, arch: 'Blackwell sm_120', pick: { model: 'qwen38', why: { pl: 'Qwen w Q3 to największy model, który mieści się w 16 GB z kontekstem 32k.', en: 'Qwen at Q3 is the largest model that fits in 16 GB with a 32k context.' } } },
		{
			qwen38: {
				c: { pl: 'kontekst 32k, KV q8_0, MTP n=4, -fit off; A0: domyślny -fit, KV f16', en: '32k context, KV q8_0, MTP n=4, -fit off; A0: default -fit, KV f16' },
				src: `${BS}:65-69`,
				note: { pl: 'Q4 nie mieści się w 16 GB. Upstream MTP z domyślnym -fit spada tu do 7,7 t/s.', en: 'Q4 does not fit in 16 GB. Upstream MTP with the default -fit drops to 7.7 t/s here.' }
			},
			lfm25: { c: { pl: 'kontekst 32k, KV q8_0, bez spekulacji; A0: domyślny -fit, KV f16', en: '32k context, KV q8_0, no speculation; A0: default -fit, KV f16' }, src: `${BS}:65-69`, note: { pl: 'Q5 nie mieści się w 16 GB.', en: 'Q5 does not fit in 16 GB.' } }
		}
	),
	RTX_4060TI,
	RTX_4070,
	RTX_3060,
	RTX_2080TI,
	RTX_3080,
	RTX_3070,
	{
		id: 'rx-7900-xtx',
		name: 'Radeon RX 7900 XTX',
		short: '7900 XTX',
		vendor: 'amd',
		vramGB: 24,
		arch: 'RDNA3 gfx1100',
		bwGBs: { v: 960, src: 'app/landing/src/lib/data/gpus.json (raport 04 §2.1.6)' },
		powerW: { v: 303, src: XTX_HW },
		hwSrc: XTX_HW,
		pick: { model: 'qwen38', why: { pl: 'Na tej karcie powstał nasz silnik: Qwen ze spekulacją MTP pisze 114,8 t/s, 3,2× szybciej niż typowa aplikacja.', en: 'Our engine was built on this card: Qwen with MTP speculation writes 114.8 t/s, 3.2× faster than the typical app.' } },
		runs: [
			{
				model: 'qwen38',
				title: 'Qwen3.8-27B UD-Q4_K_XL',
				quant: 'UD-Q4_K_XL',
				file: { v: 17.56, src: 'app/landing/src/lib/data/models.json (raport 04 §2.3.1)', unit: 'GB' },
				src: M.qwenXtxOurs.source,
				before: 'a0',
				flags: 'a1',
				ours: 'ours',
				variants: [
					{ key: 'a0', decode: n(M.qwenXtxDefault), msStep: { v: 27.89, src: `${FB}/fb-qwen-U0-p1.log:2` }, pp4096: { v: 1055.5, src: `${FB}/fb-lb-qwen.log:14` }, tg128: { v: 35.3, src: `${FB}/fb-lb-qwen.log:14` } },
					{ key: 'a1', decode: n(M.qwenXtxFlags), msStep: { v: 53.72, src: `${FB}/fb-qwen-U1-p1.log:2` } },
					{ key: 'ours', decode: n(M.qwenXtxOurs), msStep: { v: 27.67, src: `${FB}/fb-qwen-T-p1.log:2` }, pp4096: { v: 1125.5, src: `${FB}/fb-lb-qwen.log:11` }, tg128: { v: 43.4, src: `${FB}/fb-lb-qwen.log:11` }, vram: mib(23359, `${FB}/fb-qwen-T-p1.log:1 (amd-smi USED_VRAM after load, n_ctx 204800)`) }
				],
				metric: SPEC_SWEEP_XTX,
				sameHarness: true,
				conditions: { pl: 'ROCm, ten sam serwer i skrypt po obu stronach; spekulacja MTP (najlepsze flagi i nasz silnik); kontekst 200k (n_ctx 204800)', en: 'ROCm, the same server and script on both sides; MTP speculation (best flags and our engine); 200k context (n_ctx 204800)' },
				conditionsSrc: `${FB}/fb-qwen-T-p1.log:1; ${FB}/fb-qwen-U0-p1.log:1`,
				note: {
					pl: 'Edycja kodu (ten sam skrypt, T=0, 4 pliki): typowa aplikacja 35,5 t/s, najlepsze flagi 89,0 t/s, nasz silnik 419,7 t/s. Bez spekulacji (llama-bench tg128): 35,3 → 43,4 t/s.',
					en: 'Code edits (the same script, T=0, 4 files): typical app 35.5 t/s, best flags 89.0 t/s, our engine 419.7 t/s. Without speculation (llama-bench tg128): 35.3 → 43.4 t/s.'
				}
			},
			{
				model: 'lfm25',
				title: 'LFM2.5-24B-A2B Q5_K_M',
				quant: 'Q5_K_M',
				file: { v: 17.03, src: 'app/landing/src/lib/data/models.json (raport 04 §2.3.1)', unit: 'GB' },
				src: M.lfmOursTg128.source,
				before: 'a0',
				flags: 'a0',
				ours: 'ours',
				variants: [
					{ key: 'a0', decode: n(M.lfmUpstreamTg128) },
					{ key: 'ours', decode: n(M.lfmOursTg128), msStep: { v: 3.41, src: `${SN}:12` }, pp4096: { v: 6175, src: `${SN}:12` } }
				],
				metric: {
					pl: 'llama-bench tg128 (generowanie 128 tokenów), ten sam skrypt po obu stronach. Przez serwer nasz silnik: 293,7 t/s.',
					en: 'llama-bench tg128 (128 generated tokens), the same script on both sides. Through the server our engine does 293.7 t/s.'
				},
				sameHarness: true,
				conditions: { pl: 'ROCm, bez spekulacji; KV q4_0 (upstream) i q8_0 (nasz, o 2,6% wolniejszy)', en: 'ROCm, no speculation; KV q4_0 (upstream) and q8_0 (ours, 2.6% slower)' },
				conditionsSrc: `${M.lfmUpstreamTg128.source}; ${M.lfmOursTg128.source}`
			}
		]
	}
];

export const findCard = (id: string) => CARDS.find((c) => c.id === id) ?? null;
export const variantOf = (run: Run, key: VariantKey): Variant | undefined => run.variants.find((v) => v.key === key);

/** Labels of the sheet columns. Bonsai's columns are different forks of the same weights. */
export function variantLabel(run: Run, key: VariantKey): L {
	const own = run.labels?.[key];
	if (own) return own;
	if (run.model === 'bonsai') {
		const b: Record<string, L> = {
			a0: { pl: 'Prism PQ2_0 (domyślny)', en: 'Prism PQ2_0 (default)' },
			alt: { pl: 'Prism PTQ1_0 (najszybszy)', en: 'Prism PTQ1_0 (fastest)' },
			a1: { pl: 'upstream, plik Q2_0', en: 'upstream, Q2_0 file' },
			ours: { pl: 'nasz silnik, plik Q2_0', en: 'our engine, Q2_0 file' }
		};
		return b[key];
	}
	const l: Record<VariantKey, L> = {
		a0: { pl: 'Typowa aplikacja', en: 'Typical app' },
		a1: { pl: 'Najlepsze flagi', en: 'Best flags' },
		a2: { pl: 'Nasz silnik', en: 'Our engine' },
		profile: { pl: 'Nasz silnik + profil karty', en: 'Our engine + card profile' },
		ours: { pl: 'Nasz silnik', en: 'Our engine' },
		alt: { pl: 'Inny fork', en: 'Other fork' }
	};
	return l[key];
}

/** What each column means, one line (small print). */
export const VARIANT_HINT: Record<'a0' | 'a1' | 'ours', L> = {
	a0: { pl: 'llama.cpp z ustawieniami domyślnymi, tak jak w typowej aplikacji (na RTX 3090 tyle samo co Ollama)', en: 'llama.cpp with default settings, like a typical app (on the RTX 3090 the same as Ollama)' },
	a1: { pl: 'upstream llama.cpp z najlepszymi flagami, które znamy (np. spekulacja MTP)', en: 'upstream llama.cpp with the best flags we know (e.g. MTP speculation)' },
	ours: { pl: 'nasz silnik z tymi samymi flagami i łatkami', en: 'our engine with the same flags plus our patches' }
};

/** Model facts for the info panels. Every claim cites where it was read. */
export const MODEL_INFO: Record<ModelKey, { name: string; what: L; license: L; licenseSrc: string; good: L[]; src: string }> = {
	qwen38: {
		name: 'Qwen3.8-27B',
		what: { pl: 'Gęsty model 27B z hybrydową atencją (Gated DeltaNet + pełna atencja) i wbudowaną głowicą MTP, która zgaduje kilka tokenów naprzód.', en: 'A dense 27B model with hybrid attention (Gated DeltaNet + full attention) and a built-in MTP head that guesses several tokens ahead.' },
		license: { pl: 'Apache 2.0: wolno używać komercyjnie', en: 'Apache 2.0: commercial use allowed' },
		licenseSrc: 'app/landing/src/lib/data/models.json (raport 06 §2.4.2)',
		good: [{ pl: 'czat', en: 'chat' }, { pl: 'kod', en: 'code' }, { pl: 'jakość', en: 'quality' }],
		src: 'app/landing/src/lib/data/models.json'
	},
	lfm25: {
		name: 'LFM2.5-24B-A2B',
		what: { pl: 'Mieszanka ekspertów (MoE): 24B parametrów, około 2B aktywnych na token. Dlatego pisze kilka razy szybciej niż model gęsty.', en: 'A mixture of experts (MoE): 24B parameters, about 2B active per token. That is why it writes several times faster than a dense model.' },
		license: { pl: 'LFM Open License v1.0: komercyjnie tylko poniżej 10 mln USD rocznego przychodu', en: 'LFM Open License v1.0: commercial use only below USD 10M annual revenue' },
		licenseSrc: 'app/landing/src/lib/data/models.json (raport 06 §2.4.2)',
		good: [{ pl: 'szybkość', en: 'speed' }, { pl: 'czat', en: 'chat' }],
		src: 'app/landing/src/lib/data/models.json'
	},
	nemotron: {
		name: 'Nemotron 3.5 Bolt 74B-A9B',
		what: {
			pl: 'Hybryda Mamba-2 i atencji w układzie mieszanki ekspertów: 74B parametrów, około 9B aktywnych na token. W IQ2_XXS mieści się w 24 GB razem z małym drafterem DFlash.',
			en: 'A Mamba-2 + attention hybrid built as a mixture of experts: 74B parameters, about 9B active per token. At IQ2_XXS it fits in 24 GB together with a small DFlash drafter.'
		},
		license: { pl: 'OpenMDW-1.1: według karty modelu do użytku komercyjnego i niekomercyjnego', en: 'OpenMDW-1.1: commercial and non-commercial use per the model card' },
		licenseSrc: 'KERNEL/product/research/14-nemotron-3090.md:30',
		good: [{ pl: 'duży model na 24 GB', en: 'a big model on 24 GB' }, { pl: 'szybkość', en: 'speed' }],
		src: 'KERNEL/product/research/14-nemotron-3090.md:25-38'
	},
	bonsai: {
		name: 'Ternary Bonsai 2 27B',
		what: {
			pl: 'Model 27B z wagami trójkowymi (−1, 0, +1), 2-bitowa wersja Qwen3.8-27B. Zwykły llama.cpp czyta plik Q2_0; nasz silnik uruchamia format PTQ1_0 forka Prism z dołączoną głowicą MTP.',
			en: 'A 27B model with ternary weights (−1, 0, +1), a 2-bit version of Qwen3.8-27B. Plain llama.cpp reads the Q2_0 file; our engine runs the Prism fork PTQ1_0 format with an attached MTP head.'
		},
		license: { pl: 'Apache 2.0: wolno używać komercyjnie', en: 'Apache 2.0: commercial use allowed' },
		licenseSrc: 'KERNEL/product/SITE-NVIDIA.md:57-58 (Hugging Face, sprawdzone 2026-11-14)',
		good: [{ pl: 'model 27B na 11–12 GB', en: 'a 27B model on 11–12 GB' }, { pl: 'szybkość', en: 'speed' }],
		src: 'KERNEL/product/research/09-chmura-3060.md:30-36; KERNEL/product/research/67-nvidia-vast-kampania.md:68'
	},
	qwen35: {
		name: 'Qwen3.5-9B',
		what: { pl: 'Gęsty model 9B. Mieści się w 8–10 GB razem z kontekstem ponad 150 000 tokenów.', en: 'A dense 9B model. It fits in 8–10 GB together with a context above 150,000 tokens.' },
		license: { pl: 'Apache 2.0: wolno używać komercyjnie', en: 'Apache 2.0: commercial use allowed' },
		licenseSrc: 'KERNEL/product/SITE-NVIDIA.md:60 (Hugging Face, sprawdzone 2026-11-14)',
		good: [{ pl: 'mała pamięć', en: 'low memory' }, { pl: 'szybkość', en: 'speed' }],
		src: 'KERNEL/product/research/67-nvidia-vast-kampania.md:22-23'
	}
};

/**
 * Seconds for a 500-word answer. The sheet lists it for NVIDIA cards; for the RX 7900 XTX it is
 * derived the same way (words × tokens-per-word ÷ t/s) and flagged `derived`.
 */
export function words500(v: Variant | undefined, lang: 'pl' | 'en'): { v: number; src: string; derived: boolean } | null {
	if (!v) return null;
	const given = lang === 'pl' ? v.words500pl : v.words500en;
	if (given) return { v: given.v, src: given.src, derived: false };
	if (!v.decode) return null;
	const tpw = TOK_PER_WORD[lang];
	return { v: (500 * tpw) / v.decode.v, src: `${v.decode.src} × ${tpw} tok/słowo (raport 06 §2.1.2)`, derived: true };
}

/**
 * The home page's engine story: Qwen3.8-27B UD-Q4_K_XL on the RX 7900 XTX, from upstream llama.cpp
 * with default settings to our engine today. Every milestone is the same script: spec_sweep chat,
 * 6 prompts × 3 seeds, T=1, fresh server, median. The start, upstream's best and today are the
 * 2026-10-19 ABBA runs (M.qwenXtx*, first pass, as in the hero); the two milestones between are our
 * engine's earlier states measured the same way.
 */
const step = (m: Measurement, key: string) => ({ key, v: m.value, src: m.source });
export const QWEN_XTX_JOURNEY = {
	card: 'rx-7900-xtx',
	model: 'qwen38' as ModelKey,
	steps: [
		step(M.qwenXtxDefault, 'default'),
		step(M.qwenXtxFlags, 'flags'),
		/** our fork, first ROCm state (2026-10-12): 41.8 ms per step */
		{ key: 'fork', v: 74.5, src: 'KERNEL/qwen-opt/NOTES.md:183' },
		/** production amd-opt (2026-10-15): 27.74 ms per step */
		{ key: 'prod', v: 109.0, src: 'KERNEL/qwen-opt/STATUS-NEXT.md:10' },
		/** today: stable PM4 command replay + verification on the GPU, 27.67 ms per step */
		step(M.qwenXtxOurs, 'today')
	] as (Num & { key: string })[]
} as const;
