/** Shared wording for benchmark results. */
import type { BenchResult } from '../../shared/types';
import type { Dict } from './i18n';

export const BENCH_STEPS = ['bench:start', 'bench:prefill', 'bench:decode', 'bench:deep'] as const;

/**
 * "llama.cpp (oficjalny) b11742" for the upstream baseline, "Enigma b…" for ours. llama-server prints
 * versions like "0.7.0-dev (build 11742, commit 4c3c5810f)"; the release tag is b<build>.
 */
export function engineName(r: BenchResult, t: Dict): string {
	const { id, version } = r.engine;
	const m = /build (\d+)/.exec(version);
	const build = m ? `b${m[1]}` : version;
	if (id.startsWith('upstream')) return `${t.base.official} ${build}`;
	if (id.startsWith('enigma')) return `Enigma ${build}`;
	return `${id} ${build}`;
}

/** Percentage change from `a` to `b` (null when there is no base to compare with). */
export function gainPct(a: number | undefined, b: number | undefined): number | null {
	if (a === undefined || b === undefined || a <= 0) return null;
	return ((b - a) / a) * 100;
}
