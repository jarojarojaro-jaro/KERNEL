<script lang="ts">
	/**
	 * Landing teaser for the results page: the same-script pairs (HERO_PAIRS) as one compact board,
	 * each row = model mark + name, card, a steel bar (typical app) and a heat bar (our engine) on the
	 * row's own scale, both t/s values and the speed-up. The full interactive lab lives on
	 * /pl/wyniki/ · /en/results/.
	 */
	import { reveal } from '$lib/fx/actions';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { fmtRatio, fmtTps } from '$lib/format';
	import { resultsHref, type Lang } from '$lib/i18n';
	import ModelMark from '$lib/ModelMark.svelte';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import { copy } from '$lib/site/copy';
	import { HERO_PAIRS } from './data';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].results.teaser);
	const rows = HERO_PAIRS.map((p) => ({ ...p, a: p.before.decode!, b: p.ours.decode! }));
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
					<li class="row" style="--a:{r.a.v / r.b.v}; --d:{i * 70}ms">
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
						<span class="speedup g">{fmtRatio(r.b.v / r.a.v, lang)}</span>
						<SourceTip {lang} src={[r.a.src, r.b.src, r.run.conditionsSrc]} note="{r.card.name} · {r.run.quant}. {r.run.metric[lang]} {r.run.conditions[lang]}." />
					</li>
				{/each}
			</ul>
		</div>
	</div>
</section>

<style>
	.teaser {
		padding-block: clamp(3.5rem, 2.5rem + 3vw, 6rem);
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.5fr);
		gap: clamp(2rem, 5vw, 5rem);
		align-items: start;
	}
	.head {
		display: grid;
		gap: var(--sp-4);
		justify-items: start;
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
		color: var(--text);
		max-width: 40ch;
	}
	.board {
		display: grid;
		gap: var(--sp-3);
	}
	.unit {
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
		grid-template-columns: minmax(11rem, 1.1fr) minmax(6rem, 1.4fr) auto 4.2rem auto;
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
		display: grid;
		gap: 3px;
	}
	.bar-a,
	.bar-b {
		height: 5px;
		border-radius: var(--r-pill);
		transform-origin: 0 50%;
		transition: transform 1s var(--ease-out) var(--d);
	}
	.bar-a {
		background: var(--before);
		transform: scaleX(var(--a));
	}
	.bar-b {
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 10px rgb(255 122 26 / 0.45);
	}
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .board:not([data-in]) .bar-a,
		:global(html.js) .board:not([data-in]) .bar-b {
			transform: scaleX(0);
		}
	}
	.vals {
		display: flex;
		align-items: baseline;
		gap: 0.4rem;
		font-family: var(--font-mono);
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
		.inner {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (max-width: 640px) {
		.row {
			grid-template-columns: minmax(0, 1fr) auto auto;
			grid-template-areas:
				'who  g    src'
				'bars bars bars'
				'vals vals vals';
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
