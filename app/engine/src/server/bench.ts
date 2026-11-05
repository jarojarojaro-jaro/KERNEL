// Benchmark protocol (CONTRACT.md "Benchmark"), one for the baseline and every candidate.
// The workload is rendered ONCE, on the baseline server (official chat template and tokenizer, with the reasoning
// effort the product serves): raw corpus tokens for prefill, chat prompts for decode and deep, all as token ids. Every
// arm gets exactly these tokens via /completion, so a candidate with its own template flags (reasoning effort, native
// chat, late system) decodes the same requests as the baseline. Per arm: start llama-server (ctx fits = ctxOk) →
// warm-up → per repetition: prefill ~4096 tokens, decode 256 greedy (T=0, seed 1; md5 of the texts) and 256 sampled
// (T=1, the speed that decides), deep ~32k document + question, 128 decode; a short wake-up request right before every
// timed one (GPU runtime power-down after idle) → median → graceful stop.
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import type { BenchResult, EngineConfig, Phase } from '../shared/types.ts';
import corpusText from '../../data/corpus.txt' with { type: 'text' };
import { serverCtx, startServer, type ResolvedEngine, type RunningServer } from './engine.ts';
import { errMsg, log } from './log.ts';
import { paths } from './paths.ts';

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

interface Timings {
  prompt_n: number; prompt_ms: number; prompt_per_second: number; predicted_n: number; predicted_per_second: number;
  draft_n?: number; draft_n_accepted?: number;
}
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

/**
 * Decode tasks: chat requests for a long ORIGINAL text (PL + EN), formatted by the model's chat template. A raw
 * continuation of the corpus (the old protocol) makes the model loop or copy the corpus, so n-gram lookup and MTP
 * accept nearly every draft. Every repetition and arm (greedy, sampled) gets its own pair: llama-server keeps the
 * n-gram cache across requests, so an identical second request replays the first answer from it (measured: 21 → 80
 * t/s on a 4060 Ti, 204/256 drafts accepted) — speed that no real conversation gets.
 */
export const DECODE_TASKS: readonly (readonly [string, string])[] = [
  ['Napisz oryginalne opowiadanie (ok. 600 słów) o latarniku z małej wyspy na Bałtyku, który pewnej zimowej nocy ' +
    'odbiera przez radio wiadomość od statku, którego nie ma w żadnym rejestrze. Pisz prozą, bez list i nagłówków.',
  'Write an original short story (about 600 words) about a clockmaker in a mountain village who discovers that one ' +
    'of her clocks runs exactly one day ahead. Write in prose, no lists or headings.'],
  ['Napisz oryginalne opowiadanie (ok. 600 słów) o pszczelarce z Podlasia, która znajduje w ulu list sprzed ' +
    'pięćdziesięciu lat zaadresowany do niej samej. Pisz prozą, bez list i nagłówków.',
  'Write an original short story (about 600 words) about a night-shift bus driver who notices the same silent ' +
    'passenger boarding at a stop that was demolished years ago. Write in prose, no lists or headings.'],
  ['Napisz oryginalne opowiadanie (ok. 600 słów) o młodym kartografie, który odkrywa, że jedna z jego map pokazuje ' +
    'ulicę, której jeszcze nie zbudowano. Pisz prozą, bez list i nagłówków.',
  'Write an original short story (about 600 words) about a retired astronaut who starts receiving postcards ' +
    'from a town on the far side of the Moon. Write in prose, no lists or headings.'],
  ['Napisz oryginalne opowiadanie (ok. 600 słów) o stroicielce fortepianów z Krakowa, która w starym instrumencie ' +
    'znajduje strunę grającą dźwięk, którego nie ma w żadnej skali. Pisz prozą, bez list i nagłówków.',
  'Write an original short story (about 600 words) about a ferry operator on a northern lake who keeps a logbook ' +
    'of every passenger and one morning finds an entry in his own handwriting for a crossing he does not remember. ' +
    'Write in prose, no lists or headings.'],
];

const DEEP_TASKS: readonly string[] = [
  'Na podstawie dokumentu napisz własnymi słowami oryginalny esej (ok. 400 słów): jakie trzy myśli z tego tekstu ' +
    'uważasz za najważniejsze i dlaczego. Nie cytuj dokumentu, pisz prozą.',
  'Based on the document, write an original essay (about 400 words) in your own words: what does the text say about ' +
    'patience and work, and do you agree? Do not quote the document; write in prose.',
  'Na podstawie dokumentu napisz własnymi słowami list (ok. 400 słów) do jednej z opisanych postaci, w którym ' +
    'opowiadasz jej, co zmieniło się w miasteczku. Nie cytuj dokumentu, pisz prozą.',
];

