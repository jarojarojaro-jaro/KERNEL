/**
 * Measured facts behind the methodology journey. Every number here comes from a report, a log or
 * a trace on the lab machine (RX 7900 XTX, gfx1100); the `src` next to it is where to check it.
 * Speeds for the record board come from $lib/data/measurements (the same data the rest of the site uses).
 */
import { M, MD5, SHEET } from '$lib/data/measurements';

const R = 'KERNEL/product/research';

/** Greedy md5 regression gates (fresh server, T=0), equal before and after the PM4 fix. */
export const GATES = [
	{ id: 'qwen-plain', label: 'Qwen3.8-27B', mode: 'plain', md5: MD5.qwenPlain },
	{ id: 'qwen-mtp', label: 'Qwen3.8-27B', mode: 'MTP', md5: MD5.qwenMtp },
	{ id: 'lfm', label: 'LFM2.5-24B-A2B', mode: 'plain', md5: MD5.lfm }
] as const;
export const GATES_SRC = `KERNEL/qwen-opt/STATUS-NEXT.md:15; ${R}/26-kolejka-gpu-wieczor.md:9`;

const Q = SHEET.correctness.quality;
/** KLD of our engine vs upstream, next to upstream's own run-to-run noise (RTX 3060). */
export const KLD = [
	{ id: 'saluki', model: 'Saluki 27B', ours: Q.saluki.ours.v, noise: Q.saluki.noise.v, src: Q.saluki.ours.src },
	{ id: 'bonsai', model: 'Ternary Bonsai 2 27B', ours: Q.bonsai.ours.v, noise: Q.bonsai.noise.v, src: Q.bonsai.ours.src }
];

/** test-backend-ops: every case of the touched ops passes against the CPU reference. */
export const BACKEND_OPS = [
	{ op: 'TOP_K', pass: 533, of: 533, src: `${R}/24m-weryfikacja-gpu.md:36` },
	{ op: 'GET_ROWS', pass: 222, of: 222, src: `${R}/24m-weryfikacja-gpu.md:36` },
	{ op: 'MUL_MAT', pass: 822, of: 822, src: `${R}/26-kolejka-gpu-wieczor.md:15` },
	{ op: 'FLASH_ATTN', pass: 740, of: 740, src: `${R}/26-kolejka-gpu-wieczor.md:10` }
] as const;

/**
 * One MTP decode step on the RX 7900 XTX (Qwen3.8-27B, code-edit prompt), rocprofv3 kernel trace,
 * 96 steps analysed. Busy time split by kernel class; the rest of the busy time is small ops.
 */
export const STEP = {
	wall: 30.99,
	busy: 26.85,
	idle: 4.14,
	kernels: 946,
	ops: [
		{ id: 'mmvq5', label: 'mmvq n5', ms: 21.846 },
		{ id: 'mmvq1', label: 'mmvq n1', ms: 1.962 },
		{ id: 'rms', label: 'rms_norm', ms: 0.931 },
		{ id: 'gdn', label: 'gdn', ms: 0.714 },
		{ id: 'fa', label: 'flash_attn', ms: 0.607 },
		{ id: 'conv', label: 'ssm_conv', ms: 0.262 },
		{ id: 'glu', label: 'gated_op', ms: 0.223 },
		{ id: 'quant', label: 'quantize', ms: 0.203 }
	],
	/** One representative step: three bursts of kernels separated by host gaps (ms). */
	bursts: [
		{ n: 13, span: 0.13 },
		{ n: 109, span: 2.66 },
		{ n: 824, span: 26.6 }
	],
	gaps: [0.374, 0.288, 0.168],
	sampleWall: 30.22,
	src: `${R}/24m-weryfikacja-gpu.md:46; ~/qwen-opt/vcost/prof/off (vc_trace.py)`
} as const;

/** Wide (16-row) verify step, with the draft check on CPU vs on GPU (LLAMA_GPU_VERIFY). */
export const W16 = {
	off: { wall: 37.38, busy: 31.52, idle: 5.86, gaps: [0.96, 0.99, 0.05] },
	on: { wall: 36.46, busy: 31.85, idle: 4.61, gaps: [0.38, 0.16, 0.05] },
	gain: { pct: [2.2, 2.4], ms: [0.71, 0.81] },
	src: `${R}/24m-weryfikacja-gpu.md:3-20,31-32,42-47`
} as const;

/** Speculation on the RX 7900 XTX: chat (spec_sweep T=1) and code edits (T=0, 4 files). */
const qwen = { a0: M.qwenXtxDefault, a1: M.qwenXtxFlags, ours: M.qwenXtxOurs };
export const SPEC = {
	chat: { a0: qwen.a0.value, a1: qwen.a1.value, ours: qwen.ours.value, msStep: 27.67, src: qwen.ours.source },
	code: { a0: 35.5, a1: 89.0, ours: 419.7, src: 'app/landing/src/lib/data/measurements.ts (rx-7900-xtx · qwen38 · note)' },
	/** Tokens per step with the W16 lookup tail on code edits: 14.5 of 16 possible. */
	tail: { got: 14.5, of: 16, src: `${R}/24j-router-edycja.md:12` },
	lookupSrc: `${R}/16b-lookup-tail.md`
} as const;
/** Tokens per verify step in chat, derived: t/s × ms/step (both from the same run). */
export const CHAT_TOK_STEP = (SPEC.chat.ours * SPEC.chat.msStep) / 1000;

/** GFX11 PM4 fix (report 17 §9, validated in the GPU queue of report 26). */
export const PM4 = {
	requests: 1205,
	faults: 0,
	lfm: { before: 266.4, after: 295.7, pct: 11.1 },
	qwen: { before: 111.0, after: 115.3, pct: 4.2, msBefore: 29.13, msAfter: 27.8 },
	src17: `${R}/17-gpu-page-fault.md:210-240,286,381,443`,
	src26: `${R}/26-kolejka-gpu-wieczor.md:9,22`
} as const;

/** gfx1100: 1536 VGPRs per SIMD lane, allocated in blocks of 24; at most 16 waves per SIMD. */
export const SIMD = { vgprs: 1536, granule: 24, maxWaves: 16 } as const;
export const wavesFor = (vgpr: number) => Math.min(SIMD.maxWaves, Math.floor(SIMD.vgprs / (Math.ceil(vgpr / SIMD.granule) * SIMD.granule)));
export const OCC = {
	before: 140,
	after: 119,
	src: `${R}/24n-mmvq-n5.md:16-22; ${R}/24f-mmvq-i-fa.md:12`
} as const;
