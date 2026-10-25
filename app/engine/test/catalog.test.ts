import { describe, expect, test } from 'bun:test';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import measured from './catalog.measured.json';
import { MACHINES, RAM_MACHINES, windowsScan } from './catalog.fixtures.ts';
import { CATALOG, type KvType } from '../src/server/catalog/data.ts';
import { memParts } from '../src/server/catalog/memory.ts';
import { planFor, recommend, replan } from '../src/server/catalog/index.ts';
import { ramSpeed } from '../src/server/catalog/score.ts';
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
        spec: p.spec, enigmaSpec: p.enigmaSpec, prompt: p.prompt,
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
      // headroom after the full-context plan: Linux 100 MiB, Windows 512 MiB, macOS 0; CUDA +200 MiB
      const margin = { linux: 100, windows: 512, macos: 0 }[hw.os] + (pick.backend === 'cuda' ? 200 : 0);
      expect(pick.mem.freeGiB * 1024).toBeGreaterThanOrEqual(margin - 10);
      expect(r.alternatives.length).toBeLessThanOrEqual(3);
      const ids = [pick.modelId, ...r.alternatives.map((a) => a.modelId)];
      expect(new Set(ids).size).toBe(ids.length);
      for (const a of r.alternatives) expect(a.score).toBeLessThanOrEqual(pick.score);
      expect(pick.why.some((w) => w.startsWith('speed_'))).toBe(true);
      // Flint needs upstream ≥ b11803 (PR #30928 merge); the pinned engine (data/engines.json) is newer
      expect(r.rejected.some((x) => x.reason.startsWith('engine_too_old'))).toBe(false);
    });
  }

  test('RX 7900 XTX: Qwen3.8-27B UD-Q4_K_XL + MTP at 204800, KV q4_0, ub 512 (measured production)', () => {
    const pick = recommend(machine('RX 7900 XTX 24 GB')).pick;
    expect(pick).toMatchObject({
      modelId: 'qwen38-27b', quant: 'UD-Q4_K_XL', ctx: 204800, kvType: 'q4_0', ub: 512, backend: 'rocm', gpuIndex: 0,
    });
    expect(pick?.features).toContain('mtp');
    expect(pick?.why).toContain('ub512_for_ctx');
    // the production configuration, full prefill: 23.84 of 23.95 GiB
    expect(pick?.mem.totalGiB).toBeCloseTo(23.84, 1);
  });

  test('RTX 3090: Qwen3.8-27B UD-Q4_K_XL with upstream MTP at ~160k; 204800 only without MTP (fork MTP OOM measured)', () => {
    const hw = machine('RTX 3090 24 GB');
    const pick = recommend(hw).pick;
    if (!pick) throw new Error('no pick');
    expect(pick).toMatchObject({ modelId: 'qwen38-27b', quant: 'UD-Q4_K_XL', kvType: 'q4_0', backend: 'cuda' });
    expect(pick.features).toContain('mtp');
    // fit measured to a 32.6k prompt (Vast, upstream b11856 MTP 21348 MiB at 131072); the full context is the model
    expect(pick.ctx).toBeGreaterThan(131072);
    expect(pick.ctx).toBeLessThan(204800);
    expect(replan(pick, hw, { ctx: 204800, ub: 512 }).fits).toBe(false);
    expect(replan(pick, hw, { ctx: 204800, ub: 512, spec: false }).fits).toBe(true);
  });

  test('Flint (minUpstreamBuild 11803) is offered on 24 GB with the pinned engine; quality below Qwen3.8-27B', () => {
    const r = recommend(machine('RX 7900 XTX 24 GB'));
    expect(r.alternatives.some((a) => a.modelId === 'flint-40b-a2.5b')).toBe(true);
    expect(model('flint-40b-a2.5b').quality).toBeLessThan(model('qwen38-27b').quality);
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
    const at = (ub: number) =>
      memParts(m, q, { ctx: 262144, kvType: 'q4_0', ub, backend: 'rocm', vramGiB: 24, spec: false, enigmaSpec: false, prompt: 0 });
    expect(at(1024).totalMiB).toBeGreaterThan(24560);
    expect(24560 - at(512).totalMiB).toBeLessThan(300);
  });

  test('CPU only: the CPU backend, budget = RAM minus the system reserve, slow dense models rejected', () => {
    const r = recommend(machine('CPU only 32 GB'));
    expect(r.pick).toMatchObject({ backend: 'cpu', gpuIndex: null });
    expect(r.pick?.why).toContain('cpu_only');
    expect(r.pick?.mem.budgetGiB).toBeCloseTo(32 - 6.4, 2); // Linux keeps max(6 GB, 20%)
    expect(r.rejected).toContainEqual(expect.objectContaining({ modelId: 'qwen38-27b', reason: expect.stringMatching(/^too_slow_on_this_hw:\d/) }));
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
    const hw: Hw = { ...machine('RTX 3060 12 GB'), gpus: [{ vendor: 'nvidia', name: 'GeForce GTX 1650', kind: 'discrete', vramGiB: 4, backends: ['cuda'] }] };
    const r = recommend(hw);
    expect(r.pick).toBeNull();
    expect(r.rejected.find((x) => x.modelId === 'qwen38-27b')?.reason).toMatch(/^weights_too_big:/);
    expect(r.rejected.find((x) => x.modelId === 'qwen35-4b')?.reason).toMatch(/^ctx_below_min:\d+$/);
  });
});

