/**
 * The welcome screen's speed duel. Copied verbatim from the site's measurement registry
 * (KERNEL/app/landing/src/lib/data/measurements.ts, entries `qwenXtxDefault` and `qwenXtxOurs`, the
 * numbers in the enigmalabz.com hero). Never edit a value here without the registry changing first.
 */
export const DUEL = {
	gpu: 'Radeon RX 7900 XTX',
	model: 'Qwen3.8-27B UD-Q4_K_XL',
	/** upstream llama.cpp, ROCm, default settings, no speculation; ~/qwen-opt/queue/logs/fb-qwen-U0-p1.log:2 */
	typical: 35.9,
	/** amd-opt (our engine), ROCm, the same flags + MTP speculation; ~/qwen-opt/queue/logs/fb-qwen-T-p1.log:2 */
	ours: 114.8,
	/** both dials share one scale (t/s), as on the site */
	scale: 140
} as const;
