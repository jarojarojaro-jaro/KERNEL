// Memory model: total = weights + KV(ctx, kvType) + compute(ub, ctx, n_embd) + runtime overhead.
// Calibrated against our measured fits (test/catalog.measured.json; every point within ±0.4 GiB):
//   Qwen3.8-27B UD-Q4_K_XL + MTP on the XTX at 204800 / q4_0 and on the 3090 at 131072 / 204800,
//   Flint NVFP4 on the 3090 and the XTX (200k–262k, ub 128–2048), LFM2.5-24B Q5_K_M 131072 / q8_0 (ub 512–2048),
//   campaign 67 (upstream b11856/b12110 CUDA): Qwen3.8-27B Q3/Q4/Q6 plain and MTP n 1/3 on the 4090/5090/5080.
// Structure follows report 04 §2.2 and qwen-opt/cloud/fitcalc.py (validated on llama-server logs):
//   KV       = full-attention layers × ctx + SWA layers × pad256(window + ub) cells, at the KV type's bytes/element
//              (+ the MTP block's own context when speculation is planned);
//   state    = recurrent state per sequence (GDN / shortconv), ×1.686 with an MTP draft (rollback snapshots);
//   compute  = ctx × (one full layer's K+V converted to F16 for flash-attention prefill + the f16 KQ mask row per
//              ubatch token) + ub × 40 B × n_embd (activations; 100 MiB for Qwen3.8-27B at ub 512, fitcalc C_main);
//   growth   = prompt × F16 K+V of one full layer × G(backend): pools for the K/V conversion that grow with the filled
//              context (CUDA with our engine's speculation: 3.77, 3090 cuda-topka2 T 21380 → 22198 MiB after a 55.6k
//              prompt; HIP with speculation: 1.2, bounded by the XTX peak 23878 MiB after ~32k prompts and the production
//              204800 context that holds a ~196k prefill);
//   overhead = driver context, BLAS handles and pools at load (CUDA 100 + 0.4 × VRAM_GiB² MiB, fitted on fitcalc's per-card
//              values 3060 174 / 4060 Ti 184 / 5060 Ti 194 / 3090 338 and our Vast runs of the app; HIP 300,
//              between the Flint/Qwen XTX loads and the LFM XTX reading). Campaign 67 fitted per card 3060 150 /
//              4060 Ti 173 / 4070 196 / 3080 276 / 5080 309 / 3090 336 / 4090 465 / 5090 579 MiB: it tracks the SM count
//              (≈ 65 + 3 × SMs) [INFERENCE], not the VRAM size, and the catalog carries no SM counts; the formula stays
//              (4090 −135, 5080 −107 MiB, inside the CUDA headroom margin of catalog/index.ts).
// Upstream llama.cpp on CUDA (no enigma engine) follows the campaign-67 fit (qwen-opt/cloud/runs/nv67/upstream_mem.py,
// report 67b §1; error −3…+23 MiB on 19 `-lv 4` buffer sets) instead of the fork calibration above:
//   weights  − the nextn (MTP) block when no MTP draft runs (upstream loads it only with --spec-type draft-mtp);
//   state    × (n_max + 1) with an MTP draft (one sequence per draft position: 299 / 598 / 748 MiB at n 1 / 3 / 4);
//   draft KV = ctx × nextn K+V in F16 (upstream's default draft cache type, whatever -ctk/-ctv: 1024 MiB at 262144);
//   draft compute = ctx × 2 × ubd + ubd × 32 B × n_embd (ubd = --spec-draft-n-ubatch; 40 MiB at 262144 with ubd 64);
//   growth   = the plain CUDA value with or without MTP (upstream +2…+28 MiB while the context fills: the F16 K/V copy
//              lives in the compute buffer reserved at load).
import type { Backend, MemPlan } from '../../shared/types.ts';
import type { CatalogModel, KvType, QuantFile } from './data.ts';

