// Our CUDA engines (data/engines.json): enigma-cuda-lean (upstream b12110 + lean MTP reserve: q4_0 draft KV),
// enigma-cuda-prism (PrismML fork: PTQ1_0) and enigma-cuda-fork (cuda-topka2 + KVQ + lean reserve, Qwen3.8 MTP n 4).
// Published 2026-11-07 as the GitHub release enigma-engines-cuda-2026-11-07 (jarojarojaro-jaro/KERNEL): the planner
// uses them by default (the fork only on cards with a measured configuration); ENIGMA_ENGINE_DIR_<envKey> still
// overrides the download with a local directory.
import { afterAll, afterEach, beforeAll, describe, expect, test } from 'bun:test';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type { Hw, Option } from '../src/shared/types.ts';
import { CATALOG } from '../src/server/catalog/data.ts';
import { memParts } from '../src/server/catalog/memory.ts';
import { recommend, replan } from '../src/server/catalog/index.ts';
import {
  baselineEngineForOption, engineAvailable, engineById, enigmaConfig, enigmaEngineFor, ensureEngine, type EngineEntry, type ResolvedEngine,
} from '../src/server/engine.ts';
import { planCandidates } from '../src/server/optimize.ts';

const LEAN = 'ENIGMA_ENGINE_DIR_ENIGMA_CUDA_LEAN';
const PRISM = 'ENIGMA_ENGINE_DIR_ENIGMA_CUDA_PRISM';
const FORK = 'ENIGMA_ENGINE_DIR_ENIGMA_CUDA_FORK';
let dir = '';
beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), 'enigma-cuda-'));
});
afterAll(() => rmSync(dir, { recursive: true, force: true }));
afterEach(() => {
  delete process.env[LEAN];
  delete process.env[PRISM];
  delete process.env[FORK];
});
const withEngines = (): void => {
  process.env[LEAN] = dir;
  process.env[PRISM] = dir;
};

/** Campaign-67 cards: nvidia-smi total (MiB) → the scan's GiB, Linux. */
const card = (name: string, mib: number, arch: string): Hw => ({
  os: 'linux', arch: 'x64', cpu: { name: 'x', cores: 8, threads: 16 }, ramGiB: 32,
  memory: { totalGiB: 32, type: 'DDR4', speedMTs: 3200, channels: 2, modules: 2, bandwidthGBs: 51.2, source: 'detected' },
  gpus: [{ vendor: 'nvidia', name: `NVIDIA GeForce ${name}`, kind: 'discrete', vramGiB: Math.round((mib / 1024) * 10) / 10, backends: ['cuda', 'vulkan'], arch }],
  diskFreeGiB: 500, scannedAt: 0,
});
const SIXTEEN = [['RTX 4060 Ti', 16380, 'sm_89', 229376], ['RTX 5060 Ti', 16311, 'sm_120', 229376], ['RTX 5080', 16303, 'sm_120', 217088]] as const;
const TWELVE = [['RTX 2080 Ti', 11264, 'sm_75'], ['RTX 3060', 12288, 'sm_86'], ['RTX 4070', 12282, 'sm_89']] as const;
const pickOf = (hw: Hw): Option => {
  const p = recommend(hw).pick;
  if (!p) throw new Error('no pick');
  return p;
};
const resolved = (id: string): ResolvedEngine => ({ entry: engineById(id)!, dir, serverBin: join(dir, 'llama-server'), version: 'x', local: true });

