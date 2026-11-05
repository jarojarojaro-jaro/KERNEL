import { describe, expect, test } from 'bun:test';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type { BenchResult, Candidate } from '../src/shared/types.ts';
import { confirm, decide, failureCode, recipeFor } from '../src/server/optimize.ts';
import { hostAllowed, serveApi } from '../src/server/api.ts';
import { App } from '../src/server/state.ts';

function bench(prefill: number, decode: number, md5 = 'a', ctxOk = true, deep?: { prefill: number; decode: number }): BenchResult {
  const r: BenchResult = {
    engine: { id: 'e', version: '1', backend: 'cpu' },
    config: { engineId: 'e', modelPath: '/m', ctx: 1, kvType: 'f16', ub: 512, b: 2048, flashAttn: true, extraArgs: [], env: {} },
    prefill: { tokens: 4096, tps: prefill, ttftS: 1 }, decode: { tokens: 256, tps: decode, greedyTps: decode }, ctxOk, outputMd5: md5,
    at: 1,
  };
  if (deep) r.deep = { ctxTokens: 32768, prefillTps: deep.prefill, decodeTps: deep.decode };
  return r;
}

function cand(id: string, r?: BenchResult, status: Candidate['status'] = 'pending'): Candidate {
  const c: Candidate = { id, label: { pl: id, en: id }, desc: { pl: '', en: '' }, status };
  if (r) c.result = r;
  return c;
}

describe('decide', () => {
  const base = bench(1000, 100);

  test('fastest decode wins; prefill loss <= 5%, or <= 15% when decode gains >= 20%', () => {
    const cs = [cand('a', bench(960, 120)), cand('b', bench(800, 150)), cand('c', bench(1100, 110)), cand('d', undefined, 'rejected'),
      cand('e', bench(900, 115))];
    const best = decide(cs, base);
    expect(best?.id).toBe('a');
    expect(cs.map((c) => c.status)).toEqual(['kept', 'rejected', 'rejected', 'rejected', 'rejected']);
    expect(cs[1]?.reason).toBe('prefill_loss:-20');
    expect(cs[2]?.reason).toBe('slower_than:a');
    expect(cs[4]?.reason).toBe('prefill_loss:-10');
  });

  test('a big decode gain may cost up to 15% prefill (MTP on the 3090: decode +40%, prefill -11%)', () => {
    const cs = [cand('lookup', bench(1000, 102, 'x')), cand('mtp', bench(890, 140, 'y'))];
    expect(decide(cs, base)?.id).toBe('mtp');
  });

  test('a text-changing candidate needs >= 3% decode gain; an identical-output one only beats the noise floor', () => {
    const cs = [cand('lookup', bench(1000, 102.8, 'x')), cand('ub', bench(1000, 102.5, 'a'))];
    expect(decide(cs, base)?.id).toBe('ub');
    expect(cs[0]?.reason).toBe('gain_too_small:2.8');
  });

  test('a gain within the noise threshold (2%, or what the caller measured) does not win', () => {
    const cs = [cand('ub', bench(1000, 101.5)), cand('lookup', bench(1000, 104, 'x'))];
    expect(decide(cs, base)?.id).toBe('lookup');
    expect(cs[0]?.reason).toBe('within_noise:1.5');
    expect(decide(cs, base, 0.05)).toBeNull();
    expect(cs[1]?.reason).toBe('within_noise:4');
  });

  test('the deep (~32k) result is part of the decision', () => {
    const b = bench(1000, 100, 'a', true, { prefill: 900, decode: 30 });
    const cs = [
      cand('kvcpu', bench(1000, 130, 'a', true, { prefill: 900, decode: 20 })),
      cand('slowdeep', bench(1000, 110, 'a', true, { prefill: 700, decode: 30 })),
      cand('ok', bench(1000, 105, 'a', true, { prefill: 880, decode: 29 })),
    ];
    expect(decide(cs, b)?.id).toBe('ok');
    expect(cs[0]?.reason).toBe('deep_decode_loss:-33.3');
    expect(cs[1]?.reason).toBe('deep_prefill_loss:-22.2');
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

  test('a failed confirmation stays rejected when deciding again', () => {
    const cs = [cand('a', bench(1000, 130)), cand('b', bench(1000, 120))];
    cs[0]!.reason = 'not_confirmed:1';
    expect(decide(cs, base)?.id).toBe('b');
    expect(cs[0]).toMatchObject({ status: 'rejected', reason: 'not_confirmed:1' });
  });

  test('recipes rebuild from ids', () => {
    expect(recipeFor('ub-2048')).toEqual({ kind: 'ub', ub: 2048 });
    expect(recipeFor('mtp')).toEqual({ kind: 'spec', spec: 'mtp' });
    expect(recipeFor('enigma')).toEqual({ kind: 'enigma' });
    expect(recipeFor('x')).toBeNull();
  });
});

describe('confirm', () => {
  const base = bench(1000, 100);

  test('the winner measured again next to a new baseline run: kept with the confirmation numbers', () => {
    const c = cand('mtp', bench(1000, 140, 'x'), 'kept');
    const again = bench(990, 141, 'x');
    expect(confirm(c, again, base, bench(1000, 101))).toBe(true);
    expect(c).toMatchObject({ status: 'kept', result: again, decodePct: 39.6, prefillPct: -1, sameOutput: false });
    expect(c.reason).toBeUndefined();
  });

  test('a gain that does not beat 2 x the baseline run-to-run noise is not confirmed', () => {
    const c = cand('ub', bench(1000, 104), 'kept');
    // the baseline moved 3% between its runs: threshold 6%, the repeat shows +4.9%
    expect(confirm(c, bench(1000, 108), base, bench(1000, 103))).toBe(false);
    expect(c).toMatchObject({ status: 'rejected', reason: 'not_confirmed:4.9' });
    const cs = [c, cand('lookup', bench(1000, 103, 'x'))];
    expect(decide(cs, base)?.id).toBe('lookup');
  });

  test('the confirmation applies every guard of decide()', () => {
    const c = cand('mtp', bench(1000, 140), 'kept');
    expect(confirm(c, bench(800, 141), base, bench(1000, 100))).toBe(false);
    expect(c.reason).toBe('not_confirmed:41');
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

describe('serveApi port fallback', () => {
  test('a taken port moves to the next free one and ready.endpoint follows', async () => {
    const home = mkdtempSync(join(tmpdir(), 'enigma-port-'));
    const prev = process.env.ENIGMA_HOME;
    process.env.ENIGMA_HOME = home;
    const blocker = Bun.serve({ hostname: '127.0.0.1', port: 0, fetch: () => new Response('omp') });
    const app = new App();
    const server = serveApi(app, blocker.port as number);
    try {
      expect(server.port).toBeGreaterThan(blocker.port as number);
      expect(app.apiPort).toBe(server.port as number);
      const r = await fetch(`http://127.0.0.1:${server.port}/api/state`);
      expect(((await r.json()) as { phase: string }).phase).toBe('license');
    } finally {
      server.stop(true);
      blocker.stop(true);
      if (prev === undefined) delete process.env.ENIGMA_HOME;
      else process.env.ENIGMA_HOME = prev;
      rmSync(home, { recursive: true, force: true });
    }
  });
});
