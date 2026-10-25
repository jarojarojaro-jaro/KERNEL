// Memory model: total = weights + KV(ctx, kvType) + compute(ub, ctx, n_embd) + runtime overhead.
// Calibrated against our measured fits (test/catalog.measured.json; every point within ±0.4 GiB):
//   Qwen3.8-27B UD-Q4_K_XL + MTP on the XTX at 204800 / q4_0 and on the 3090 at 131072 / 204800,
//   Flint NVFP4 on the 3090 and the XTX (200k–262k, ub 128–2048), LFM2.5-24B Q5_K_M 131072 / q8_0 (ub 512–2048).
// Structure follows report 04 §2.2 and qwen-opt/cloud/fitcalc.py (validated on llama-server logs):
//   KV       = full-attention layers × ctx + SWA layers × pad256(window + ub) cells, at the KV type's bytes/element
//              (+ the MTP block's own context when speculation is planned);
//   state    = recurrent state per sequence (GDN / shortconv), ×1.686 with an MTP draft (rollback snapshots);
//   compute  = ctx × (one full layer's K+V converted to F16 for flash-attention prefill + the f16 KQ mask row per
//              ubatch token) + ub × 40 B × n_embd (activations; 100 MiB for Qwen3.8-27B at ub 512, fitcalc C_main);
//   growth   = prompt × F16 K+V of one full layer × G(backend): pools for the K/V conversion that grow with the filled
//              context (CUDA with speculation: 3.77, 3090 Qwen T 21380 → 22198 MiB after a 55.6k prompt; HIP with
//              speculation: 1.2, bounded by the XTX peak 23878 MiB after ~32k prompts and the production 204800 context
//              that holds a ~196k prefill);
//   overhead = driver context, BLAS handles and pools at load (CUDA 100 + 0.4 × VRAM_GiB² MiB, fitted on fitcalc's per-card
//              values 3060 174 / 4060 Ti 184 / 5060 Ti 194 / 3090 338 and our Vast runs of the app; HIP 300,
//              between the Flint/Qwen XTX loads and the LFM XTX reading).
import type { Backend, MemPlan } from '../../shared/types.ts';
import type { CatalogModel, KvType, QuantFile } from './data.ts';

const MiB = 1024 * 1024;

/** Bytes per cached element: q4_0 = 4.5 bits, q8_0 = 8.5 bits, f16 = 16 bits. */
export const KV_BYTES: Record<KvType, number> = { q4_0: 4.5 / 8, q8_0: 8.5 / 8, f16: 2 };

/** Activation bytes per ubatch token per n_embd (main graph, MTP draft graph). */
const ACT_MAIN = 40;
const ACT_DRAFT = 32;
/** Recurrent state multiplier with an MTP draft (snapshots for rollback; fitcalc RS_SPEC 252.19 / 149.6). */
const STATE_SPEC = 1.686;

/** Prompt-growth factor per backend, × F16 K+V bytes of one full layer per filled token. Vulkan/Metal are unmeasured:
 *  plain as HIP, speculation as CUDA (the conservative measured value). Overheads for Vulkan/Metal/CPU: [SZACUNEK]. */
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
  /** Speculation runs in our engine (enigma, e.g. topka): + its reduced draft-vocab buffers. Upstream llama.cpp MTP has
   *  none (3090 b11856 MTP: 21342 MiB at load). Prompt growth with speculation stays at GROWTH.spec for both: upstream
   *  grew 6 MiB up to a 32.6k prompt, but nothing longer is measured, while our fork OOMed at 55.6k (3090, 204800). */
  enigmaSpec: boolean;
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
  const kv = kvBytes(m, c.ctx, c.kvType, c.ub, c.spec);

  // One full-attention layer's K+V in F16 per token (the FA prefill view); SWA-only models use their window layer.
  const f16Layer = a.full.layers
    ? a.full.kvHeads * (a.full.keyLen + a.full.valueLen) * 2
    : a.swa.kvHeads * (a.swa.keyLen + a.swa.valueLen) * 2;
  const perCtx = c.ctx * (f16Layer + 2 * c.ub);
  const g = GROWTH[c.backend];
  let compute = perCtx + c.ub * ACT_MAIN * a.nEmbd + c.prompt * f16Layer * (spec ? g.spec : g.plain);
  if (spec) compute += perCtx + c.ub * ACT_DRAFT * a.nEmbd + (c.enigmaSpec ? a.mtpExtraMiB * MiB : 0);

  const weights = q.sizeBytes - q.hostEmbdBytes;
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