describe('engines.json: our CUDA builds', () => {
  test('published: our archive from the KERNEL release, the CUDA runtime from the official b12110 release, all with sha256', () => {
    const REL = 'https://github.com/jarojarojaro-jaro/KERNEL/releases/download/enigma-engines-cuda-2026-11-07/';
    for (const id of ['enigma-cuda-lean', 'enigma-cuda-prism', 'enigma-cuda-fork']) {
      const e = engineById(id)!;
      expect(e).toMatchObject({ kind: 'enigma', os: 'linux', arch: 'x64', backend: 'cuda', distribution: 'download' });
      expect(e.unpublishedAssets).toBeUndefined();
      for (const a of e.assets) expect(a.sha256).toMatch(/^[0-9a-f]{64}$/);
      expect(e.assets[0]?.url).toBe(REL + e.assets[0]?.name);
      expect(e.assets[1]?.url).toStartWith('https://github.com/ggml-org/llama.cpp/releases/download/b12110/cudart-');
      expect(engineAvailable(e)).toBe(true);
    }
    expect(engineById('enigma-cuda-lean')?.assets[0]).toMatchObject({
      name: 'llama-b12110lean-bin-ubuntu-cuda-12.8-x64.tar.gz', sha256: '1ea7532e9edd17216eab559494dfb653258fce9281d2d67a961666349cbe9798',
    });
    expect(engineById('enigma-cuda-prism')?.assets[0]).toMatchObject({
      name: 'llama-prism-bin-ubuntu-cuda-12.8-x64.tar.gz', sha256: '4f6927ec8e2e6df311cee311584f5d0e8a6527caa942665a7a88474f100c23d9',
    });
    // lean has no sm_75 code; prism reaches the 2080 Ti through PTX JIT
    expect(engineById('enigma-cuda-lean')?.gpuArchs).not.toContain('sm_75');
    expect(engineById('enigma-cuda-prism')?.gpuArchs).toContain('sm_75');
  });

  test('profiles turn into the measured flags: lean MTP n 2 + q4_0 draft KV, prism MTP n 2 (draft cache follows -ctk)', () => {
    withEngines();
    const gsq = pickOf(card('RTX 5080', 16303, 'sm_120'));
    expect(enigmaEngineFor(card('RTX 5080', 16303, 'sm_120'), gsq).entry?.id).toBe('enigma-cuda-lean');
    const lean = enigmaConfig(resolved('enigma-cuda-lean'), gsq, '/m/Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf').config!;
    expect(lean.spec).toBe('mtp');
    expect(lean.extraArgs).toEqual(['--jinja', '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2', '--spec-draft-n-ubatch', '64', '-ctkd', 'q4_0', '-ctvd', 'q4_0']);
    const hw4070 = card('RTX 4070', 12282, 'sm_89');
    const bonsai = pickOf(hw4070);
    expect(enigmaEngineFor(hw4070, bonsai).entry?.id).toBe('enigma-cuda-prism');
    const prism = enigmaConfig(resolved('enigma-cuda-prism'), bonsai, '/m/Ternary-Bonsai-2-27B-PTQ1_0-mtp-lean.gguf').config!;
    expect(prism.extraArgs).toEqual(['--jinja', '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2', '--spec-draft-n-ubatch', '64']);
  });

  test('without a local directory the published engines are resolved for download', () => {
    const hw = card('RTX 5080', 16303, 'sm_120');
    expect(enigmaEngineFor(hw, pickOf(hw)).entry?.id).toBe('enigma-cuda-lean');
    const hw3090 = card('RTX 3090', 24576, 'sm_86');
    expect(enigmaEngineFor(hw3090, pickOf(hw3090)).entry?.id).toBe('enigma-cuda-fork');
  });
});

describe('memory model: our engines\' MTP draft', () => {
  test('lean reserve with a q4_0 draft KV saves the F16 draft cache (5080 GSQ 217088: within the measured peak)', () => {
    const m = CATALOG.models.find((x) => x.id === 'qwen38-27b')!;
    const q = m.quants.find((x) => x.quant === 'GSQ-IQ3_XXS')!;
    const base = { ctx: 217088, kvType: 'q4_0', ub: 256, backend: 'cuda', vramGiB: 15.9, spec: true, enigmaSpec: false, mtpN: 2, ubd: 64, prompt: 0 } as const;
    const stock = memParts(m, q, base).totalMiB;
    const lean = memParts(m, q, { ...base, draftKv: 'q4_0', leanReserve: true }).totalMiB;
    // nextn K+V 4 × 512 per token: 2 → 0.5625 B per element, plus the ubd × ctx mask
    expect(stock - lean).toBeGreaterThan(600);
    expect(stock - lean).toBeLessThan(700);
  });
});

