<script lang="ts">
	/**
	 * Scene 03, Przyspieszenie: three measured setups on one card and one model, side by side as
	 * bars on the page-wide 0–100 t/s scale with the red zone from 70 (a0 typical app, a1 best
	 * upstream flags + MTP, a2 our engine; same script). The first two are cold steel, ours is
	 * white-hot and glowing and the only one in the red zone. On entering the viewport the bars grow
	 * one after another, each value counting from 0 to its exact measured value, and each multiplier
	 * (vs the typical app, from the sheet's `run.gain`) lands when its bar does; the room behind
	 * warms with every bar and flares once ours crosses the redline. Armed below the fold (no flash
	 * of the end state), replay button; reduced motion: the final state.
	 */
	import { Autoplay } from '$lib/fx/autoplay.svelte';
	import { clamp01 } from '$lib/fx/motion';
	import Replay from '$lib/fx/Replay.svelte';
	import { num, type Lang } from '$lib/i18n';
	import ModelMark from '$lib/ModelMark.svelte';
	import { copy } from '$lib/site/copy';
	import { DIAL_MAX, fmtRatio, HERO_CARD, HERO_GAIN, HERO_MODEL, HERO_RUN, HERO_V, REDLINE } from './data';
	import SceneHead from './SceneHead.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].how.boost);
	/** Starts once ~15 % of the scene is up; the three bars grow in 0,7 s with an 80 ms stagger. */
	const tl = new Autoplay(0.78, '0px 0px -15% 0px', { arm: true });

	const vals = [HERO_V.a0.decode!, HERO_V.a1.decode!, HERO_V.a2.decode!];
	/** Multiplier of each setup vs the typical app, from the measured medians (×1.76 MTP, ×2.17 total). */
	const mult = [null, HERO_GAIN.flags!, HERO_GAIN.total!];
	const KEYS = ['cold', 'warm', 'hot'] as const;
	/** Each bar's slice of the timeline (0,78 s): 0,54 s each, 80 ms apart, all done at 0,7 s. */
	const WIN: [number, number][] = [
		[0, 0.69],
		[0.103, 0.795],
		[0.205, 0.9]
	];
	const easeOut = (t: number) => 1 - (1 - t) ** 3;
	const ks = $derived(WIN.map(([a, b]) => easeOut(clamp01((tl.p - a) / (b - a)))));
	/** Value shown on a bar: counts 0 → value, exactly the measured value at rest. */
	const shown = (i: number) => (ks[i] >= 1 ? vals[i].v : vals[i].v * ks[i]);
	const stage = $derived(ks[2] > 0 ? 3 : ks[1] > 0 ? 2 : ks[0] > 0 ? 1 : 0);
	const overRed = $derived(shown(2) >= REDLINE);
	const width = (v: number) => num(v, lang, 1).length;
</script>

