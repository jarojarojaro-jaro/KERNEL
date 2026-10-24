// Bench protocol against a fake llama-server: prefill on the raw corpus, decode and deep on chat-formatted prompts.
import { afterAll, expect, test } from 'bun:test';
import { DECODE_TASKS, measure } from '../src/server/bench.ts';
import type { RunningServer } from '../src/server/engine.ts';

interface Seen { prompt: unknown; body: Record<string, unknown> }
const seen: Seen[] = [];
const TEMPLATE = (u: string): string => `<|im_start|>user\n${u}<|im_end|>\n<|im_start|>assistant\n`;

const fake = Bun.serve({
  port: 0,
  hostname: '127.0.0.1',
  async fetch(req) {
    const path = new URL(req.url).pathname;
    const body = (await req.json()) as Record<string, unknown>;
    if (path === '/tokenize') return Response.json({ tokens: Array.from({ length: 1000 }, (_, i) => i + 1) });
    if (path === '/detokenize') return Response.json({ content: `DOC(${(body.tokens as number[]).length})` });
    if (path === '/apply-template') {
      const msgs = body.messages as { role: string; content: string }[];
      return Response.json({ prompt: msgs.map((m) => TEMPLATE(m.content)).join('') });
    }
    if (path === '/completion') {
      seen.push({ prompt: body.prompt, body });
      const n = body.n_predict as number;
      const promptN = Array.isArray(body.prompt) ? body.prompt.length : 5000;
      const predicted = n > 100 ? n - 6 : n; // the model stops a bit early: real token count must be reported
      return Response.json({
        content: 'x'.repeat(predicted),
        timings: { prompt_n: promptN, prompt_ms: 100, prompt_per_second: 1000, predicted_n: predicted, predicted_per_second: 50 },
      });
    }
    return new Response('not found', { status: 404 });
  },
});
afterAll(() => fake.stop(true));

const server = { url: `http://127.0.0.1:${fake.port}`, apiKey: 'k' } as RunningServer;

test('decode and deep prompts are chat-formatted, prefill is the raw corpus, no ignore_eos', async () => {
  const plan = { prefillTokens: 512, decodeTokens: 256, deepTokens: 4096, deepDecode: 128, reps: 2 };
  const run = await measure(server, 8192, plan);
  const calls = seen.filter((c) => c.body.n_predict !== 4); // drop the warm-up
  const prefill = calls.filter((c) => c.body.n_predict === 1);
  const decode = calls.filter((c) => c.body.n_predict === 256);
  const deep = calls.filter((c) => c.body.n_predict === 128);
  expect(prefill).toHaveLength(2);
  for (const c of prefill) expect(Array.isArray(c.prompt) && c.prompt.length === 512).toBe(true);
  expect(decode).toHaveLength(2 * DECODE_TASKS.length);
  for (const c of decode) {
    expect(typeof c.prompt).toBe('string');
    expect(c.prompt as string).toStartWith('<|im_start|>user\n');
    expect(DECODE_TASKS.some((t) => c.prompt === TEMPLATE(t))).toBe(true);
  }
  expect(deep).toHaveLength(2);
  for (const c of deep) {
    expect(c.prompt as string).toStartWith('<|im_start|>user\n');
    expect(c.prompt as string).toContain(`DOC(${4096 - 256})`);
  }
  for (const c of seen) {
    expect(c.body.ignore_eos).toBeUndefined();
    expect(c.body.temperature).toBe(0);
    expect(c.body.seed).toBe(1);
    expect(c.body.cache_prompt).toBe(false);
  }
  expect(run.decode.tokens).toBe(250); // actual tokens, not n_predict
  expect(run.prefill.tokens).toBe(512);
  expect(run.deep?.decodeTps).toBe(50);
});
