<script lang="ts">
	import { CARDS, MODEL_INFO, variantOf } from '$lib/data/measurements';
	import { fmtRatio } from '$lib/format';
	import { magnetic, reveal } from '$lib/fx/actions';
	import { cardsHref, href, num, type Lang } from '$lib/i18n';
	import { COPY } from './copy';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(COPY[lang]);

	/** Every card × model pair with a measured before and after decode speed. */
	const rows = CARDS.flatMap((card) =>
		card.runs.flatMap((run) => {
			const before = variantOf(run, run.before)?.decode;
			const after = variantOf(run, run.ours)?.decode;
			return before && after ? [{ id: `${card.id}-${run.model}`, card, run, before: before.v, after: after.v, src: after.src }] : [];
		})
	).sort((a, b) => b.after / b.before - a.after / a.before);
	let pick = $state('all');
	const shown = $derived(pick === 'all' ? rows : rows.filter((r) => r.card.id === pick));
	const cards = CARDS.filter((card) => rows.some((r) => r.card.id === card.id));
</script>

<div class="board">
	<div class="seg wrap" role="group" aria-label={c.ch[7].nav}>
		<button type="button" aria-pressed={pick === 'all'} onclick={() => (pick = 'all')}>{c.r.filterAll}</button>
		{#each cards as card (card.id)}
			<button type="button" aria-pressed={pick === card.id} onclick={() => (pick = card.id)}>{card.short}</button>
		{/each}
	</div>

	<ol class="rows">
		{#each shown as r (r.id)}
			<li class="row" use:reveal>
				<div class="who">
					<span class="m" style="--mc:var(--model-{r.run.model})">{MODEL_INFO[r.run.model].name}</span>
					<span class="cd mono">{r.card.name} · {r.run.quant}</span>
				</div>
				<div class="bars" aria-hidden="true">
					<span class="track"><i class="b0" style="transform:scaleX({r.before / Math.max(r.before, r.after)})"></i></span>
					<span class="track"><i class="b1" style="transform:scaleX({r.after / Math.max(r.before, r.after)})"></i></span>
				</div>
				<p class="vals mono">
					<span class="v0">{num(r.before, lang, 1)}</span>
					<span class="arr" aria-hidden="true">→</span>
					<span class="v1">{num(r.after, lang, 1)}</span>
					<span class="u">{c.r.speed}</span>
				</p>
				<p class="x speedup" class:speedup--down={r.after < r.before}>{fmtRatio(r.after / r.before, lang)}</p>
			</li>
		{/each}
	</ol>
	<p class="fine legend"><i class="l0"></i>{c.r.before}<i class="l1"></i>{c.r.after} · <a href="#archive">{c.r.archive} ↓</a></p>

	<div class="cta">
		<div>
			<p class="ct">{c.r.ctaTitle}</p>
			<p class="cl">{c.r.ctaLead}</p>
		</div>
		<div class="acts">
			<a class="ignite" href={cardsHref(lang)} use:magnetic={{ max: 6 }}>
				<span>{c.r.cta}</span>
				<svg class="ig-arrow" viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><path d="M3 10h13M11 4.5 16.5 10 11 15.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
			</a>
			<a class="sec" href={href(lang, '/start')}>{c.r.cta2} →</a>
		</div>
	</div>
</div>

<style>
	.board {
		display: grid;
		gap: var(--sp-5);
	}
	.wrap {
		flex-wrap: wrap;
	}
	.rows {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		gap: 0;
		border-top: 1px solid var(--line);
	}
	.row {
		display: grid;
		grid-template-columns: minmax(0, 15rem) minmax(0, 1fr) 11rem 5rem;
		gap: var(--sp-5);
		align-items: center;
		padding: var(--sp-4) 0;
		border-bottom: 1px solid var(--line);
	}
	.who {
		display: grid;
		gap: 0.1rem;
		min-width: 0;
	}
	.m {
		font-weight: 600;
		color: var(--text-hi);
		display: inline-flex;
		align-items: center;
		gap: var(--sp-2);
	}
	.m::before {
		content: '';
		width: 0.55rem;
		height: 0.55rem;
		border-radius: 50%;
		background: var(--mc, var(--text-mute));
	}
	.cd {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.bars {
		display: grid;
		gap: 4px;
	}
	.track {
		height: 0.5rem;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		overflow: hidden;
	}
	.track i {
		display: block;
		height: 100%;
		border-radius: inherit;
		transform-origin: left;
	}
	.b0 {
		background: var(--before);
	}
	.b1 {
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 14px -2px var(--heat-3);
	}
	@media (prefers-reduced-motion: no-preference) {
		.track i {
			transition: transform 1.1s var(--ease-out) 0.15s;
		}
		:global(html.js) .row:not([data-in]) .track i {
			transform: scaleX(0) !important;
		}
	}
	.vals {
		margin: 0;
		display: flex;
		gap: var(--sp-2);
		align-items: baseline;
		justify-content: flex-end;
		font-size: var(--fs-sm);
	}
	.v0 {
		color: var(--before);
	}
	.v1 {
		color: var(--accent-ink);
		font-weight: 600;
		font-size: var(--fs-md);
	}
	.arr,
	.u {
		color: var(--text-mute);
		font-size: var(--fs-xs);
	}
	.x {
		margin: 0;
		text-align: right;
		font-size: var(--fs-xl);
		font-weight: 650;
		letter-spacing: -0.03em;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2);
	}
	.legend i {
		width: 0.9rem;
		height: 0.4rem;
		border-radius: 2px;
	}
	.l0 {
		background: var(--before);
	}
	.l1 {
		margin-left: var(--sp-2);
		background: var(--heat-3);
	}
	.legend a {
		color: var(--info-ink);
	}
	.cta {
		margin-top: var(--sp-8);
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		align-items: center;
		gap: var(--sp-6);
		padding: clamp(1.5rem, 1rem + 3vw, 3rem);
		border-radius: var(--r-xl);
		border: 1px solid color-mix(in srgb, var(--heat-3) 40%, var(--line));
		background:
			radial-gradient(60% 140% at 100% 100%, color-mix(in srgb, var(--heat-3) 22%, transparent), transparent 70%),
			radial-gradient(40% 100% at 0% 0%, color-mix(in srgb, var(--heat-2) 12%, transparent), transparent 70%),
			var(--bg-1);
		box-shadow: 0 50px 120px -60px color-mix(in srgb, var(--heat-3) 90%, transparent);
	}
	.ct {
		margin: 0;
		font-size: clamp(1.6rem, 1.1rem + 2vw, 2.6rem);
		font-weight: 650;
		letter-spacing: -0.03em;
		color: var(--text-hi);
	}
	.cl {
		margin: var(--sp-2) 0 0;
		color: var(--text);
		max-width: 48ch;
	}
	.acts {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-5);
	}
	.sec {
		color: var(--text-hi);
		font-weight: 560;
		text-decoration: underline;
		text-decoration-color: var(--line-strong);
		text-underline-offset: 0.3em;
		min-height: 2.75rem;
		display: inline-flex;
		align-items: center;
	}
	.sec:hover {
		text-decoration-color: var(--heat-3);
	}
	@property --ig {
		syntax: '<angle>';
		inherits: false;
		initial-value: 0deg;
	}
	/* the hero's ignite key: dark body, a turning heat edge and an ember glow */
	.ignite {
		position: relative;
		isolation: isolate;
		display: inline-flex;
		align-items: center;
		gap: 0.9rem;
		min-height: 3.4rem;
		padding: 0 1.4rem 0 1.6rem;
		border-radius: 14px;
		background: linear-gradient(180deg, #17171b, #0b0b0d);
		box-shadow:
			inset 0 1px 0 rgb(255 255 255 / 0.08),
			0 16px 40px -18px rgb(255 122 26 / 0.55);
		color: #edeae3;
		font-weight: 680;
		font-size: var(--fs-md);
		letter-spacing: -0.01em;
		text-decoration: none;
		transition: transform 0.25s var(--ease-out);
	}
	.ignite::before,
	.ignite::after {
		content: '';
		position: absolute;
		border-radius: inherit;
		background: conic-gradient(from var(--ig), var(--heat-2), var(--heat-3) 12%, var(--heat-5) 20%, var(--heat-4) 28%, rgb(255 122 26 / 0.18) 42%, rgb(255 122 26 / 0.12) 78%, var(--heat-2));
		animation: ig-turn 5.5s linear infinite;
		pointer-events: none;
	}
	.ignite::before {
		inset: 0;
		padding: 1.5px;
		-webkit-mask:
			linear-gradient(#000 0 0) content-box,
			linear-gradient(#000 0 0);
		-webkit-mask-composite: xor;
		mask:
			linear-gradient(#000 0 0) content-box,
			linear-gradient(#000 0 0);
		mask-composite: exclude;
	}
	.ignite::after {
		inset: -3px;
		z-index: -1;
		filter: blur(14px);
		opacity: 0.4;
		transition: opacity 0.35s var(--ease-out);
	}
	@keyframes ig-turn {
		to {
			--ig: 360deg;
		}
	}
	.ig-arrow {
		color: var(--heat-4);
		transition: transform 0.3s var(--ease-spring);
	}
	.ignite:hover::after,
	.ignite:focus-visible::after {
		opacity: 0.85;
	}
	.ignite:hover .ig-arrow,
	.ignite:focus-visible .ig-arrow {
		transform: translate3d(4px, 0, 0);
	}
	.ignite:focus-visible {
		outline: 2px solid var(--heat-4);
		outline-offset: 4px;
	}
	@media (max-width: 760px) {
		.row {
			grid-template-columns: minmax(0, 1fr) auto;
			gap: var(--sp-2) var(--sp-4);
		}
		.bars {
			grid-column: 1 / -1;
			grid-row: 2;
		}
		.vals {
			grid-column: 1;
			justify-content: flex-start;
		}
		.x {
			grid-column: 2;
			grid-row: 1 / span 1;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.ignite::before,
		.ignite::after {
			animation: none;
		}
	}
</style>
