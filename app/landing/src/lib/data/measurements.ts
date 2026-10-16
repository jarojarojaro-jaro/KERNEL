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

function nvidia(
	id: string,
	meta: Pick<CardView, 'name' | 'short' | 'vramGB' | 'arch' | 'pick'>,
	conditions: Partial<Record<ModelKey, { c: L; src: string; note?: L }>>
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
		runs: c.runs.map((r) => ({
			...r,
			metric: SPEC_SWEEP,
			sameHarness: true,
			conditions: conditions[r.model]!.c,
			conditionsSrc: conditions[r.model]!.src,
			...(r.gain ? { gainText: { pl: r.gain.text, en: r.gain.text.map(toEn) as [string, string, string] } } : {}),
			...(conditions[r.model]!.note ? { note: conditions[r.model]!.note } : {})
		}))
	};
}

const XTX_HW = 'KERNEL/qwen-opt/NOTES.md:110';

export const CARDS: CardView[] = [
	nvidia(
		'rtx-3090',
		{ name: 'GeForce RTX 3090', short: '3090', vramGB: 24, arch: 'Ampere sm_86', pick: { model: 'qwen38', why: { pl: 'Najlepsza jakość, która mieści się w 24 GB, i największy zysk: 2× szybciej.', en: 'The best quality that fits in 24 GB, and the biggest gain: 2× faster.' } } },
		{
			qwen38: { c: { pl: 'kontekst 64k (-c 65536), KV q4_0, MTP n=4; A0: -fit wybrał 84k, KV f16', en: '64k context (-c 65536), KV q4_0, MTP n=4; A0: -fit chose 84k, KV f16' }, src: `${BS}:19-23` },
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
	nvidia(
		'rtx-3060-12',
		{ name: 'GeForce RTX 3060 12 GB', short: '3060', vramGB: 12, arch: 'Ampere sm_86', pick: { model: 'saluki', why: { pl: 'Lepsza jakość (perplexity 7,67 wobec 8,62). Bonsai jest szybszy, ale słabszy.', en: 'Better quality (perplexity 7.67 vs 8.62). Bonsai is faster but weaker.' } } },
		{
			saluki: { c: { pl: 'kontekst 32k, KV f16, -ub 1024; bez spekulacji (brak głowicy MTP)', en: '32k context, KV f16, -ub 1024; no speculation (no MTP head)' }, src: `${BS}:109-113` },
			bonsai: {
				c: { pl: 'kontekst 32k, KV f16, -ub 1024; bez spekulacji (brak głowicy MTP)', en: '32k context, KV f16, -ub 1024; no speculation (no MTP head)' },
				src: `${BS}:109-113`,
				note: {
					pl: 'Uczciwie: fork Prism z formatem PTQ1_0 jest tu szybszy od nas (44,8 t/s). Nasz silnik przyspiesza upstream na tym samym pliku Q2_0 o 7%.',
					en: 'Honestly: the Prism fork with its PTQ1_0 format is faster than us here (44.8 t/s). Our engine speeds up upstream on the same Q2_0 file by 7%.'
				}
			}
		}
	),
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
		pick: { model: 'qwen38', why: { pl: 'Na tej karcie powstał nasz silnik: Qwen ze spekulacją MTP pisze 109 t/s.', en: 'Our engine was built on this card: Qwen with MTP speculation writes 109 t/s.' } },
		runs: [
			{
				model: 'qwen38',
				title: 'Qwen3.8-27B UD-Q4_K_XL',
				quant: 'UD-Q4_K_XL',
				file: { v: 17.56, src: 'app/landing/src/lib/data/models.json (raport 04 §2.3.1)', unit: 'GB' },
				src: M.qwenOursMtp.source,
				before: 'a0',
				flags: 'a1',
				ours: 'ours',
				variants: [
					{ key: 'a0', decode: n(M.qwenUpstreamVulkanPlain) },
					{ key: 'a1', decode: n(M.qwenUpstreamVulkanMtp) },
					{ key: 'ours', decode: n(M.qwenOursMtp), msStep: { v: 27.74, src: `${SN}:10` }, pp4096: n(M.qwenOursPrefill), tg128: n(M.qwenOursPlainTg128) }
				],
				metric: {
					pl: 'Różne skrypty: upstream serve_bench (256 tokenów, temp 0), nasz spec_sweep (6 promptów × 3 seedy, T=1). Porównanie orientacyjne.',
					en: 'Different scripts: upstream serve_bench (256 tokens, temp 0), ours spec_sweep (6 prompts × 3 seeds, T=1). Indicative comparison.'
				},
				sameHarness: false,
				conditions: { pl: 'ROCm (nasz) i Vulkan (upstream), KV q4_0, MTP', en: 'ROCm (ours) and Vulkan (upstream), KV q4_0, MTP' },
				conditionsSrc: `${M.qwenUpstreamVulkanPlain.source}; ${SN}:6-10`
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
	saluki: {
		name: 'Underdog Saluki 27B',
		what: { pl: 'Model 27B (architektura qwen35) skwantyzowany do ~2 bitów standardowymi typami IQ: plik 7,9 GB. Bez głowicy MTP.', en: 'A 27B model (qwen35 architecture) quantised to ~2 bits with standard IQ types: a 7.9 GB file. No MTP head.' },
		license: { pl: 'Licencji jeszcze nie zweryfikowaliśmy', en: 'Licence not verified yet' },
		licenseSrc: 'KERNEL/product/research/09-chmura-3060.md:25-29',
		good: [{ pl: 'mała pamięć', en: 'low memory' }, { pl: 'jakość przy 12 GB', en: 'quality on 12 GB' }],
		src: 'KERNEL/product/research/09-chmura-3060.md:25-29'
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
		what: { pl: 'Model 27B z wagami trójkowymi (−1, 0, +1) w formatach forka Prism. Bez głowicy MTP. Przepakowujemy go do formatu Q2_0 z upstreamu bez strat.', en: 'A 27B model with ternary weights (−1, 0, +1) in the Prism fork formats. No MTP head. We repack it into upstream Q2_0 losslessly.' },
		license: { pl: 'Licencji jeszcze nie zweryfikowaliśmy', en: 'Licence not verified yet' },
		licenseSrc: 'KERNEL/product/research/09-chmura-3060.md:30-36',
		good: [{ pl: 'szybkość przy 12 GB', en: 'speed on 12 GB' }],
		src: 'KERNEL/product/research/09-chmura-3060.md:30-36'
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
 * In validation (not a product claim): on the RX 7900 XTX, MTP speculation in bit-exact mode gave
 * byte-identical greedy output to plain decoding in one end-to-end test. Full validation and the
 * speed cost of the bit-exact mode are still pending.
 */
export const BITEXACT_XTX = {
	card: 'rx-7900-xtx',
	model: 'qwen38' as ModelKey,
	quant: 'Q4_K_XL',
	conditions: { pl: 'KV q4_0, kontekst 8192, MTP n_max 4, odpowiedź zachłanna (greedy)', en: 'KV q4_0, context 8192, MTP n_max 4, greedy decoding' } as L,
	md5: '74952fd5c918b0486194c21d3ee0576c',
	chars: 2783,
	src: 'KERNEL/product/research/12-bit-exact-spekulacja.md:235',
	pendingSrc: 'KERNEL/product/research/12-bit-exact-spekulacja.md:241-252'
} as const;