describe('machines without a discrete GPU (integrated graphics or none): the model lives in RAM', () => {
  const DENSE_BIG: Record<string, true> = { 'qwen38-27b': true, 'gemma4-31b': true };
  const ramMachine = (prefix: string): Hw => {
    const k = Object.keys(RAM_MACHINES).find((x) => x.startsWith(prefix));
    const hw = k ? RAM_MACHINES[k] : undefined;
    if (!hw) throw new Error(`no fixture ${prefix}`);
    return hw;
  };
  /** "speed_ram_moe:3/11-14" -> { size: 3, lo: 11, hi: 14 } */
  const speedOf = (why: string[]) => {
    const m = /^speed_ram_(moe|dense):([\d.]+)\/(\d+)-(\d+)$/.exec(why.find((w) => w.startsWith('speed_ram_')) ?? '');
    if (!m) throw new Error(`no RAM speed in ${why.join(' ')}`);
    return { kind: m[1], size: Number(m[2]), lo: Number(m[3]), hi: Number(m[4]) };
  };

  for (const [name, hw] of Object.entries(RAM_MACHINES)) {
    test(`${name}: low-active MoE or small model, usable speed, no dense 27B+, RAM budget`, () => {
      const r = recommend(hw);
      const pick = r.pick;
      if (!pick) throw new Error('no pick');
      const m = model(pick.modelId);
      expect(m.kind === 'moe' ? m.activeB <= 4 : m.paramsB <= 10).toBe(true);
      expect(pick.why[0] === 'quality_best' ? pick.why[1] : pick.why[0]).toBe('no_dgpu_ram');
      const s = speedOf(pick.why);
      expect(s.lo).toBeGreaterThanOrEqual(8);
      expect(s.hi).toBeLessThanOrEqual(60);
      expect(s.lo).toBeLessThan(s.hi);
      expect(pick.why.some((w) => /^prefill_ram:\d+-\d+\/131072$/.test(w))).toBe(true);
      for (const o of [pick, ...r.alternatives.slice(0, 1)]) expect(DENSE_BIG[o.modelId]).toBeUndefined();
      // the whole model in RAM: never more than RAM minus the system reserve; a card's "VRAM budget" never appears
      const reserve = hw.os === 'windows' ? Math.max(8, hw.ramGiB * 0.25) : Math.max(6, hw.ramGiB * 0.2);
      for (const o of [pick, ...r.alternatives]) {
        expect(o.mem.budgetGiB).toBeLessThanOrEqual(hw.ramGiB - reserve + 0.06);
        expect(['cpu', 'vulkan']).toContain(o.backend);
        expect(o.why).not.toContain('windows_reserve');
        expect(o.why).not.toContain('unified_memory');
      }
      for (const x of r.rejected.filter((x) => DENSE_BIG[x.modelId])) expect(x.reason).toMatch(/^(too_slow_on_this_hw|weights_too_big):/);
    });
  }

  test('the user report: Radeon(TM) Graphics (1 GB), 31 GB DDR4-3200 dual channel', () => {
    const hw = ramMachine('APU Ryzen 7 5700G');
    expect(hw.ramGiB).toBe(31);
    expect(hw.memory).toMatchObject({ type: 'DDR4', speedMTs: 3200, channels: 2, bandwidthGBs: 51.2, source: 'detected' });
    expect(hw.gpus).toEqual([{
      vendor: 'amd', name: 'AMD Radeon(TM) Graphics', kind: 'integrated', vramGiB: 1, sharedGiB: 15.5, backends: ['vulkan'],
      arch: 'gfx90c', driver: '24.9.1',
    }]);
    const r = recommend(hw);
    const pick = r.pick;
    if (!pick) throw new Error('no pick');
    // Windows keeps 8 GB: 23 GB for the model; the iGPU may map only 1 + 15.5 GB, so the 20 GB+ plans run on the CPU
    expect(pick.backend).toBe('cpu');
    expect(pick.mem.budgetGiB).toBe(23);
    expect(pick.why).toContain('cpu_igpu_pool:16.5');
    expect(pick.ctx).toBeGreaterThanOrEqual(131072);
    for (const o of r.alternatives.filter((x) => x.backend === 'vulkan')) expect(o.mem.budgetGiB).toBe(16.5);
    // dense Qwen3.8-27B: ~2–3 t/s on DDR4 dual channel (we measured 2.29 for Q4_K_XL on a Ryzen 7 5700X)
    const dense = r.rejected.find((x) => x.modelId === 'qwen38-27b' && x.quant === 'UD-Q3_K_XL')?.reason ?? '';
    expect(Number(/^too_slow_on_this_hw:([\d.]+)$/.exec(dense)?.[1])).toBeLessThan(4);
    // Qwen3.6-35B-A3B IQ4_XS: the estimate brackets our CPU measurement on the same RAM (13.09 t/s)
    const qwen = [pick, ...r.alternatives].find((o) => o.modelId === 'qwen36-35b-a3b');
    if (!qwen) throw new Error('Qwen3.6-35B-A3B not offered');
    const s = speedOf(qwen.why);
    expect(s).toMatchObject({ kind: 'moe', size: 3 });
    expect(s.lo).toBeLessThanOrEqual(13.09);
    expect(s.hi).toBeGreaterThanOrEqual(13.09);
  });

  test('Linux APU 780M: carve-out + GTT, Vulkan only (no ROCm kernels for gfx1103), DDR5 from udev DMI', () => {
    const hw = ramMachine('Linux APU');
    expect(hw.gpus).toEqual([{
      vendor: 'amd', name: 'AMD Radeon 760M/780M Graphics', kind: 'integrated', vramGiB: 2, sharedGiB: 15.3, backends: ['vulkan'],
      arch: 'gfx1103', driver: 'amdgpu',
    }]);
    expect(hw.memory).toMatchObject({ type: 'DDR5', speedMTs: 5600, channels: 2, bandwidthGBs: 89.6, source: 'detected' });
    const r = recommend(hw);
    for (const o of [r.pick, ...r.alternatives]) if (o?.backend === 'vulkan') expect(o.mem.budgetGiB).toBeCloseTo(2 + 15.3, 1);
  });

  test('Iris Xe laptop 16 GB: Intel integrated, a small model on Vulkan', () => {
    const hw = ramMachine('Laptop i7-1165G7');
    expect(hw.gpus[0]).toMatchObject({ vendor: 'intel', kind: 'integrated', vramGiB: 0, backends: ['vulkan'] });
    expect(hw.memory).toMatchObject({ type: 'DDR4', speedMTs: 3200, channels: 2, bandwidthGBs: 51.2 });
    const pick = recommend(hw).pick;
    expect(pick).toMatchObject({ backend: 'vulkan', gpuIndex: 0 });
    expect(pick?.why).toContain('igpu_backend:vulkan');
    expect(model(pick?.modelId ?? '').paramsB).toBeLessThanOrEqual(10);
  });

  test('desktop without any GPU, 64 GB DDR5: CPU backend, DDR5-5600 dual channel', () => {
    const hw = ramMachine('Desktop i9-13900KF');
    expect(hw.gpus).toEqual([]);
    expect(hw.memory).toMatchObject({ type: 'DDR5', speedMTs: 5600, channels: 2, bandwidthGBs: 89.6 });
    const pick = recommend(hw).pick;
    expect(pick).toMatchObject({ backend: 'cpu', gpuIndex: null });
    expect(pick?.why).toContain('cpu_only');
    expect(pick?.mem.budgetGiB).toBeCloseTo(63.8 - 63.8 * 0.25, 1);
  });

  test('a discrete GPU next to an iGPU: the iGPU and the CPU are not planned for', () => {
    const hw = windowsScan('windows-rtx4090-igpu-sample.json');
    expect(hw.gpus.map((g) => g.kind)).toEqual(['discrete', 'integrated']);
    const r = recommend(hw);
    for (const o of [r.pick, ...r.alternatives]) expect(o?.gpuIndex).toBe(0);
  });

  test('the RAM speed model reproduces our CPU measurements on their own RAM', () => {
    for (const m of CATALOG.models) {
      for (const x of m.ramMeasured ?? []) {
        const q = m.quants.find((y) => y.quant === x.quant);
        if (!q) throw new Error(`${m.id} has no ${x.quant}`);
        const s = ramSpeed(m, q, x.ramBwGBs, x.cores);
        expect(s.lo).toBeLessThanOrEqual(x.decodeTps);
        expect(s.hi).toBeGreaterThanOrEqual(x.decodeTps);
        expect(s.prefillHi).toBeCloseTo(x.prefillTps, 5);
      }
    }
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
