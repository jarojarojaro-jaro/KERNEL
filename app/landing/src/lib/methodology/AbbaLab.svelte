<script lang="ts">
	import { num, type Lang } from '$lib/i18n';
	import { COPY } from './copy';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(COPY[lang]);

	/** Illustrative drift: every run 0.4% slower than the one before (ms/step grows). */
	const DRIFT = 0.004;
	const PRESETS = [
		{ id: 'AABB', seq: 'AAAABBBB' },
		{ id: 'ABAB', seq: 'ABABABAB' },
		{ id: 'ABBA', seq: 'ABBAABBA' }
	];
	let seq = $state<('A' | 'B')[]>([...'AAAABBBB'] as ('A' | 'B')[]);

	const ms = Array.from({ length: 8 }, (_, i) => 1 + DRIFT * i);
	const stats = $derived.by(() => {
		const a = seq.flatMap((v, i) => (v === 'A' ? [ms[i]] : []));
		const b = seq.flatMap((v, i) => (v === 'B' ? [ms[i]] : []));
		if (a.length !== b.length) return null;
		const mean = (x: number[]) => x.reduce((s, v) => s + v, 0) / x.length;
		return ((mean(b) - mean(a)) / mean(a)) * 100;
	});
	const active = $derived(PRESETS.find((p) => p.seq === seq.join(''))?.id ?? null);
	const flip = (i: number) => (seq[i] = seq[i] === 'A' ? 'B' : 'A');

	/** Bar heights: speed (1 / ms) relative to the first run, stretched so the drift is visible. */
	const H = (i: number) => 0.35 + (1 / ms[i] - 1 / ms[ms.length - 1]) / (1 - 1 / ms[ms.length - 1]) * 0.6;

	/* T=0 vs T=1: an illustrative next-token distribution. */
	const DIST = {
		pl: [
			['szybka', 0.41],
			['droga', 0.22],
			['gorąca', 0.15],
			['nowa', 0.12],
			['głośna', 0.1]
		],
		en: [
			['fast', 0.41],
			['expensive', 0.22],
			['hot', 0.15],
			['new', 0.12],
			['loud', 0.1]
		]
	} as const;
	const dist = $derived(DIST[lang]);
	let temp = $state<0 | 1>(0);
	let picks = $state<number[]>([]);
	function sample() {
		let k = 0;
		if (temp === 1) {
			let r = Math.random();
			while (k < dist.length - 1 && (r -= dist[k][1]) > 0) k++;
		}
		picks = [...picks.slice(-7), k];
	}
	function setTemp(v: 0 | 1) {
		temp = v;
		picks = [];
	}
</script>

