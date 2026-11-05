// Optimisation: candidates (CONTRACT.md "Optymalizacja"), each measured with the same benchmark (the same request
// tokens) as the baseline. Kept: the fastest decode within the guards of decide() (prefill and long-context loss, the
// noise threshold, minimum gain for text changes), confirmed by a second measurement of the winner against the baseline
// measured again. sameOutput = greedy decode md5 equals the baseline's.
import type { BenchResult, Candidate, EngineConfig, Hw, Option } from '../shared/types.ts';
import { benchEngine, type BenchProgress, type BenchWorkload } from './bench.ts';
import { replan } from './catalog/index.ts';
import { enigmaConfig, enigmaEngineFor, ensureEngine, type ResolvedEngine } from './engine.ts';
import { errMsg, log } from './log.ts';

export const PREFILL_LOSS_MAX = 0.05;
/** Prefill loss allowed when decode gains at least BIG_DECODE_GAIN. */
export const PREFILL_LOSS_MAX_BIG = 0.15;
export const BIG_DECODE_GAIN = 0.2;
/** Minimum decode gain for a candidate whose output text differs from the baseline. */
export const MIN_GAIN_TEXT_CHANGE = 0.03;
/** Decode gains up to this are noise; the confirmation raises it to 2 × the baseline's run-to-run change. */
export const NOISE_FLOOR = 0.02;
/** Decode at the deep (~32k) context may drop at most this much; deep prefill follows the prefill rule. */
export const DEEP_DECODE_LOSS_MAX = 0.05;
const UB_STEPS = [512, 1024, 2048] as const;

/** How a candidate's config is built; kept out of the persisted Candidate (rebuilt from the id on resume). */
type Recipe =
  | { kind: 'enigma' }
  | { kind: 'ub'; ub: number }
  | { kind: 'spec'; spec: 'mtp' | 'lookup' };

export interface PlannedCandidate { candidate: Candidate; recipe: Recipe | null }

/** The candidate list for this machine/option. Candidates that cannot run here are listed as rejected with the reason. */
export function planCandidates(hw: Hw, option: Option, base: ResolvedEngine): PlannedCandidate[] {
  const out: PlannedCandidate[] = [];
  const enigma = enigmaEngineFor(hw, option);
  out.push({
    candidate: {
      id: 'enigma',
      label: { pl: 'Silnik Enigma', en: 'Enigma engine' },
      desc: {
        pl: 'Nasza zoptymalizowana kompilacja llama.cpp z ustawieniami dobranymi pod ten model i kartę.',
        en: 'Our optimised llama.cpp build with settings tuned for this model and GPU.',
      },
      status: enigma.entry ? 'pending' : 'rejected',
      ...(enigma.entry ? {} : { reason: enigma.code }),
    },
    recipe: enigma.entry ? { kind: 'enigma' } : null,
  });
  for (const ub of UB_STEPS) {
    if (ub === option.ub) continue;
    const fits = replan(option, hw, { ub }).fits;
    out.push({
      candidate: {
        id: `ub-${ub}`,
        label: { pl: `Mikro-batch ${ub}`, en: `Micro-batch ${ub}` },
        desc: {
          pl: `Prompt przetwarzany po ${ub} tokenów na krok (-ub ${ub} -b ${Math.max(2048, ub)}).`,
          en: `The prompt is processed ${ub} tokens per step (-ub ${ub} -b ${Math.max(2048, ub)}).`,
        },
        status: fits ? 'pending' : 'rejected',
        ...(fits ? {} : { reason: `ub_no_fit:${ub}` }),
      },
      recipe: fits ? { kind: 'ub', ub } : null,
    });
  }
  const hasMtp = option.features.includes('mtp');
  const engineMtp = base.entry.features.includes('mtp');
  out.push({
    candidate: {
      id: 'mtp',
      label: { pl: 'MTP (głowica wielotokenowa)', en: 'MTP (multi-token prediction)' },
      desc: {
        pl: 'Model sam podpowiada kolejne tokeny swoją głowicą MTP; serwer weryfikuje je w jednym kroku.',
        en: "The model drafts the next tokens with its own MTP head; the server verifies them in one step.",
      },
      status: hasMtp && engineMtp ? 'pending' : 'rejected',
      ...(hasMtp && engineMtp ? {} : {
        // the catalog drops 'mtp' from features when the head exists but its draft context does not fit (why code)
        reason: hasMtp ? 'engine_no_mtp' : option.why.includes('mtp_no_memory') ? 'mtp_no_memory' : 'no_mtp_head',
      }),
    },
    recipe: hasMtp && engineMtp ? { kind: 'spec', spec: 'mtp' } : null,
  });
  const engineLookup = base.entry.features.includes('lookup');
  out.push({
    candidate: {
      id: 'lookup',
      label: { pl: 'Lookup n-gram', en: 'N-gram lookup' },
      desc: {
        pl: 'Szkice z powtórzeń w kontekście (bez dodatkowego modelu); pomaga przy kodzie i cytowaniu.',
        en: 'Drafts from repetitions in the context (no extra model); helps with code and quoting.',
      },
      status: engineLookup ? 'pending' : 'rejected',
      ...(engineLookup ? {} : { reason: 'engine_no_lookup' }),
    },
    recipe: engineLookup ? { kind: 'spec', spec: 'lookup' } : null,
  });
  return out;
}