describe('planner with our CUDA engines available', () => {
  test('16 GB: Qwen3.8-27B GSQ IQ3_XXS + lean MTP n 2 at the measured context (4060 Ti / 5060 Ti 229376, 5080 217088)', () => {
    withEngines();
    for (const [name, mib, arch, ctx] of SIXTEEN) {
      const hw = card(name, mib, arch);
      const p = pickOf(hw);
      expect(p).toMatchObject({ modelId: 'qwen38-27b', quant: 'GSQ-IQ3_XXS', ctx, ub: 256, kvType: 'q4_0', mtpEngine: 'enigma-cuda-lean' });
      expect(p.features).toContain('mtp');
      expect(p.why).toContain('mtp_engine:enigma-cuda-lean/2');
      expect(p.needsEngine).toBeUndefined();
      expect(baselineEngineForOption(hw, p)?.id).toBe('upstream-linux-x64-cuda');
      // stock upstream MTP (n 3, F16 draft KV) at that context does not fit: only the enigma candidate runs MTP
      expect(replan(p, hw, { mtpEngine: null }).fits).toBe(false);
      const cands = planCandidates(hw, p, resolved('upstream-linux-x64-cuda'));
      expect(cands.find((c) => c.candidate.id === 'enigma')?.candidate.status).toBe('pending');
      expect(cands.find((c) => c.candidate.id === 'mtp')?.candidate).toMatchObject({ status: 'rejected', reason: 'mtp_no_memory' });
    }
  });

  test('11/12 GB: Ternary Bonsai 2 PTQ1_0 + MTP n 2 on prism, baseline on prism too, ≤ the measured 229376', () => {
    withEngines();
    for (const [name, mib, arch] of TWELVE) {
      const hw = card(name, mib, arch);
      const p = pickOf(hw);
      expect(p).toMatchObject({ modelId: 'bonsai2-27b-mtp', quant: 'PTQ1_0', needsEngine: 'enigma-cuda-prism', mtpEngine: 'enigma-cuda-prism' });
      expect(p.features).toContain('mtp');
      expect(p.ctx).toBeGreaterThanOrEqual(131072);
      expect(p.ctx).toBeLessThanOrEqual(229376);
      expect(p.why).toContain('engine_required:enigma-cuda-prism');
      // Apache-2.0 (prism-ml weights, sudoingx MTP block): no licence condition
      expect(CATALOG.licenses[CATALOG.models.find((m) => m.id === p.modelId)!.license]?.commercial).toBe('yes');
      expect(p.why.some((w) => w.startsWith('license_conditional'))).toBe(false);
      // upstream outputs garbage on PTQ1_0: the baseline runs on the fork
      expect(baselineEngineForOption(hw, p)?.id).toBe('enigma-cuda-prism');
    }
  });

  test('10 GB (3080): Bonsai PTQ1_0 MTP does not fit and an unmeasured plain PTQ1_0 plan is not offered: Qwen3.5-9B Q6_K stays', () => {
    withEngines();
    const r = recommend(card('RTX 3080', 10240, 'sm_86'));
    expect(r.pick).toMatchObject({ modelId: 'qwen35-9b', quant: 'Q6_K', ctx: 192512 });
    // not offered at all (the reason shown comes from the device with the most memory, here the Vulkan one)
    expect(r.alternatives.some((a) => a.modelId === 'bonsai2-27b-mtp')).toBe(false);
    expect(r.rejected.some((x) => x.modelId === 'bonsai2-27b-mtp')).toBe(true);
  });

  test('24/32 GB: the measured fork plans at 262144 (3090 and 4090 ub 256, 5090 ub 512)', () => {
    expect(pickOf(card('RTX 3090', 24576, 'sm_86'))).toMatchObject({ modelId: 'qwen38-27b', quant: 'UD-Q4_K_XL', ctx: 262144, ub: 256, mtpEngine: 'enigma-cuda-fork' });
    expect(pickOf(card('RTX 4090', 24564, 'sm_89'))).toMatchObject({ modelId: 'qwen38-27b', quant: 'UD-Q4_K_XL', ctx: 262144, ub: 256, mtpEngine: 'enigma-cuda-fork' });
    expect(pickOf(card('RTX 5090', 32607, 'sm_120'))).toMatchObject({ modelId: 'qwen38-27b', quant: 'UD-Q6_K', ctx: 262144, ub: 512, mtpEngine: 'enigma-cuda-fork' });
  });
});

