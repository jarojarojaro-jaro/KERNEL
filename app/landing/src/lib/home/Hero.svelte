<script lang="ts">
	/**
	 * Hero (design/REDESIGN.md §6): heat field, a two-tier headline (CSS only: it is the LCP) — the
	 * steel line "Ten sam sprzęt. Ten sam model." over the focal, much larger heat line "Po prostu
	 * szybciej." — one custom primary CTA with a slowly turning heat edge plus a text link, then the
	 * duel (fx/StreamDuel, shared with the final CTA): two terminals stream the same answer nonstop,
	 * without Podkręt (steel) and with it (heat), each with a small live speedometer in its header,
	 * on our lab card (RX 7900 XTX × Qwen3.8-27B, upstream llama.cpp default vs our engine, one
	 * script, ABBA); MTP bursts from the measured step time; the speed-up counts up once.
	 * No caption or source pill here: conditions and sources live on /metodologia (the „Jak mierzymy”
	 * link), in the boost section and on the card page.
	 * Redline flare: when the stream starts, the heat field runs hot, a bloom sweeps the hero once and
	 * the heat line flares.
	 */
	import { magnetic } from '$lib/fx/actions';
	import HeatField from '$lib/fx/HeatField.svelte';
	import SpeedLines from '$lib/fx/SpeedLines.svelte';
	import StreamDuel from '$lib/fx/StreamDuel.svelte';
	import { variantLabel } from '$lib/data/measurements';
	import { fmtTps } from '$lib/format';
	import { cardsHref, href, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { fill, heroDial, RACE_CARD, RACE_MODEL, RACE_RUN, RACE_V } from './data';
	import Kin from './Kin.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].hero);
	const r = $derived(c.race);
	const dl = $derived(copy[lang].duel);

	const cold = RACE_V.before;
	const hot = RACE_V.ours;
	const dial = heroDial(hot.decode!.v);
	const gain = hot.decode!.v / cold.decode!.v;
	/** Tokens accepted per step = measured t/s × measured ms per step (MTP bursts; 1 without MTP). */
	const burstOf = (v: typeof hot) => (v.msStep ? Math.max(1, (v.decode!.v * v.msStep.v) / 1000) : 1);
	const summary = $derived(
		fill(r.summary, { card: RACE_CARD.name, model: RACE_MODEL, quant: RACE_RUN.quant, a0: fmtTps(cold.decode!.v, lang), a2: fmtTps(hot.decode!.v, lang) })
	);
	const lanes = $derived([
		{ id: 'cold' as const, tag: dl.without, who: variantLabel(RACE_RUN, cold.key)[lang], tps: cold.decode!.v, burst: burstOf(cold) },
		{ id: 'hot' as const, tag: dl.with, who: variantLabel(RACE_RUN, hot.key)[lang], tps: hot.decode!.v, burst: burstOf(hot) }
	]);

	/** The stream start: the field runs hot for a moment, one bloom sweep and one heat-line flare. */
	let heat = $state(false);
	let bloomed = $state(false);
	function onstart() {
		heat = bloomed = true;
		setTimeout(() => (heat = false), 2600);
	}
</script>

<section class="hero" class:hot={heat} aria-labelledby="hero-title">
	<HeatField heat={heat ? 1 : 0.8} boost={heat ? 1 : 0.35} />
	<div class="veil" aria-hidden="true"></div>
	{#if bloomed}<div class="bloom" aria-hidden="true"></div>{/if}
	<div class="inner">
		<h1 id="hero-title" class="title">
			<Kin lines={c.title} wide={[1]} heat={[1]} cold={[0]} delays={[0, 120]} />
		</h1>
		<div class="actions">
			<a class="ignite" href={cardsHref(lang)} use:magnetic={{ max: 6 }}>
				<span class="ig-label">{c.cta}</span>
				<svg class="ig-arrow" viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><path d="M3 10h13M11 4.5 16.5 10 11 15.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
			</a>
			<a class="mlink" href={href(lang, '/methodology')}>
				<span class="ml-label">{c.ctaSecondary}</span>
				<svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true"><path d="M4.5 11.5 11.5 4.5M6 4.5h5.5V10" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
			</a>
		</div>
		<div class="race">
			<div class="lines"><SpeedLines /></div>
			<!-- keyed: the duel caches its text nodes, so a language switch mounts a fresh one -->
			{#key lang}
				<StreamDuel {lanes} {gain} text={r.stream} {lang} labels={dl} {summary} {dial} countUp seam {onstart} />
			{/key}
		</div>
	</div>
</section>

<style>
	.hero {
		position: relative;
		min-height: 100vh;
		min-height: 100svh;
		display: grid;
		align-items: center;
		isolation: isolate;
		overflow: clip;
		background: var(--bg-0);
	}
	.hero :global(.heatfield) {
		z-index: -2;
	}
	/* the field's faint speed lines stay at the edges: never behind the text columns */
	.hero :global(.heatfield .streak-frame) {
		-webkit-mask-image: linear-gradient(90deg, #000, transparent 9%, transparent 91%, #000);
		mask-image: linear-gradient(90deg, #000, transparent 9%, transparent 91%, #000);
	}
	/* darken the top so the header and headline sit on near-black; heat rises from below */
	.veil {
		position: absolute;
		inset: 0;
		z-index: -1;
		pointer-events: none;
		background:
			linear-gradient(180deg, rgb(5 5 6 / 0.9) 0%, rgb(5 5 6 / 0.45) 45%, rgb(5 5 6 / 0.2) 75%, rgb(5 5 6 / 0.55) 100%),
			radial-gradient(60% 45% at 25% 30%, rgb(5 5 6 / 0.5), transparent 70%);
	}
	/* redline flare: one warm light sweep across the whole hero when the race starts */
	.bloom {
		position: absolute;
		inset: -10% 0;
		z-index: 3;
		pointer-events: none;
		mix-blend-mode: screen;
		background: linear-gradient(100deg, transparent 30%, rgb(255 122 26 / 0.16) 42%, rgb(255 243 214 / 0.32) 50%, rgb(255 122 26 / 0.16) 58%, transparent 70%);
		transform: translate3d(-100%, 0, 0);
		animation: bloom 1.3s var(--ease-in-out) 0.25s both;
	}
	@keyframes bloom {
		to {
			transform: translate3d(100%, 0, 0);
		}
	}
	/* inline-block always (toggling display with the flare would be a layout change) */
	.title :global(.kin--heat > [aria-hidden]) {
		display: inline-block;
	}
	.hot .title :global(.kin--heat > [aria-hidden]) {
		animation: head-flare 1.4s var(--ease-out) 0.3s both;
	}
	@keyframes head-flare {
		25% {
			filter: brightness(1.18) drop-shadow(0 0 24px rgb(255 122 26 / 0.35));
		}
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		padding-block: clamp(5.5rem, 3rem + 5vh, 7rem) clamp(1.5rem, 1rem + 2vh, 2.5rem);
		display: grid;
		justify-items: center;
		gap: clamp(1.25rem, 0.5rem + 2.4vh, 2.4rem);
		text-align: center;
	}
	/* two tiers: the steel line, then the focal heat line much larger (font-size = heat line) */
	.title {
		margin: 0;
		font-family: var(--font-display);
		font-size: min(10.4vw, 15svh, 8.2rem);
		font-weight: 840;
		font-stretch: 118%;
		line-height: 0.86;
		letter-spacing: -0.05em;
		color: var(--text-hi);
		font-kerning: none;
		text-align: center;
	}
	.title :global(.kin--wide) {
		transform-origin: 50% 50%;
	}
	.title :global(.kin--cold) {
		font-size: 0.355em;
		font-weight: 760;
		font-stretch: 108%;
		letter-spacing: -0.035em;
		line-height: 1;
		margin-bottom: 0.32em;
	}
	.title :global(.kin--heat .ch) {
		/* one soft bloom (≈24px, 35%): the letters stay crisp */
		text-shadow: 0 0 24px rgb(255 122 26 / 0.35);
	}
	/* ---- CTAs ---- */
	.actions {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		align-items: center;
		gap: var(--sp-4) clamp(1.5rem, 3vw, 2.5rem);
	}
	@property --ig {
		syntax: '<angle>';
		inherits: false;
		initial-value: 0deg;
	}
	/* primary: a dark key with a living heat edge (conic border, slowly turning) and an ember glow */
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
		color: var(--text-hi);
		font-weight: 680;
		font-size: var(--fs-md);
		letter-spacing: -0.01em;
		text-decoration: none;
		transition:
			transform 0.25s var(--ease-out),
			box-shadow 0.35s var(--ease-out);
	}
	.ignite::before,
	.ignite::after {
		content: '';
		position: absolute;
		border-radius: inherit;
		background: conic-gradient(
			from var(--ig),
			var(--heat-2),
			var(--heat-3) 12%,
			var(--heat-5) 20%,
			var(--heat-4) 28%,
			rgb(255 122 26 / 0.18) 42%,
			rgb(255 122 26 / 0.12) 78%,
			var(--heat-2)
		);
		animation: ig-turn 5.5s linear infinite;
		pointer-events: none;
	}
	/* the 1.5px edge */
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
	/* the glow behind it */
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
	.ignite:active {
		transform: scale(0.97);
	}
	.ignite:focus-visible {
		outline: 2px solid var(--heat-4);
		outline-offset: 4px;
	}
	/* secondary: a refined text link, underline draws in, arrow lifts */
	.mlink {
		position: relative;
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		padding-block: 0.4rem;
		color: var(--text-hi);
		font-weight: 600;
		font-size: var(--fs-md);
		text-decoration: none;
	}
	.ml-label {
		position: relative;
	}
	.ml-label::after {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		bottom: -0.2em;
		height: 1px;
		background: currentColor;
		transform-origin: 0 50%;
		transform: scaleX(0.3);
		opacity: 0.6;
		transition:
			transform 0.4s var(--ease-out),
			opacity 0.4s;
	}
	.mlink svg {
		transition: transform 0.3s var(--ease-spring);
	}
	.mlink:hover .ml-label::after,
	.mlink:focus-visible .ml-label::after {
		transform: none;
		opacity: 1;
	}
	.mlink:hover svg,
	.mlink:focus-visible svg {
		transform: translate3d(2px, -2px, 0);
	}
	.mlink:focus-visible {
		outline: 2px solid var(--text-hi);
		outline-offset: 4px;
		border-radius: 4px;
	}
	/* the speed lines run the full width of the screen behind the duel (the hero clips them) */
	.lines {
		position: absolute;
		z-index: -1;
		inset: -14% calc(50% - 50vw) -10%;
	}
	.race {
		position: relative;
		width: min(100%, 72rem);
		min-width: 0;
		text-align: left;
		/* the stream windows: as tall as the first screen allows (stacked on phones: short) */
		--duel-win: clamp(7.5rem, 30svh - 6rem, 12rem);
		--duel-win-sm: 6.6rem;
	}
	@media (prefers-reduced-motion: no-preference) {
		/* the headline lands first; the CTAs follow, then the race rises */
		:global(html.js) .actions {
			animation: fade-up 0.6s var(--ease-out) 0.25s both;
		}
		:global(html.js) .race {
			animation: rise 0.7s var(--ease-out) 0.35s both;
		}
	}
	/* transform-only: the CTAs and the race are visible from the first painted frame */
	@keyframes fade-up {
		from {
			transform: translate3d(0, 0.75rem, 0);
		}
	}
	@keyframes rise {
		from {
			transform: translate3d(0, 1.5rem, 0);
		}
	}
	@media (max-width: 640px) {
		.hero {
			align-items: start;
			min-height: 0;
		}
		.inner {
			padding-top: 5.25rem;
			gap: var(--sp-4);
		}
		/* condensed cut: steel on two lines, the heat line on two big lines */
		.title {
			font-size: 16.5vw;
			font-stretch: 82%;
			line-height: 0.84;
		}
		.title :global(.kin--wide) {
			font-stretch: 82%;
		}
		.title :global(.kin--cold) {
			font-size: 0.5em;
			font-stretch: 86%;
			max-width: 8.4em;
			margin-inline: auto;
			line-height: 0.98;
			margin-bottom: 0.22em;
		}
		/* primary and the text link on one row */
		.actions {
			flex-wrap: nowrap;
			gap: var(--sp-4);
		}
		.ignite {
			min-height: 2.9rem;
			padding: 0 1rem 0 1.15rem;
			gap: 0.6rem;
			font-size: var(--fs-sm);
			white-space: nowrap;
		}
		.mlink {
			font-size: var(--fs-sm);
			white-space: nowrap;
		}
	}
	/* the smallest phones: the text link drops under the primary instead of running off the edge */
	@media (max-width: 380px) {
		.actions {
			flex-wrap: wrap;
			row-gap: var(--sp-2);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.bloom {
			display: none;
		}
		.hot .title :global(.kin--heat > [aria-hidden]),
		.ignite::before,
		.ignite::after {
			animation: none;
		}
	}
</style>