/** Rebuilds recipes for persisted candidates (resume after restart). */
export function recipeFor(id: string): Recipe | null {
  if (id === 'enigma') return { kind: 'enigma' };
  if (id === 'mtp' || id === 'lookup') return { kind: 'spec', spec: id };
  const m = /^ub-(\d+)$/.exec(id);
  return m ? { kind: 'ub', ub: Number(m[1]) } : null;
}

function specArgs(spec: 'mtp' | 'lookup'): string[] {
  // upstream llama.cpp: MTP head drafting; n-gram drafting with the server's recommended settings (--spec-default)
  return spec === 'mtp' ? ['--spec-type', 'draft-mtp', '--spec-draft-n-max', '4'] : ['--spec-default'];
}

export interface OptimizeContext {
  hw: Hw;
  option: Option;
  modelPath: string;
  base: ResolvedEngine;
  baseConfig: EngineConfig;
  baseline: BenchResult;
  /** the requests the baseline was measured with; every candidate (and the confirmation) gets the same tokens */
  workload: BenchWorkload;
  candidates: Candidate[];
  /** called after every candidate change (persist + broadcast) */
  update(candidates: Candidate[]): void;
  progress?: BenchProgress;
  signal?: AbortSignal;
}

export interface OptimizeResult { best: BenchResult; bestCandidateId: string | null; candidates: Candidate[] }

function pct(now: number, base: number): number {
  return base > 0 ? Math.round(((now / base - 1) * 100) * 10) / 10 : 0;
}

async function configFor(ctx: OptimizeContext, recipe: Recipe): Promise<{ engine: ResolvedEngine; config: EngineConfig }> {
  if (recipe.kind === 'enigma') {
    const choice = enigmaEngineFor(ctx.hw, ctx.option);
    if (!choice.entry) throw new Error(choice.reason);
    const engine = await ensureEngine(choice.entry, ctx.signal ? { signal: ctx.signal } : {});
    const r = enigmaConfig(engine, ctx.option, ctx.modelPath);
    if (!r.config) throw new Error(r.reason);
    return { engine, config: r.config };
  }
  if (recipe.kind === 'ub') {
    return { engine: ctx.base, config: { ...ctx.baseConfig, ub: recipe.ub, b: Math.max(2048, recipe.ub) } };
  }
  return {
    engine: ctx.base,
    config: { ...ctx.baseConfig, spec: recipe.spec, extraArgs: [...ctx.baseConfig.extraArgs, ...specArgs(recipe.spec)] },
  };
}