/** The deep task of repetition `rep`: the long corpus as a document plus a question that needs a fresh answer. */
export function deepQuestion(document: string, rep = 0): string {
  return 'Poniżej jest długi dokument. / Below is a long document.\n\n<dokument>\n' + document + '\n</dokument>\n\n' +
    (DEEP_TASKS[rep % DEEP_TASKS.length] as string);
}

/** Token budget reserved for the deep question and the chat template around the document. */
const DEEP_OVERHEAD = 256;

/** What a workload was rendered for; a different key (other model, engine, ctx, effort or plan) renders it again. */
export interface WorkloadKey { modelPath: string; engine: string; ctx: number; reasoningEffort: string | null; plan: BenchPlan }

/** The requests of the benchmark as token ids, rendered once on the baseline and sent unchanged to every arm. */
export interface BenchWorkload {
  key: WorkloadKey;
  /** the first 32 corpus tokens: warm-up and wake-up requests */
  warm: number[];
  prefill: number[];
  /** [repetition][task]: chat prompts of the greedy (md5) and the sampled decode arm, never the same task twice */
  greedy: number[][][];
  sampled: number[][][];
  /** [repetition]; empty when the baseline context cannot hold the deep document */
  deep: number[][];
}

export function workloadKey(engine: ResolvedEngine, cfg: EngineConfig, reasoningEffort: string | null, plan = benchPlan()): WorkloadKey {
  return { modelPath: cfg.modelPath, engine: `${engine.entry.id}@${engine.version}`, ctx: cfg.ctx, reasoningEffort, plan };
}

/** Persists the workload (resume measures candidates with the same tokens as the baseline). */
export function saveWorkload(w: BenchWorkload): void {
  writeFileSync(paths().workload, JSON.stringify(w));
}

/** The saved workload for `key`, or null (none, unreadable, or rendered for something else). */
export function loadWorkload(key: WorkloadKey): BenchWorkload | null {
  const file = paths().workload;
  if (!existsSync(file)) return null;
  try {
    const w = JSON.parse(readFileSync(file, 'utf8')) as BenchWorkload;
    return JSON.stringify(w.key) === JSON.stringify(key) ? w : null;
  } catch (e) {
    log.warn(`${file} unreadable: ${errMsg(e)}`);
    return null;
  }
}

/**
 * One user message rendered by the baseline's chat template (`/apply-template`, the reasoning effort as a template
 * kwarg like `--reasoning-effort`), tokenised the way /completion tokenises a string prompt (special tokens added and
 * parsed).
 */
export async function chatTokens(s: RunningServer, user: string, reasoningEffort: string | null, signal?: AbortSignal): Promise<number[]> {
  const { prompt } = await call<{ prompt: string }>(s, '/apply-template', {
    messages: [{ role: 'user', content: user }],
    ...(reasoningEffort ? { chat_template_kwargs: { reasoning_effort: reasoningEffort } } : {}),
  }, signal);
  if (typeof prompt !== 'string' || prompt.length === 0) throw new Error('/apply-template returned no prompt');
  const { tokens } = await call<{ tokens: number[] }>(s, '/tokenize', { content: prompt, add_special: true, parse_special: true }, signal);
  if (tokens.length === 0) throw new Error('tokenizer returned no tokens for a chat prompt');
  return tokens;
}

/** Renders the workload on the baseline server (`ctx` = its allocated context). */
export async function buildWorkload(s: RunningServer, ctx: number, key: WorkloadKey, signal?: AbortSignal): Promise<BenchWorkload> {
  const plan = key.plan;
  const deepFits = ctx >= plan.deepTokens + plan.deepDecode + 8;
  const prefillN = Math.min(plan.prefillTokens, ctx - 8);
  const all = await corpusTokens(s, Math.max(prefillN, 32, deepFits ? plan.deepTokens - DEEP_OVERHEAD : 0), signal);
  if (2 * plan.reps > DECODE_TASKS.length) {
    log.warn(`${plan.reps} repetitions need ${2 * plan.reps} task pairs, ${DECODE_TASKS.length} exist: later ones repeat a request (n-gram cache replay)`);
  }
  const chat = (user: string): Promise<number[]> => chatTokens(s, user, key.reasoningEffort, signal);
  const pair = async (i: number): Promise<number[][]> => {
    const out: number[][] = [];
    for (const task of DECODE_TASKS[i % DECODE_TASKS.length] as readonly string[]) out.push(await chat(task));
    return out;
  };
  const w: BenchWorkload = { key, warm: all.slice(0, 32), prefill: all.slice(0, prefillN), greedy: [], sampled: [], deep: [] };
  for (let r = 0; r < plan.reps; r++) {
    w.greedy.push(await pair(2 * r));
    w.sampled.push(await pair(2 * r + 1));
  }
  if (deepFits) {
    const { content: document } = await call<{ content: string }>(s, '/detokenize', { tokens: all.slice(0, plan.deepTokens - DEEP_OVERHEAD) }, signal);
    for (let r = 0; r < plan.reps; r++) w.deep.push(await chat(deepQuestion(document, r)));
  }
  return w;
}