<div class="grid">
	<ol class="rules">
		{#each c.m.rules as [k, v], i (k)}
			<li style="--i:{i}"><span class="rk mono">{k}</span><p>{v}</p></li>
		{/each}
	</ol>

	<div class="lab panel">
		<div class="lab-head">
			<p class="panel-h">{c.m.labTitle} <span class="tag-ill">{c.illustr}</span></p>
			<p class="small">{c.m.labLead}</p>
		</div>
		<div class="seg" role="group" aria-label={c.m.presets}>
			{#each PRESETS as p (p.id)}
				<button type="button" aria-pressed={active === p.id} onclick={() => (seq = [...p.seq] as ('A' | 'B')[])}>{p.id}</button>
			{/each}
		</div>

		<div class="chart">
			<svg class="drift" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">
				<path d="M0 6 L100 34" />
			</svg>
			<span class="drift-l mono" aria-hidden="true">{c.m.drift} ↘</span>
			<ol class="slots">
				{#each seq as v, i (i)}
					<li>
						<button type="button" class="slot {v}" onclick={() => flip(i)} aria-label={c.m.slot(i + 1, v)}>
							<span class="bar" style="transform:scaleY({H(i)})"></span>
							<span class="v mono">{v}</span>
						</button>
					</li>
				{/each}
			</ol>
		</div>

		<div class="out" aria-live="polite">
			{#if stats === null}
				<p class="verdict warn">{c.m.verdictUneven}</p>
			{:else}
				<p class="fake"><span class="k">{c.m.fake}</span><span class="fig mono" class:zero={Math.abs(stats) < 0.005}>{stats > 0.005 ? '+' : ''}{num(stats, lang, 2)}%</span></p>
				<p class="verdict" class:ok={Math.abs(stats) < 0.005}>{Math.abs(stats) < 0.005 ? c.m.verdictOk : c.m.verdictBad}</p>
			{/if}
			<p class="fine">{c.m.model}</p>
		</div>
	</div>

	<div class="temp panel">
		<p class="panel-h">{c.m.tTitle}</p>
		<div class="seg" role="group" aria-label="T">
			<button type="button" aria-pressed={temp === 0} onclick={() => setTemp(0)}>T=0</button>
			<button type="button" aria-pressed={temp === 1} onclick={() => setTemp(1)}>T=1</button>
		</div>
		<p class="small">{temp === 0 ? c.m.t0 : c.m.t1}</p>
		<p class="fine">{c.m.next} <span class="tag-ill">{c.illustr}</span></p>
		<ul class="dist">
			{#each dist as [w, p], k (w)}
				<li class:top={temp === 0 && k === 0}>
					<span class="w">{w}</span>
					<span class="track" aria-hidden="true"><i style="transform:scaleX({p / dist[0][1]})"></i></span>
					<span class="p mono">{num(p * 100, lang, 0)}%</span>
				</li>
			{/each}
		</ul>
		<button type="button" class="btn-m" onclick={sample}>{c.m.pick}</button>
		<ol class="picks" aria-live="polite">
			{#each picks as k, i (i)}<li class="chip">{dist[k][0]}</li>{/each}
		</ol>
	</div>
</div>

<style>
	.grid {
		display: grid;
		grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr);
		gap: var(--sp-6);
	}
	.rules {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--sp-4) var(--sp-5);
		grid-column: 1 / -1;
	}
	.rules li {
		display: grid;
		gap: var(--sp-1);
		padding-top: var(--sp-3);
		border-top: 1px solid var(--line);
	}
	.rk {
		font-size: var(--fs-xs);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--accent-ink);
	}
	.rules p {
		margin: 0;
		font-size: var(--fs-sm);
		line-height: 1.55;
		color: var(--text);
	}
	.lab {
		align-self: stretch;
		display: grid;
		gap: var(--sp-4);
		align-content: start;
	}
	.lab-head {
		display: grid;
		gap: var(--sp-2);
	}
	.chart {
		position: relative;
		padding-top: var(--sp-5);
	}
	.drift {
		position: absolute;
		inset: var(--sp-5) 0 2rem;
		width: 100%;
		height: calc(100% - var(--sp-5) - 2rem);
		pointer-events: none;
		overflow: visible;
	}
	.drift path {
		fill: none;
		stroke: var(--warn);
		stroke-width: 1.5;
		stroke-dasharray: 3 3;
		vector-effect: non-scaling-stroke;
		opacity: 0.8;
	}
	.drift-l {
		position: absolute;
		top: 0;
		right: 0;
		font-size: var(--fs-2xs);
		color: var(--warn-ink);
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}
	.slots {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		grid-template-columns: repeat(8, minmax(0, 1fr));
		gap: var(--sp-2);
	}
	.slot {
		width: 100%;
		display: grid;
		grid-template-rows: 9rem auto;
		gap: var(--sp-2);
		padding: 0;
		border: 0;
		background: none;
		cursor: pointer;
		color: inherit;
		border-radius: var(--r-sm);
	}
	.slot:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 3px;
	}
	.bar {
		align-self: end;
		height: 100%;
		border-radius: var(--r-sm) var(--r-sm) 2px 2px;
		transform-origin: bottom;
		transition:
			transform var(--dur-4) var(--ease-spring),
			background-color var(--dur-3);
		background: var(--before);
	}
	.slot.B .bar {
		background: linear-gradient(180deg, var(--heat-4), var(--heat-2));
		box-shadow: 0 0 22px -6px var(--heat-3);
	}
	.v {
		justify-self: center;
		display: grid;
		place-items: center;
		width: 2rem;
		height: 2rem;
		border-radius: var(--r-sm);
		border: 1px solid var(--line-strong);
		font-weight: 600;
		transition: transform var(--dur-3) var(--ease-spring);
	}
	.slot:hover .v {
		transform: translateY(-2px);
	}
	.slot.B .v {
		border-color: var(--heat-3);
		color: var(--accent-ink);
	}
	.out {
		display: grid;
		gap: var(--sp-2);
		min-height: 7.5rem;
	}
	.fake {
		margin: 0;
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--sp-3);
		flex-wrap: wrap;
	}
	.k {
		font-size: var(--fs-sm);
		color: var(--text-mute);
	}
	.fig {
		font-size: clamp(2rem, 1.5rem + 2vw, 3rem);
		font-weight: 600;
		letter-spacing: -0.03em;
		color: var(--danger-ink);
	}
	.fig.zero {
		color: var(--ok-ink);
	}
	.verdict {
		margin: 0;
		font-weight: 560;
		color: var(--danger-ink);
	}
	.verdict.ok {
		color: var(--ok-ink);
	}
	.verdict.warn {
		color: var(--warn-ink);
	}
	.temp {
		display: grid;
		gap: var(--sp-3);
		align-content: start;
	}
	.dist {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		gap: var(--sp-1);
	}
	.dist li {
		display: grid;
		grid-template-columns: 6.5rem minmax(0, 1fr) 3rem;
		align-items: center;
		gap: var(--sp-3);
		font-size: var(--fs-sm);
		color: var(--text-mute);
		transition: color var(--dur-2);
	}
	.dist li.top {
		color: var(--text-hi);
	}
	.track {
		height: 0.45rem;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		overflow: hidden;
	}
	.track i {
		display: block;
		height: 100%;
		transform-origin: left;
		background: var(--line-strong);
	}
	.top .track i {
		background: var(--heat-ramp-hot);
	}
	.p {
		text-align: right;
	}
	.btn-m {
		justify-self: start;
	}
	.picks {
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
		min-height: 2rem;
	}
	@media (max-width: 960px) {
		.grid {
			grid-template-columns: minmax(0, 1fr);
		}
		.rules {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 520px) {
		.rules {
			grid-template-columns: minmax(0, 1fr);
		}
		.slot {
			grid-template-rows: 6.5rem auto;
		}
		.v {
			width: 1.6rem;
			height: 1.6rem;
		}
		.slots {
			gap: var(--sp-1);
		}
	}
</style>
