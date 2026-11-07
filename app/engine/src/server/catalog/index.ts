// Recommender: for every device (GPU × backend, or the CPU) and every model × quant, the largest context that fits
// (step 4096, ≤ ctxMax), then the best KV type at that context and the ubatch; options are scored by quality × speed.
// Machines without a discrete GPU (integrated graphics or none) are RAM-bound: the model lives in system RAM, speed comes
// from the RAM bandwidth (`ramSpeed`), and options too slow to use are rejected.
import type { Backend, Gpu, Hw, MemPlan, Option, Recommendation } from '../../shared/types.ts';
import { CATALOG, type CatalogModel, type GpuSpec, type KvType, type QuantFile } from './data.ts';
import { memParts, memPlan, MTP_DRAFT_UB, MTP_N_MAX_DEFAULT, type MemConfig } from './memory.ts';
import { decodeSpeed, matchGpu, MIN_DECODE_TPS, ramSpeed, score, type RamSpeed } from './score.ts';
import {
  engineAvailable, engineById, ENGINES, enigmaEnginesFor, profileMatch, type EngineEntry, type EngineProfile, type ProfileMtp,
} from '../engine.ts';

export { CATALOG } from './data.ts';
export const DEFAULT_MIN_CTX = 131072;
const CTX_STEP = 4096;
/** Headroom left free after the full-context plan. Linux: 100 MiB, what our measured production run proves safe
 *  (XTX, Qwen3.8-27B 204800 / ub 512 / MTP / full prompt: 23.84 of 23.95 GiB). Windows: 512 MiB for the compositor
 *  (DWM) and WDDM [INFERENCE]. macOS: none on top of the unified-memory budget (already 66–75% of RAM). */
const MARGIN_MIB: Record<Hw['os'], number> = { linux: 100, windows: 512, macos: 0 };
/** Extra headroom of full-context CUDA plans. Our engine's K/V conversion pool grows with the prompt and is measured only
 *  up to a 55.6k prompt (3090: OOM at 204800 with 633 MiB free after load, report 27). Upstream grows only +2…+28 MiB
 *  (campaign 67), but this also covers the CUDA total that VRAM_RESERVE overstates and the per-card overhead that
 *  memory.ts's formula understates (4090 −135, 5080 −107 MiB). */
const CUDA_POOL_MARGIN_MIB = 200;
/** f16 KV only with this much memory left at the chosen context. */
const F16_HEADROOM_MIB = 2048;
/** Driver/firmware share of VRAM that is never allocatable (3090: 24576 total, 24126–24134 usable; XTX: 24560 total).
 *  NVIDIA: the scan reads nvidia-smi's total, the allocatable limit is CUDA's (cudaMemGetInfo). Campaign 67 measured the
 *  gap per card: 3080 313, 4070 327, 3070 350, 3060 379, 4060 Ti 433, 2080 Ti 447, 3090 450, 5060 Ti 465, 5080 466,
 *  4090 482, 5090 498 MiB (1.5–4.3%): neither a constant nor a share of VRAM, so the 1.8% (exact on the 3090) stays;
 *  with the scan's 0.1 GiB rounding it overstates the CUDA total by up to ~250 MiB on 8–16 GB cards (CUDA_POOL_MARGIN_MIB). */
const VRAM_RESERVE: Record<Gpu['vendor'], number> = { nvidia: 0.018, amd: 0.002, intel: 0.02, apple: 0 };
/** Measured nvidia-smi-total → CUDA-allocatable gap per card (campaign 67, `-lv 4`, MiB). CUDA plans take the exact
 *  value instead of VRAM_RESERVE; an unknown card falls back to 1.8% + 150 MiB. */
const CUDA_GAP_MIB: [RegExp, number][] = [
  [/RTX 5090/i, 498], [/RTX 5080/i, 466], [/RTX 5070 Ti/i, 466], [/RTX 5070/i, 400], [/RTX 5060 Ti/i, 465],
  [/RTX 4090/i, 482], [/RTX 4080/i, 470], [/RTX 4070 Ti/i, 400], [/RTX 4070/i, 327], [/RTX 4060 Ti/i, 433],
  [/RTX 3090/i, 450], [/RTX 3080/i, 313], [/RTX 3070/i, 350], [/RTX 3060 Ti/i, 350], [/RTX 3060/i, 379],
  [/RTX 2080 Ti/i, 447],
];
/** Lazy-loaded CUDA kernels: a 16 GB plan with 0.5–0.66 GiB free by nvidia-smi (0.08–0.21 GiB by cudaMemGetInfo) OOMed in
 *  `launch_mul_mat_q` on the first 4096-token prompt (campaign 67). Together with the CUDA_GAP_MIB budget it keeps ≈0.7 GiB. */
