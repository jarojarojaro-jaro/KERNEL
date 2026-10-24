import { describe, expect, test } from 'bun:test';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import measured from './catalog.measured.json';
import { MACHINES } from './catalog.fixtures.ts';
import { CATALOG, type KvType } from '../src/server/catalog/data.ts';
import { memParts } from '../src/server/catalog/memory.ts';
import { planFor, recommend, replan } from '../src/server/catalog/index.ts';
import { ggufArch, readGgufHeader } from '../src/server/catalog/gguf.ts';
import type { Backend, Hw } from '../src/shared/types.ts';

const GIB_MIB = 1024;
const machine = (k: string): Hw => {
  const hw = MACHINES[k];
  if (!hw) throw new Error(`no fixture ${k}`);
  return hw;
};
const model = (id: string) => {
  const m = CATALOG.models.find((x) => x.id === id);
  if (!m) throw new Error(`no model ${id}`);
  return m;
};

describe('catalog data', () => {
  test('every quant has HF size + sha256 and every model a KV layout', () => {
    for (const m of CATALOG.models) {
      expect(m.arch.full.layers + m.arch.swa.layers).toBeGreaterThan(0);
      expect(m.arch.nVocab).toBeGreaterThan(0);
      expect(m.ctxMax).toBeGreaterThan(0);
      for (const q of m.quants) {
        expect(q.sizeBytes).toBeGreaterThan(1e9);
        expect(q.sha256).toMatch(/^[0-9a-f]{64}$/);
        expect(q.bTokGB).toBeGreaterThan(0);
      }
    }
  });

  test('hybrid models count only their full-attention layers', () => {
    expect(model('qwen38-27b').arch.full).toEqual({ layers: 16, kvHeads: 4, keyLen: 256, valueLen: 256 });
    expect(model('qwen38-27b').arch.nextn.layers).toBe(1);
    expect(model('lfm25-24b-a2b').arch.full.layers).toBe(10);
    expect(model('flint-40b-a2.5b').arch.swa).toMatchObject({ layers: 35, window: 513 });
    expect(model('gpt-oss-20b').arch.swa).toMatchObject({ layers: 12, window: 128 });
  });
});

describe('memory model vs our measurements (±0.4 GiB)', () => {
  for (const p of measured.points) {
    test(p.id, () => {
      const m = model(p.modelId);
      const q = m.quants.find((x) => x.quant === p.quant);
      if (!q) throw new Error(`${p.modelId} has no ${p.quant}`);
      const r = memParts(m, q, {
        ctx: p.ctx, kvType: p.kvType as KvType, ub: p.ub, backend: p.backend as Backend, vramGiB: p.vramGiB,
        spec: p.spec, prompt: p.prompt,
      });
      const used: number | undefined = 'usedMiB' in p ? p.usedMiB : undefined;
      const oom: number | undefined = 'oomAboveMiB' in p ? p.oomAboveMiB : undefined;
      if (used !== undefined) expect(Math.abs(r.totalMiB - used)).toBeLessThanOrEqual(0.4 * GIB_MIB);
      else if (oom !== undefined) expect(r.totalMiB).toBeGreaterThan(oom);
      else throw new Error('measured point without usedMiB / oomAboveMiB');
    });
  }
});

