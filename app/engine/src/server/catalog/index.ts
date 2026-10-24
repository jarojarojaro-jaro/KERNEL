// Recommender: for every device (GPU × backend, or the CPU) and every model × quant, the largest context that fits
// (step 4096, ≤ ctxMax), then the best KV type at that context and the ubatch; options are scored by quality × speed.
import type { Backend, Gpu, Hw, MemPlan, Option, Recommendation } from '../../shared/types.ts';
import { CATALOG, type CatalogModel, type GpuSpec, type KvType, type QuantFile } from './data.ts';
import { memParts, memPlan, type MemConfig } from './memory.ts';
import { decodeSpeed, matchGpu, score } from './score.ts';
import engines from '../../../data/engines.json';

export { CATALOG } from './data.ts';
export const DEFAULT_MIN_CTX = 131072;
const CTX_STEP = 4096;
/** Headroom left free after the full-context plan. Linux: 100 MiB, what our measured production run proves safe
 *  (XTX, Qwen3.8-27B 204800 / ub 512 / MTP / full prompt: 23.84 of 23.95 GiB). Windows: 512 MiB for the compositor
 *  (DWM) and WDDM [INFERENCE]. macOS: none on top of the unified-memory budget (already 66–75% of RAM). */
const MARGIN_MIB: Record<Hw['os'], number> = { linux: 100, windows: 512, macos: 0 };
/** CUDA's K/V conversion pool grows with the prompt and is measured only up to a 55.6k prompt (3090: OOM at 204800 with
 *  633 MiB free after load, report 27); full-context CUDA plans keep this extra headroom. */
const CUDA_POOL_MARGIN_MIB = 200;
/** f16 KV only with this much memory left at the chosen context. */
const F16_HEADROOM_MIB = 2048;
/** Driver/firmware share of VRAM that is never allocatable (3090: 24576 total, 24126–24134 usable; XTX: 24560 total). */
const VRAM_RESERVE: Record<Gpu['vendor'], number> = { nvidia: 0.018, amd: 0.002, intel: 0.02, apple: 0 };
/** Apple: recommendedMaxWorkingSetSize ≈ 66% of RAM on smaller machines, 75% above 36 GB (report 04 §2.1.3). */
const unifiedShare = (ramGiB: number): number => (ramGiB > 36 ? 0.75 : 0.66);
const CPU_SHARE = 0.7;
const BACKEND_ORDER: Backend[] = ['cuda', 'rocm', 'metal', 'vulkan'];
/** ub 512 is chosen when it buys at least this much more context than ub 1024. */
const UB512_GAIN = 1.08;
/** Build number of the pinned upstream llama.cpp release (data/engines.json `upstream.tag`, "b<N>"). */
const PINNED_BUILD = Number(/^b(\d+)$/.exec(engines.upstream.tag)?.[1] ?? 0);

interface Device {
  backend: Backend;
  gpuIndex: number | null;
  gpu: Gpu | null;
  spec: GpuSpec | null;
  /** Memory the model may use, MiB (before the headroom margin). */
  budgetMiB: number;
  marginMiB: number;
  vramGiB: number;
  /** Speculation would run in one of our engines (data/engines.json kind "enigma" with MTP for this GPU). */
  enigmaMtp: boolean;
}

function devices(hw: Hw): Device[] {
  const marginMiB = MARGIN_MIB[hw.os];
  const out: Device[] = [];
  hw.gpus.forEach((gpu, i) => {
    const spec = matchGpu(gpu.name, gpu.vramGiB);
    const enigmaFor = (backend: Backend): boolean =>
      engines.engines.some((e) => e.kind === 'enigma' && e.backend === backend && e.os === hw.os && e.features.includes('mtp')
        && (!('gpuArchs' in e) || (gpu.arch !== undefined && (e.gpuArchs ?? []).includes(gpu.arch))));
    const budgetMiB = gpu.unified
      ? hw.ramGiB * unifiedShare(hw.ramGiB) * 1024
      : gpu.vramGiB * 1024 * (1 - VRAM_RESERVE[gpu.vendor]);
    for (const backend of BACKEND_ORDER.filter((b) => gpu.backends.includes(b))) {
      const margin = marginMiB + (backend === 'cuda' ? CUDA_POOL_MARGIN_MIB : 0);
      out.push({
        backend, gpuIndex: i, gpu, spec, budgetMiB, marginMiB: margin, vramGiB: gpu.unified ? hw.ramGiB : gpu.vramGiB,
        enigmaMtp: enigmaFor(backend),
      });
    }
  });
  if (out.length === 0) {
    out.push({
      backend: 'cpu', gpuIndex: null, gpu: null, spec: null, budgetMiB: hw.ramGiB * CPU_SHARE * 1024, marginMiB, vramGiB: 0,
      enigmaMtp: false,
    });
  }
  return out;
}

