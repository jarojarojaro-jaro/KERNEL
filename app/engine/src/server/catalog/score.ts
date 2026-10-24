// Speed estimate and option score.
// decode t/s = our upstream measurement on this GPU/backend when we have one, else η × bandwidth / bytes per token
// (η = middle of estimator.ts ETA ranges: dense 0.55–0.67, MoE 0.31–0.55; CPU-only takes the low end).
// score = quality × quant quality factor × speed utility, utility = sqrt(min(t/s, 60) / 60): speed matters until a model
// is comfortably interactive, quality decides above that. MTP models get the low end of our measured MTP band (×1.5).
import type { Backend, Gpu } from '../../shared/types.ts';
import { CATALOG, type CatalogModel, type GpuSpec, type QuantFile } from './data.ts';

const ETA = { dense: { lo: 0.55, mid: 0.61 }, moe: { lo: 0.31, mid: 0.43 } } as const;
/** Low end of the measured MTP speed-up band (estimator.ts L1_MTP_BAND 1.5–2.2). */
export const MTP_FACTOR = 1.5;
/** Decode speed above which a model counts as fully interactive. */
const INTERACTIVE_TPS = 60;
/** Two-channel desktop RAM (between DDR4-3200 51 GB/s and DDR5-5600 89.6 GB/s, report 04 §2.1.6). */
export const CPU_BW_GBS = 60;

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
  if (gpu.unified) return 120;
  return gpu.vramGiB >= 20 ? 700 : gpu.vramGiB >= 14 ? 400 : 270;
}

export interface Speed { tps: number; measured: boolean }

/** Plain (no speculation) decode speed of the upstream engine, t/s. */
export function decodeSpeed(m: CatalogModel, q: QuantFile, gpu: Gpu | null, spec: GpuSpec | null, backend: Backend): Speed {
  const hit = spec && m.measured.find((x) => x.gpu === spec.id && x.backend === backend && x.quant === q.quant);
  if (hit) return { tps: hit.decodeTps, measured: true };
  const eta = m.kind === 'moe' ? ETA.moe : ETA.dense;
  const bw = backend === 'cpu' || !gpu ? CPU_BW_GBS : spec?.bwGBs ?? fallbackBw(gpu);
  return { tps: ((backend === 'cpu' ? eta.lo : eta.mid) * bw) / q.bTokGB, measured: false };
}

export function score(m: CatalogModel, q: QuantFile, tps: number, mtp: boolean): number {
  const effective = mtp ? tps * MTP_FACTOR : tps;
  return m.quality * q.qualityFactor * Math.sqrt(Math.min(effective, INTERACTIVE_TPS) / INTERACTIVE_TPS);
}