/** Greedy and deterministic: the arm whose texts give outputMd5 (sameOutput). */
const GREEDY = { temperature: 0, seed: 1 } as const;
/**
 * The sampled arm: T=1 like a chat (speculative decoding accepts fewer drafts than at T=0); llama.cpp's default
 * top-k/top-p/min-p sent explicitly so that no arm's server defaults differ. Its speed is `decode.tps`.
 */
const sampled = (rep: number) => ({ temperature: 1, top_k: 40, top_p: 0.95, min_p: 0.05, seed: 1 + rep });

type Sampling = Record<string, number>;

/** One /completion on token ids; no ignore_eos: an early stop counts the tokens actually generated (timings.predicted_n). */
async function complete(s: RunningServer, prompt: number[], nPredict: number, sampling: Sampling, signal?: AbortSignal): Promise<CompletionResponse> {
  return call<CompletionResponse>(s, '/completion', {
    prompt, n_predict: nPredict, ...sampling, cache_prompt: false, stream: false,
  }, signal);
}

const median = (xs: number[]): number => {
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? (s[m] as number) : ((s[m - 1] as number) + (s[m] as number)) / 2;
};

/** "draft 412/530 accepted (78%)" when the server reports speculative decoding stats, else ''. */
function acceptance(ts: Timings[]): string {
  const n = ts.reduce((a, t) => a + (t.draft_n ?? 0), 0);
  if (n === 0) return '';
  const ok = ts.reduce((a, t) => a + (t.draft_n_accepted ?? 0), 0);
  return `draft ${ok}/${n} accepted (${((100 * ok) / n).toFixed(0)}%)`;
}

export interface BenchRun { prefill: BenchResult['prefill']; decode: BenchResult['decode']; deep?: BenchResult['deep']; outputMd5: string }

/** Runs the measurement part of the protocol on a started server (`ctx` = its allocated context). */
export async function measure(s: RunningServer, ctx: number, w: BenchWorkload, progress?: BenchProgress, signal?: AbortSignal): Promise<BenchRun> {
  const plan = w.key.plan;
  const reps = w.greedy.length;
  const wakeUp = w.warm.slice(0, 8);
  // a GPU with runtime power management (amdgpu BACO, `power/control=auto`) parks VRAM after a few idle seconds; the
  // short request right before every timed one makes sure the timed request never pays for the wake-up
  const timed = async (prompt: number[], nPredict: number, sampling: Sampling): Promise<CompletionResponse> => {
    await complete(s, wakeUp, 1, GREEDY, signal);
    return complete(s, prompt, nPredict, sampling, signal);
  };
  // warm-up: first graph allocation and kernel loading are not part of the numbers
  await complete(s, w.warm, 4, GREEDY, signal);
  const pre: Timings[] = [];
  const greedy: Timings[] = [];
  const dec: Timings[] = [];
  const h = createHash('md5'); // all greedy decode texts of all repetitions (the same tokens for baseline and candidates)
  for (let r = 0; r < reps; r++) {
    // prefill: the raw corpus (a fixed, exact token count), one token generated
    progress?.('bench:prefill', r, reps);
    pre.push((await timed(w.prefill, 1, GREEDY)).timings);
    // decode: this repetition's own chat tasks (never a request the server has already answered)
    progress?.('bench:decode', r, reps);
    for (const p of w.greedy[r] ?? []) {
      const res = await timed(p, plan.decodeTokens, GREEDY);
      greedy.push(res.timings);
      h.update(res.content);
    }
    for (const p of w.sampled[r] ?? []) dec.push((await timed(p, plan.decodeTokens, sampled(r))).timings);
    progress?.('bench:decode', r + 1, reps);
  }
  const short = [...greedy, ...dec].filter((t) => t.predicted_n < plan.decodeTokens);
  if (short.length) log.info(`decode: ${short.length}/${greedy.length + dec.length} answers stopped early (${short.map((t) => t.predicted_n).join(', ')} tokens)`);
  for (const [name, ts] of [['greedy', greedy], ['sampled', dec]] as const) {
    const acc = acceptance(ts);
    if (acc) log.info(`decode ${name} speculation: ${acc}`);
  }
  const run: BenchRun = {
    prefill: {
      tokens: pre[0]?.prompt_n ?? w.prefill.length,
      tps: median(pre.map((t) => t.prompt_per_second)),
      ttftS: median(pre.map((t) => t.prompt_ms / 1000)),
    },
    decode: {
      tokens: Math.round(median(dec.map((t) => t.predicted_n))),
      tps: median(dec.map((t) => t.predicted_per_second)),
      greedyTps: median(greedy.map((t) => t.predicted_per_second)),
    },
    outputMd5: h.digest('hex'),
  };
  const deepFits = w.deep.length > 0 && w.deep.every((p) => p.length + plan.deepDecode + 8 <= ctx);
  if (w.deep.length > 0 && !deepFits) log.warn(`deep: n_ctx ${ctx} cannot hold the ${w.deep[0]?.length}-token prompt, not measured`);
  if (deepFits) {
    const deep: Timings[] = [];
    for (let r = 0; r < w.deep.length; r++) {
      progress?.('bench:deep', r, w.deep.length);
      deep.push((await timed(w.deep[r] as number[], plan.deepDecode, GREEDY)).timings);
    }
    progress?.('bench:deep', w.deep.length, w.deep.length);
    const deepAcc = acceptance(deep);
    if (deepAcc) log.info(`deep speculation: ${deepAcc}`);
    run.deep = {
      ctxTokens: deep[0]?.prompt_n ?? w.deep[0]?.length ?? 0,
      prefillTps: median(deep.map((t) => t.prompt_per_second)),
      decodeTps: median(deep.map((t) => t.predicted_per_second)),
    };
  }
  return run;
}