/** The model carries an MTP head that the optimisation can use on this device. */
const mtpCapable = (m: CatalogModel, d: Device): boolean =>
  d.backend !== 'cpu' && m.features.includes('mtp') && m.arch.nextn.layers > 0;

function config(d: Device, ctx: number, kvType: KvType, ub: number, spec: boolean): MemConfig {
  return { ctx, kvType, ub, backend: d.backend, vramGiB: d.vramGiB, spec, enigmaSpec: d.enigmaMtp, prompt: ctx };
}

const freeMiB = (m: CatalogModel, q: QuantFile, d: Device, c: MemConfig): number =>
  d.budgetMiB - d.marginMiB - memParts(m, q, c).totalMiB;

/** Largest context (multiple of 4096, or ctxMax itself) that fits; 0 when even 4096 does not. */
function maxCtx(m: CatalogModel, q: QuantFile, d: Device, kvType: KvType, ub: number, spec: boolean): number {
  const fits = (ctx: number): boolean => freeMiB(m, q, d, config(d, ctx, kvType, ub, spec)) >= 0;
  if (fits(m.ctxMax)) return m.ctxMax;
  let lo = 0, hi = Math.floor((m.ctxMax - 1) / CTX_STEP); // in CTX_STEP units; lo = 0 means "nothing fits"
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    if (fits(mid * CTX_STEP)) lo = mid;
    else hi = mid - 1;
  }
  return lo * CTX_STEP;
}

type Rejection = Recommendation['rejected'][number];

interface Plan { ctx: number; kvType: KvType; ub: number; spec: boolean }

/** ub 1024 by default; 512 when it reaches the minimum that 1024 misses or ≥ 8% more context (prefill slower, decode
 *  unchanged). Then the best KV type at that context. */
function plan(m: CatalogModel, q: QuantFile, d: Device, minCtx: number, spec: boolean): Plan | { ctx: number } {
  const ctx1024 = maxCtx(m, q, d, 'q4_0', 1024, spec);
  const ctx512 = maxCtx(m, q, d, 'q4_0', 512, spec);
  const use512 = ctx512 >= minCtx && (ctx1024 < minCtx || ctx512 >= ctx1024 * UB512_GAIN);
  const ub = use512 ? 512 : 1024;
  const ctx = use512 ? ctx512 : ctx1024;
  if (ctx < minCtx) return { ctx: Math.max(ctx1024, ctx512) };
  let kvType: KvType = 'q4_0';
  if (freeMiB(m, q, d, config(d, ctx, 'f16', ub, spec)) >= F16_HEADROOM_MIB) kvType = 'f16';
  else if (freeMiB(m, q, d, config(d, ctx, 'q8_0', ub, spec)) >= 0) kvType = 'q8_0';
  return { ctx, kvType, ub, spec };
}

function evaluate(m: CatalogModel, q: QuantFile, d: Device, hw: Hw, minCtx: number): Option | Rejection {
  const reject = (reason: string): Rejection => ({ modelId: m.id, quant: q.quant, reason });
  if (m.minUpstreamBuild > PINNED_BUILD) return reject(`engine_too_old:b${m.minUpstreamBuild}`);
  if (d.backend === 'cpu' && !m.cpuTier) return reject('not_cpu_tier');
  if (m.ctxMax < minCtx) return reject(`ctx_max_below_min:${m.ctxMax}`);
  const empty = memParts(m, q, config(d, 0, 'q4_0', 512, false));
  const usable = d.budgetMiB - d.marginMiB;
  if (empty.totalMiB > usable) return reject(`weights_too_big:${(empty.totalMiB / 1024).toFixed(1)}/${(usable / 1024).toFixed(1)}`);

  // With an MTP head, plan the draft context too (so the MTP candidate runs at the same context); without it the
  // plain plan may reach a larger context. Both are scored, the better one is offered.
  const speed = decodeSpeed(m, q, d.gpu, d.spec, d.backend);
  const plans = (mtpCapable(m, d) ? [true, false] : [false]).map((spec) => plan(m, q, d, minCtx, spec));
  const ok = plans.filter((p): p is Plan => 'kvType' in p);
  const best = ok.sort((a, b) => score(m, q, speed.tps, b.spec) - score(m, q, speed.tps, a.spec) || b.ctx - a.ctx)[0];
  if (!best) return reject(`ctx_below_min:${Math.max(...plans.map((p) => p.ctx))}`);
  const { ctx, kvType, ub, spec } = best;

  const why: string[] = [speed.measured ? `speed_measured:${speed.tps.toFixed(0)}` : `speed_estimated:${speed.tps.toFixed(0)}`];
  if (spec) why.push('mtp_head');
  else if (mtpCapable(m, d)) why.push('mtp_no_memory'); // the file has an MTP head, its draft context does not fit
  if (m.kind === 'moe' && m.activeB <= 4) why.push('moe_fast');
  why.push(ctx === m.ctxMax ? 'ctx_model_max' : 'ctx_memory_limit', `kv_${kvType}`);
  if (ub === 512) why.push('ub512_for_ctx');
  if (d.gpu?.unified) why.push('unified_memory');
  if (d.backend === 'cpu') why.push('cpu_only');
  if (hw.os === 'windows' && d.backend !== 'cpu') why.push('windows_reserve');
  if (CATALOG.licenses[m.license]?.commercial === 'conditional') why.push('license_conditional');

  return {
    id: `${m.id}/${q.quant}/${d.backend}${d.gpuIndex === null ? '' : `/${d.gpuIndex}`}`,
    modelId: m.id, name: m.name, family: m.family, params: m.params, quant: q.quant,
    file: { repo: q.repo, path: q.path, sizeBytes: q.sizeBytes, sha256: q.sha256 },
    ctx, ctxMax: m.ctxMax, kvType, ub, backend: d.backend, gpuIndex: d.gpuIndex,
    mem: memPlan(m, q, config(d, ctx, kvType, ub, spec), d.budgetMiB / 1024),
    features: m.features.filter((f) => f !== 'mtp' || spec),
    score: Math.round(score(m, q, speed.tps, spec) * 100) / 100,
    why,
  };
}

