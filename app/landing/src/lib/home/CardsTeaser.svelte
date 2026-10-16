<script lang="ts">
	/**
	 * Twoja karta: the measured cards as big tactile tiles (tilt + glare), each with the headline
	 * gain of its pick run, linking into the cards explorer; planned cards as queue chips.
	 */
	import { headline } from '$lib/cards/explorer';
	import { tilt } from '$lib/fx/actions';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { MODEL_INFO } from '$lib/data/measurements';
	import { cardsHref, num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { CARDS, decode, nb, PLANNED, fmtRatio } from './data';
	import Duo from './Duo.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].cards);
	/** Same headline rule as the explorer gallery: the pick, unless it has no same-script pair. */
	const tiles = CARDS.flatMap((card) => {
		const d = headline(card);
		if (!d) return [];
		return [{ card, run: d.run, gain: d.ratio, src: d.run.gain?.total?.src ?? d.run.src, before: decode(d.before), ours: decode(d.ours), model: MODEL_INFO[d.run.model].name }];
	});
	const top = Math.max(...tiles.map((t) => t.ours));
</script>

<section id="cards" class="cards heat-top" aria-labelledby="cards-title">
	<div class="inner">
		<header class="head">
			<div>
				<Duo text={c.title} id="cards-title" mode="plain" />
			</div>
			<p class="lede">{c.lede}</p>
		</header>
		<ul class="grid" role="list">
			{#each tiles as t (t.card.id)}
				<li>
					<a class="tile" href={cardsHref(lang, t.card.id)} use:tilt style="--b:{t.before / top}; --o:{t.ours / top}; --len:{t.card.short.length}">
						<span class="meta">{t.card.arch} · {t.card.vramGB} GB</span>
						<span class="short" aria-hidden="true">{t.card.short}</span>
						<span class="name">{nb(t.card.name)}</span>
						<span class="gain">
							{#if t.gain !== null}
								<b class="speedup" class:speedup--down={t.gain < 1}>{fmtRatio(t.gain, lang)}</b>
								<span>{c.faster} · {t.model}</span>
							{:else}
								<b>{num(t.ours, lang)} <small>t/s</small></b>
								<span>{c.diff}</span>
							{/if}
						</span>
						{#if t.run.sameHarness}
							<span class="tbar" aria-hidden="true"><span class="bb"></span><span class="bo"></span></span>
							<span class="nums">{num(t.before, lang)} → {num(t.ours, lang)} t/s</span>
						{/if}
						<span class="go" aria-hidden="true">→</span>
					</a>
				</li>
			{/each}
		</ul>
		<p class="fn">
			<span>{c.note}</span>
			<SourceTip {lang} src={tiles.flatMap((t) => [t.src, ...t.run.variants.map((v) => v.decode?.src ?? '')]).filter(Boolean)} note={tiles.map((t) => `${t.card.short}: ${t.run.metric[lang]}`).join(' ')} />
		</p>
		<div class="queue">
			<p class="ql">{c.queue}</p>
			<ul role="list">
				{#each PLANNED as g (g.id)}<li><span class="plus" aria-hidden="true">+</span>{g.name}</li>{/each}
			</ul>
			<a class="cta cta--line" href={cardsHref(lang)}>{c.open} <span class="arrow" aria-hidden="true">→</span></a>
		</div>
	</div>
</section>

<style>
	.cards {
		padding-block: clamp(3.5rem, 2.5rem + 3vw, 6rem);
		background: var(--bg-0);
	}
	.fn {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2) var(--sp-3);
		margin-top: calc(-1 * var(--sp-6));
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		gap: clamp(2.5rem, 5vw, 4rem);
	}
	.head {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
		align-items: end;
		gap: var(--sp-6);
	}
	.head > div {
		display: grid;
		gap: var(--sp-5);
	}
	.grid {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: var(--sp-4);
		perspective: 1200px;
	}
	.grid > li {
		display: grid;
	}
	.tile {
		position: relative;
		display: grid;
		gap: var(--sp-3);
		container-type: inline-size;
		min-height: 23rem;
		padding: var(--sp-6);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background:
			radial-gradient(90% 60% at 50% 0%, rgb(255 255 255 / 0.04), transparent 70%),
			linear-gradient(180deg, var(--bg-2), var(--bg-1));
		color: var(--text);
		text-decoration: none;
		overflow: hidden;
		isolation: isolate;
		align-content: start;
		transition:
			border-color var(--dur-3),
			box-shadow var(--dur-3);
	}
	.tile:hover {
		border-color: var(--line-strong);
		box-shadow: 0 30px 60px -30px rgb(237 234 227 / 0.18);
	}
	.meta {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-mute);
	}
	.short {
		position: absolute;
		left: var(--sp-5);
		top: 2.4rem;
		font-family: var(--font-display);
		/* fit the model number to the tile width whatever its length */
		font-size: min(7.5rem, calc(150cqi / var(--len)));
		font-weight: 850;
		font-stretch: 112%;
		letter-spacing: -0.05em;
		line-height: 1;
		color: transparent;
		-webkit-text-stroke: 1px rgb(237 234 227 / 0.18);
		z-index: -1;
		white-space: nowrap;
		transition: -webkit-text-stroke-color var(--dur-3);
	}
	.tile:hover .short {
		-webkit-text-stroke-color: rgb(237 234 227 / 0.45);
	}
	.name {
		margin-top: auto;
		padding-top: 6.5rem;
		font-weight: 760;
		font-stretch: 110%;
		font-size: var(--fs-md);
		letter-spacing: -0.015em;
		color: var(--text-hi);
	}
	.gain {
		display: grid;
		gap: 0.2rem;
	}
	.gain b {
		font-size: clamp(2.2rem, 1.4rem + 1.8vw, 3.2rem);
	}
	.gain b:not(.speedup) {
		font-family: var(--font-display);
		font-weight: 820;
		font-stretch: 115%;
		letter-spacing: -0.04em;
		line-height: 1;
		color: var(--text-hi);
	}
	.gain small {
		font-size: 0.4em;
		font-family: var(--font-mono);
		color: var(--text-mute);
	}
	.gain span {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-mute);
	}
	.tbar {
		position: relative;
		height: 4px;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		overflow: hidden;
	}
	.bo,
	.bb {
		position: absolute;
		inset: 0;
		transform-origin: 0 50%;
	}
	.bo {
		background: var(--heat-ramp-hot);
		transform: scaleX(var(--o));
		transition: transform 0.6s var(--ease-out);
	}
	.bb {
		background: var(--before);
		transform: scaleX(var(--b));
		z-index: 1;
	}
	.nums {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text);
	}
	.go {
		position: absolute;
		right: var(--sp-6);
		bottom: var(--sp-6);
		font-size: var(--fs-lg);
		color: var(--text-mute);
		transition:
			transform var(--dur-3) var(--ease-out),
			color var(--dur-2);
	}
	.tile:hover .go {
		transform: translateX(4px);
		color: var(--text-hi);
	}
	.queue {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-3) var(--sp-5);
	}
	.ql {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--text-mute);
	}
	.queue ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
		flex: 1;
	}
	.queue li {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.35rem 0.8rem;
		border: 1px dashed var(--line-strong);
		border-radius: var(--r-pill);
		font-size: var(--fs-xs);
		color: var(--text);
	}
	.plus {
		font-family: var(--font-mono);
		color: var(--text-mute);
	}
	@media (max-width: 1100px) {
		.grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 720px) {
		.head {
			grid-template-columns: minmax(0, 1fr);
		}
		.grid {
			grid-template-columns: minmax(0, 1fr);
		}
		.tile {
			min-height: 0;
		}
		.name {
			padding-top: 4.5rem;
		}
	}
</style>
