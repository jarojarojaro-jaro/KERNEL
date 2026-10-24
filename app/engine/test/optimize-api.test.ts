import { describe, expect, test } from 'bun:test';
import type { BenchResult, Candidate } from '../src/shared/types.ts';
import { decide, failureCode, recipeFor } from '../src/server/optimize.ts';
import { hostAllowed } from '../src/server/api.ts';

function bench(prefill: number, decode: number, md5 = 'a', ctxOk = true): BenchResult {
  return {
    engine: { id: 'e', version: '1', backend: 'cpu' },
    config: { engineId: 'e', modelPath: '/m', ctx: 1, kvType: 'f16', ub: 512, b: 2048, flashAttn: true, extraArgs: [], env: {} },
    prefill: { tokens: 4096, tps: prefill, ttftS: 1 }, decode: { tokens: 256, tps: decode }, ctxOk, outputMd5: md5, at: 1,
  };
}

function cand(id: string, r?: BenchResult, status: Candidate['status'] = 'pending'): Candidate {
  const c: Candidate = { id, label: { pl: id, en: id }, desc: { pl: '', en: '' }, status };
  if (r) c.result = r;
  return c;
}

describe('decide', () => {
  const base = bench(1000, 100);

  test('fastest decode with prefill loss <= 5% wins', () => {
    const cs = [cand('a', bench(960, 120)), cand('b', bench(900, 150)), cand('c', bench(1100, 110)), cand('d', undefined, 'rejected')];
    const best = decide(cs, base);
    expect(best?.id).toBe('a');
    expect(cs.map((c) => c.status)).toEqual(['kept', 'rejected', 'rejected', 'rejected']);
    expect(cs[1]?.reason).toBe('prefill_loss:-10');
    expect(cs[2]?.reason).toBe('slower_than:a');
  });

  test('nothing beats the baseline: keep baseline', () => {
    const cs = [cand('a', bench(1000, 99)), cand('b', bench(1000, 120, 'x', false))];
    expect(decide(cs, base)).toBeNull();
    expect(cs[0]?.reason).toBe('decode_not_faster:-1');
    expect(cs[1]?.reason).toBe('ctx_not_fit');
  });

  test('re-deciding after resume demotes a stale kept', () => {
    const cs = [cand('a', bench(1000, 120), 'kept'), cand('b', bench(1000, 130))];
    expect(decide(cs, base)?.id).toBe('b');
    expect(cs[0]?.status).toBe('rejected');
  });

  test('recipes rebuild from ids', () => {
    expect(recipeFor('ub-2048')).toEqual({ kind: 'ub', ub: 2048 });
    expect(recipeFor('mtp')).toEqual({ kind: 'spec', spec: 'mtp' });
    expect(recipeFor('enigma')).toEqual({ kind: 'enigma' });
    expect(recipeFor('x')).toBeNull();
  });
});

describe('hostAllowed', () => {
  const req = (headers: Record<string, string>): Request => new Request('http://127.0.0.1:11500/api/state', { headers });
  test('local host and origin pass', () => {
    expect(hostAllowed(req({ host: '127.0.0.1:11500' }))).toBe(true);
    expect(hostAllowed(req({ host: 'localhost:11500', origin: 'http://localhost:11501' }))).toBe(true);
    expect(hostAllowed(req({ host: '[::1]:11500', origin: 'http://[::1]:11500' }))).toBe(true);
  });
  test('rebinding and cross-site requests are refused', () => {
    expect(hostAllowed(req({ host: 'evil.example:11500' }))).toBe(false);
    expect(hostAllowed(req({ host: '127.0.0.1:11500', origin: 'https://evil.example' }))).toBe(false);
    expect(hostAllowed(req({ host: '127.0.0.1.evil.example' }))).toBe(false);
    expect(hostAllowed(req({ host: '127.0.0.1:11500', origin: 'null' }))).toBe(false);
  });
});

describe('failureCode', () => {
  test('classifies failures', () => {
    expect(failureCode('llama-server exited (1) while loading:\nggml_backend_cuda_buffer_type_alloc_buffer: allocating 9000 MiB on device 0: cudaMalloc failed: out of memory')).toBe('oom');
    expect(failureCode('llama-server exited (1) while loading:\nerror: unknown argument')).toBe('start_failed:llama-server exited (1) while loading:');
    expect(failureCode('/completion HTTP 500: x')).toBe('failed:/completion HTTP 500: x');
  });
});