const CUDA_KERNEL_MARGIN_MIB = 300;
/** Apple: recommendedMaxWorkingSetSize ≈ 66% of RAM on smaller machines, 75% above 36 GB (report 04 §2.1.3). */
const unifiedShare = (ramGiB: number): number => (ramGiB > 36 ? 0.75 : 0.66);
/** RAM-bound machines: RAM kept for the system and the user's programs (browser, editor) while the model is loaded:
 *  Windows at least 8 GB or 25% (a 32 GB box keeps 8), Linux/macOS at least 6 GB or 20% [SZACUNEK]. */
const RAM_RESERVE: Record<Hw['os'], { minGiB: number; share: number }> = {
  windows: { minGiB: 8, share: 0.25 }, linux: { minGiB: 6, share: 0.2 }, macos: { minGiB: 6, share: 0.2 },
};
/** System RAM an integrated GPU may map when the scan could not read it (Windows WDDM: ½ RAM; amdgpu GTT default). */
const IGPU_SHARED_DEFAULT = 0.5;
const BACKEND_ORDER: Backend[] = ['cuda', 'rocm', 'metal', 'vulkan'];
/** A smaller ub must buy at least this much more context to replace the larger one. */
const UB_GAIN = 1.08;
/** A measured speed beats an estimated one unless the estimate's score is more than 20% higher. */
const UNMEASURED_MARGIN = 1.2;
/** RAM-bound plans with less than 3% of the budget free are demoted by this factor (`tight_memory`). */
const TIGHT_FREE = 0.03;
const TIGHT_DEMOTE = 0.8;
/** Build number of the pinned upstream llama.cpp release (data/engines.json `upstream.tag`, "b<N>"). */
const PINNED_BUILD = Number(/^b(\d+)$/.exec(ENGINES.upstream.tag)?.[1] ?? 0);

/** A RAM-bound device: integrated graphics or the CPU, weights in system RAM. */
interface RamDevice {
  bwGBs: number;
  reserveGiB: number;
  /** CPU device on a machine with integrated graphics: the RAM that graphics can map (GiB); null without one. */
  igpuPoolGiB: number | null;
}

interface Device {
  backend: Backend;
  gpuIndex: number | null;
  gpu: Gpu | null;
  spec: GpuSpec | null;
  /** Memory the model may use, MiB (before the headroom margin). */
  budgetMiB: number;
  marginMiB: number;
  vramGiB: number;
  /** Speculation would run in our fork engine (data/engines.json kind "enigma", `memory: "fork"`, MTP, this GPU). */
  forkMtp: boolean;
  /** Our engines built for this GPU × backend (published or not; `engineAvailable` decides). */
  enigma: EngineEntry[];
  ram: RamDevice | null;
}

export function ramReserveGiB(hw: Hw): number {
  const r = RAM_RESERVE[hw.os];
  return Math.round(Math.max(r.minGiB, hw.ramGiB * r.share) * 10) / 10;
}

function devices(hw: Hw): Device[] {
  const marginMiB = MARGIN_MIB[hw.os];
  const out: Device[] = [];
  const ownMemory = hw.gpus.some((g) => g.kind !== 'integrated');
  const reserveGiB = ramReserveGiB(hw);
  const ramFreeGiB = Math.max(0, hw.ramGiB - reserveGiB);
  let igpuPoolGiB: number | null = null;
  hw.gpus.forEach((gpu, i) => {
    const spec = matchGpu(gpu.name, gpu.vramGiB);
    if (gpu.kind === 'integrated') {
      // With a discrete GPU the iGPU only drives the display. Without one it computes in RAM: what the driver lets it
      // map (carve-out + shared/GTT; llama.cpp's Vulkan backend sums these heaps for an integrated GPU), capped by
      // the RAM left after the system reserve. Strix Halo-class chips are in the bandwidth table; the rest run at RAM speed.
      if (ownMemory) return;
      const poolGiB = gpu.vramGiB + (gpu.sharedGiB ?? hw.ramGiB * IGPU_SHARED_DEFAULT);
      const budgetGiB = Math.min(poolGiB, gpu.vramGiB + ramFreeGiB);
      for (const backend of BACKEND_ORDER.filter((b) => gpu.backends.includes(b))) {
        igpuPoolGiB = Math.max(igpuPoolGiB ?? 0, budgetGiB);
        out.push({
          backend, gpuIndex: i, gpu, spec, budgetMiB: budgetGiB * 1024, marginMiB, vramGiB: gpu.vramGiB, forkMtp: false, enigma: [],
          ram: { bwGBs: spec?.unified ? spec.bwGBs : hw.memory.bandwidthGBs, reserveGiB, igpuPoolGiB: null },
        });
      }
      return;
    }
    const budgetAll = gpu.kind === 'apple'
      ? hw.ramGiB * unifiedShare(hw.ramGiB) * 1024
      : gpu.vramGiB * 1024 * (1 - VRAM_RESERVE[gpu.vendor]);
    const budgetCuda = gpu.kind === 'apple'
      ? budgetAll
      : gpu.vramGiB * 1024
        - (CUDA_GAP_MIB.find(([re]) => re.test(gpu.name))?.[1] ?? gpu.vramGiB * 1024 * VRAM_RESERVE.nvidia + 150);
    for (const backend of BACKEND_ORDER.filter((b) => gpu.backends.includes(b))) {
      const budgetMiB = backend === 'cuda' ? budgetCuda : budgetAll;
      const margin = marginMiB + (backend === 'cuda' ? CUDA_POOL_MARGIN_MIB + CUDA_KERNEL_MARGIN_MIB : 0);
      const enigma = enigmaEnginesFor(hw.os, hw.arch, backend, gpu.arch);
      out.push({
        backend, gpuIndex: i, gpu, spec, budgetMiB, marginMiB: margin, vramGiB: gpu.kind === 'apple' ? hw.ramGiB : gpu.vramGiB,
        forkMtp: enigma.some((e) => e.memory === 'fork' && e.features.includes('mtp')), enigma, ram: null,
      });
    }
  });
  if (!ownMemory || out.length === 0) {
    out.push({
      backend: 'cpu', gpuIndex: null, gpu: null, spec: null, budgetMiB: ramFreeGiB * 1024, marginMiB, vramGiB: 0,
      forkMtp: false, enigma: [], ram: { bwGBs: hw.memory.bandwidthGBs, reserveGiB, igpuPoolGiB },
    });
  }
  return out;
}

