<script lang="ts">
	/**
	 * Twoja karta: the measured cards as a lineup of product tiles. Each tile is a dark showroom in
	 * the maker's colour (NVIDIA green, AMD red: identity only), the card's render angled on a
	 * reflective floor, its name, the headline gain of its pick run (heat: speed) and the two measured
	 * speeds as bars on one scale. Links into the explorer.
	 *
	 * Alive: while the lineup is on screen one card at a time is "live" (fans spin, a light sweep
	 * passes, the render turns to face you), cycling; hover or focus takes over. On narrow screens
	 * the tiles are a snap carousel and the live card is the one in view. Reduced motion: no cycle,
	 * no spin (GpuArt), bars at rest.
	 */
	import { untrack } from 'svelte';
	import { heatOf, headline } from '$lib/cards/explorer';
	import GpuArt, { artSpec } from '$lib/cards/GpuArt.svelte';
	import Ratio from '$lib/cards/Ratio.svelte';
	import { play, tilt, visible } from '$lib/fx/actions';
	import { reducedMotion } from '$lib/fx/motion';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { MODEL_INFO, variantLabel } from '$lib/data/measurements';
	import { cardsHref, num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { CARDS, decode } from './data';
	import Duo from './Duo.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].cards);
	/** Same headline rule as the explorer gallery: the pick, unless it has no same-script pair. */
	const tiles = CARDS.flatMap((card) => {
		const d = headline(card);
		if (!d) return [];
		return [{ card, run: d.run, gain: d.ratio, src: d.run.gain?.total?.src ?? d.run.src, before: decode(d.before), ours: decode(d.ours), beforeKey: d.before.key, oursKey: d.ours.key, model: MODEL_INFO[d.run.model].name }];
	});
	const MAKER: Record<string, string> = { nvidia: 'NVIDIA', amd: 'AMD' };
	/** The render fills ~90% of its stage (board + bracket, 640-unit viewBox); longer boards stay
	 * longer, so the real length order survives. Transform only: no layout change. */
	const artScale = (label: string, vendor: string, vram: number | null) => Math.max(1, (0.9 * 640) / (artSpec(label, vendor, vram).len + 22)).toFixed(3);

	let hover = $state<string | null>(null);
	let spot = $state(-1);
	let onScreen = $state(false);
	let rep = $state(0);
	let grid: HTMLUListElement | undefined = $state();
	const live = $derived(hover ?? (spot >= 0 ? (tiles[spot]?.card.id ?? null) : null));

	/** The live card cycles while on screen (wide); on the narrow carousel it is the card in view. */
	$effect(() => {
		if (!onScreen || !grid || reducedMotion()) return;
		const g = grid;
		const narrow = matchMedia('(max-width: 640px)');
		const inView = () => {
			const [a, b] = g.children as unknown as HTMLElement[];
			const step = a && b ? b.offsetLeft - a.offsetLeft : 1;
			return Math.max(0, Math.min(tiles.length - 1, Math.round(g.scrollLeft / step)));
		};
		untrack(() => (spot = narrow.matches ? inView() : Math.max(0, spot)));
		const id = setInterval(() => {
			if (!narrow.matches) spot = (spot + 1) % tiles.length;
		}, 3200);
		const scroll = () => {
			if (narrow.matches) spot = inView();
		};
		g.addEventListener('scroll', scroll, { passive: true });
		return () => {
			clearInterval(id);
			g.removeEventListener('scroll', scroll);
		};
	});
</script>

<section id="cards" class="cards heat-top" aria-labelledby="cards-title">
	<div class="inner">
		<header class="head">
			<div>
				<Duo text={c.title} id="cards-title" mode="plain" />
			</div>
			<p class="lede">{c.lede}</p>
		</header>
		<ul class="grid" role="list" bind:this={grid} use:visible={(v) => (onScreen = v)} use:play={{ threshold: 0.35, onplay: () => rep++ }} class:played={rep > 0}>
			{#each tiles as t (t.card.id)}
				{@const prefix = t.card.name.split(t.card.short)[0].trim()}
				<li class="v-{t.card.vendor}" style="--th:{heatOf(t.gain)}; --b:{(t.before / Math.max(t.before, t.ours)).toFixed(4)}; --o:{(t.ours / Math.max(t.before, t.ours)).toFixed(4)}">
					<article class="tile" class:live={live === t.card.id} use:tilt={{ max: 5 }} onpointerenter={() => (hover = t.card.id)} onpointerleave={() => (hover = null)} onfocusin={() => (hover = t.card.id)} onfocusout={() => (hover = null)}>
						<p class="brand">
							<span class="maker">{MAKER[t.card.vendor] ?? t.card.vendor}</span>
							<span class="pre">{prefix}</span>
							<span class="vram">{t.card.vramGB}&nbsp;GB</span>
						</p>
						<div class="stage" aria-hidden="true">
							<div class="art" style="--as:{artScale(t.card.short, t.card.vendor, t.card.vramGB)}">
								<GpuArt label={t.card.short} vendor={t.card.vendor} vram={t.card.vramGB} heat={heatOf(t.gain)} live={live === t.card.id} />
							</div>
							<span class="sweep"></span>
						</div>
						<div class="id">
							<h3 class="short"><a class="stretch" href={cardsHref(lang, t.card.id)}>{t.card.short}</a></h3>
							{#if t.gain !== null}
								<span class="x"><Ratio value={t.gain} {lang} size="md" replay={rep} /></span>
							{/if}
						</div>
						<p class="spec">
							<span>{t.card.arch}</span>
							{#if t.gain !== null}<span class="fx">{c.faster}</span>{/if}
						</p>
						<div class="bars">
							<p class="speed cold">
								<span class="lb">{variantLabel(t.run, t.beforeKey)[lang]}</span>
								<b>{num(t.before, lang)}</b>
								<span class="track"><i style="--w:var(--b)"></i></span>
							</p>
							<p class="speed hot">
								<span class="lb">{variantLabel(t.run, t.oursKey)[lang]}</span>
								<b>{num(t.ours, lang)}&nbsp;<small>t/s</small></b>
								<span class="track"><i style="--w:var(--o)"></i></span>
							</p>
							<p class="model"><span class="m">{MODEL_STYLE[t.run.model].short}</span>{#if t.gain === null}<span>{c.diff}</span>{/if}</p>
						</div>
					</article>
				</li>
			{/each}
		</ul>
		<div class="fn">
			<p>
				<span>{c.note}</span>
				<SourceTip {lang} src={tiles.flatMap((t) => [t.src, ...t.run.variants.map((v) => v.decode?.src ?? '')]).filter(Boolean)} note={tiles.map((t) => `${t.card.short}: ${t.run.metric[lang]}`).join(' ')} />
			</p>
			<a class="cta cta--line" href={cardsHref(lang)}>{c.open} <span class="arrow" aria-hidden="true">→</span></a>
		</div>
	</div>
</section>

<style>
	.cards {
		padding-block: clamp(3.5rem, 2.5rem + 3vw, 6rem);
		background: var(--bg-0);
		overflow: clip;
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		gap: clamp(2rem, 4vw, 3.5rem);
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

	/* the lineup: four across on wide screens, two on tablets, a snap carousel on phones */
	.grid {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: var(--sp-4);
		perspective: 1200px;
	}
	/* every tile spans the same five rows (brand, stage, name, spec, speeds): rows line up across
	 * the lineup whatever the size of each gain */
	.grid > li {
		display: grid;
		grid-row: span 5;
		grid-template-rows: subgrid;
		row-gap: 0;
		min-width: 0;
		/* maker colour (identity only; speed is always heat) */
		--v: 118 185 0;
		--v-hi: #9be22a;
		--v-deep: #0b1405;
	}
	.grid > li.v-amd {
		--v: 237 28 36;
		--v-hi: #ff5a5f;
		--v-deep: #170607;
	}

	/* a product tile: always a dark showroom, also in the light theme */
	.tile {
		--text-hi: #edeae3;
		--text: #bdb9b1;
		--text-mute: #8e8a83;
		--before: #7d8794;
		color-scheme: dark;
		position: relative;
		display: grid;
		grid-row: 1 / -1;
		grid-template-rows: subgrid;
		row-gap: 0;
		padding: var(--sp-4) var(--sp-4) var(--sp-5);
		border-radius: var(--r-xl);
		color: var(--text);
		background:
			radial-gradient(90% 55% at 50% 34%, rgb(var(--v) / 0.3), transparent 70%),
			linear-gradient(155deg, rgb(var(--v) / 0.34), rgb(var(--v) / 0.06) 32%, transparent 52%),
			linear-gradient(200deg, var(--v-deep), #070708 62%);
		box-shadow:
			inset 0 0 0 1px rgb(var(--v) / 0.32),
			inset 0 1px 0 rgb(255 255 255 / 0.08),
			0 24px 50px -30px rgb(0 0 0 / 0.9);
		overflow: hidden;
		isolation: isolate;
		transition: box-shadow 0.6s var(--ease-out);
	}
	/* the maker's diagonal accent across the top corner */
	.tile::before {
		content: '';
		position: absolute;
		z-index: -1;
		top: -30%;
		right: -18%;
		width: 55%;
		height: 70%;
		background: linear-gradient(115deg, transparent 0 38%, rgb(var(--v) / 0.42) 38% 41%, transparent 41% 47%, rgb(var(--v) / 0.2) 47% 48.5%, transparent 48.5%);
		pointer-events: none;
	}
	.tile.live,
	.tile:is(:hover, :focus-within) {
		box-shadow:
			inset 0 0 0 1px rgb(var(--v) / 0.75),
			inset 0 1px 0 rgb(255 255 255 / 0.12),
			0 0 50px -14px rgb(var(--v) / 0.55),
			0 24px 50px -30px rgb(0 0 0 / 0.9);
	}
	.tile:has(.stretch:focus-visible) {
		outline: 2px solid var(--focus);
		outline-offset: 3px;
	}

	.brand {
		margin: 0;
		display: flex;
		align-items: center;
		gap: 0.55rem;
		min-width: 0;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
		white-space: nowrap;
	}
	.maker {
		font-family: var(--font-display);
		font-size: 0.8rem;
		font-weight: 850;
		font-style: italic;
		letter-spacing: 0.06em;
		color: var(--v-hi);
		text-shadow: 0 0 14px rgb(var(--v) / 0.6);
	}
	.pre {
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.vram {
		margin-left: auto;
		padding: 0.2rem 0.5rem;
		border-radius: var(--r-pill);
		box-shadow: inset 0 0 0 1px rgb(var(--v) / 0.45);
		color: var(--text);
		letter-spacing: 0.06em;
	}

	/* the stage: the render angled over a floor lit in the maker's colour */
	.stage {
		position: relative;
		margin: var(--sp-2) calc(-1 * var(--sp-2)) var(--sp-3);
		padding-block: 7% 9%;
		user-select: none;
	}
	.stage::before {
		content: '';
		position: absolute;
		left: 6%;
		right: 6%;
		bottom: 2%;
		height: 26%;
		border-radius: 50%;
		background: radial-gradient(closest-side, rgb(var(--v) / 0.38), rgb(var(--v) / 0.08) 60%, transparent);
		filter: blur(6px);
		transform: scaleY(0.7);
	}
	/* scaled by size, not transform; the margins keep every stage the same height (viewBox
	 * 640×300: height = 46.875% of width) */
	.art {
		position: relative;
		width: calc(var(--as, 1) * 100%);
		margin-inline: calc((1 - var(--as, 1)) * 50%);
		margin-block: calc((1 - var(--as, 1)) * 23.4375%);
	}
	/* the maker's light behind the card replaces the render's own glow; the heat strip stays */
	.art :global(.glow) {
		background: radial-gradient(closest-side, rgb(var(--v) / calc(0.22 + var(--th) * 0.2)), transparent);
	}
	.sweep {
		position: absolute;
		inset: -10% auto -10% 0;
		width: 30%;
		background: linear-gradient(100deg, transparent, rgb(255 255 255 / 0.12), transparent);
		transform: translateX(-120%) skewX(-16deg);
		opacity: 0;
		pointer-events: none;
	}
	@media (prefers-reduced-motion: no-preference) {
		.tile.live .sweep {
			animation: sweep 1.4s var(--ease-out) 0.15s both;
		}
	}
	@keyframes sweep {
		from {
			opacity: 1;
			transform: translateX(-120%) skewX(-16deg);
		}
		to {
			opacity: 1;
			transform: translateX(420%) skewX(-16deg);
		}
	}

	.id {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--sp-3);
		min-width: 0;
	}
	.short {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(1.6rem, 1.1rem + 1vw, 2.2rem);
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
		z-index: 1;
	}
	.stretch:focus-visible {
		outline: none;
	}
	.tile:is(:hover, :focus-within) .stretch {
		color: #fff;
	}
	.x {
		line-height: 0.9;
	}
	.spec {
		margin: 0.35rem 0 0;
		display: flex;
		justify-content: space-between;
		gap: var(--sp-3);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.fx {
		text-transform: uppercase;
		letter-spacing: 0.1em;
	}

	/* the two measured speeds on one scale (the faster one = full width) */
	.bars {
		align-self: end;
		display: grid;
		gap: 0.55rem;
		margin-top: var(--sp-4);
		padding-top: var(--sp-3);
		border-top: 1px solid rgb(255 255 255 / 0.08);
	}
	.speed {
		margin: 0;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 0.3rem var(--sp-2);
		align-items: baseline;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
	}
	.lb {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: var(--text-mute);
	}
	.speed b {
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}
	.speed small {
		font-size: 1em;
		color: var(--text-mute);
		font-weight: 400;
	}
	.cold b {
		color: var(--before);
	}
	.hot b {
		color: var(--heat-4);
	}
	.track {
		grid-column: 1 / -1;
		height: 0.4rem;
		border-radius: var(--r-pill);
		background: rgb(255 255 255 / 0.06);
		overflow: hidden;
	}
	.track i {
		display: block;
		height: 100%;
		width: calc(var(--w) * 100%);
		border-radius: inherit;
		transform-origin: 0 50%;
	}
	.cold .track i {
		background: var(--before);
		opacity: 0.7;
	}
	.hot .track i {
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 12px rgb(255 122 26 / 0.6);
	}
	@media (prefers-reduced-motion: no-preference) {
		.played .track i {
			animation: fillbar 1.3s var(--ease-out) backwards;
		}
		.played .hot .track i {
			animation-delay: 0.25s;
		}
	}
	@keyframes fillbar {
		from {
			transform: scaleX(0);
		}
	}
	.model {
		margin: 0.15rem 0 0;
		display: flex;
		flex-wrap: wrap;
		gap: 0.1rem 0.6rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.model .m {
		color: var(--text);
	}

	.fn {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-4) var(--sp-6);
	}
	.fn p {
		margin: 0;
		flex: 1 1 28rem;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2) var(--sp-3);
		font-size: var(--fs-xs);
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
	}
	@media (max-width: 640px) {
		.grid {
			grid-template-columns: none;
			grid-auto-flow: column;
			grid-auto-columns: min(84%, 22rem);
			margin-inline: calc(-1 * var(--gutter));
			padding: var(--sp-2) var(--gutter) var(--sp-4);
			scroll-padding-inline: var(--gutter);
			overflow-x: auto;
			overscroll-behavior-x: contain;
			scroll-snap-type: x mandatory;
			scrollbar-width: none;
		}
		.grid::-webkit-scrollbar {
			display: none;
		}
		.grid > li {
			scroll-snap-align: start;
		}
	}
</style>
