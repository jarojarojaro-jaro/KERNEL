// Optimisation: candidates (CONTRACT.md "Optymalizacja"), each measured with the same benchmark as the baseline.
// Kept: the best decode whose prefill is at most 5% below the baseline. sameOutput = decode md5 equals the baseline's.
import type { BenchResult, Candidate, EngineConfig, Hw, Option } from '../shared/types.ts';
import { benchEngine, type BenchProgress } from './bench.ts';
import { replan } from './catalog/index.ts';
import { enigmaConfig, enigmaEngineFor, ensureEngine, type ResolvedEngine } from './engine.ts';
import { errMsg, log } from './log.ts';

export const PREFILL_LOSS_MAX = 0.05;
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
      ...(hasMtp && engineMtp ? {} : { reason: hasMtp ? 'engine_no_mtp' : 'no_mtp_head' }),
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
      const result = await benchEngine(engine, config, {
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

  const best = decide(cands, base);
  ctx.update(cands);
  const bestResult = best?.result ?? base;
  log.info(best
    ? `optimize: kept ${best.id}: decode ${base.decode.tps.toFixed(1)} → ${bestResult.decode.tps.toFixed(1)} t/s (${best.decodePct}%), prefill ${best.prefillPct}%, same output: ${best.sameOutput}`
    : 'optimize: no candidate beat the baseline; keeping the baseline configuration');
  return { best: bestResult, bestCandidateId: best?.id ?? null, candidates: cands };
}

/**
 * Marks every measured candidate kept/rejected (in place) and returns the winner: the fastest decode among candidates
 * whose context fit, whose prefill lost at most 5% and whose decode beats the baseline. Null = keep the baseline.
 */
export function decide(cands: Candidate[], base: BenchResult): Candidate | null {
  let best: Candidate | null = null;
  for (const c of cands) {
    if (!c.result || c.status === 'failed') continue;
    c.status = 'rejected';
    if (!c.result.ctxOk) c.reason = 'ctx_not_fit';
    else if (c.result.prefill.tps < base.prefill.tps * (1 - PREFILL_LOSS_MAX)) {
      c.reason = `prefill_loss:${pct(c.result.prefill.tps, base.prefill.tps)}`;
    } else if (c.result.decode.tps <= base.decode.tps) c.reason = `decode_not_faster:${pct(c.result.decode.tps, base.decode.tps)}`;
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