/** The model carries an MTP head that the optimisation can use on this device. */
const mtpCapable = (m: CatalogModel, d: Device): boolean =>
  d.backend !== 'cpu' && m.features.includes('mtp') && m.arch.nextn.layers > 0;

/** An MTP plan run by one of our engines' MTP profiles (upstream-style flags: draft length, draft ubatch, draft KV).
 *  `ctk`: the engine's draft cache takes -ctk/-ctv (feature `mtp-draft-kv-ctk`, the PrismML fork); `fork`: our CUDA
 *  fork's draft (feature `mtp-fork-draft`: state snapshots + reduced draft vocabulary, memory.ts forkDraft). */
interface MtpRun { entry: EngineEntry; profile: EngineProfile; mtp: ProfileMtp; lean: boolean; ctk: boolean; fork: boolean }

function mtpRun(entry: EngineEntry, m: CatalogModel, q: QuantFile): MtpRun | null {
  const profile = profileMatch(entry, m.id, q.path);
  if (profile?.spec !== 'mtp' || !profile.mtp) return null;
  const has = (f: string): boolean => entry.features.includes(f);
  return { entry, profile, mtp: profile.mtp, lean: has('mtp-lean-reserve'), ctk: has('mtp-draft-kv-ctk'), fork: has('mtp-fork-draft') };
}

/** The engine that runs this file's MTP plan on the device: an available engine of ours for this GPU with an MTP profile
 *  for it (only the model's own engine when it needs one; a `planOnlyMeasured` engine only with a VERIFIED entry for this
 *  card × model × quant); null = the baseline engine with the optimisation's default upstream MTP (optimize.ts specArgs). */
function mtpRunFor(m: CatalogModel, q: QuantFile, d: Device, os: Hw['os']): MtpRun | null {
  for (const e of d.enigma) {
    if ((m.engine && e.id !== m.engine) || !engineAvailable(e)) continue;
    if (e.planOnlyMeasured && !VERIFIED.some((v) => v.engine === e.id && v.os === os && v.modelId === m.id && v.quant === q.quant
      && d.gpu !== null && v.card.test(d.gpu.name))) continue;
    const run = mtpRun(e, m, q);
    if (run) return run;
  }
  return null;
}

/** MTP plans size the draft as it will run: our engine's MTP profile, else the optimisation's MTP candidate (upstream
 *  defaults: f16 draft KV). */
function config(d: Device, ctx: number, kvType: KvType, ub: number, spec: boolean, run: MtpRun | null): MemConfig {
  return {
    ctx, kvType, ub, backend: d.backend, vramGiB: d.vramGiB, spec, enigmaSpec: run ? false : d.forkMtp,
    mtpN: run?.mtp.nMax ?? MTP_N_MAX_DEFAULT, ubd: run ? (run.mtp.ubd ?? ub) : MTP_DRAFT_UB,
    draftKv: run?.ctk ? kvType : (run?.mtp.draftKv ?? 'f16'), leanReserve: run?.lean ?? false, forkDraft: run?.fork ?? false,
    prompt: ctx,
  };
}

const freeMiB = (m: CatalogModel, q: QuantFile, d: Device, c: MemConfig): number =>
  d.budgetMiB - d.marginMiB - memParts(m, q, c).totalMiB;

