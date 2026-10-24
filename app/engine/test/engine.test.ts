import { afterAll, beforeAll, describe, expect, test } from 'bun:test';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { join } from 'node:path';
import { deflateRawSync } from 'node:zlib';
import type { Hw, Option } from '../src/shared/types.ts';
import {
  baselineConfig, baselineEngineFor, ENGINES, engineById, enigmaConfig, enigmaEngineFor, extractZip, findServerBin, gatherLibs,
  serverArgs, type ResolvedEngine,
} from '../src/server/engine.ts';

let dir = '';
beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), 'enigma-engine-'));
});
afterAll(() => rmSync(dir, { recursive: true, force: true }));

const hwXtx: Hw = {
  os: 'linux', arch: 'x64', cpu: { name: 'AMD Ryzen 7 5700X 8-Core Processor', cores: 8, threads: 16 }, ramGiB: 62.7,
  gpus: [{ vendor: 'amd', name: 'AMD Radeon RX 7900 XTX', vramGiB: 24, unified: false, arch: 'gfx1100', driver: 'amdgpu', backends: ['rocm', 'vulkan'] }],
  diskFreeGiB: 100, scannedAt: 1,
};

function option(modelId: string, path: string, over: Partial<Option> = {}): Option {
  return {
    id: `${modelId}/q/rocm`, modelId, name: modelId, family: 'x', params: '27B', quant: 'q',
    file: { repo: 'org/repo', path, sizeBytes: 1 }, ctx: 204800, ctxMax: 262144, kvType: 'q4_0', ub: 512, backend: 'rocm',
    gpuIndex: 0, mem: { weightsGiB: 16, kvGiB: 4, computeGiB: 1, overheadGiB: 0.5, totalGiB: 21.5, budgetGiB: 23.5, freeGiB: 2 },
    features: ['mtp'], score: 1, why: [], ...over,
  };
}

/** Writes a zip with one stored and one deflated entry (our reader ignores CRCs). */
function makeZip(file: string, entries: Record<string, string>): void {
  const locals: Buffer[] = [];
  const centrals: Buffer[] = [];
  let off = 0;
  let i = 0;
  for (const [name, text] of Object.entries(entries)) {
    const raw = Buffer.from(text);
    const method = i++ % 2 === 0 ? 0 : 8;
    const data = method === 8 ? deflateRawSync(raw) : raw;
    const n = Buffer.from(name);
    const lh = Buffer.alloc(30);
    lh.writeUInt32LE(0x04034b50, 0); lh.writeUInt16LE(20, 4); lh.writeUInt16LE(method, 8);
    lh.writeUInt32LE(data.length, 18); lh.writeUInt32LE(raw.length, 22); lh.writeUInt16LE(n.length, 26);
    const ch = Buffer.alloc(46);
    ch.writeUInt32LE(0x02014b50, 0); ch.writeUInt16LE(20, 6); ch.writeUInt16LE(method, 10);
    ch.writeUInt32LE(data.length, 20); ch.writeUInt32LE(raw.length, 24); ch.writeUInt16LE(n.length, 28);
    ch.writeUInt32LE((0o100755 << 16) >>> 0, 38); ch.writeUInt32LE(off, 42);
    locals.push(lh, n, data);
    centrals.push(ch, n);
    off += 30 + n.length + data.length;
  }
  const cd = Buffer.concat(centrals);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0); end.writeUInt16LE(centrals.length / 2, 8); end.writeUInt16LE(centrals.length / 2, 10);
  end.writeUInt32LE(cd.length, 12); end.writeUInt32LE(off, 16);
  writeFileSync(file, Buffer.concat([...locals, cd, end]));
}

describe('engines.json', () => {
  test('pinned upstream builds cover the platforms', () => {
    expect(ENGINES.upstream.tag).toMatch(/^b\d+$/);
    for (const [os, arch, backend] of [
      ['linux', 'x64', 'cpu'], ['linux', 'x64', 'vulkan'], ['linux', 'x64', 'rocm'], ['windows', 'x64', 'cuda'],
      ['windows', 'x64', 'vulkan'], ['windows', 'x64', 'rocm'], ['macos', 'arm64', 'metal'],
    ] as const) {
      const e = baselineEngineFor(os, arch, backend);
      expect(e).toBeDefined();
      for (const a of e?.assets ?? []) {
        expect(a.url).toStartWith(`https://github.com/ggml-org/llama.cpp/releases/download/${ENGINES.upstream.tag}/`);
        expect(a.sizeBytes).toBeGreaterThan(1_000_000);
        expect(a.sha256).toMatch(/^[0-9a-f]{64}$/);
      }
    }
    expect(baselineEngineFor('windows', 'x64', 'cuda')?.assets.length).toBe(2);
  });
});