/** Measures every pending candidate, then picks the winner. Already measured candidates (resume) are kept as they are. */
export async function optimize(ctx: OptimizeContext): Promise<OptimizeResult> {
  const cands = ctx.candidates.map((c) => ({ ...c }));
  const base = ctx.baseline;
  for (const c of cands) {
    if ((c.status === 'rejected' && c.result === undefined) || c.status === 'failed') continue;
    if (c.result !== undefined && c.status !== 'running') continue;
    const recipe = recipeFor(c.id);
    if (!recipe) continue;
    if (ctx.signal?.aborted) throw new Error('cancelled');
    c.status = 'running';
    delete c.reason;
    ctx.update(cands);
    try {
      const { engine, config } = await configFor(ctx, recipe);
      const result = await benchEngine(engine, config, ctx.workload, {
        label: `candidate ${c.id}`, ...(ctx.progress ? { progress: ctx.progress } : {}), ...(ctx.signal ? { signal: ctx.signal } : {}),
      });
      c.result = result;
      c.decodePct = pct(result.decode.tps, base.decode.tps);
      c.prefillPct = pct(result.prefill.tps, base.prefill.tps);
      c.sameOutput = result.outputMd5 === base.outputMd5;
      c.status = 'pending'; // decided below, once every candidate is measured
    } catch (e) {
      if (ctx.signal?.aborted) {
        c.status = 'pending';
        ctx.update(cands);
        throw e;
      }
      c.status = 'failed';
      c.reason = failureCode(errMsg(e));
      log.warn(`candidate ${c.id} failed: ${errMsg(e)}`);
    }
    ctx.update(cands);
  }

  // the winner of one pass is the maximum of several noisy numbers: measure it again, next to a new baseline run
  let best = decide(cands, base);
  let baseAgain: BenchResult | null = null;
  while (best) {
    if (ctx.signal?.aborted) throw new Error('cancelled');
    const winner = best;
    winner.status = 'running';
    ctx.update(cands);
    const opts = { ...(ctx.progress ? { progress: ctx.progress } : {}), ...(ctx.signal ? { signal: ctx.signal } : {}) };
    baseAgain ??= await benchEngine(ctx.base, ctx.baseConfig, ctx.workload, { label: 'baseline (confirmation)', ...opts });
    try {
      const recipe = recipeFor(winner.id);
      if (!recipe) throw new Error(`no recipe for ${winner.id}`);
      const { engine, config } = await configFor(ctx, recipe);
      const again = await benchEngine(engine, config, ctx.workload, { label: `candidate ${winner.id} (confirmation)`, ...opts });
      if (confirm(winner, again, base, baseAgain)) break;
    } catch (e) {
      if (ctx.signal?.aborted) {
        winner.status = 'pending';
        ctx.update(cands);
        throw e;
      }
      winner.status = 'failed';
      winner.reason = failureCode(errMsg(e));
      log.warn(`candidate ${winner.id} confirmation failed: ${errMsg(e)}`);
    }
    best = decide(cands, base);
  }
  ctx.update(cands);
  const bestResult = best?.result ?? base;
  log.info(best
    ? `optimize: kept ${best.id}: decode ${(baseAgain ?? base).decode.tps.toFixed(1)} → ${bestResult.decode.tps.toFixed(1)} t/s (${best.decodePct}%, confirmed), prefill ${best.prefillPct}%, same output: ${best.sameOutput}`
    : 'optimize: no candidate beat the baseline; keeping the baseline configuration');
  return { best: bestResult, bestCandidateId: best?.id ?? null, candidates: cands };
}

/**
 * Second measurement of the winner `c` (`again`) against the baseline measured again (`baseAgain`). The decode
 * threshold becomes max(2 × noise, NOISE_FLOOR), noise = how far the baseline moved between its two runs; the other
 * guards of decide() apply unchanged. Confirmed: `c` is kept with the confirmation numbers (result, percentages and
 * sameOutput against `baseAgain`). Not confirmed: rejected with `not_confirmed:<decode pct of the confirmation>`,
 * which decide() keeps from then on.
 */
export function confirm(c: Candidate, again: BenchResult, base: BenchResult, baseAgain: BenchResult): boolean {
  const noise = Math.abs(baseAgain.decode.tps / base.decode.tps - 1);
  const minGain = Math.max(2 * noise, NOISE_FLOOR);
  const probe: Candidate = { ...c, result: again, status: 'pending' };
  delete probe.reason;
  const ok = decide([probe], baseAgain, minGain) === probe;
  const decodePct = pct(again.decode.tps, baseAgain.decode.tps);
  log.info(`optimize: confirmation of ${c.id}: baseline ${base.decode.tps.toFixed(1)} → ${baseAgain.decode.tps.toFixed(1)} t/s ` +
    `(noise ${(noise * 100).toFixed(1)}%, threshold ${(minGain * 100).toFixed(1)}%), ${c.id} ${again.decode.tps.toFixed(1)} t/s ` +
    `(${decodePct}%): ${ok ? 'confirmed' : `not confirmed (${probe.reason})`}`);
  if (!ok) {
    c.status = 'rejected';
    c.reason = `not_confirmed:${decodePct}`;
    return false;
  }
  c.result = again;
  c.decodePct = decodePct;
  c.prefillPct = pct(again.prefill.tps, baseAgain.prefill.tps);
  c.sameOutput = again.outputMd5 === baseAgain.outputMd5;
  c.status = 'kept';
  delete c.reason;
  return true;
}