<div class="wrap" use:tl.view data-stage={stage} class:live={tl.inView}>
	<div class="room">
		<!-- the room temperature: one layer per bar, cross-faded -->
		<div class="temp t1" aria-hidden="true"></div>
		<div class="temp t2" aria-hidden="true"></div>
		<div class="temp t3" aria-hidden="true"></div>
		<div class="rim" aria-hidden="true"></div>
		<div class="layout">
			<SceneHead id="scene-boost" k={c.k} step={c.title} head={c.head} body={c.body} mode="duo" />
			<figure class="race" class:landed={ks[2] >= 1} style="--red:{REDLINE / DIAL_MAX}; --top:{Math.max(...vals.map((v) => v.v)) / DIAL_MAX}">
				<div class="plot">
					<div class="redzone" class:flare={overRed} aria-hidden="true"><span>{REDLINE} t/s</span></div>
					{#each vals as v, i (i)}
						<div class="col col--{KEYS[i]}" class:done={ks[i] >= 1} style="--h:{v.v / DIAL_MAX}; --k:{ks[i]}" aria-hidden="true">
							<div class="pillar"><span class="fill"></span></div>
							<div class="tag">
								<span class="val" style="min-width:{width(v.v)}ch">{num(shown(i), lang, 1)}</span>
								<span class="x">{mult[i] ? fmtRatio(mult[i]!.v, lang) : '1×'}</span>
							</div>
						</div>
					{/each}
				</div>
				<ol class="names">
					{#each vals as v, i (i)}
						<li class="nm nm--{KEYS[i]}">
							<b>{c.layers[i]}</b>
							<small>{c.subs[i]}</small>
							<span class="sr-only">: {num(v.v, lang, 1)} {c.unit}{mult[i] ? `, ${fmtRatio(mult[i]!.v, lang)} ${c.vs}` : ''}</span>
						</li>
					{/each}
				</ol>
				<figcaption class="foot">
					<span class="win"><b>{fmtRatio(HERO_GAIN.total!.v, lang)}</b> {c.over}</span>
					{#if HERO_GAIN.engine}<span class="win2">{fmtRatio(HERO_GAIN.engine.v, lang)} {c.overFlags}</span>{/if}
					<span class="tt"><ModelMark model={HERO_RUN.model} size="0.8em" /> {HERO_MODEL} · {HERO_CARD.name} · t/s</span>
					<Replay {lang} onclick={tl.replay} disabled={tl.playing} />
				</figcaption>
			</figure>
		</div>
	</div>
</div>

<style>
	.wrap {
		position: relative;
	}
	.room {
		position: relative;
		overflow: hidden;
	}
	/* ---- room temperature ---- */
	.temp,
	.rim {
		position: absolute;
		inset: 0;
		pointer-events: none;
		opacity: 0;
		transition: opacity 0.5s var(--ease-out);
	}
	.t1 {
		background:
			radial-gradient(70% 55% at 50% 110%, rgb(110 124 140 / 0.22), transparent 70%),
			linear-gradient(180deg, transparent 50%, rgb(30 52 72 / 0.25));
	}
	.t2 {
		background:
			radial-gradient(80% 60% at 60% 115%, rgb(226 64 28 / 0.3), rgb(122 46 31 / 0.14) 45%, transparent 75%),
			linear-gradient(180deg, transparent 45%, rgb(122 46 31 / 0.18));
	}
	.t3 {
		background:
			radial-gradient(60% 70% at 78% 105%, rgb(255 122 26 / 0.5), rgb(226 64 28 / 0.25) 45%, transparent 78%),
			radial-gradient(50% 40% at 80% 0%, rgb(255 193 90 / 0.14), transparent 70%),
			linear-gradient(180deg, rgb(122 46 31 / 0.12), transparent 40%, rgb(226 64 28 / 0.22));
	}
	/* white-hot rim round the viewport once our bar is in the red zone */
	.rim {
		box-shadow:
			inset 0 0 0 1px rgb(255 243 214 / 0.35),
			inset 0 0 60px rgb(255 193 90 / 0.28),
			inset 0 0 180px rgb(255 122 26 / 0.18);
	}
	[data-stage='1'] .t1,
	[data-stage='2'] .t2,
	[data-stage='3'] .t3,
	[data-stage='3'] .rim {
		opacity: 1;
	}
	.layout {
		position: relative;
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.3fr);
		align-items: center;
		gap: clamp(2rem, 5vw, 6rem);
		padding-block: var(--header-clear) clamp(1.25rem, 3vh, 2.5rem);
	}

	/* ---- the race: three bars on 0–100 t/s, red zone from 70 ---- */
	/*
	 * The whole scene fits one viewport below the header. Our value rides the top of the tallest bar
	 * (--top of the scale): its tag (--tag) overhangs the plot by --tag − (1 − --top) of the plot,
	 * kept as headroom. The plot takes what is left of the viewport after the header, the tag and
	 * --rest (labels, footer, gaps, bottom padding; on phones also the heading above):
	 * plot = (left) / --top.
	 */
	.race {
		--val-hot: clamp(2rem, min(1.1rem + 3vw, 6svh), 4.4rem);
		--tag: calc(var(--val-hot) + 3.2rem);
		--rest: 13.5rem;
		--plot: clamp(7rem, (100svh - var(--header-clear) - var(--tag) - var(--rest)) / var(--top), 26rem);
		margin: 0;
		padding-top: max(0px, var(--tag) - (1 - var(--top)) * var(--plot));
		display: grid;
		gap: clamp(0.5rem, 1.4vh, 0.9rem);
	}
	.plot {
		position: relative;
		height: var(--plot);
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: clamp(0.7rem, 2.5vw, 2.2rem);
		padding-inline: clamp(0.5rem, 2vw, 1.5rem);
		border-bottom: 1px solid var(--line-strong);
		background: repeating-linear-gradient(0deg, transparent 0 calc(10% - 1px), rgb(237 234 227 / 0.06) calc(10% - 1px) 10%);
	}
	.redzone {
		position: absolute;
		inset: 0 0 auto;
		height: calc((1 - var(--red)) * 100%);
		border-bottom: 2px dashed var(--heat-2);
		background: linear-gradient(0deg, rgb(226 64 28 / 0.2), transparent);
		pointer-events: none;
	}
	.redzone span {
		position: absolute;
		left: 0;
		bottom: 0.35rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.08em;
		color: #ff6a4a;
	}
	.redzone.flare {
		animation: zone-flare 1.3s var(--ease-out) both;
	}
	@keyframes zone-flare {
		20% {
			border-bottom-color: var(--heat-5);
			background: linear-gradient(0deg, rgb(255 193 90 / 0.5), rgb(255 122 26 / 0.1));
			box-shadow: 0 6px 40px rgb(255 122 26 / 0.7);
		}
	}
	.col {
		position: relative;
		z-index: 1;
	}
	.pillar {
		position: absolute;
		inset: auto 8% 0;
		height: calc(var(--h) * 100%);
		transform-origin: 50% 100%;
		transform: scaleY(var(--k));
	}
	.fill {
		position: absolute;
		inset: 0;
		overflow: hidden;
		border-radius: 10px 10px 2px 2px;
	}
	.col--cold .fill {
		background: linear-gradient(0deg, #1b2027, #3a424c);
		box-shadow: inset 0 0 0 1px rgb(125 135 148 / 0.35);
	}
	.col--warm .fill {
		background: linear-gradient(0deg, #1f252d, #56606c);
		box-shadow: inset 0 0 0 1px rgb(125 135 148 / 0.45);
	}
	.col--hot .pillar {
		inset-inline: 2%;
	}
	/* ours: the only hot thing on the chart */
	.col--hot .fill {
		background: linear-gradient(0deg, var(--heat-2), var(--heat-3) 40%, var(--heat-4) 80%, var(--heat-5));
		box-shadow:
			inset 0 0 0 1px rgb(255 243 214 / 0.5),
			0 0 30px rgb(255 122 26 / 0.65),
			0 0 90px rgb(255 122 26 / 0.35);
	}
	.col--hot .fill {
		overflow: visible;
	}
	/* heat shimmer running up our bar while the scene is on screen */
	.col--hot .fill::after {
		content: '';
		position: absolute;
		inset: 0;
		border-radius: inherit;
		background: linear-gradient(0deg, transparent 0 35%, rgb(255 243 214 / 0.55) 50%, transparent 65% 100%) 0 0 / 100% 200%;
		opacity: 0;
		mix-blend-mode: soft-light;
	}
	@media (prefers-reduced-motion: no-preference) {
		.live .col--hot.done .fill::after {
			opacity: 1;
			animation: shimmer 2.6s linear infinite;
		}
	}
	@keyframes shimmer {
		from {
			background-position: 0 200%;
		}
		to {
			background-position: 0 0;
		}
	}
	/* the value rides the top of its bar as it grows */
	.tag {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		display: grid;
		justify-items: center;
		gap: 0.3rem;
		padding-bottom: 0.6rem;
		transform: translate3d(0, calc(var(--k) * var(--h) * -1 * var(--plot)), 0);
	}
	.val {
		display: inline-block;
		text-align: center;
		font-family: var(--font-display);
		font-variant-numeric: tabular-nums lining-nums;
		font-weight: 760;
		font-size: clamp(1.3rem, min(0.9rem + 1.6vw, 4svh), 2.6rem);
		letter-spacing: -0.03em;
		line-height: 1;
		color: var(--before);
	}
	.col--hot .val {
		font-size: var(--val-hot);
		font-weight: 820;
		letter-spacing: -0.045em;
		color: #fff;
		text-shadow:
			0 0 16px rgb(255 193 90 / 0.6),
			0 0 44px rgb(255 122 26 / 0.55);
	}
	.x {
		padding: 0.25em 0.6em 0.2em;
		border-radius: var(--r-pill);
		font-family: var(--font-display);
		font-weight: 800;
		font-size: clamp(0.8rem, 0.7rem + 0.4vw, 1.05rem);
		line-height: 1;
		color: var(--text);
		background: rgb(125 135 148 / 0.16);
		box-shadow: inset 0 0 0 1px rgb(125 135 148 / 0.4);
		opacity: 0;
		transform: scale(0.6);
		transition:
			opacity 0.12s,
			transform 0.28s var(--ease-spring);
	}
	.col--hot .x {
		font-size: clamp(1rem, 0.8rem + 0.9vw, 1.6rem);
		color: #140a04;
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 26px rgb(255 122 26 / 0.65);
	}
	.done .x {
		opacity: 1;
		transform: none;
	}
	.names {
		margin: 0;
		padding: 0 clamp(0.5rem, 2vw, 1.5rem);
		list-style: none;
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: clamp(0.7rem, 2.5vw, 2.2rem);
		text-align: center;
	}
	.nm {
		display: grid;
		gap: 0.2rem;
		align-content: start;
	}
	.nm b {
		font-weight: 700;
		font-size: var(--fs-md);
		line-height: 1.2;
		color: var(--text);
	}
	.nm small {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.03em;
		line-height: 1.35;
		color: var(--text-mute);
	}
	.nm--hot b {
		color: var(--heat-4);
	}
	.foot {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.5rem 0.9rem;
		padding-top: var(--sp-3);
		border-top: 1px solid rgb(255 122 26 / 0.35);
	}
	.win {
		display: inline-flex;
		align-items: baseline;
		gap: 0.5rem;
		font-weight: 650;
		color: var(--text-hi);
	}
	/* the headline gain (vs the typical app) pops right after our bar lands */
	.win b {
		display: inline-block;
		font-family: var(--font-display);
		font-size: clamp(1.4rem, 1rem + 1vw, 2rem);
		font-weight: 820;
		background: var(--heat-ramp-hot);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		padding: 0.1em 0.12em 0.2em 0;
		margin: -0.1em -0.12em -0.2em 0;
		opacity: 0;
		transform: scale(0.7);
		transform-origin: 0 70%;
		transition:
			opacity 0.1s 0.04s,
			transform 0.3s var(--ease-spring) 0.04s;
	}
	.landed .win b {
		opacity: 1;
		transform: none;
	}
	.win2 {
		margin-right: auto;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text);
	}
	.tt {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		color: var(--text);
	}

	@media (max-width: 900px) {
		.layout {
			grid-template-columns: minmax(0, 1fr);
			align-content: start;
			gap: clamp(1rem, 2.5vh, 2rem);
		}
		/* stacked: the heading above the chart also comes out of the viewport */
		.race {
			--rest: 33rem;
		}
	}
	@media (max-width: 380px) {
		.race {
			--rest: 35rem;
		}
	}
	/* short phones: the setup sublines go (names and values stay) so the plot keeps its height */
	@media (max-width: 900px) and (max-height: 800px) {
		.race {
			--rest: 27rem;
		}
		.nm small {
			display: none;
		}
	}
	@media (max-width: 380px) and (max-height: 800px) {
		.race {
			--rest: 29rem;
		}
	}
	@media (max-width: 480px) {
		.plot,
		.names {
			padding-inline: 0;
			gap: 0.6rem;
		}
		.nm b {
			font-size: var(--fs-sm);
		}
		.nm small {
			font-size: 0.68rem;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.temp,
		.rim,
		.x,
		.win b {
			transition: none;
		}
		.redzone.flare {
			animation: none;
		}
	}
</style>