describe('enigma engine choice', () => {
  test('AMD gfx1100 gets enigma-rocm only with a local dir; other platforms get a plain reason', () => {
    const qwen = option('qwen38-27b', 'Qwen3.8-27B-UD-Q4_K_XL.gguf');
    delete process.env.ENIGMA_ENGINE_DIR_ENIGMA_ROCM;
    expect(enigmaEngineFor(hwXtx, qwen).reason).toContain('not published for download yet');
    process.env.ENIGMA_ENGINE_DIR_ENIGMA_ROCM = dir;
    expect(enigmaEngineFor(hwXtx, qwen).entry?.id).toBe('enigma-rocm-gfx1100');
    const cpu = enigmaEngineFor({ ...hwXtx, gpus: [] }, { ...qwen, backend: 'cpu', gpuIndex: null });
    expect(cpu.entry).toBeNull();
    expect(cpu.reason).toContain('No Enigma-optimised engine for CPU');
    const flint = enigmaEngineFor(hwXtx, option('flint-40b-a2.5b', 'flint-nvfp4.gguf'));
    expect(flint.reason).toContain('has no profile');
    delete process.env.ENIGMA_ENGINE_DIR_ENIGMA_ROCM;
  });
});

describe('enigma profiles reproduce run-topka.sh + run-llm.sh', () => {
  const entry = engineById('enigma-rocm-gfx1100');
  const engine = (): ResolvedEngine => ({ entry: entry!, dir: join(dir, 'llama-topka'), serverBin: join(dir, 'llama-topka', 'bin', 'llama-server'), version: 'x', local: true });

  test('Qwen3.8: MTP + lookup + PM4 + coupled + host-gap + safety switches', () => {
    const models = join(dir, 'models');
    mkdirSync(join(models, 'draft'), { recursive: true });
    writeFileSync(join(models, 'draft', 'draft_vocab_qwen38.txt'), '1\n');
    process.env.ENIGMA_MODELS_DIR = models;
    const r = enigmaConfig(engine(), option('qwen38-27b', 'Qwen3.8-27B-UD-Q4_K_XL.gguf'), join(models, 'Qwen3.8-27B-UD-Q4_K_XL.gguf'));
    delete process.env.ENIGMA_MODELS_DIR;
    expect(r.reason).toBe('');
    const c = r.config!;
    expect(c.spec).toBe('mtp');
    expect([c.b, c.ub, c.kvType, c.ctx]).toEqual([2048, 512, 'q4_0', 204800]);
    expect(c.env).toMatchObject({
      LLAMA_SPEC_LOOKUP: '3', LLAMA_SPEC_LOOKUP_W: '16', LLAMA_SERVER_CACHE_SHARE_MIN: '1024',
      LLAMA_MTP_REQUANT_CACHE: join(homedir(), '.cache', 'llama-mtp'),
      GGML_HIP_PM4: '1', GGML_HIP_PM4_WA: '2', GGML_HIP_PM4_GUARD: '1', HSA_USE_SVM: '0', LLAMA_GPU_VERIFY: '1',
      LLAMA_SPEC_COUPLED: '1', LLAMA_SERVER_YIELD_FAST: '2', GGML_HIP_PM4_MIN_DISPATCH: '16', GGML_HIP_PM4_LAZY_EXEC: '1',
      DRAFT_N: '4', LLAMA_SERVER_SAFE_SPECIAL: '1', LLAMA_SERVER_SAFE_TOOLS: '1', LLAMA_TOKENIZE_PAR: '8',
      LLAMA_CKPT_VRAM: '2', LLAMA_CHAT_NATIVE: '1', LLAMA_CHAT_LATE_SYSTEM: '1', LLAMA_SERVER_REASONING_CONTROL: '0',
    });
    expect(c.env.LD_LIBRARY_PATH).toStartWith(`${join(dir, 'llama-topka')}/lib:`);
    const args = serverArgs(engine(), c, 8080, 'k');
    expect(args.join(' ')).toContain('-ngl 999 -fa on -ctk q4_0 -ctv q4_0 -b 2048 -ub 512 -np 1');
    expect(args.join(' ')).toContain('--jinja --cache-ram 16384 --reasoning-effort low --spec-type draft-mtp --spec-draft-n-max 4 ' +
      `--spec-draft-vocab ${join(models, 'draft', 'draft_vocab_qwen38.txt')} --spec-draft-vocab-n 65536 ` +
      '--spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs -ctkd q4_0 -ctvd q4_0');
    expect(args).toContain('--api-key');
  });

  test('LFM2.5-24B: no MTP, lookup 0, coupled 0, no host-gap, -b/-ub 2048, KV q8_0', () => {
    const r = enigmaConfig(engine(), option('lfm25-24b-a2b', 'LFM2.5-24B-A2B-Q5_K_M.gguf', { ctx: 131072, kvType: 'q8_0', features: [] }), '/m/x.gguf');
    const c = r.config!;
    expect([c.spec, c.b, c.ub, c.kvType]).toEqual(['none', 2048, 2048, 'q8_0']);
    expect(c.env.LLAMA_SPEC_LOOKUP).toBe('0');
    expect(c.env.LLAMA_SPEC_COUPLED).toBe('0');
    expect(c.env.LLAMA_SERVER_YIELD_FAST).toBeUndefined();
    expect(c.env.LLAMA_MTP_REQUANT_CACHE).toBeUndefined();
    expect(c.extraArgs).toEqual(['--jinja', '--cache-ram', '16384']);
  });

  test('Qwen3.8 without the draft vocabulary is not offered silently', () => {
    process.env.ENIGMA_MODELS_DIR = join(dir, 'empty');
    const r = enigmaConfig(engine(), option('qwen38-27b', 'Qwen3.8-27B-UD-Q4_K_XL.gguf'), '/nowhere/Qwen3.8-27B-UD-Q4_K_XL.gguf');
    delete process.env.ENIGMA_MODELS_DIR;
    expect(r.config).toBeNull();
    expect(r.reason).toContain('draftVocab');
  });
});

