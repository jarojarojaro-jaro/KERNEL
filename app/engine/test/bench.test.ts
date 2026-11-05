// Bench protocol against fake llama-servers: the workload is rendered once on the baseline (its template, its
// tokenizer, the served reasoning effort) and every arm gets exactly those tokens; prefill on the raw corpus, decode
// greedy (md5) + sampled (T=1, decides), deep on chat prompts, a wake-up request before every timed one.
import { afterAll, expect, test } from 'bun:test';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildWorkload, DECODE_TASKS, loadWorkload, measure, saveWorkload, type WorkloadKey } from '../src/server/bench.ts';
import type { RunningServer } from '../src/server/engine.ts';

interface Seen { path: string; body: Record<string, unknown> }

/** Tokens = code points, so a test can read a prompt back; `tag` makes each server's template (and tokens) its own. */
const enc = (s: string): number[] => [...s].map((c) => c.codePointAt(0) as number);
const dec = (t: number[]): string => String.fromCodePoint(...t);

function fakeServer(tag: string, decodeTps: number) {
  const seen: Seen[] = [];
  const template = (u: string, kw: Record<string, unknown>): string =>
    `<|${tag}|>${kw.reasoning_effort ? `[effort=${String(kw.reasoning_effort)}]` : ''}user\n${u}<|end|>\n<|assistant|>\n`;
  const srv = Bun.serve({
    port: 0,
    hostname: '127.0.0.1',
    async fetch(req) {
      const path = new URL(req.url).pathname;
      const body = (await req.json()) as Record<string, unknown>;
      seen.push({ path, body });
      if (path === '/tokenize') return Response.json({ tokens: enc(`${tag}:${body.content as string}`) });
      if (path === '/detokenize') return Response.json({ content: `DOC(${(body.tokens as number[]).length})`.padEnd((body.tokens as number[]).length, '.') });
      if (path === '/apply-template') {
        const msgs = body.messages as { role: string; content: string }[];
        const kw = (body.chat_template_kwargs ?? {}) as Record<string, unknown>;
        return Response.json({ prompt: msgs.map((m) => template(m.content, kw)).join('') });
      }
      if (path === '/completion') {
        const n = body.n_predict as number;
        const prompt = body.prompt as number[];
        const predicted = n > 100 ? n - 6 : n; // the model stops a bit early: real token count must be reported
        const tps = body.temperature === 1 ? decodeTps : decodeTps / 2; // greedy and sampled arms report apart
        return Response.json({
          content: `${tag}:${'x'.repeat(predicted)}`,
          timings: { prompt_n: prompt.length, prompt_ms: 100, prompt_per_second: 1000, predicted_n: predicted, predicted_per_second: tps },
        });
      }
      return new Response('not found', { status: 404 });
    },
  });
  return { srv, seen, server: { url: `http://127.0.0.1:${srv.port}`, apiKey: 'k' } as RunningServer };
}

const base = fakeServer('base', 50);
const cand = fakeServer('cand', 80);
const home = mkdtempSync(join(tmpdir(), 'enigma-bench-'));
const prevHome = process.env.ENIGMA_HOME;
process.env.ENIGMA_HOME = home;
afterAll(() => {
  base.srv.stop(true);
  cand.srv.stop(true);
  if (prevHome === undefined) delete process.env.ENIGMA_HOME;
  else process.env.ENIGMA_HOME = prevHome;
  rmSync(home, { recursive: true, force: true });
});

const plan = { prefillTokens: 512, decodeTokens: 256, deepTokens: 4096, deepDecode: 128, reps: 2 };
const key: WorkloadKey = { modelPath: '/m/q.gguf', engine: 'upstream@b1', ctx: 8192, reasoningEffort: 'low', plan };
const completions = (seen: Seen[]) => seen.filter((c) => c.path === '/completion');
const timedOnly = (seen: Seen[]) => {
  // every timed request follows a wake-up (8 tokens, 1 predicted); the first request is the warm-up (32/4)
  const cs = completions(seen).slice(1);
  const out: Seen[] = [];
  for (let i = 0; i < cs.length; i += 2) {
    expect((cs[i]?.body.prompt as number[]).length).toBe(8);
    expect(cs[i]?.body.n_predict).toBe(1);
    out.push(cs[i + 1] as Seen);
  }
  return out;
};

