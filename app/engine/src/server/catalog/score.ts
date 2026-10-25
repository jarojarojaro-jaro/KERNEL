// Speed estimate and option score.
// GPU: decode t/s = our upstream measurement on this GPU/backend when we have one, else η × bandwidth / bytes per token
// (η = middle of estimator.ts ETA ranges: dense 0.55–0.67, MoE 0.31–0.55). RAM-bound machines: `ramSpeed` below.
// score = quality × quant quality factor × speed utility, utility = sqrt(min(t/s, 60) / 60): speed matters until a model
// is comfortably interactive, quality decides above that. MTP models get the low end of our measured MTP band (×1.5).
import type { Backend, Gpu } from '../../shared/types.ts';
import { CATALOG, type CatalogModel, type GpuSpec, type QuantFile } from './data.ts';
import { kvBytes } from './memory.ts';

const ETA = { dense: 0.61, moe: 0.43 } as const;
/** Low end of the measured MTP speed-up band (estimator.ts L1_MTP_BAND 1.5–2.2). */
export const MTP_FACTOR = 1.5;
/** Decode speed above which a model counts as fully interactive. */
const INTERACTIVE_TPS = 60;

const tokens = (s: string): Set<string> =>
  new Set(
    s.toLowerCase()
      .replace(/\((tm|r)\)|nvidia|geforce|amd|ati|radeon|intel|graphics|laptop gpu|series|apple/g, ' ')
      .split(/[^a-z0-9+]+/)
      .filter(Boolean),
  );

/** Matches a scanned GPU name to the bandwidth table (token-subset match, VRAM breaks ties; as landing matchGpu). */
export function matchGpu(name: string, vramGiB: number): GpuSpec | null {
  const q = tokens(name);
  if (q.size === 0) return null;
  const subset = (a: Set<string>, b: Set<string>): boolean => [...a].every((t) => b.has(t));
  const hits = CATALOG.gpus.filter((g) => {
    const n = tokens(g.name);
    return subset(n, q) || subset(q, n);
  });
  if (hits.length === 0) return null;
  const byVram = hits.filter((g) => g.vramGiB !== null && Math.abs(g.vramGiB - vramGiB) < 1.5);
  const pool = byVram.length ? byVram : hits;
  const rank = (g: GpuSpec): number => {
    const n = tokens(g.name);
    if (n.size === q.size && subset(n, q)) return 1e6;
    return subset(n, q) ? 1e3 + n.size : -n.size;
  };
  return [...pool].sort((a, b) => rank(b) - rank(a))[0] ?? null;
}

/** Memory bandwidth for an unknown GPU: conservative by memory size [SZACUNEK]. */
function fallbackBw(gpu: Gpu): number {
  if (gpu.kind !== 'discrete') return 120;
  return gpu.vramGiB >= 20 ? 700 : gpu.vramGiB >= 14 ? 400 : 270;
}

export interface Speed { tps: number; measured: boolean }

/** Plain (no speculation) decode speed of the upstream engine on a GPU with its own memory pool, t/s. */
export function decodeSpeed(m: CatalogModel, q: QuantFile, gpu: Gpu, spec: GpuSpec | null, backend: Backend): Speed {
  const hit = spec && m.measured.find((x) => x.gpu === spec.id && x.backend === backend && x.quant === q.quant);
  if (hit) return { tps: hit.decodeTps, measured: true };
  return { tps: ((m.kind === 'moe' ? ETA.moe : ETA.dense) * (spec?.bwGBs ?? fallbackBw(gpu))) / q.bTokGB, measured: false };
}

// RAM-bound machines (integrated graphics or CPU only): every generated token streams the active weights and the KV
// cache from system RAM, so decode t/s ≈ η × RAM bandwidth / bytes per token, prefill ≈ compute per CPU core.
// Calibrated on our lab CPU (Ryzen 7 5700X, 8 cores, DDR4-3200 2 channels = 51.2 GB/s, catalog `ramMeasured`):
// η = Qwen3.8-27B 0.75 (dense), LFM2.5-24B-A2B 0.70, Qwen3.6-35B-A3B 0.39 (MoE; its catalog bytes/token leave out
// the 248k-vocab output head, so the measured η absorbs it).
/** η range for models without a RAM measurement. */
const RAM_ETA = { dense: [0.6, 0.75], moe: [0.4, 0.7] } as const;
/** A model measured on our CPU, moved to other RAM and CPUs (and an integrated GPU on the same RAM) [SZACUNEK]. */
const RAM_SPREAD = [0.85, 1.1] as const;
/** KV read per token at this many cached tokens (the benchmark's prompt); deeper contexts write slower. */
export const RAM_KV_FILL = 4096;
/** Prefill compute per CPU core for unmeasured models, GFLOP/s (lab: 77 MoE … 132 dense, pp512). */
const PREFILL_GFLOPS_PER_CORE = 75;
/** Prefill of a long prompt: full attention grows with the filled context; the low end of the range [SZACUNEK]. */
const PREFILL_DEEP = 0.6;
/** Below this estimated decode speed an option is not offered (`too_slow_on_this_hw:<t/s>`). */
export const MIN_DECODE_TPS = 8;

/** Decode range (`tps` = its middle, used for ranking) and prefill range, t/s. */
export interface RamSpeed { tps: number; lo: number; hi: number; prefillLo: number; prefillHi: number }

export function ramSpeed(m: CatalogModel, q: QuantFile, bwGBs: number, cores: number): RamSpeed {
  const kvGB = kvBytes(m, RAM_KV_FILL, 'q8_0', 512, false) / 1e9;
  const bytes = q.bTokGB + kvGB;
  const meas = m.ramMeasured?.find((x) => x.quant === q.quant) ?? m.ramMeasured?.[0];
  const measQ = meas && m.quants.find((x) => x.quant === meas.quant);
  let lo: number;
  let hi: number;
  if (meas && measQ) {
    const eta = (meas.decodeTps * (measQ.bTokGB + kvGB)) / meas.ramBwGBs;
    lo = (eta * RAM_SPREAD[0] * bwGBs) / bytes;
    hi = (eta * RAM_SPREAD[1] * bwGBs) / bytes;
  } else {
    const eta = m.kind === 'moe' ? RAM_ETA.moe : RAM_ETA.dense;
    lo = (eta[0] * bwGBs) / bytes;
    hi = (eta[1] * bwGBs) / bytes;
  }
  const perCore = meas ? meas.prefillTps / meas.cores : PREFILL_GFLOPS_PER_CORE / (2 * m.activeB);
  const prefillHi = perCore * cores;
  return { tps: (lo + hi) / 2, lo, hi, prefillLo: prefillHi * PREFILL_DEEP, prefillHi };
}

export function score(m: CatalogModel, q: QuantFile, tps: number, mtp: boolean): number {
  const effective = mtp ? tps * MTP_FACTOR : tps;
  return m.quality * q.qualityFactor * Math.sqrt(Math.min(effective, INTERACTIVE_TPS) / INTERACTIVE_TPS);
}