describe('baseline config and install helpers', () => {
  test('CPU baseline sets threads, GPU baseline offloads everything', () => {
    const cpuEngine: ResolvedEngine = { entry: baselineEngineFor('linux', 'x64', 'cpu')!, dir, serverBin: '/x/llama-server', version: 'b1', local: true };
    const opt = option('lfm25-2.6b', 'LFM2.5-2.6B-QAD-Q4_0.gguf', { backend: 'cpu', gpuIndex: null, ub: 512, ctx: 128000, kvType: 'f16' });
    const c = baselineConfig(cpuEngine, opt, '/m.gguf', hwXtx);
    expect(c.threads).toBeGreaterThan(0);
    expect(c.threads).toBeLessThanOrEqual(8);
    expect(serverArgs(cpuEngine, c, 1, 'k').slice(0, 6)).toEqual(['-m', '/m.gguf', '-c', '128000', '-ngl', '0']);
  });

  test('zip extraction (stored + deflate, exec bit) and llama-server lookup', () => {
    const z = join(dir, 'a.zip');
    makeZip(z, { 'llama-b1-bin/llama-server': '#!/bin/sh\n', 'llama-b1-bin/README.md': 'hello '.repeat(100) });
    const out = join(dir, 'zip-out');
    extractZip(z, out);
    expect(readFileSync(join(out, 'llama-b1-bin', 'README.md'), 'utf8')).toBe('hello '.repeat(100));
    expect(findServerBin(out)).toBe(join(out, 'llama-b1-bin', 'llama-server'));
  });

  test('zip with path traversal is refused', () => {
    const z = join(dir, 'evil.zip');
    makeZip(z, { '../evil.txt': 'x' });
    expect(() => extractZip(z, join(dir, 'evil-out'))).toThrow('unsafe path');
  });

  test('CUDA runtime unpacked beside the release dir is moved next to llama-server', () => {
    const root = join(dir, 'cuda-install');
    const bin = join(root, 'llama-b1');
    const rt = join(root, 'cudart-llama-b1');
    mkdirSync(bin, { recursive: true });
    mkdirSync(rt, { recursive: true });
    writeFileSync(join(bin, 'llama-server'), '');
    writeFileSync(join(bin, 'libggml-cuda.so'), 'ours');
    for (const f of ['libcudart.so.12', 'libcublas.so.12', 'LICENSE', 'libggml-cuda.so']) writeFileSync(join(rt, f), 'rt');
    gatherLibs(root, bin);
    expect(readFileSync(join(bin, 'libcudart.so.12'), 'utf8')).toBe('rt');
    expect(readFileSync(join(bin, 'libcublas.so.12'), 'utf8')).toBe('rt');
    expect(readFileSync(join(bin, 'libggml-cuda.so'), 'utf8')).toBe('ours'); // never overwrites the engine's own
    expect(readFileSync(join(rt, 'LICENSE'), 'utf8')).toBe('rt'); // only shared libraries move
  });
});