const MiB = 1024 * 1024;

/** Bytes per cached element: q4_0 = 4.5 bits, q8_0 = 8.5 bits, f16 = 16 bits. */
export const KV_BYTES: Record<KvType, number> = { q4_0: 4.5 / 8, q8_0: 8.5 / 8, f16: 2 };

/** Activation bytes per ubatch token per n_embd (main graph, MTP draft graph). */
const ACT_MAIN = 40;
const ACT_DRAFT = 32;
/** Recurrent state multiplier with our engine's MTP draft (snapshots for rollback; fitcalc RS_SPEC 252.19 / 149.6). */
const STATE_SPEC = 1.686;

/** Upstream `--spec-draft-n-max` of the MTP candidate (optimize.ts); the planner sizes the recurrent state with it. */
export const MTP_N_MAX_DEFAULT = 3;
/** Upstream `--spec-draft-n-ubatch` of the MTP candidate: the draft context's physical batch. It sizes only the draft
 *  compute buffer (5090 262144: 648 → 40 MiB at ub 1024); the output does not change. */
export const MTP_DRAFT_UB = 64;
/** Nextn (MTP) block weights upstream loads only with an MTP draft: 335 MiB measured on Qwen3.8-27B (n_embd 5120, one
 *  block) in UD-Q3_K_XL, UD-Q4_K_XL and UD-Q6_K alike (the block keeps one tensor type across these quants). The catalog
 *  has no per-tensor sizes, so other models scale it by blocks × (n_embd / 5120)² [SZACUNEK]. */
const NEXTN_MIB_5120 = 335;

/** Prompt-growth factor per backend, × F16 K+V bytes of one full layer per filled token. `spec` is our engine's MTP
 *  draft (upstream CUDA uses `plain` either way, see memParts). Vulkan/Metal are unmeasured: plain as HIP, speculation
 *  as our CUDA engine (the conservative measured value). Overheads for Vulkan/Metal/CPU: [SZACUNEK]. */
const GROWTH: Record<Backend, { plain: number; spec: number }> = {
  cuda: { plain: 0.07, spec: 3.77 },
  rocm: { plain: 0.25, spec: 1.2 },
  vulkan: { plain: 0.25, spec: 3.77 },
  metal: { plain: 0.25, spec: 3.77 },
  cpu: { plain: 0, spec: 0 },
};

export function overheadMiB(backend: Backend, vramGiB: number): number {
  switch (backend) {
    case 'cuda': return 100 + 0.4 * vramGiB * vramGiB;
    case 'rocm': return 300;
    case 'vulkan': return 300;
    case 'metal': return 200;
    case 'cpu': return 256;
  }
}

export interface MemConfig {
  ctx: number;
  kvType: KvType;
  ub: number;
  backend: Backend;
  /** Device memory size (for the CUDA context overhead), GiB. */
  vramGiB: number;
  /** Reserve the MTP draft context (model has an MTP head and speculation will be tried). */
  spec: boolean;
  /** Speculation runs in our engine (enigma, e.g. topka): + its reduced draft-vocab buffers, draft KV at the target's KV
   *  type, GROWTH.spec. Otherwise upstream llama.cpp: on CUDA the campaign-67 fit (header); other backends keep the
   *  fork calibration (unmeasured upstream MTP there). */
  enigmaSpec: boolean;
  /** Upstream `--spec-draft-n-max` (recurrent state × (n + 1) with upstream MTP on CUDA). */
  mtpN: number;
  /** Upstream `--spec-draft-n-ubatch` (draft compute buffer with upstream MTP on CUDA); llama.cpp's default is `ub`. */
  ubd: number;
  /** Tokens already in the context; the recommender plans for a full context (prompt = ctx). */
  prompt: number;
}

export interface MemParts { weightsMiB: number; kvMiB: number; computeMiB: number; overheadMiB: number; totalMiB: number }

