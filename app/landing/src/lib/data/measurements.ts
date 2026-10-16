/**
 * Every performance number the site shows comes from this registry. Each entry names the file
 * and line it was copied from and the harness that produced it. Nothing here is rounded up,
 * extrapolated or invented; when two numbers come from different harnesses, `harness` says so
 * and the UI shows the warning next to the comparison.
 *
 * Machine for all entries: AMD Radeon RX 7900 XTX (gfx1100, 24 GB), Ryzen 7 5700X, Linux, our lab server.
 */

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

