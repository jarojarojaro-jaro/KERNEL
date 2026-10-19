<script lang="ts">
	/**
	 * Landing teaser for the results page: a full-width heat band. The same-script pairs (HERO_PAIRS)
	 * as one board, each row = model mark + name, card, a steel bar (typical app = 1×) and a thick
	 * glowing heat bar (our engine) on one shared speed-up scale, both t/s values and the speed-up.
	 * The full interactive lab lives on /pl/wyniki/ · /en/results/.
	 */
	import { heatOf } from '$lib/cards/explorer';
	import { reveal } from '$lib/fx/actions';
	import { fmtRatio, fmtTps } from '$lib/format';
	import { resultsHref, type Lang } from '$lib/i18n';
	import ModelMark from '$lib/ModelMark.svelte';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import { copy } from '$lib/site/copy';
	import { HERO_PAIRS } from './data';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].results.teaser);
	const rows = HERO_PAIRS.map((p) => ({ ...p, a: p.before.decode!, b: p.ours.decode! }));
	/** One shared speed-up scale: steel = the typical app (1×), heat = our engine (its ×), so a 2,0× bar is twice the steel. */
	const maxR = Math.max(...rows.map((r) => r.b.v / r.a.v));
</script>

<section id="results" class="teaser heat-top" aria-labelledby="results-title">
	<div class="inner">
		<header class="head">
			<h2 id="results-title" class="t">{c.title}</h2>
			<p class="lede">{c.lede}</p>
			<a class="cta cta--line" href={resultsHref(lang)}>{c.link} <span class="arrow" aria-hidden="true">→</span></a>
		</header>
		<div class="board" use:reveal={{ threshold: 0.25 }}>
			<p class="unit">{c.unit}</p>
			<ul class="rows" role="list">
				{#each rows as r, i (r.id)}
					<li class="row" style="--a:{1 / maxR}; --b:{r.b.v / r.a.v / maxR}; --d:{i * 70}ms; --th:{heatOf(r.b.v / r.a.v)}">
						<span class="who">
							<ModelMark model={r.run.model} size="0.75em" />
							<b>{MODEL_STYLE[r.run.model].short}</b>
							<span class="cshort">{r.card.short}</span>
						</span>
						<span class="bars" aria-hidden="true">
							<span class="bar-a"></span>
							<span class="bar-b"></span>
						</span>
						<span class="vals">
							<span class="va">{fmtTps(r.a.v, lang)}</span>
							<span class="arr" aria-hidden="true">→</span>
							<span class="vb">{fmtTps(r.b.v, lang)}</span>
						</span>
						<span class="speedup g" style="--rh:{heatOf(r.b.v / r.a.v)}">{fmtRatio(r.b.v / r.a.v, lang)}</span>
					</li>
				{/each}
			</ul>
		</div>
	</div>
</section>

<style>
	/* a full-bleed heat band: the warmth lives in the data here, not in the headline */
	.teaser {
		position: relative;
		padding-block: clamp(3.5rem, 2.5rem + 3vw, 6rem);
		background:
			radial-gradient(60% 120% at 70% 55%, rgb(255 122 26 / 0.13), transparent 70%),
			radial-gradient(40% 90% at 15% 80%, rgb(226 64 28 / 0.09), transparent 70%),
			linear-gradient(180deg, rgb(255 122 26 / 0.02), rgb(255 122 26 / 0.06) 50%, rgb(255 122 26 / 0.02));
	}
	.teaser::after {
		content: '';
		position: absolute;
		inset: auto 0 0;
		height: 1px;
		background: linear-gradient(90deg, transparent, var(--heat-2) 20%, var(--heat-4) 60%, transparent);
		opacity: 0.6;
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		gap: clamp(1.75rem, 3vw, 3rem);
	}
	.head {
		display: grid;
		grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr) auto;
		align-items: end;
		gap: var(--sp-4) clamp(2rem, 4vw, 4rem);
	}
	.t {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(1.9rem, 1rem + 2.4vw, 3.4rem);
		font-weight: 780;
		font-stretch: 104%;
		letter-spacing: -0.03em;
		line-height: 1;
		color: var(--text-hi);
		text-wrap: balance;
	}
	.lede {
		margin: 0;
		color: var(--text);
		max-width: 40ch;
	}
	.board {
		display: grid;
		gap: var(--sp-3);
	}
	.unit {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.rows {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
	}
	.row {
		display: grid;
		/* fixed columns: every row's bars start on one shared baseline */
		grid-template-columns: 14rem minmax(6rem, 1fr) 11rem 5rem;
		align-items: center;
		gap: var(--sp-4);
		padding-block: var(--sp-3);
		border-bottom: 1px solid var(--line);
		transition: background 0.3s;
	}
	.row:hover {
		background: linear-gradient(90deg, rgb(255 122 26 / 0.08), transparent 70%);
	}
	.who {
		display: flex;
		align-items: baseline;
		gap: 0.5rem;
		min-width: 0;
		white-space: nowrap;
	}
	.who b {
		font-weight: 650;
		color: var(--text-hi);
	}
	.cshort {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.bars {
		position: relative;
		display: grid;
		gap: 5px;
	}
	/* the 1× line: where the typical app ends, through every row */
	.bars::after {
		content: '';
		position: absolute;
		top: -0.5rem;
		bottom: -0.5rem;
		left: calc(var(--a) * 100%);
		border-left: 1px dashed rgb(237 234 227 / 0.22);
	}
	.bar-a,
	.bar-b {
		border-radius: var(--r-pill);
		transform-origin: 0 50%;
	}
	.bar-a {
		height: 8px;
	}
	.bar-b {
		height: 14px;
	}
	.bar-a {
		background: var(--before);
		transform: scaleX(var(--a));
	}
	/* one heat colour; the glow grows with the speed-up (heatOf) */
	.bar-b {
		transform: scaleX(var(--b));
		background: var(--heat-ramp-hot);
		box-shadow:
			0 0 calc(8px + 16px * var(--th)) rgb(255 122 26 / calc(0.35 + 0.35 * var(--th))),
			inset 0 1px 0 rgb(255 243 214 / 0.5);
	}
	@media (prefers-reduced-motion: no-preference) {
		/* resting state final; entering view replays the bars filling */
		:global(html.js) .board:global([data-in]) .bar-a,
		:global(html.js) .board:global([data-in]) .bar-b {
			animation: bar-in 1s var(--ease-out) var(--d) backwards;
		}
	}
	@keyframes bar-in {
		from {
			transform: scaleX(0);
		}
	}
	.vals {
		display: flex;
		justify-content: flex-end;
		align-items: baseline;
		gap: 0.4rem;
		font-family: var(--font-display);
		font-variant-numeric: tabular-nums lining-nums;
		font-weight: 650;
		font-size: var(--fs-sm);
		white-space: nowrap;
	}
	.va {
		color: var(--before);
	}
	.vb {
		color: var(--heat-4);
		text-shadow: 0 0 10px rgb(255 122 26 / 0.45);
	}
	.arr {
		color: var(--text-mute);
	}
	.g {
		font-size: var(--fs-lg);
		text-align: right;
	}
	@media (max-width: 1000px) {
		.head {
			grid-template-columns: minmax(0, 1fr);
			align-items: start;
			justify-items: start;
		}
	}
	@media (max-width: 640px) {
		.row {
			grid-template-columns: minmax(0, 1fr) auto;
			grid-template-areas:
				'who  g'
				'bars bars'
				'vals vals';
			row-gap: var(--sp-2);
		}
		.who {
			grid-area: who;
		}
		.bars {
			grid-area: bars;
		}
		.vals {
			grid-area: vals;
			font-size: var(--fs-xs);
		}
		.g {
			grid-area: g;
		}
	}
</style>