test('the workload is rendered on the baseline with the served reasoning effort; every arm gets the same tokens', async () => {
  const w = await buildWorkload(base.server, 8192, key);
  for (const c of base.seen.filter((x) => x.path === '/apply-template')) {
    expect(c.body.chat_template_kwargs).toEqual({ reasoning_effort: 'low' });
  }
  // chat prompts are tokenised as /completion would tokenise the string
  for (const c of base.seen.filter((x) => x.path === '/tokenize' && x.body.add_special === true)) expect(c.body.parse_special).toBe(true);
  expect(w.prefill).toHaveLength(512);
  expect(w.greedy).toHaveLength(2);
  expect(w.sampled).toHaveLength(2);
  const prompts = [...w.greedy, ...w.sampled].flat().map(dec);
  expect(prompts).toHaveLength(8);
  expect(new Set(prompts).size).toBe(8); // the n-gram cache survives requests: never the same task twice
  const tasks = DECODE_TASKS.flat();
  for (const p of prompts) {
    expect(p).toStartWith('base:<|base|>[effort=low]user\n');
    expect(tasks.some((t) => p.includes(`user\n${t}<|end|>`))).toBe(true);
  }
  expect(w.deep).toHaveLength(2);
  expect(dec(w.deep[0] as number[])).toContain(`DOC(${4096 - 256})`);
  expect(w.deep[0]).not.toEqual(w.deep[1]);

  const b = await measure(base.server, 8192, w);
  const before = cand.seen.length;
  const c = await measure(cand.server, 8192, w);
  // the candidate renders and tokenises nothing itself: its own template flags cannot change the requests
  expect(cand.seen.slice(before).every((x) => x.path === '/completion')).toBe(true);
  const tb = timedOnly(base.seen);
  const tc = timedOnly(cand.seen.slice(before));
  expect(tc.map((x) => x.body)).toEqual(tb.map((x) => x.body));
  for (const x of tc) expect(Array.isArray(x.body.prompt)).toBe(true);

  const greedy = tc.filter((x) => x.body.n_predict === 256 && x.body.temperature === 0);
  const sampled = tc.filter((x) => x.body.n_predict === 256 && x.body.temperature === 1);
  expect(greedy.map((x) => x.body.prompt)).toEqual(w.greedy.flat());
  expect(sampled.map((x) => x.body.prompt)).toEqual(w.sampled.flat());
  for (const x of greedy) expect(x.body.seed).toBe(1);
  expect(sampled.map((x) => x.body.seed)).toEqual([1, 1, 2, 2]);
  for (const x of sampled) expect([x.body.top_k, x.body.top_p, x.body.min_p]).toEqual([40, 0.95, 0.05]);
  expect(tc.filter((x) => x.body.n_predict === 1).map((x) => x.body.prompt)).toEqual([w.prefill, w.prefill]);
  expect(tc.filter((x) => x.body.n_predict === 128).map((x) => x.body.prompt)).toEqual(w.deep);
  for (const x of completions(cand.seen)) {
    expect(x.body.ignore_eos).toBeUndefined();
    expect(x.body.cache_prompt).toBe(false);
  }

  expect(b.decode.tps).toBe(50); // the sampled arm decides
  expect(b.decode.greedyTps).toBe(25);
  expect(c.decode.tps).toBe(80);
  expect(c.decode.tokens).toBe(250); // actual tokens, not n_predict
  expect(c.prefill.tokens).toBe(512);
  expect(c.deep?.decodeTps).toBe(40);
  expect(b.outputMd5).not.toBe(c.outputMd5); // md5 of the greedy texts
});

test('a deep prompt that does not fit the arm context is skipped, not truncated', async () => {
  const w = await buildWorkload(base.server, 8192, key);
  const run = await measure(cand.server, 2048, w);
  expect(run.deep).toBeUndefined();
});

test('the saved workload is reused only for the same key', async () => {
  const w = await buildWorkload(base.server, 8192, key);
  saveWorkload(w);
  expect(loadWorkload(key)?.greedy).toEqual(w.greedy);
  expect(loadWorkload({ ...key, reasoningEffort: null })).toBeNull();
  expect(loadWorkload({ ...key, plan: { ...plan, reps: 3 } })).toBeNull();
});