/**
 * Marks every measured candidate kept/rejected (in place) and returns the winner: the fastest decode among candidates
 * whose context fit and whose decode beats the baseline by more than `minGain` (noise; NOISE_FLOOR before the
 * confirmation), under these guards:
 *  - prefill may drop at most 5%, or at most 15% when decode gains ≥ 20% (decode is what users feel on every reply;
 *    prefill only moves the first-token wait — 2026-10-24: MTP on the 3090 gave decode +40.5%, deep +102%, prefill −11%);
 *    the deep (~32k) prefill follows the same rule and the deep decode may drop at most 5%;
 *  - a candidate that changes the output text (sameOutput false) must gain at least 3% decode (no text change for noise).
 * A candidate whose confirmation failed (`not_confirmed`) stays rejected. Null = keep the baseline.
 */
export function decide(cands: Candidate[], base: BenchResult, minGain = NOISE_FLOOR): Candidate | null {
  let best: Candidate | null = null;
  for (const c of cands) {
    if (!c.result || c.status === 'failed') continue;
    c.status = 'rejected';
    if (c.reason?.startsWith('not_confirmed:')) continue;
    const gain = c.result.decode.tps / base.decode.tps - 1;
    const prefillLoss = gain >= BIG_DECODE_GAIN ? PREFILL_LOSS_MAX_BIG : PREFILL_LOSS_MAX;
    const changesText = c.result.outputMd5 !== base.outputMd5;
    const deep = base.deep && c.result.deep ? { base: base.deep, now: c.result.deep } : null;
    if (!c.result.ctxOk) c.reason = 'ctx_not_fit';
    else if (c.result.prefill.tps < base.prefill.tps * (1 - prefillLoss)) c.reason = `prefill_loss:${pct(c.result.prefill.tps, base.prefill.tps)}`;
    else if (deep && deep.now.prefillTps < deep.base.prefillTps * (1 - prefillLoss)) {
      c.reason = `deep_prefill_loss:${pct(deep.now.prefillTps, deep.base.prefillTps)}`;
    } else if (deep && deep.now.decodeTps < deep.base.decodeTps * (1 - DEEP_DECODE_LOSS_MAX)) {
      c.reason = `deep_decode_loss:${pct(deep.now.decodeTps, deep.base.decodeTps)}`;
    } else if (gain <= 0) c.reason = `decode_not_faster:${pct(c.result.decode.tps, base.decode.tps)}`;
    else if (gain <= minGain) c.reason = `within_noise:${pct(c.result.decode.tps, base.decode.tps)}`;
    else if (changesText && gain < MIN_GAIN_TEXT_CHANGE) c.reason = `gain_too_small:${pct(c.result.decode.tps, base.decode.tps)}`;
    else {
      delete c.reason;
      if (!best || c.result.decode.tps > (best.result?.decode.tps ?? 0)) best = c;
    }
  }
  for (const c of cands) {
    if (c === best) c.status = 'kept';
    else if (c.result && c.status === 'rejected' && c.reason === undefined) c.reason = `slower_than:${best?.id ?? ''}`;
  }
  return best;
}

/** Failure -> reason code: `oom`, `start_failed:<first line>` (server did not come up) or `failed:<first line>`. */
export function failureCode(msg: string): string {
  if (/out of memory|failed to allocate|ErrorOutOfDeviceMemory|cudaMalloc failed|hipErrorOutOfMemory/i.test(msg)) return 'oom';
  const first = msg.split('\n')[0] ?? '';
  return /^llama-server (exited|not healthy)/.test(first) ? `start_failed:${first}` : `failed:${first}`;
}
