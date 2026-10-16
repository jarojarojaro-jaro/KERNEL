/**
 * The machine every desktop-prototype screen describes: our lab server. Spec values were read
 * from procfs/sysfs text files on 2026-10-16 (no GPU access): MemTotal 65 768 884 kB = 62.7 GiB,
 * mem_info_vram_total 25 753 026 560 B = 24.0 GiB, PCIe 16.0 GT/s ×16 = gen 4, power/control = on.
 * Observed GPU telemetry comes from the lab notes, never from a live reading.
 */
import { findGpu, type Hw } from '$lib/estimator';
import { M, type Measurement } from '$lib/data/measurements';

export const SCAN_SOURCE = '/proc/meminfo, /proc/cpuinfo, /sys/class/drm/card0/device/{mem_info_vram_total,current_link_speed,current_link_width,power/control}';

export const DEMO = {
	os: 'linux' as const,
	kernel: '6.8.0-138-generic',
	gpu: 'AMD Radeon RX 7900 XTX',
	gpuDetail: 'Navi 31 · RDNA3 gfx1100',
	vendor: 'amd',
	vramGiB: 24.0,
	ramGiB: 62.7,
	cpu: 'AMD Ryzen 7 5700X',
	threads: 16,
	isa: 'AVX2',
	pcie: { gen: 4, width: 16 },
	unified: false
};

export const DEMO_HW: Hw = { gpu: findGpu('rx-7900-xtx'), vramGiB: DEMO.vramGiB, ramGiB: DEMO.ramGiB, os: DEMO.os };

/** Model the prototype pretends is loaded (the one with the full measured before → after path). */
export const ACTIVE_MODEL_ID = 'qwen38-27b-q4kxl';
export const ACTIVE = M.qwenOursMtp;

/** GPU telemetry observed during MTP decode at a 285 W power cap (NOTES.md:146, NOTES.md:170). */
export const OBSERVED = {
	capW: 285,
	powerW: 284,
	junction: { lo: 85, hi: 88 },
	edge: { lo: 64, hi: 67 },
	fansRpm: 1850,
	source: 'KERNEL/qwen-opt/NOTES.md:146',
	second: { junction: 87, junctionMax: 90, mem: 84, edge: 67, powerW: 284, source: 'KERNEL/qwen-opt/NOTES.md:170' }
};

/** Engine build history on the lab machine (dates from the registry). */
export const HISTORY = {
	engine: { date: M.qwenOursMtp.date, m: M.qwenOursMtp },
	baco: { date: M.bacoAwake.date, before: M.bacoAsleep, after: M.bacoAwake }
};

/** Payload the opt-in telemetry would send. No IDs, no names, no content. */
export function telemetryPayload() {
	return {
		schema: 'HW1',
		os: DEMO.os,
		gpu: 'Radeon RX 7900 XTX',
		vendor: DEMO.vendor,
		vram_gib: DEMO.vramGiB,
		ngpu: 1,
		driver: 'amdgpu 6.8',
		ram_gib: DEMO.ramGiB,
		threads: DEMO.threads,
		isa: 'avx2',
		pcie: `${DEMO.pcie.gen}x${DEMO.pcie.width}`,
		unified_memory: false,
		backends: ['rocm', 'vulkan', 'cpu'],
		engine: 'amd-opt f61994f58',
		model: 'Qwen3.8-27B UD-Q4_K_XL',
		results: [] as number[]
	};
}

/** Strip a registry entry to what a downloaded report should carry. */
export function reportEntry(m: Measurement, lang: 'pl' | 'en') {
	return {
		id: m.id,
		model: `${m.model} ${m.quant}`,
		gpu: m.gpu,
		backend: m.backend,
		build: m.build,
		config: m.config[lang],
		value: m.value,
		unit: m.unit,
		harness: m.harness,
		method: m.method[lang],
		source: m.source,
		date: m.date
	};
}
