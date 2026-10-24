// Benchmark protocol (CONTRACT.md "Benchmark"), one for the baseline and every candidate:
// start llama-server (ctx fits = ctxOk) → warm-up → prefill ~4096 tokens + decode 256 greedy (seed 1, md5 of the text)
// → deep ~32k tokens + 128 decode → 2 repetitions, median → graceful stop.
import { createHash } from 'node:crypto';
import type { BenchResult, EngineConfig, Phase } from '../shared/types.ts';
import corpusText from '../../data/corpus.txt' with { type: 'text' };
import { serverCtx, startServer, type ResolvedEngine, type RunningServer } from './engine.ts';
import { log } from './log.ts';

export interface BenchPlan { prefillTokens: number; decodeTokens: number; deepTokens: number; deepDecode: number; reps: number }

function envInt(name: string, dflt: number): number {
  const v = Number(process.env[name]);
  return Number.isInteger(v) && v > 0 ? v : dflt;
}

/** The contract protocol; ENIGMA_BENCH_{PREFILL,DECODE,DEEP,REPS} override sizes (slow CPU dev machines). */
export function benchPlan(): BenchPlan {
  return {
    prefillTokens: envInt('ENIGMA_BENCH_PREFILL', 4096),
    decodeTokens: envInt('ENIGMA_BENCH_DECODE', 256),
    deepTokens: envInt('ENIGMA_BENCH_DEEP', 32768),
    deepDecode: 128,
    reps: envInt('ENIGMA_BENCH_REPS', 2),
  };
}

export type BenchProgress = (label: string, done: number, total: number) => void;

interface Timings { prompt_n: number; prompt_ms: number; prompt_per_second: number; predicted_n: number; predicted_per_second: number }
interface CompletionResponse { content: string; timings: Timings; tokens_predicted?: number }

async function call<T>(s: RunningServer, path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const r = await fetch(`${s.url}${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${s.apiKey}` },
    body: JSON.stringify(body),
    ...(signal ? { signal } : {}),
  });
  if (!r.ok) throw new Error(`${path} HTTP ${r.status}: ${(await r.text()).slice(0, 300)}`);
  return (await r.json()) as T;
}

/** Exactly `n` tokens of the corpus (repeated if the corpus is shorter), tokenised by the server itself. */
export async function corpusTokens(s: RunningServer, n: number, signal?: AbortSignal): Promise<number[]> {
  const { tokens } = await call<{ tokens: number[] }>(s, '/tokenize', { content: corpusText, add_special: false }, signal);
  if (tokens.length === 0) throw new Error('tokenizer returned no tokens');
  const out: number[] = [];
  while (out.length < n) out.push(...tokens.slice(0, n - out.length));
  return out;
}

async function complete(s: RunningServer, prompt: number[], nPredict: number, signal?: AbortSignal): Promise<CompletionResponse> {
  return call<CompletionResponse>(s, '/completion', {
    prompt, n_predict: nPredict, temperature: 0, seed: 1, cache_prompt: false, ignore_eos: true, stream: false,
  }, signal);
}

const median = (xs: number[]): number => {
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? (s[m] as number) : ((s[m - 1] as number) + (s[m] as number)) / 2;
};

export interface BenchRun { prefill: BenchResult['prefill']; decode: BenchResult['decode']; deep?: BenchResult['deep']; outputMd5: string }

/** Runs the measurement part of the protocol on a started server. */
export async function measure(s: RunningServer, ctx: number, plan: BenchPlan, progress?: BenchProgress, signal?: AbortSignal): Promise<BenchRun> {
  const deepFits = ctx >= plan.deepTokens + plan.deepDecode + 8;
  const prefillN = Math.min(plan.prefillTokens, ctx - plan.decodeTokens - 8);
  const all = await corpusTokens(s, Math.max(prefillN, deepFits ? plan.deepTokens : 0), signal);
  // warm-up: first graph allocation and kernel loading are not part of the numbers
  await complete(s, all.slice(0, 32), 4, signal);
  const pre: Timings[] = [];
  const md5s: string[] = [];
  for (let r = 0; r < plan.reps; r++) {
    progress?.('bench:prefill', r, plan.reps);
    const res = await complete(s, all.slice(0, prefillN), plan.decodeTokens, signal);
    pre.push(res.timings);
    md5s.push(createHash('md5').update(res.content).digest('hex'));
    progress?.('bench:decode', r + 1, plan.reps);
  }
  if (new Set(md5s).size > 1) log.warn(`decode text differs between repetitions (${md5s.join(', ')}): the engine is not deterministic here`);
  const run: BenchRun = {
    prefill: {
      tokens: pre[0]?.prompt_n ?? prefillN,
      tps: median(pre.map((t) => t.prompt_per_second)),
      ttftS: median(pre.map((t) => t.prompt_ms / 1000)),
    },
    decode: { tokens: pre[0]?.predicted_n ?? plan.decodeTokens, tps: median(pre.map((t) => t.predicted_per_second)) },
    outputMd5: md5s[0] ?? '',
  };
  if (deepFits) {
    const deep: Timings[] = [];
    for (let r = 0; r < plan.reps; r++) {
      progress?.('bench:deep', r, plan.reps);
      deep.push((await complete(s, all.slice(0, plan.deepTokens), plan.deepDecode, signal)).timings);
    }
    progress?.('bench:deep', plan.reps, plan.reps);
    run.deep = {
      ctxTokens: deep[0]?.prompt_n ?? plan.deepTokens,
      prefillTps: median(deep.map((t) => t.prompt_per_second)),
      decodeTps: median(deep.map((t) => t.predicted_per_second)),
    };
  }
  return run;
}

export interface BenchOptions { plan?: BenchPlan; progress?: BenchProgress; signal?: AbortSignal; label?: string; phase?: Phase }

/** Full protocol: start (ctx must fit), measure, graceful stop. */
export async function benchEngine(engine: ResolvedEngine, cfg: EngineConfig, opts: BenchOptions = {}): Promise<BenchResult> {
  const plan = opts.plan ?? benchPlan();
  opts.progress?.('bench:start', 0, 1);
  const s = await startServer(engine, cfg, { ...(opts.signal ? { signal: opts.signal } : {}), ...(opts.label ? { label: opts.label } : {}) });
  try {
    const nCtx = await serverCtx(s);
    const ctxOk = nCtx === null ? true : nCtx >= cfg.ctx;
    if (!ctxOk) log.warn(`server allocated n_ctx=${nCtx}, requested ${cfg.ctx}`);
    opts.progress?.('bench:start', 1, 1);
    const run = await measure(s, nCtx ?? cfg.ctx, plan, opts.progress, opts.signal);
    const result: BenchResult = {
      engine: { id: engine.entry.id, version: engine.version, backend: engine.entry.backend },
      config: cfg, prefill: run.prefill, decode: run.decode, ctxOk, outputMd5: run.outputMd5, at: Date.now(),
    };
    if (run.deep) result.deep = run.deep;
    log.info(`bench ${opts.label ?? engine.entry.id}: prefill ${run.prefill.tps.toFixed(1)} t/s, decode ${run.decode.tps.toFixed(1)} t/s` +
      (run.deep ? `, deep ${run.deep.ctxTokens} tok: ${run.deep.prefillTps.toFixed(1)} / ${run.deep.decodeTps.toFixed(1)} t/s` : '') +
      `, md5 ${run.outputMd5.slice(0, 8)}`);
    return result;
  } finally {
    await s.stop();
  }
}
