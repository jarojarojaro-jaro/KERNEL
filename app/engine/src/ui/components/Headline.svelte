<script lang="ts">
	/** Baseline → now → gain for prefill, decode, deep decode and context (the user's reporting rule). */
	import type { BenchResult } from '../../shared/types';
	import { gainPct } from '../lib/bench';
	import { int, kTokens, num, pct } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	let { base, now }: { base: BenchResult; now: BenchResult } = $props();
	const t = $derived(store.t.opt);
	const lang = $derived(store.lang);

	interface Row {
		key: string;
		label: string;
		a: number;
		b: number;
		unit: string;
		digits: number;
		speed: boolean;
	}
	const rows = $derived<Row[]>([
		{ key: 'pp', label: t.prefill, a: base.prefill.tps, b: now.prefill.tps, unit: 't/s', digits: 1, speed: true },
		{ key: 'tg', label: t.decode, a: base.decode.tps, b: now.decode.tps, unit: 't/s', digits: 1, speed: true },
		...(base.deep && now.deep
			? [{ key: 'deep', label: t.deep(kTokens(base.deep.ctxTokens)), a: base.deep.decodeTps, b: now.deep.decodeTps, unit: 't/s', digits: 1, speed: true }]
			: []),
		{ key: 'ctx', label: t.ctx, a: base.config.ctx, b: now.config.ctx, unit: 'tok', digits: 0, speed: false }
	]);
	const fmt = (v: number, d: number) => (d === 0 ? int(v, lang) : num(v, lang, d));
</script>

<div class="table-wrap">
	<table class="table head">
		<caption class="sr-only">{t.headline}</caption>
		<thead>
			<tr>
				<th scope="col">{t.metric}</th>
				<th scope="col" class="num">{t.baseline}</th>
				<th scope="col" class="num">{t.now}</th>
				<th scope="col" class="num">{t.gain}</th>
			</tr>
		</thead>
		<tbody>
			{#each rows as r (r.key)}
				{@const g = gainPct(r.a, r.b)}
				{@const max = Math.max(r.a, r.b, 1e-9)}
				<tr>
					<th scope="row">
						{r.label}
						{#if r.speed}
							<span class="bars" aria-hidden="true">
								<span class="bar bar--before"><i style="--v:{r.a / max}"></i></span>
								<span class="bar"><i style="--v:{r.b / max}"></i></span>
							</span>
						{/if}
					</th>
					<td class="num before">{fmt(r.a, r.digits)} <span class="u">{r.unit}</span></td>
					<td class="num cur" class:speed={r.speed && r.b > r.a}>{fmt(r.b, r.digits)} <span class="u">{r.unit}</span></td>
					<td class="num gain" class:up={g !== null && g >= 0.5} class:down={g !== null && g <= -0.5}>
						{g === null || Math.abs(g) < 0.5 ? t.noChange : pct(g, lang)}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.table-wrap {
		background: var(--bg-2);
	}
	.head td,
	.head th {
		vertical-align: middle;
	}
	.head tbody th {
		min-width: 11rem;
	}
	.bars {
		display: grid;
		gap: 3px;
		margin-top: 0.45rem;
		max-width: 14rem;
	}
	.bars .bar {
		height: 0.35rem;
	}
	.before {
		color: var(--before);
	}
	.cur {
		color: var(--text-hi);
		font-weight: 600;
	}
	.cur.speed {
		color: var(--accent-ink);
	}
	.u {
		font-size: 0.8em;
		color: var(--text-mute);
		font-weight: 400;
	}
	.gain {
		font-weight: 600;
		color: var(--text-mute);
	}
	.gain.up {
		color: var(--accent-ink);
	}
	.gain.down {
		color: var(--danger-ink);
	}
	td {
		font-size: var(--fs-md);
	}
	@media (max-width: 600px) {
		.head tbody th {
			min-width: 8rem;
		}
		td {
			font-size: var(--fs-sm);
		}
		.head th,
		.head td {
			padding-inline: var(--sp-3);
		}
	}
</style>
