<script lang="ts">
	/**
	 * Final CTA: one giant number on a heat track (no dial; the gauges belong to the hero race). It
	 * rests on our engine's measured value (server HTML included); in view it counts up and the track
	 * fills once more. The typical app is marked on the same scale.
	 */
	import { magnetic, play } from '$lib/fx/actions';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import Odometer from '$lib/fx/Odometer.svelte';
	import { cardsHref, href, num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { DIAL_MAX, fill, HERO_CARD, HERO_MODEL, HERO_RUN, HERO_V, REDLINE } from './data';
	import Duo from './Duo.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].final);
	const v = HERO_V.a2.decode!;
	const a0 = HERO_V.a0.decode!;
	let rep = $state(0);
	const label = $derived(fill(c.tacho, { card: HERO_CARD.name, v: num(v.v, lang) }));
</script>

<section class="final heat-top" aria-labelledby="final-title">
	<div class="heat" aria-hidden="true"></div>
	<div class="inner">
		<!-- one number on a heat track (0–100 t/s, red zone from 70): our engine, with the typical app marked -->
		<div class="meter" use:play={{ threshold: 0.4, onplay: () => rep++ }}>
			<!-- the graphic is one labelled image; the source button below stays outside it (no interactive child in role="img") -->
			<div role="img" aria-label={label}>
				<p class="mbig" aria-hidden="true">
					<span class="num"><Odometer value={v.v} replay={rep} decimals={1} {lang} duration={1600} minInt={2} /></span>
					<span class="u">t/s</span>
				</p>
				<div class="htrack" aria-hidden="true" style="--v:{v.v / DIAL_MAX}; --a:{a0.v / DIAL_MAX}; --r:{REDLINE / DIAL_MAX}">
					<span class="red"></span>
					{#key rep}<span class="hfill" class:play={rep > 0}></span>{/key}
					<span class="mk mk-a"><i></i><b>{num(a0.v, lang)}</b></span>
					<span class="scale"><span>0</span><span class="rl">{REDLINE}</span><span>{DIAL_MAX}</span></span>
				</div>
			</div>
			<p class="cap">
				{HERO_CARD.name} · {HERO_MODEL} {HERO_RUN.quant}
				<SourceTip {lang} src={[v.src, a0.src]} note="{HERO_RUN.metric[lang]}. {HERO_RUN.conditions[lang]}." />
			</p>
		</div>
		<div class="copy">
			<Duo text={c.title} id="final-title" burn />
			<p class="lede">{c.lede}</p>
			<div class="ctas">
				<a class="cta cta--bone" href={cardsHref(lang)} use:magnetic>{c.cards} <span class="arrow" aria-hidden="true">→</span></a>
				<a class="cta cta--line" href={href(lang, '/methodology')} use:magnetic>{c.method}</a>
			</div>
		</div>
	</div>
</section>

<style>
	.final {
		position: relative;
		overflow: clip;
		padding-block: clamp(4rem, 3rem + 4vw, 7rem);
		background: var(--bg-0);
		isolation: isolate;
	}
	.heat {
		position: absolute;
		inset: auto -20% -40% -20%;
		height: 100%;
		z-index: -1;
		background:
			radial-gradient(35% 45% at 25% 85%, rgb(255 122 26 / 0.32), transparent 70%),
			radial-gradient(60% 60% at 30% 100%, rgb(226 64 28 / 0.45), rgb(122 46 31 / 0.15) 50%, transparent 75%);
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
		gap: clamp(2rem, 6vw, 6rem);
		align-items: center;
	}
	.meter {
		display: grid;
		gap: var(--sp-5);
	}
	.mbig {
		margin: 0;
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
	}
	.num {
		font-size: clamp(5rem, 2.5rem + 8vw, 11rem);
		font-weight: 800;
		letter-spacing: -0.05em;
		line-height: 0.85;
		color: var(--heat-5);
		filter: drop-shadow(0 0 22px rgb(255 122 26 / 0.55)) drop-shadow(0 0 60px rgb(226 64 28 / 0.35));
	}
	.num :global(.odo) {
		font-family: var(--font-display);
		font-variant-numeric: tabular-nums lining-nums;
	}
	.u {
		font-family: var(--font-mono);
		font-size: var(--fs-sm);
		color: var(--text-mute);
		letter-spacing: 0.12em;
	}
	/* the heat track: the full ramp revealed up to our value; red zone from the redline */
	.htrack {
		position: relative;
		height: 1.1rem;
		margin-bottom: 2.2rem;
		border-radius: var(--r-pill);
		background: var(--bg-2);
		box-shadow: inset 0 0 0 1px var(--line);
	}
	.red {
		position: absolute;
		top: -0.35rem;
		bottom: -0.35rem;
		left: calc(var(--r) * 100%);
		right: 0;
		border-left: 2px solid var(--heat-2);
		background: linear-gradient(90deg, rgb(226 64 28 / 0.18), transparent);
		border-radius: 0 var(--r-pill) var(--r-pill) 0;
	}
	.hfill {
		position: absolute;
		inset: 0;
		width: calc(var(--v) * 100%);
		border-radius: var(--r-pill);
		background: var(--heat-ramp-hot);
		box-shadow:
			0 0 18px rgb(255 122 26 / 0.7),
			0 0 50px rgb(226 64 28 / 0.4);
		transform-origin: 0 50%;
	}
	@media (prefers-reduced-motion: no-preference) {
		.hfill.play {
			animation: hfill 1.6s var(--ease-out) backwards;
		}
	}
	@keyframes hfill {
		from {
			transform: scaleX(0);
		}
	}
	.mk {
		position: absolute;
		top: -0.5rem;
		bottom: -0.5rem;
		left: calc(var(--a) * 100%);
		display: grid;
		justify-items: center;
	}
	.mk i {
		width: 2px;
		height: 100%;
		background: var(--before);
	}
	.mk b {
		position: absolute;
		top: calc(100% + 0.25rem);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		font-weight: 500;
		color: var(--before);
		white-space: nowrap;
	}
	.scale {
		position: absolute;
		left: 0;
		right: 0;
		top: calc(100% + 0.75rem);
		display: flex;
		justify-content: space-between;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.scale .rl {
		position: absolute;
		left: calc(var(--r) * 100%);
		transform: translateX(-50%);
		color: #ff6a4a;
	}
	.cap {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.copy {
		display: grid;
		gap: var(--sp-6);
	}
	.ctas {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-3);
	}
	@media (max-width: 900px) {
		.inner {
			grid-template-columns: minmax(0, 1fr);
		}
		.meter {
			order: 2;
		}
	}
</style>