describe('enigma-cuda-fork (cuda-topka2 + KVQ + lean MTP reserve)', () => {
  const hw4090 = card('RTX 4090', 24564, 'sm_89');

  test('engines.json: portable build + official cudart + the draft vocabulary, planned only where measured', () => {
    const e = engineById('enigma-cuda-fork')!;
    expect(e).toMatchObject({ distribution: 'download', planOnlyMeasured: true, gpuArchs: ['sm_86', 'sm_89', 'sm_120'] });
    expect(e.assets.map((a) => a.name)).toEqual([
      'llama-kvqleana-bin-ubuntu-cuda-12.8-x64.tar.gz', 'cudart-llama-b12110-bin-ubuntu-cuda-12.8-x64.tar.gz', 'draft_vocab_qwen38.txt',
    ]);
    // the published portable build: RUNPATH set to $ORIGIN after the campaign (the tested build pointed at the build dir)
    expect(e.assets[0]?.sha256).toBe('b63ec233f60a35a8407a5ad583fbfa14ab705470219c08849656c6e256b71df3');
  });

  test('available: the 4090 plan runs on it at the measured 262144 / ub 256 with the exact run config', () => {
    process.env[FORK] = dir;
    const p = pickOf(hw4090);
    expect(p).toMatchObject({ modelId: 'qwen38-27b', quant: 'UD-Q4_K_XL', ctx: 262144, ub: 256, kvType: 'q4_0', mtpEngine: 'enigma-cuda-fork' });
    expect(p.why).toContain('mtp_engine:enigma-cuda-fork/4');
    expect(enigmaEngineFor(hw4090, p).entry?.id).toBe('enigma-cuda-fork');
    // the pinned upstream MTP n 3 at 262144 / ub 256 is a measured configuration too: both MTP candidates are measured
    const cands = planCandidates(hw4090, p, resolved('upstream-linux-x64-cuda'));
    expect(cands.find((c) => c.candidate.id === 'enigma')?.candidate.status).toBe('pending');
    expect(cands.find((c) => c.candidate.id === 'mtp')?.candidate.status).toBe('pending');
    mkdirSync(join(dir, 'share'), { recursive: true });
    writeFileSync(join(dir, 'share', 'draft_vocab_qwen38.txt'), '1\n');
    const cfg = enigmaConfig(resolved('enigma-cuda-fork'), p, '/m/Qwen3.8-27B-UD-Q4_K_XL.gguf').config!;
    expect(cfg.env).toEqual({
      LLAMA_SPEC_LOOKUP: '3', LLAMA_SPEC_LOOKUP_W: '16', LLAMA_SERVER_CACHE_SHARE_MIN: '1024', LLAMA_GPU_VERIFY: '1',
      LLAMA_SERVER_REASONING_CONTROL: '0', GGML_CUDA_KVQ: '1',
    });
    expect(cfg.extraArgs).toEqual([
      '--jinja', '--spec-draft-vocab', join(dir, 'share', 'draft_vocab_qwen38.txt'), '--spec-draft-vocab-n', '65536',
      '--spec-draft-head-type', 'iq4_xs', '--spec-mtp-type', 'iq4_xs',
      // the fork has no --spec-draft-n-ubatch
      '--spec-type', 'draft-mtp', '--spec-draft-n-max', '4', '-ctkd', 'q4_0', '-ctvd', 'q4_0',
    ]);
    expect({ ub: cfg.ub, ctx: cfg.ctx, kvType: cfg.kvType }).toEqual({ ub: 256, ctx: 262144, kvType: 'q4_0' });
  });

  test('available: the 3090 plan becomes UD-Q4_K_XL 262144 / ub 256 on it (measured on the shipped portable build)', () => {
    withEngines();
    process.env[FORK] = dir;
    const hw = card('RTX 3090', 24576, 'sm_86');
    const p = pickOf(hw);
    expect(p).toMatchObject({ quant: 'UD-Q4_K_XL', ctx: 262144, ub: 256, mtpEngine: 'enigma-cuda-fork' });
    expect(enigmaEngineFor(hw, p).entry?.id).toBe('enigma-cuda-fork');
    // the 16 GB cards keep lean-upstream
    for (const [name, mib, arch] of SIXTEEN) expect(pickOf(card(name, mib, arch)).mtpEngine).toBe('enigma-cuda-lean');
  });

  test('available: the 5090 plan runs on it at the measured 262144 / ub 512 (UD-Q6_K)', () => {
    process.env[FORK] = dir;
    const hw = card('RTX 5090', 32607, 'sm_120');
    expect(pickOf(hw)).toMatchObject({ quant: 'UD-Q6_K', ctx: 262144, ub: 512, mtpEngine: 'enigma-cuda-fork' });
  });

  test('16 GB: lean-upstream (earlier in engines.json) wins over the fork, which is measured there only on the 5060 Ti', () => {
    expect(pickOf(card('RTX 5060 Ti', 16311, 'sm_120'))).toMatchObject({ quant: 'GSQ-IQ3_XXS', ctx: 229376, mtpEngine: 'enigma-cuda-lean' });
    expect(pickOf(card('RTX 4060 Ti', 16380, 'sm_89')).mtpEngine).toBe('enigma-cuda-lean');
    expect(pickOf(card('RTX 5080', 16303, 'sm_120')).mtpEngine).toBe('enigma-cuda-lean');
  });

  test('2080 Ti: prism Bonsai PTQ1_0 MTP n 2 at the measured 155648 / ub 512', () => {
    process.env[PRISM] = dir;
    expect(pickOf(card('RTX 2080 Ti', 11264, 'sm_75'))).toMatchObject({ modelId: 'bonsai2-27b-mtp', ctx: 155648, ub: 512, mtpEngine: 'enigma-cuda-prism' });
  });

  test('install: archives are extracted, a plain asset (draft vocabulary) lands in <engine>/share', async () => {
    const prevHome = process.env.ENIGMA_HOME;
    process.env.ENIGMA_HOME = join(dir, 'home');
    try {
      const src = join(dir, 'pkg');
      mkdirSync(join(src, 'llama-x'), { recursive: true });
      writeFileSync(join(src, 'llama-x', 'llama-server'), '#!/bin/sh\n');
      const dl = join(dir, 'home', 'downloads', 'enigma-cuda-fork');
      mkdirSync(dl, { recursive: true });
      const tar = Bun.spawnSync(['tar', '-czf', join(dl, 'llama-x.tar.gz'), '-C', src, 'llama-x']);
      expect(tar.exitCode).toBe(0);
      writeFileSync(join(dl, 'draft_vocab_qwen38.txt'), 'vocab\n');
      const sha = (f: string): string => new Bun.CryptoHasher('sha256').update(readFileSync(f)).digest('hex');
      const entry: EngineEntry = {
        ...engineById('enigma-cuda-fork')!, distribution: 'download',
        assets: ['llama-x.tar.gz', 'draft_vocab_qwen38.txt'].map((name) => ({ name, url: 'http://127.0.0.1:9/unused', sizeBytes: 1, sha256: sha(join(dl, name)) })),
      };
      const r = await ensureEngine(entry);
      expect(r.serverBin.endsWith(join('llama-x', 'llama-server'))).toBe(true);
      expect(readFileSync(join(r.dir, 'share', 'draft_vocab_qwen38.txt'), 'utf8')).toBe('vocab\n');
    } finally {
      if (prevHome === undefined) delete process.env.ENIGMA_HOME;
      else process.env.ENIGMA_HOME = prevHome;
    }
  });
});
