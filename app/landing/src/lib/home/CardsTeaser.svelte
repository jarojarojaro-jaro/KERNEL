<script lang="ts">
	/**
	 * Twoja karta: the measured cards as the same product tiles as the explorer gallery (GpuArt render
	 * warmed by heatOf(gain), identity, headline gain of its pick run), linking into the explorer;
	 * planned cards as queue chips.
	 */
	import { heatOf } from '$lib/cards/explorer';
	import { headline } from '$lib/cards/explorer';
	import GpuArt from '$lib/cards/GpuArt.svelte';
	import { tilt } from '$lib/fx/actions';
	import { MODEL_STYLE } from '$lib/modelStyle';
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
	let hover = $state<string | null>(null);
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
				{@const prefix = t.card.name.split(t.card.short)[0].trim()}
				<li style="--th:{heatOf(t.gain)}">
					<!-- the same product tile as the cards explorer gallery: render, identity, gain -->
					<article class="tile" use:tilt={{ max: 5 }} onpointerenter={() => (hover = t.card.id)} onpointerleave={() => (hover = null)} onfocusin={() => (hover = t.card.id)} onfocusout={() => (hover = null)}>
						<div class="art"><GpuArt label={t.card.short} vendor={t.card.vendor} vram={t.card.vramGB} heat={heatOf(t.gain)} live={hover === t.card.id} flat /></div>
						<div class="body">
							<p class="pre"><span class="dot" aria-hidden="true"></span>{prefix}</p>
							<h3 class="short"><a class="stretch" href={cardsHref(lang, t.card.id)}>{t.card.short}</a></h3>
							<p class="spec">{t.card.arch} · {t.card.vramGB}&nbsp;GB</p>
							<div class="stat">
								{#if t.gain !== null}
									<p class="x"><b class="speedup" class:speedup--down={t.gain < 1} style="--rh:{heatOf(t.gain)}">{fmtRatio(t.gain, lang)}</b> <span>{c.faster}</span></p>
									<p class="tps"><span class="m">{MODEL_STYLE[t.run.model].short}</span> <span><span class="cold">{num(t.before, lang)}</span> → <span class="hot">{num(t.ours, lang)}</span>&nbsp;t/s</span></p>
								{:else}
									<p class="x"><b class="plain">{num(t.ours, lang)} <small>t/s</small></b></p>
									<p class="tps">{c.diff}</p>
								{/if}
							</div>
						</div>
					</article>
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
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--sp-4);
		perspective: 1200px;
	}
	.grid > li {
		display: grid;
	}
	/* product tile (same design as the explorer gallery): render left, identity and gain right */
	.tile {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
		align-items: center;
		gap: var(--sp-3) var(--sp-4);
		height: 100%;
		padding: var(--sp-4);
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		background:
			radial-gradient(120% 80% at 18% 50%, rgb(255 122 26 / calc(0.03 + var(--th) * 0.12)), transparent 60%),
			radial-gradient(90% 70% at 100% 0%, rgb(226 64 28 / calc(0.02 + var(--th) * 0.06)), transparent 60%),
			linear-gradient(180deg, rgb(17 15 14 / 0.94), rgb(7 7 8 / 0.94));
		overflow: hidden;
		isolation: isolate;
		transition:
			border-color var(--dur-3),
			box-shadow var(--dur-3) var(--ease-out);
	}
	.tile::before {
		content: '';
		position: absolute;
		inset: -10% -10% 40%;
		z-index: -1;
		background: radial-gradient(50% 50% at 30% 50%, rgb(255 122 26 / calc(0.1 + var(--th) * 0.32)), transparent 70%);
		opacity: 0.6;
		transition: opacity 0.6s var(--ease-out);
		pointer-events: none;
	}
	.tile:is(:hover, :focus-within) {
		border-color: rgb(255 122 26 / calc(0.25 + var(--th) * 0.45));
		box-shadow: 0 0 40px -16px rgb(255 122 26 / calc(0.3 + var(--th) * 0.5));
	}
	.tile:is(:hover, :focus-within)::before {
		opacity: 1;
	}
	.tile:has(.stretch:focus-visible) {
		outline: 2px solid var(--focus);
		outline-offset: 3px;
	}
	.art {
		width: 100%;
		user-select: none;
	}
	.body {
		display: grid;
		gap: 0.3rem;
		min-width: 0;
	}
	.pre,
	.spec,
	.tps {
		margin: 0;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.pre {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}
	.dot {
		width: 0.4rem;
		height: 0.4rem;
		border-radius: 50%;
		background: var(--heat-3);
		box-shadow: 0 0 8px var(--heat-3);
	}
	.short {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(1.5rem, 1.1rem + 0.9vw, 2.1rem);
		font-weight: 850;
		line-height: 0.95;
		letter-spacing: -0.035em;
		white-space: nowrap;
	}
	.stretch {
		color: var(--text-hi);
		text-decoration: none;
		transition: color var(--dur-2);
	}
	.stretch::after {
		content: '';
		position: absolute;
		inset: 0;
	}
	.stretch:focus-visible {
		outline: none;
	}
	.tile:is(:hover, :focus-within) .stretch {
		color: var(--heat-5);
	}
	.stat {
		display: grid;
		gap: 0.2rem;
		margin-top: var(--sp-2);
		padding-top: var(--sp-2);
		border-top: 1px solid rgb(255 122 26 / calc(0.15 + var(--th) * 0.35));
	}
	.x {
		margin: 0;
		display: flex;
		align-items: baseline;
		gap: 0.5rem;
	}
	.x b {
		font-size: clamp(1.35rem, 1.1rem + 0.5vw, 1.7rem);
	}
	.x b.plain {
		font-family: var(--font-display);
		font-weight: 800;
		color: var(--text-hi);
	}
	.x span,
	.x small {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-mute);
	}
	.tps {
		display: flex;
		flex-wrap: wrap;
		gap: 0.1rem 0.6rem;
	}
	.tps .m {
		color: var(--text);
	}
	.cold {
		color: var(--before);
	}
	.hot {
		color: var(--heat-4);
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
	@media (max-width: 720px) {
		.head {
			grid-template-columns: minmax(0, 1fr);
		}
		.grid {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
