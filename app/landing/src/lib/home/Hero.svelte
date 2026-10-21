<script lang="ts">
	import { SITE_PUBLIC } from '$lib/site/public';
	/**
	 * Hero (design/REDESIGN.md §6): heat field, a two-tier headline (CSS only: it is the LCP) — the
	 * steel line "Ten sam sprzęt. Ten sam model." over the focal, much larger heat line "Po prostu
	 * szybciej." — one custom primary CTA with a slowly turning heat edge plus a text link, then the
	 * race, as one full screen: the token highway (fx/Highway) runs full bleed behind everything, out
	 * from under the headline toward the viewer, two lanes of the same text at the measured speeds on
	 * our lab card (RX 7900 XTX × Qwen3.8-27B, upstream llama.cpp default vs our engine, one script,
	 * ABBA; MTP steps from the measured step time). The headline sits around the middle on a soft dark
	 * halo; at the near end two glass windshields show each lane's live answer, readable, each with
	 * its own speedometer on the outer side (fx/Dial, one scale: steel 35,9 vs ember 114,8) and the
	 * speed-up between the windshields. The conditions in small print at the very bottom.
	 * When the page is idle and the cluster on screen, it makes its one entrance: the heat field
	 * runs hot, a bloom sweeps the hero once and the heat line flares.
	 */
	import { onMount } from 'svelte';
	import { magnetic, visible } from '$lib/fx/actions';
	import Ratio from '$lib/cards/Ratio.svelte';
	import Dial from '$lib/fx/Dial.svelte';
	import HeatField from '$lib/fx/HeatField.svelte';
	import Highway from '$lib/fx/Highway.svelte';
	import { reducedMotion, whenIdle } from '$lib/fx/motion';
	import { fmtSec, fmtTps } from '$lib/format';
	import { cardsHref, href, num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { fill, heroDial, RACE_CARD, RACE_MODEL, RACE_RUN, RACE_V } from './data';
	import Kin from './Kin.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].hero);
	const r = $derived(c.race);

	const cold = RACE_V.before.decode!.v;
	const hot = RACE_V.ours.decode!.v;
	const dial = heroDial(hot);
	const gain = hot / cold;
	/** Tokens accepted per step = measured t/s × measured ms per step (MTP steps; 1 without MTP). */
	const burstOf = (v: typeof RACE_V.ours) => (v.msStep ? Math.max(1, (v.decode!.v * v.msStep.v) / 1000) : 1);
	const lanes = $derived([
		{ id: 'cold' as const, name: r.cold, tps: cold, burst: burstOf(RACE_V.before) },
		{ id: 'hot' as const, name: r.hot, tps: hot, burst: burstOf(RACE_V.ours) }
	]);
	/** The demo answer's length (tokens); the finish times follow from the measured t/s. */
	const ANSWER = 500;
	const vars = $derived({
		card: RACE_CARD.name,
		model: RACE_MODEL,
		quant: RACE_RUN.quant,
		a0: fmtTps(cold, lang),
		a2: fmtTps(hot, lang),
		tok: num(ANSWER, lang, 0),
		t0: fmtSec(ANSWER / cold, lang),
		t2: fmtSec(ANSWER / hot, lang)
	});
	/** The rest of the highway's long text: a separate chunk per language, loaded once the page is idle. */
	const more = (l: Lang) => () => (l === 'pl' ? import('./stream/pl') : import('./stream/en')).then((m) => m.default);

	let playing = $state(true);
	let cluster: HTMLElement | undefined = $state();
	/** The cluster's entrance, once the page is idle and the cluster is on screen: the field runs
	 * hot for a moment and a bloom sweeps the hero once. Reduced motion: the final state at once. */
	let go = $state(false);
	/* the bloom sweeps once, then leaves the DOM: a resting screen-blended layer over the whole hero would be composited every frame */
	let bloomed = $state(false);
	let heat = $state(false);
	let idle = $state(false);
	let dashOn = $state(false);
	onMount(() => {
		if (reducedMotion()) {
			go = true;
			return;
		}
		return whenIdle(() => (idle = true));
	});
	$effect(() => {
		if (go || !idle || !dashOn) return;
		go = heat = true;
		setTimeout(() => (heat = false), 2600);
	});
</script>

<section class="hero" class:hot={heat} aria-labelledby="hero-title">
	<HeatField heat={heat ? 1 : 0.7} boost={heat ? 1 : 0} />
	<div class="veil" aria-hidden="true"></div>
	{#if go && idle && !bloomed}<div class="bloom" aria-hidden="true" onanimationend={() => (bloomed = true)}></div>{/if}
	<p class="sr-only">{fill(r.summary, vars)}</p>
	<div class="inner">
		<h1 id="hero-title" class="title">
			<Kin lines={c.title} wide={[1]} heat={[1]} cold={[0]} delays={[0, 120]} />
		</h1>
		<div class="actions">
			<a class="ignite" href={cardsHref(lang)} use:magnetic={{ max: 6 }}>
				<span class="ig-label">{c.cta}</span>
				<svg class="ig-arrow" viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><path d="M3 10h13M11 4.5 16.5 10 11 15.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
			</a>
			{#if !SITE_PUBLIC}
			<a class="mlink" href={href(lang, '/methodology')}>
				<span class="ml-label">{c.ctaSecondary}</span>
				<svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true"><path d="M4.5 11.5 11.5 4.5M6 4.5h5.5V10" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
			</a>
			{/if}
		</div>
	</div>
	<!-- keyed: the highway caches its text rows, so a language switch mounts a fresh one -->
	{#key lang}
		<Highway {lanes} opening={r.opening} more={more(lang)} {lang} answer={ANSWER} labels={r} {playing} keepClear={cluster}>
			{#snippet center()}
				<p class="factor" bind:this={cluster} aria-hidden="true" use:visible={(v) => (dashOn = v)}>
					<Ratio value={gain} {lang} size="xl" replay={go ? 1 : 0} duration={1500} /><span>{r.faster}</span>
				</p>
			{/snippet}
			{#snippet side(i: number)}
				<div class="gauge" aria-hidden="true">
					<Dial value={i ? hot : cold} max={dial.max} redline={dial.redline} tone={i ? 'hot' : 'cold'} {lang} unit="t/s" {go} still={!playing} />
				</div>
			{/snippet}
		</Highway>
	{/key}
	<div class="foot">
		<p class="note">{fill(r.note, vars)}</p>
		<button type="button" class="pp" aria-pressed={!playing} aria-label={playing ? r.pause : r.resume} title={playing ? r.pause : r.resume} onclick={() => (playing = !playing)}>
			{#if playing}<svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2.5" y="2" width="2.4" height="8" rx="0.6" /><rect x="7.1" y="2" width="2.4" height="8" rx="0.6" /></svg>
			{:else}<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3.5 2.2v7.6L10 6z" /></svg>{/if}
		</button>
	</div>
</section>

<style>
	/* one full screen: the headline around the middle, the race's near end below, the small print at the bottom */
	.hero {
		position: relative;
		min-height: 100vh;
		min-height: 100svh;
		display: grid;
		grid-template-rows: minmax(0, 1fr) auto auto;
		row-gap: clamp(0.75rem, 2svh, 1.5rem);
		padding-top: clamp(4.75rem, 3rem + 4svh, 6rem);
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
		position: relative;
		z-index: 1;
		align-self: center;
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		padding-block: clamp(0.5rem, 3svh, 2rem);
		display: grid;
		justify-items: center;
		gap: clamp(1.25rem, 0.5rem + 2.4vh, 2.4rem);
		text-align: center;
	}
	/* the headline reads over the road: a soft dark halo behind it, a deep shadow under the letters */
	.inner::before {
		content: '';
		position: absolute;
		inset: -14% -4% -22%;
		z-index: -1;
		pointer-events: none;
		background: radial-gradient(closest-side, rgb(5 5 6 / 0.85), rgb(5 5 6 / 0.6) 60%, transparent);
	}
	.title {
		filter: drop-shadow(0 10px 28px rgb(0 0 0 / 0.75));
	}
	/* two tiers: the steel line, then the focal heat line much larger (font-size = heat line) */
	.title {
		margin: 0;
		font-family: var(--font-display);
		font-size: min(11vw, 17svh, 9rem);
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
		font-size: 0.4em;
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
	/* the gauge between the windshields, small: it never fights the headline */
	/* each lane's gauge beside its windshield; the speed-up between the windshields */
	.gauge {
		width: min(clamp(9rem, 12vw, 14rem), 25svh);
	}
	.factor {
		margin: 0;
		display: grid;
		justify-items: center;
		gap: 0.3rem;
		line-height: 1;
	}
	.factor :global(.speedup) {
		--rx-fs: clamp(3.25rem, 1.5rem + 3.6vw, 6rem);
		background: linear-gradient(180deg, #fff 6%, var(--heat-5) 30%, var(--heat-4) 55%, var(--heat-3) 80%, var(--heat-2));
		-webkit-background-clip: text;
		background-clip: text;
		filter: drop-shadow(0 0 18px rgb(255 122 26 / 0.5));
	}
	.factor span {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		font-weight: 600;
		letter-spacing: 0.2em;
		text-transform: uppercase;
		color: var(--heat-4);
	}
	.foot {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		padding-bottom: 0.75rem;
		display: flex;
		align-items: center;
		gap: var(--sp-3);
	}
	.note {
		flex: 1;
		margin: 0;
		min-width: 0;
		/* centred (the pause button's width balanced on the left) */
		padding-left: calc(2rem + var(--sp-3));
		text-align: center;
		text-wrap: balance;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.03em;
		color: var(--text-mute);
	}
	.pp {
		flex: none;
		display: inline-grid;
		place-items: center;
		width: 2rem;
		height: 2rem;
		padding: 0;
		border: 1px solid var(--line-strong);
		border-radius: 50%;
		background: rgb(5 5 6 / 0.6);
		color: var(--text);
		cursor: pointer;
		transition:
			border-color var(--dur-2),
			color var(--dur-2);
	}
	.pp:hover {
		border-color: var(--text-hi);
		color: var(--text-hi);
	}
	.pp:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.pp svg {
		width: 0.75rem;
		height: 0.75rem;
		fill: currentColor;
	}
	@media (max-width: 900px) {
		.gauge {
			width: min(8.5rem, 28vw);
		}
		.note {
			padding-left: 0;
			text-align: left;
		}
	}
	@media (prefers-reduced-motion: no-preference) {
		/* the headline lands first; the CTAs follow, then the windshields rise */
		:global(html.js) .actions {
			animation: fade-up 0.6s var(--ease-out) 0.25s both;
		}
		:global(html.js) .hero :global(.near) {
			animation: rise 0.7s var(--ease-out) 0.35s both;
		}
	}
	/* transform-only: the CTAs and the windshields are visible from the first painted frame */
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
		/* phones: the headline in the upper half, the two windshields right under the CTAs */
		.hero {
			grid-template-rows: auto auto auto;
			padding-top: 5rem;
		}
		.inner {
			align-self: start;
			padding-block: 0;
			gap: var(--sp-4);
		}
		/* condensed cut: steel on two lines, the heat line on two big lines */
		.title {
			font-size: 17.5vw;
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
		.pp {
			display: none;
		}
	}
</style>