const better = (a: Option, b: Option): number => b.score - a.score || b.ctx - a.ctx;

export function recommend(hw: Hw, minCtx: number = DEFAULT_MIN_CTX): Recommendation {
  const options = new Map<string, Option>();
  const rejected = new Map<string, Rejection>();
  for (const d of devices(hw)) {
    for (const m of CATALOG.models) {
      for (const q of m.quants) {
        const key = `${m.id}/${q.quant}`;
        const r = evaluate(m, q, d, hw, minCtx);
        if ('reason' in r) {
          if (!rejected.has(key)) rejected.set(key, r);
          continue;
        }
        // Same model × quant: on one GPU the preferred backend wins (devices come in BACKEND_ORDER: our engines are
        // CUDA/ROCm/Metal builds); across GPUs the better option wins.
        const prev = options.get(key);
        if (!prev || (prev.gpuIndex !== r.gpuIndex && better(r, prev) < 0)) options.set(key, r);
      }
    }
  }
  for (const key of options.keys()) rejected.delete(key);
  const ranked = [...options.values()].sort(better);
  const pick = ranked[0] ?? null;
  if (pick) {
    const topQuality = Math.max(...ranked.map((o) => qualityOf(o)));
    if (qualityOf(pick) === topQuality) pick.why.unshift('quality_best');
  }
  // Alternatives: the next best options of other models (one quant per model).
  const seen = new Set(pick ? [pick.modelId] : []);
  const alternatives: Option[] = [];
  for (const o of ranked) {
    if (alternatives.length === 3) break;
    if (seen.has(o.modelId)) continue;
    seen.add(o.modelId);
    alternatives.push(o);
  }
  return { minCtx, pick, alternatives, rejected: [...rejected.values()] };
}

function qualityOf(o: Option): number {
  const m = CATALOG.models.find((x) => x.id === o.modelId);
  const q = m?.quants.find((x) => x.quant === o.quant);
  return m && q ? m.quality * q.qualityFactor : 0;
}

export interface PlanRequest { ctx: number; kvType: KvType; ub: number; spec: boolean; backend: Backend; gpuIndex: number | null }

/** Memory plan of one model × quant on this machine in an explicit configuration (same margins as recommend). */
export function planFor(hw: Hw, modelId: string, quant: string, r: PlanRequest): { mem: MemPlan; fits: boolean } {
  const m = CATALOG.models.find((x) => x.id === modelId);
  const q = m?.quants.find((x) => x.quant === quant);
  const d = devices(hw).find((x) => x.backend === r.backend && x.gpuIndex === r.gpuIndex);
  if (!m || !q) throw new Error(`planFor: ${modelId} ${quant} is not in the catalog`);
  if (!d) throw new Error(`planFor: no ${r.backend} device ${r.gpuIndex ?? 'cpu'} on this machine`);
  const c = config(d, r.ctx, r.kvType, r.ub, r.spec && m.arch.nextn.layers > 0);
  return { mem: memPlan(m, q, c, d.budgetMiB / 1024), fits: freeMiB(m, q, d, c) >= 0 };
}

/** Re-plans an option with another ubatch / context / KV type / speculation (backend: does `-ub 2048` fit?). */
export function replan(
  opt: Option, hw: Hw, change: { ub?: number; ctx?: number; kvType?: KvType; spec?: boolean },
): { mem: MemPlan; fits: boolean } {
  return planFor(hw, opt.modelId, opt.quant, {
    ctx: change.ctx ?? opt.ctx, kvType: change.kvType ?? opt.kvType, ub: change.ub ?? opt.ub,
    spec: change.spec ?? opt.features.includes('mtp'), backend: opt.backend, gpuIndex: opt.gpuIndex,
  });
}