describe('recommend on typical machines', () => {
  for (const [name, hw] of Object.entries(MACHINES)) {
    test(`${name}: a pick with ≥ 131072 context and headroom`, () => {
      const r = recommend(hw);
      expect(r.minCtx).toBe(131072);
      const pick = r.pick;
      if (!pick) throw new Error(`${name}: no pick`);
      expect(pick.ctx).toBeGreaterThanOrEqual(131072);
      expect(pick.ctx).toBeLessThanOrEqual(pick.ctxMax);
      expect(pick.ctx % 4096 === 0 || pick.ctx === pick.ctxMax).toBe(true);
      // ≥ 300 MiB headroom (1 GiB on Windows) left after the full-context plan
      expect(pick.mem.freeGiB).toBeGreaterThanOrEqual(hw.os === 'windows' ? 0.97 : 0.29);
      expect(r.alternatives.length).toBeLessThanOrEqual(3);
      const ids = [pick.modelId, ...r.alternatives.map((a) => a.modelId)];
      expect(new Set(ids).size).toBe(ids.length);
      for (const a of r.alternatives) expect(a.score).toBeLessThanOrEqual(pick.score);
      expect(pick.why.some((w) => w.startsWith('speed_'))).toBe(true);
      expect(r.rejected.some((x) => x.modelId === 'flint-40b-a2.5b' && x.reason === 'engine_unsupported')).toBe(true);
    });
  }

  test('RX 7900 XTX: Qwen3.8-27B UD-Q4_K_XL at ~200k with KV q4_0 (production 204800)', () => {
    const pick = recommend(machine('RX 7900 XTX 24 GB')).pick;
    expect(pick).toMatchObject({ modelId: 'qwen38-27b', quant: 'UD-Q4_K_XL', kvType: 'q4_0', backend: 'rocm', gpuIndex: 0 });
    expect(pick?.features).toContain('mtp');
    expect(pick?.ctx).toBeGreaterThanOrEqual(172032);
    expect(pick?.ctx).toBeLessThanOrEqual(212992);
    // the production configuration (ub 512, MTP, 204800, full prefill) fits the card on our headless server; the
    // recommender's extra 300 MiB desktop headroom is what moves the pick a little below it
    const prod = planFor(machine('RX 7900 XTX 24 GB'), 'qwen38-27b', 'UD-Q4_K_XL',
      { ctx: 204800, kvType: 'q4_0', ub: 512, spec: true, backend: 'rocm', gpuIndex: 0 });
    expect(prod.mem.freeGiB).toBeGreaterThan(0);
    expect(prod.mem.totalGiB).toBeLessThanOrEqual(prod.mem.budgetGiB);
  });

  test('RTX 3090: Qwen3.8-27B UD-Q4_K_XL with MTP at ≥ 131072, but not 204800 (OOM measured)', () => {
    const hw = machine('RTX 3090 24 GB');
    const pick = recommend(hw).pick;
    if (!pick) throw new Error('no pick');
    expect(pick).toMatchObject({ modelId: 'qwen38-27b', quant: 'UD-Q4_K_XL', kvType: 'q4_0', backend: 'cuda' });
    expect(pick.ctx).toBeGreaterThanOrEqual(131072);
    expect(replan(pick, hw, { ctx: 204800, ub: 512 }).fits).toBe(false);
  });

  test('LFM2.5-24B Q5_K_M fits 131072 with KV q8_0 on the XTX (production)', () => {
    const r = planFor(machine('RX 7900 XTX 24 GB'), 'lfm25-24b-a2b', 'Q5_K_M',
      { ctx: 131072, kvType: 'q8_0', ub: 2048, spec: false, backend: 'rocm', gpuIndex: 0 });
    expect(r.fits).toBe(true);
  });

  test('Flint NVFP4 at 262144 / ub 1024 does not fit 24 GB (segfault at load), ub 512 is beyond our margin', () => {
    const m = model('flint-40b-a2.5b');
    const q = m.quants[0];
    if (!q) throw new Error('no flint quant');
    const at = (ub: number) => memParts(m, q, { ctx: 262144, kvType: 'q4_0', ub, backend: 'rocm', vramGiB: 24, spec: false, prompt: 0 });
    expect(at(1024).totalMiB).toBeGreaterThan(24560);
    expect(24560 - at(512).totalMiB).toBeLessThan(300);
  });

  test('CPU only: a small model on the CPU backend, flagged slow', () => {
    const r = recommend(machine('CPU only 32 GB'));
    expect(r.pick).toMatchObject({ backend: 'cpu', gpuIndex: null });
    expect(model(r.pick?.modelId ?? '').cpuTier).toBe(true);
    expect(r.pick?.why).toContain('cpu_only');
    expect(r.pick?.mem.budgetGiB).toBeCloseTo(32 * 0.7, 2);
    expect(r.rejected.some((x) => x.modelId === 'gpt-oss-20b' && x.reason === 'not_cpu_tier')).toBe(true);
    expect(r.rejected).toContainEqual({ modelId: 'lfm25-2.6b', quant: 'QAD-Q4_0', reason: 'ctx_max_below_min:128000' });
  });

  test('a lower minimum lets the 128k-trained LFM2.5-2.6B through', () => {
    const r = recommend(machine('CPU only 32 GB'), 65536);
    expect(r.rejected.some((x) => x.modelId === 'lfm25-2.6b')).toBe(false);
  });

  test('Apple unified memory: budget 66% of 24 GB, 75% of 48 GB', () => {
    expect(recommend(machine('Mac M4 Pro 24 GB')).pick?.mem.budgetGiB).toBeCloseTo(24 * 0.66, 2);
    expect(recommend(machine('Mac M4 Pro 48 GB')).pick?.mem.budgetGiB).toBeCloseTo(48 * 0.75, 2);
    expect(recommend(machine('Mac M4 Pro 24 GB')).pick?.why).toContain('unified_memory');
  });

  test('nothing fits: a 4 GB card gets no pick and clear reasons', () => {
    const hw: Hw = { ...machine('RTX 3060 12 GB'), gpus: [{ vendor: 'nvidia', name: 'GeForce GTX 1650', vramGiB: 4, unified: false, backends: ['cuda'] }] };
    const r = recommend(hw);
    expect(r.pick).toBeNull();
    expect(r.rejected.find((x) => x.modelId === 'qwen38-27b')?.reason).toMatch(/^weights_too_big:/);
    expect(r.rejected.find((x) => x.modelId === 'qwen35-4b')?.reason).toMatch(/^ctx_below_min:\d+$/);
  });
});

const modelsDir = (process.env.ENIGMA_MODELS_DIR ?? '').replace(/^~/, process.env.HOME ?? '~');
const localQwen = join(modelsDir, 'Qwen3.8-27B-UD-Q4_K_XL.gguf');

describe('GGUF header reader', () => {
  test.skipIf(!modelsDir || !existsSync(localQwen))('reads Qwen3.8-27B arch from the local header only', async () => {
    const h = await readGgufHeader(localQwen);
    expect(h.headerBytes).toBeLessThan(32 << 20);
    const a = ggufArch(h);
    expect(a).toMatchObject({ arch: 'qwen35', nLayer: 65, nextn: 1, nEmbd: 5120, ctxTrain: 262144 });
    expect(a.full).toEqual({ layers: 16, kvHeads: 4, keyLen: 256, valueLen: 256 });
  });
});
