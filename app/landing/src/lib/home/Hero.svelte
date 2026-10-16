<script lang="ts">
	/**
	 * Hero (design/REDESIGN.md §6): heat field, a two-tier headline (CSS only: it is the LCP) — the
	 * steel line "Ten sam sprzęt. Ten sam model." over the focal, much larger heat line "Po prostu
	 * szybciej." — one custom primary CTA with a slowly turning heat edge plus a text link, then the
	 * race as two frameless typographic streams (LiveRace): RTX 3090 × Qwen3.8-27B, the typical app
	 * (a0) vs our engine (a2), same script, MTP bursts from the measured tokens per step.
	 * Conditions and sources live only in the „źródło” popover. Other pairs: /wyniki and card pages.
	 * Redline flare: while the race starts, the heat field runs hot, a bloom sweeps the hero once and
	 * the heat line flares.
	 */
	import { magnetic } from '$lib/fx/actions';
	import HeatField from '$lib/fx/HeatField.svelte';
	import LiveRace from '$lib/fx/LiveRace.svelte';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { variantLabel } from '$lib/data/measurements';
	import { TOK_PER_WORD } from '$lib/estimator';
	import { fmtTps, localizeDecimals } from '$lib/format';
	import { cardsHref, href, num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { fill, HERO_CARD, HERO_MODEL, HERO_RUN, HERO_V, heroDial } from './data';
	import Kin from './Kin.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].hero);
	const r = $derived(c.race);

	const cold = HERO_V.a0;
	const hot = HERO_V.a2;
	const dial = heroDial(hot.decode!.v);
	const words = $derived(r.text.split(/\s+/).filter(Boolean).length);
	const vars = $derived({
		card: HERO_CARD.name,
		model: HERO_MODEL,
		quant: HERO_RUN.quant,
		a0: fmtTps(cold.decode!.v, lang),
		a2: fmtTps(hot.decode!.v, lang),
		words,
		tok: Math.round(words * TOK_PER_WORD[lang]),
		tpw: num(TOK_PER_WORD[lang], lang, 2)
	});
	const lanes = $derived([
		{ id: 'cold', label: variantLabel(HERO_RUN, 'a0')[lang], sub: r.coldSub, tps: cold.decode!.v, hot: false, burst: cold.tokStep?.v, lo: cold.decode!.lo, hi: cold.decode!.hi },
		{ id: 'hot', label: variantLabel(HERO_RUN, 'a2')[lang], sub: r.hotSub, tps: hot.decode!.v, hot: true, burst: hot.tokStep?.v, lo: hot.decode!.lo, hi: hot.decode!.hi }
	]);
	const src = [HERO_RUN.src, cold.decode!.src, hot.decode!.src, cold.tokStep?.src, hot.tokStep?.src, cold.msStep?.src, hot.msStep?.src, HERO_RUN.conditionsSrc, 'TOK_PER_WORD: raport 06 §2.1.2'].filter(
		(x): x is string => !!x
	);
	/** The sheet's "skąd zysk" cells (honest attribution: upstream MTP flags vs our engine). */
	const gainWhy = $derived(HERO_RUN.gainText ? localizeDecimals(HERO_RUN.gainText[lang].join(' · ').replaceAll('\u0060', ''), lang) : '');
	const burstText = $derived(
		[
			hot.tokStep ? fill(r.burstNote, { burst: num(hot.tokStep.v, lang, 2) }) : '',
			cold.msStep && hot.msStep ? fill(r.msNote, { a: num(cold.msStep.v, lang, 2), b: num(hot.msStep.v, lang, 2) }) : ''
		]
			.filter(Boolean)
			.join('; ')
	);
	const liveText = $derived(
		fill(r.liveNote, { a0: fmtTps(cold.decode!.v, lang), a2: fmtTps(hot.decode!.v, lang), lo: num(hot.decode!.lo ?? hot.decode!.v, lang, 0), hi: num(hot.decode!.hi ?? hot.decode!.v, lang, 0) })
	);
	const note = $derived(
		[`${HERO_CARD.name} · ${HERO_MODEL} ${HERO_RUN.quant}`, fill(c.answer, vars), HERO_RUN.metric[lang], HERO_RUN.conditions[lang], liveText, gainWhy, burstText, r.stripNote, fill(r.textNote, vars)]
			.filter(Boolean)
			.join('. ')
	);

	let heat = $state(false);
	let flares = $state(0);
	function onheat(h: boolean) {
		heat = h;
		if (h) flares++;
	}
</script>

<section class="hero" class:hot={heat} aria-labelledby="hero-title">
	<HeatField heat={heat ? 1 : 0.62} boost={heat ? 1 : 0} />
	<div class="veil" aria-hidden="true"></div>
	{#key flares}{#if flares > 0}<div class="bloom" aria-hidden="true"></div>{/if}{/key}
	<div class="inner">
		<h1 id="hero-title" class="title">
			<Kin lines={c.title} wide={[1]} heat={[1]} cold={[0]} delays={[100, 420]} />
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
			<LiveRace {lanes} text={r.text} {lang} max={dial.max} redline={dial.redline} startDelay={0.9} prompt={r.prompt} summary={fill(r.summary, vars)} {onheat}>
				{#snippet meta()}
					<span class="now">{HERO_MODEL} {HERO_RUN.quant} · {HERO_CARD.name}</span>
					<SourceTip {lang} {src} {note} />
				{/snippet}
			</LiveRace>
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
			filter: brightness(1.45) drop-shadow(0 0 0.25em rgb(255 122 26 / 0.85));
		}
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		padding-block: clamp(6rem, 3rem + 7vh, 8rem) clamp(1.5rem, 1rem + 2vh, 2.5rem);
		display: grid;
		gap: clamp(1.75rem, 1rem + 3vh, 3rem);
	}
	/* two tiers: the steel line, then the focal heat line much larger (font-size = heat line) */
	.title {
		margin: 0;
		font-family: var(--font-display);
		font-size: min(10.4vw, 19svh);
		font-weight: 840;
		font-stretch: 118%;
		line-height: 0.86;
		letter-spacing: -0.05em;
		color: var(--text-hi);
		font-kerning: none;
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
		text-shadow:
			0 0 0.18em rgb(255 122 26 / 0.35),
			0 0 0.6em rgb(226 64 28 / 0.25);
	}
	/* ---- CTAs ---- */
	.actions {
		display: flex;
		flex-wrap: wrap;
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
	.race {
		min-width: 0;
	}
	.now {
		font-family: var(--font-mono);
		letter-spacing: 0.03em;
		color: var(--text);
	}
	@media (prefers-reduced-motion: no-preference) {
		/* the headline lands first; the CTAs follow, then the race rises */
		:global(html.js) .actions {
			animation: fade-up 0.7s var(--ease-out) 0.8s both;
		}
		:global(html.js) .race {
			animation: rise 0.9s var(--ease-out) 0.95s both;
		}
	}
	@keyframes fade-up {
		from {
			opacity: 0.01;
			transform: translate3d(0, 1rem, 0);
		}
	}
	@keyframes rise {
		from {
			opacity: 0.01;
			transform: translate3d(0, 2rem, 0);
		}
	}
	@media (max-width: 640px) {
		.hero {
			align-items: start;
		}
		.inner {
			padding-top: 5.75rem;
			gap: var(--sp-6);
		}
		/* condensed cut: steel on two lines, the heat line on two big lines */
		.title {
			font-size: 19.5vw;
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
			line-height: 0.98;
			margin-bottom: 0.22em;
		}
		.actions {
			gap: var(--sp-3) var(--sp-5);
		}
		.ignite {
			min-height: 3.1rem;
			font-size: var(--fs-sm);
		}
		.mlink {
			font-size: var(--fs-sm);
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