/** KV cache + recurrent state, bytes, with `ctx` cells (decode reads all of it once per generated token). */
export function kvBytes(m: CatalogModel, ctx: number, kvType: KvType, ub: number, withSpec: boolean): number {
  const a = m.arch;
  const fullTok = a.full.layers * a.full.kvHeads * (a.full.keyLen + a.full.valueLen);
  const swaTok = a.swa.layers * a.swa.kvHeads * (a.swa.keyLen + a.swa.valueLen);
  const swaCells = a.swa.layers ? Math.min(ctx, Math.ceil((a.swa.window + ub) / 256) * 256) : 0;
  const spec = withSpec && a.nextn.layers > 0;
  const nextnTok = spec ? a.nextn.layers * a.nextn.kvHeads * (a.nextn.keyLen + a.nextn.valueLen) : 0;
  const state = a.stateMiB * MiB * (spec ? STATE_SPEC : 1);
  return (ctx * (fullTok + nextnTok) + swaCells * swaTok) * KV_BYTES[kvType] + state;
}

export function memParts(m: CatalogModel, q: QuantFile, c: MemConfig): MemParts {
  const a = m.arch;
  const spec = c.spec && a.nextn.layers > 0;
  const upstreamCuda = c.backend === 'cuda' && !c.enigmaSpec;

  // One full-attention layer's K+V in F16 per token (the FA prefill view); SWA-only models use their window layer.
  const f16Layer = a.full.layers
    ? a.full.kvHeads * (a.full.keyLen + a.full.valueLen) * 2
    : a.swa.kvHeads * (a.swa.keyLen + a.swa.valueLen) * 2;
  const perCtx = c.ctx * (f16Layer + 2 * c.ub);
  const g = GROWTH[c.backend];
  let compute = perCtx + c.ub * ACT_MAIN * a.nEmbd;
  let weights = q.sizeBytes - q.hostEmbdBytes;
  let kv: number;
  if (upstreamCuda) {
    kv = kvBytes(m, c.ctx, c.kvType, c.ub, false);
    compute += c.prompt * f16Layer * g.plain;
    if (spec) {
      const nextnTok = a.nextn.layers * a.nextn.kvHeads * (a.nextn.keyLen + a.nextn.valueLen);
      kv += c.ctx * nextnTok * KV_BYTES.f16 + a.stateMiB * MiB * c.mtpN;
      compute += c.ctx * 2 * c.ubd + c.ubd * ACT_DRAFT * a.nEmbd;
    } else {
      weights -= NEXTN_MIB_5120 * MiB * a.nextn.layers * (a.nEmbd / 5120) ** 2;
    }
  } else {
    kv = kvBytes(m, c.ctx, c.kvType, c.ub, c.spec);
    compute += c.prompt * f16Layer * (spec ? g.spec : g.plain);
    if (spec) compute += perCtx + c.ub * ACT_DRAFT * a.nEmbd + (c.enigmaSpec ? a.mtpExtraMiB * MiB : 0);
  }

  const overhead = overheadMiB(c.backend, c.vramGiB) * MiB;
  const total = weights + kv + compute + overhead;
  return { weightsMiB: weights / MiB, kvMiB: kv / MiB, computeMiB: compute / MiB, overheadMiB: overhead / MiB, totalMiB: total / MiB };
}

const gib = (mib: number): number => Math.round((mib / 1024) * 100) / 100;

export function memPlan(m: CatalogModel, q: QuantFile, c: MemConfig, budgetGiB: number): MemPlan {
  const p = memParts(m, q, c);
  return {
    weightsGiB: gib(p.weightsMiB), kvGiB: gib(p.kvMiB), computeGiB: gib(p.computeMiB), overheadGiB: gib(p.overheadMiB),
    totalGiB: gib(p.totalMiB), budgetGiB: Math.round(budgetGiB * 100) / 100, freeGiB: gib(budgetGiB * 1024 - p.totalMiB),
  };
}