export interface BenchOptions { progress?: BenchProgress; signal?: AbortSignal; label?: string; phase?: Phase }

/** Full protocol on one arm: start (ctx must fit), `prepare` the workload, measure it, graceful stop. */
async function run(
  engine: ResolvedEngine, cfg: EngineConfig, opts: BenchOptions,
  prepare: (s: RunningServer, nCtx: number) => Promise<BenchWorkload>,
): Promise<{ result: BenchResult; workload: BenchWorkload }> {
  opts.progress?.('bench:start', 0, 1);
  const s = await startServer(engine, cfg, { ...(opts.signal ? { signal: opts.signal } : {}), ...(opts.label ? { label: opts.label } : {}) });
  try {
    const nCtx = await serverCtx(s);
    const ctxOk = nCtx === null ? true : nCtx >= cfg.ctx;
    if (!ctxOk) log.warn(`server allocated n_ctx=${nCtx}, requested ${cfg.ctx}`);
    const workload = await prepare(s, nCtx ?? cfg.ctx);
    opts.progress?.('bench:start', 1, 1);
    const m = await measure(s, nCtx ?? cfg.ctx, workload, opts.progress, opts.signal);
    const result: BenchResult = {
      engine: { id: engine.entry.id, version: engine.version, backend: engine.entry.backend },
      config: cfg, prefill: m.prefill, decode: m.decode, ctxOk, outputMd5: m.outputMd5, at: Date.now(),
    };
    if (m.deep) result.deep = m.deep;
    log.info(`bench ${opts.label ?? engine.entry.id}: prefill ${m.prefill.tps.toFixed(1)} t/s, decode ${m.decode.tps.toFixed(1)} t/s ` +
      `(greedy ${m.decode.greedyTps.toFixed(1)})` +
      (m.deep ? `, deep ${m.deep.ctxTokens} tok: ${m.deep.prefillTps.toFixed(1)} / ${m.deep.decodeTps.toFixed(1)} t/s` : '') +
      `, md5 ${m.outputMd5.slice(0, 8)}`);
    return { result, workload };
  } finally {
    await s.stop();
  }
}

/** The baseline: renders the workload on its own server (`key`, see workloadKey), then measures it. */
export async function benchBaseline(engine: ResolvedEngine, cfg: EngineConfig, key: WorkloadKey, opts: BenchOptions = {}): Promise<{ result: BenchResult; workload: BenchWorkload }> {
  return run(engine, cfg, opts, async (s, nCtx) => {
    const w = await buildWorkload(s, nCtx, key, opts.signal);
    log.info(`bench workload rendered on ${opts.label ?? engine.entry.id}` +
      `${key.reasoningEffort ? ` (reasoning effort ${key.reasoningEffort})` : ''}: prefill ${w.prefill.length}, ` +
      `decode prompts ${[...w.greedy, ...w.sampled].flat().map((p) => p.length).join('/')}, deep ${w.deep.map((p) => p.length).join('/') || '-'} tokens`);
    return w;
  });
}

/** A candidate (or the baseline again): measures the baseline's workload, token for token. */
export async function benchEngine(engine: ResolvedEngine, cfg: EngineConfig, workload: BenchWorkload, opts: BenchOptions = {}): Promise<BenchResult> {
  return (await run(engine, cfg, opts, async () => workload)).result;
}