/** Largest context (multiple of 4096, or ctxMax itself) that fits; 0 when even 4096 does not. */
function maxCtx(m: CatalogModel, q: QuantFile, d: Device, kvType: KvType, ub: number, spec: boolean, run: MtpRun | null): number {
  const fits = (ctx: number): boolean => freeMiB(m, q, d, config(d, ctx, kvType, ub, spec, run)) >= 0;
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

/** Configurations run end-to-end in campaign 67 on the real card (KV q4_0), with upstream CUDA unless `engine` names one
 *  of ours (the engine that runs that plan: the MTP profile's for an MTP plan, else the baseline engine). A measured
 *  configuration replaces the estimate for that card × model × quant × engine when the estimate lands no more than
 *  VERIFIED_SLACK_MIB over the margin (the catalog's per-card overhead is conservative): it may reach further than the
 *  estimate, and it caps it (a context we did not run is not offered above one we did). Only the measured speculation
 *  mode is offered there: MTP with stock upstream on the 16 GB cards (b12110, ub 256, ubd 64) OOMed at load with n 3 and,
 *  with n 1/2, loaded with 0.4–0.6 GiB free by nvidia-smi and OOMed on the first long prefill, so their plain runs
 *  exclude it (our lean-reserve engine's MTP is a different engine: its own entries and profile cap apply). */
const VERIFIED_SLACK_MIB = 700;
const VERIFIED: { card: RegExp; os: Hw['os']; modelId: string; quant: string; ctx: number; ub: number; spec: boolean; engine?: string }[] = [
  // 4090, upstream b12110, MTP n 3 + ubd 64: peak 24 036 of 24 082 MiB at a 261 504-token fill, 30-min soak
  { card: /RTX 4090/i, os: 'linux', modelId: 'qwen38-27b', quant: 'UD-Q4_K_XL', ctx: 262144, ub: 256, spec: true },
  // 4090, UD-Q4_K_M, MTP n 2 + ubd 64, ub 512: load 23 598 MiB
  { card: /RTX 4090/i, os: 'linux', modelId: 'qwen38-27b', quant: 'UD-Q4_K_M', ctx: 262144, ub: 512, spec: true },
  // 5090, UD-Q6_K, MTP n 2 + ubd 64, ub 1024: peak 28 448 of 32 109 MiB, 30-min soak. ABBA on one host (67c): the pinned
  // b11856 with MTP n 3 runs 99.8 t/s vs b12110 91.6–91.9 (n 2: 93.5), so 24/32 GB keep the pin.
  { card: /RTX 5090/i, os: 'linux', modelId: 'qwen38-27b', quant: 'UD-Q6_K', ctx: 262144, ub: 1024, spec: true },
  // 16 GB, GSQ IQ3_XXS plain, ub 256: 4060 Ti fill 216 448 tokens peak 14 562 MiB; 5060 Ti fill 200 064 peak 14 569;
  // 5080 load + T=1 runs (63 t/s)
  { card: /RTX 4060 Ti/i, os: 'linux', modelId: 'qwen38-27b', quant: 'GSQ-IQ3_XXS', ctx: 217088, ub: 256, spec: false },
  { card: /RTX 5060 Ti/i, os: 'linux', modelId: 'qwen38-27b', quant: 'GSQ-IQ3_XXS', ctx: 200704, ub: 256, spec: false },
  { card: /RTX 5080/i, os: 'linux', modelId: 'qwen38-27b', quant: 'GSQ-IQ3_XXS', ctx: 208896, ub: 256, spec: false },
  // 12 GB, Saluki IQ2-mix plain, ub 256: 4070 fill 150 912 tokens peak 11 197 MiB (135 168: fill + soak);
  // 3060 load + T=1 runs at 135 168
  { card: /RTX 4070(?! Ti| SUPER)/i, os: 'linux', modelId: 'saluki-27b', quant: 'IQ2-mix', ctx: 151552, ub: 256, spec: false },
  { card: /RTX 3060(?! Ti)/i, os: 'linux', modelId: 'saluki-27b', quant: 'IQ2-mix', ctx: 135168, ub: 256, spec: false },
  // enigma-cuda-lean (b12110 + lean reserve), GSQ IQ3_XXS, MTP n 2 + ubd 64, draft KV q4_0, ub 256 (campaign 67c): full
  // fills 4060 Ti 229 376 (peak 15 736 MiB, 36.3 t/s T=1), 5060 Ti 229 376 (15 762, 43.4), 5080 217 088 (15 632, 81.6;
  // 229 376 crashed there)
  { card: /RTX 4060 Ti/i, os: 'linux', modelId: 'qwen38-27b', quant: 'GSQ-IQ3_XXS', ctx: 229376, ub: 256, spec: true, engine: 'enigma-cuda-lean' },
  { card: /RTX 5060 Ti/i, os: 'linux', modelId: 'qwen38-27b', quant: 'GSQ-IQ3_XXS', ctx: 229376, ub: 256, spec: true, engine: 'enigma-cuda-lean' },
  { card: /RTX 5080/i, os: 'linux', modelId: 'qwen38-27b', quant: 'GSQ-IQ3_XXS', ctx: 217088, ub: 256, spec: true, engine: 'enigma-cuda-lean' },
  // enigma-cuda-fork (cuda-topka2 + kvq + topka-q63 lean reserve), MTP n 4, draft KV q4_0, draft vocab 64k,
  // GGML_CUDA_KVQ=1, ub 256 (campaign 67c). Planned only where measured (planOnlyMeasured):
  // 4090 UD-Q4_K_XL: load 23 732, fill 261 504 peak 23 852 MiB, 101.27 t/s T=1 (pin MTP n 3: 76.4);
  // 3090 UD-Q4_K_XL (portable build = the shipped engine): load 23 590, fill 261 504 peak 23 706 MiB, 79.97 t/s T=1
  // (pick XL 245 760 pin MTP n 3: 61.49); UD-Q4_K_M there 78.97 (peak 22 662), not in the catalog;
  // 5060 Ti GSQ IQ3_XXS: 196 608 load 15 106, peak 15 416, 49.44 t/s (229 376 crashed, 262 144 OOM; enigma-cuda-lean,
  // earlier in engines.json and so preferred, reaches 229 376 at 43.4); UD-Q3_K_XL only 98 304 (below the minimum);
  // 5090 (575 W) UD-Q6_K at ub 512 (AVX2 build): load 28 126, fill 261 504 peak 28 232 MiB, 148.57 t/s T=1 (pin MTP n 3,
  // ubd 64, ub 1024 on the same host: 100.90 / 100.61).
  { card: /RTX 4090/i, os: 'linux', modelId: 'qwen38-27b', quant: 'UD-Q4_K_XL', ctx: 262144, ub: 256, spec: true, engine: 'enigma-cuda-fork' },
  { card: /RTX 3090/i, os: 'linux', modelId: 'qwen38-27b', quant: 'UD-Q4_K_XL', ctx: 262144, ub: 256, spec: true, engine: 'enigma-cuda-fork' },
  { card: /RTX 5060 Ti/i, os: 'linux', modelId: 'qwen38-27b', quant: 'GSQ-IQ3_XXS', ctx: 196608, ub: 256, spec: true, engine: 'enigma-cuda-fork' },
  { card: /RTX 5090/i, os: 'linux', modelId: 'qwen38-27b', quant: 'UD-Q6_K', ctx: 262144, ub: 512, spec: true, engine: 'enigma-cuda-fork' },
  // enigma-cuda-prism, Bonsai PTQ1_0-mtp-lean, MTP n 2 + ubd 64, ub 512: 2080 Ti 155 648 full fill, peak 10 151 MiB,
  // 77.96 t/s T=1 (n 1 reached 196 608, peak 10 701)
  { card: /RTX 2080 Ti/i, os: 'linux', modelId: 'bonsai2-27b-mtp', quant: 'PTQ1_0', ctx: 155648, ub: 512, spec: true, engine: 'enigma-cuda-prism' },
];

/** ub 1024 by default; a smaller one replaces it only when it reaches the minimum that 1024 misses or gives ≥ 8% more
 *  context (prefill slower, decode unchanged). 256 is the step that brings 262 144 within reach on a 24 GB card
 *  (campaign 67: 4090 UD-Q4_K_XL + MTP n 3 / ubd 64 peaks at 24 036 of 24 082 MiB; ub 512 needs 23 858 just at load).
 *  Then the best KV type at that context. */
const UB_CHOICES = [1024, 512, 256] as const;

function plan(m: CatalogModel, q: QuantFile, d: Device, minCtx: number, spec: boolean, os: Hw['os'], run: MtpRun | null): Plan | { ctx: number } {
  const engine = run?.entry.id ?? m.engine;
  // our engine's profile: never above the context it ran (its MTP flags size the draft)
  const cap = run?.profile.maxCtx ?? Infinity;
  const measured = d.gpu && d.backend === 'cuda'
    ? VERIFIED.filter((v) => v.card.test(d.gpu!.name) && v.os === os && v.modelId === m.id && v.quant === q.quant && v.engine === engine && v.ctx <= cap)
    : [];
  if (measured.length > 0 && !measured.some((v) => v.spec === spec)) return { ctx: 0 };
  const verified = measured.filter((v) => v.spec === spec).sort((a, b) => b.ctx - a.ctx)[0];
  if (verified && verified.ctx >= minCtx && freeMiB(m, q, d, config(d, verified.ctx, 'q4_0', verified.ub, spec, run)) >= -VERIFIED_SLACK_MIB) {
    return { ctx: verified.ctx, kvType: 'q4_0', ub: verified.ub, spec };
  }
  const limit = Math.min(verified?.ctx ?? Infinity, cap);
  const fitsByUb = UB_CHOICES.map((ub) => ({ ub, ctx: Math.min(maxCtx(m, q, d, 'q4_0', ub, spec, run), limit) }));
  let chosen = fitsByUb[0]!;
  for (const c of fitsByUb.slice(1)) {
    if (chosen.ctx >= m.ctxMax) break;
    if (c.ctx >= minCtx && (chosen.ctx < minCtx || c.ctx >= chosen.ctx * UB_GAIN)) chosen = c;
  }
  const { ub, ctx } = chosen;
  if (ctx < minCtx) return { ctx: Math.max(...fitsByUb.map((c) => c.ctx)) };
  let kvType: KvType = 'q4_0';
  if (freeMiB(m, q, d, config(d, ctx, 'f16', ub, spec, run)) >= F16_HEADROOM_MIB) kvType = 'f16';
  else if (freeMiB(m, q, d, config(d, ctx, 'q8_0', ub, spec, run)) >= 0) kvType = 'q8_0';
  return { ctx, kvType, ub, spec };
}

/** "1 decimal, no trailing .0" for codes: 3 -> "3", 2.2 -> "2.2". */
const dec = (v: number): string => String(Math.round(v * 10) / 10);

/** Measured decode of this model on 16–24 GB cards in our catalog vs the RAM estimate, as "<lo>-<hi>" times faster;
 *  null without such a measurement (no claim without a number behind it). */
function gpuFaster(m: CatalogModel, s: RamSpeed): string | null {
  const tps = m.measured
    .filter((x) => CATALOG.gpus.some((g) => g.id === x.gpu && !g.unified && g.vramGiB !== null && g.vramGiB >= 16 && g.vramGiB <= 24))
    .map((x) => x.decodeTps);
  if (tps.length === 0) return null;
  const lo = Math.min(...tps) / s.hi;
  const hi = Math.max(...tps) / s.lo;
  return lo >= 1.5 ? `${Math.floor(lo)}-${Math.ceil(hi)}` : null;
}

function evaluate(m: CatalogModel, q: QuantFile, d: Device, hw: Hw, minCtx: number): Option | Rejection {
  const reject = (reason: string): Rejection => ({ modelId: m.id, quant: q.quant, reason });
  if (m.engine) {
    // files only our engine runs (PTQ1_0): offered where it is built for this GPU and available here
    const own = d.enigma.find((e) => e.id === m.engine);
    if (!own || !engineAvailable(own)) return reject(`needs_engine:${m.engine}`);
  } else if (m.minUpstreamBuild > PINNED_BUILD) return reject(`engine_too_old:b${m.minUpstreamBuild}`);
  if (m.ctxMax < minCtx) return reject(`ctx_max_below_min:${m.ctxMax}`);
  const empty = memParts(m, q, config(d, 0, 'q4_0', 512, false, null));
  const usable = d.budgetMiB - d.marginMiB;
  if (empty.totalMiB > usable) return reject(`weights_too_big:${(empty.totalMiB / 1024).toFixed(1)}/${(usable / 1024).toFixed(1)}`);

  const ram = d.ram ? ramSpeed(m, q, d.ram.bwGBs, hw.cpu.cores) : null;
  const gpuSpeed = !ram && d.gpu ? decodeSpeed(m, q, d.gpu, d.spec, d.backend) : null;
  const tps = ram?.tps ?? gpuSpeed?.tps ?? 0;
  // usability first: a model that writes slower than this is not offered, however good it is
  if (tps < MIN_DECODE_TPS) return reject(`too_slow_on_this_hw:${tps.toFixed(1)}`);

  // With an MTP head, plan the draft context too (so the MTP candidate runs at the same context); without it the
  // plain plan may reach a larger context. Both are scored, the better one is offered; on a tie (plain already above
  // INTERACTIVE_TPS) the MTP plan, whose speed-up is real. The MTP plan is sized for the engine that runs it: our
  // engine's MTP profile for this file when one is available here, else upstream MTP. A file only our engine runs is
  // offered only as that engine's MTP profile (what we measured), never as an unmeasured plain plan (10 GB 3080: none).
  const run = mtpCapable(m, d) ? mtpRunFor(m, q, d, hw.os) : null;
  if (m.engine && !run) return reject(`needs_engine:${m.engine}`);
  const specs = m.engine ? [true] : mtpCapable(m, d) ? [true, false] : [false];
  const plans = specs.map((spec) => plan(m, q, d, minCtx, spec, hw.os, spec ? run : null));
  const ok = plans.filter((p): p is Plan => 'kvType' in p);
  const best = ok.sort((a, b) => score(m, q, tps, b.spec) - score(m, q, tps, a.spec) || Number(b.spec) - Number(a.spec) || b.ctx - a.ctx)[0];
  if (!best) return reject(`ctx_below_min:${Math.max(...plans.map((p) => p.ctx))}`);
  const { ctx, kvType, ub, spec } = best;
  const mtpBy = spec ? run : null;

  const why: string[] = [];
  if (ram && d.ram) {
    // no discrete GPU: say so, which processor computes, the speed range and what a long prompt costs
    why.push('no_dgpu_ram');
    if (d.backend !== 'cpu') why.push(`igpu_backend:${d.backend}`);
    else why.push(d.ram.igpuPoolGiB !== null ? `cpu_igpu_pool:${dec(d.ram.igpuPoolGiB)}` : 'cpu_only');
    const range = `${Math.round(ram.lo)}-${Math.round(ram.hi)}`;
    why.push(m.kind === 'moe' ? `speed_ram_moe:${dec(m.activeB)}/${range}` : `speed_ram_dense:${dec(m.paramsB)}/${range}`);
    why.push(`prefill_ram:${Math.round(ram.prefillLo)}-${Math.round(ram.prefillHi)}/${minCtx}`);
    why.push(`ram_reserve:${dec(d.ram.reserveGiB)}/${dec(d.budgetMiB / 1024)}`);
  } else {
    // the measured speed is the baseline engine's: upstream llama.cpp, or the engine the model needs
    why.push(gpuSpeed?.measured ? `speed_measured:${tps.toFixed(0)}${m.engine ? `/${m.engine}` : ''}` : `speed_estimated:${tps.toFixed(0)}`);
  }
  if (m.engine) why.push(`engine_required:${m.engine}`);
  if (spec) why.push('mtp_head');
  else if (mtpCapable(m, d)) why.push('mtp_no_memory'); // the file has an MTP head, its draft context does not fit
  if (mtpBy) why.push(`mtp_engine:${mtpBy.entry.id}/${mtpBy.mtp.nMax}`);
  if (!ram && m.kind === 'moe' && m.activeB <= 4) why.push('moe_fast');
  why.push(ctx === m.ctxMax ? 'ctx_model_max' : 'ctx_memory_limit', `kv_${kvType}`);
  if (ub === 512) why.push('ub512_for_ctx');
  if (d.gpu?.kind === 'apple') why.push('unified_memory');
  if (hw.os === 'windows' && !ram) why.push('windows_reserve');
  if (CATALOG.licenses[m.license]?.commercial === 'conditional') why.push(`license_conditional:${m.license}`);
  const faster = ram ? gpuFaster(m, ram) : null;
  if (faster) why.push(`gpu_faster:${faster}`);

  // Ranking: a speed we measured on this hardware class (this GPU; for RAM-bound machines our CPU run of the model)
  // beats an estimate unless the estimate's score is more than UNMEASURED_MARGIN higher; on RAM-bound machines a plan
  // that leaves under TIGHT_FREE of its budget free is demoted (the system and the user's programs share that RAM).
  const mem = memPlan(m, q, config(d, ctx, kvType, ub, spec, mtpBy), d.budgetMiB / 1024);
  const measured = ram ? (m.ramMeasured?.length ?? 0) > 0 : gpuSpeed?.measured === true;
  const tight = ram !== null && mem.freeGiB < mem.budgetGiB * TIGHT_FREE;
  if (tight) why.push('tight_memory');
  const rank = score(m, q, tps, spec) / (measured ? 1 : UNMEASURED_MARGIN) * (tight ? TIGHT_DEMOTE : 1);

  return {
    id: `${m.id}/${q.quant}/${d.backend}${d.gpuIndex === null ? '' : `/${d.gpuIndex}`}`,
    modelId: m.id, name: m.name, family: m.family, params: m.params, quant: q.quant,
    file: { repo: q.repo, path: q.path, sizeBytes: q.sizeBytes, sha256: q.sha256 },
    ctx, ctxMax: m.ctxMax, kvType, ub, backend: d.backend, gpuIndex: d.gpuIndex,
    mem,
    features: m.features.filter((f) => f !== 'mtp' || spec),
    score: Math.round(rank * 100) / 100,
    ...(m.engine ? { needsEngine: m.engine } : {}),
    ...(mtpBy ? { mtpEngine: mtpBy.entry.id } : {}),
    why,
  };
}

const better = (a: Option, b: Option): number => b.score - a.score || b.ctx - a.ctx;

export function recommend(hw: Hw, minCtx: number = DEFAULT_MIN_CTX): Recommendation {
  const options = new Map<string, Option>();
  const rejected = new Map<string, Rejection & { budgetMiB: number }>();
  for (const d of devices(hw)) {
    for (const m of CATALOG.models) {
      for (const q of m.quants) {
        const key = `${m.id}/${q.quant}`;
        const r = evaluate(m, q, d, hw, minCtx);
        if ('reason' in r) {
          // the reason from the device with the most memory says the most (an iGPU's small pool vs the CPU's RAM)
          const prev = rejected.get(key);
          if (!prev || d.budgetMiB > prev.budgetMiB) rejected.set(key, { ...r, budgetMiB: d.budgetMiB });
          continue;
        }
        // Same model × quant: on one GPU the preferred backend wins (devices come in BACKEND_ORDER: our engines are
        // CUDA/ROCm/Metal builds); integrated graphics wins over the CPU (same RAM speed; its prompt reading is usually
        // faster [INFERENCE: not measured on our hardware]); across GPUs the better option wins.
        const prev = options.get(key);
        if (prev && r.backend === 'cpu') continue;
        if (!prev || (prev.gpuIndex !== r.gpuIndex && better(r, prev) < 0)) options.set(key, r);
      }
    }
  }
  for (const key of options.keys()) rejected.delete(key);
  const ranked = [...options.values()].sort(better);
  // the pick skips models marked `defaultPick: false`; they stay in the ranking for the alternatives
  const noDefault = new Set(CATALOG.models.filter((m) => m.defaultPick === false).map((m) => m.id));
  const pick = ranked.find((o) => !noDefault.has(o.modelId)) ?? null;
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
  return { minCtx, pick, alternatives, rejected: [...rejected.values()].map(({ modelId, quant, reason }) => ({ modelId, quant, reason })) };
}

function qualityOf(o: Option): number {
  const m = CATALOG.models.find((x) => x.id === o.modelId);
  const q = m?.quants.find((x) => x.quant === o.quant);
  return m && q ? m.quality * q.qualityFactor : 0;
}

export interface PlanRequest {
  ctx: number; kvType: KvType; ub: number; spec: boolean; backend: Backend; gpuIndex: number | null;
  /** engines.json id whose MTP profile runs the draft (Option.mtpEngine); absent: upstream MTP (optimize.ts specArgs) */
  mtpEngine?: string;
}

/** Memory plan of one model × quant on this machine in an explicit configuration (same margins as recommend). A
 *  configuration at or below one measured on this card with the same engine, ub, KV q4_0 and speculation mode fits
 *  within VERIFIED_SLACK_MIB, as in recommend. */
export function planFor(hw: Hw, modelId: string, quant: string, r: PlanRequest): { mem: MemPlan; fits: boolean } {
  const m = CATALOG.models.find((x) => x.id === modelId);
  const q = m?.quants.find((x) => x.quant === quant);
  const d = devices(hw).find((x) => x.backend === r.backend && x.gpuIndex === r.gpuIndex);
  if (!m || !q) throw new Error(`planFor: ${modelId} ${quant} is not in the catalog`);
  if (!d) throw new Error(`planFor: no ${r.backend} device ${r.gpuIndex ?? 'cpu'} on this machine`);
  const engine = r.mtpEngine ? engineById(r.mtpEngine) : undefined;
  const spec = r.spec && m.arch.nextn.layers > 0;
  const run = engine && spec ? mtpRun(engine, m, q) : null;
  const c = config(d, r.ctx, r.kvType, r.ub, spec, run);
  const free = freeMiB(m, q, d, c);
  const engineId = run?.entry.id ?? m.engine;
  const measured = d.gpu !== null && d.backend === 'cuda' && r.kvType === 'q4_0' && VERIFIED.some((v) => v.card.test(d.gpu!.name)
    && v.os === hw.os && v.modelId === m.id && v.quant === q.quant && v.engine === engineId && v.spec === spec && v.ub === r.ub && v.ctx >= r.ctx);
  return { mem: memPlan(m, q, c, d.budgetMiB / 1024), fits: free >= 0 || (measured && free >= -VERIFIED_SLACK_MIB) };
}

/** Re-plans an option with another ubatch / context / KV type / speculation (backend: does `-ub 2048` fit?). The MTP
 *  draft keeps the option's engine unless `mtpEngine: null` asks for upstream MTP on the baseline engine. */
export function replan(
  opt: Option, hw: Hw, change: { ub?: number; ctx?: number; kvType?: KvType; spec?: boolean; mtpEngine?: string | null },
): { mem: MemPlan; fits: boolean } {
  const mtpEngine = change.mtpEngine === undefined ? opt.mtpEngine : change.mtpEngine;
  return planFor(hw, opt.modelId, opt.quant, {
    ctx: change.ctx ?? opt.ctx, kvType: change.kvType ?? opt.kvType, ub: change.ub ?? opt.ub,
    spec: change.spec ?? opt.features.includes('mtp'), backend: opt.backend, gpuIndex: opt.gpuIndex,
    ...(mtpEngine ? { mtpEngine } : {}),
  });
}
