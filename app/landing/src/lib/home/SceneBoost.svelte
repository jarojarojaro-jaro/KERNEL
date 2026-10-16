<script lang="ts">
	/**
	 * Scene 03, Przyspieszenie: "the page heats up". Three measured layers stack on one card and one
	 * model (a0 typical app → a1 best flags + MTP → a2 our engine). With each layer the whole
	 * viewport's temperature shifts along the heat ramp (cold steel → ember glow from the floor →
	 * white-hot rim once the speed crosses the 70 t/s redline), and the giant counter widens from
	 * wdth 75 to 125 as it climbs. The tower uses the page-wide 0–100 t/s scale with the red zone from
	 * 70; crossing it fires a flare. Gains from the sheet (`run.gain`). The layers play on an
	 * auto-played timeline (once on entering the viewport, replay button; reduced motion: final).
	 */
	import { Autoplay } from '$lib/fx/autoplay.svelte';
	import Replay from '$lib/fx/Replay.svelte';
	import Odometer from '$lib/fx/Odometer.svelte';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { fmtTps } from '$lib/format';
	import { type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { DIAL_MAX, fmtRatio, HERO_CARD, HERO_GAIN, HERO_MODEL, HERO_RUN, HERO_V, REDLINE } from './data';
	import SceneHead from './SceneHead.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].how.boost);
	const tl = new Autoplay(5);
	const p = $derived(tl.p);
	const stage = $derived(p >= 0.62 ? 3 : p >= 0.32 ? 2 : p > 0.02 ? 1 : 0);

	const vals = [HERO_V.a0.decode!, HERO_V.a1.decode!, HERO_V.a2.decode!];
	const gains = [null, HERO_GAIN.flags, HERO_GAIN.engine];
	const segs = $derived(
		vals.map((v, i) => ({ from: i ? vals[i - 1].v / DIAL_MAX : 0, to: v.v / DIAL_MAX, v, gain: gains[i], label: c.layers[i], key: ['cold', 'warm', 'hot'][i] }))
	);
	const shown = $derived(stage ? vals[stage - 1].v : 0);
	const overRed = $derived(shown >= REDLINE);
	const src = $derived([...vals.map((v) => v.src), HERO_GAIN.src]);
	const note = $derived(`${HERO_CARD.name} · ${HERO_MODEL} ${HERO_RUN.quant}. ${HERO_RUN.metric[lang]}. ${HERO_RUN.conditions[lang]}.`);
</script>

<div class="wrap" use:tl.view data-stage={stage}>
	<div class="room">
		<!-- the room temperature: one layer per stage, cross-faded -->
		<div class="temp t1" aria-hidden="true"></div>
		<div class="temp t2" aria-hidden="true"></div>
		<div class="temp t3" aria-hidden="true"></div>
		<div class="rim" aria-hidden="true"></div>
		<div class="layout">
			<SceneHead id="scene-boost" k={c.k} step={c.title} head={c.head} body={c.body} mode="duo" />
			<div class="meter">
				<div class="read">
					<div class="readout">
						<span class="bignum"><Odometer value={shown} decimals={1} {lang} duration={800} minInt={2} label={c.unit} /></span>
						<span class="unit">t/s</span>
					</div>
					<p class="layer-name" aria-live="polite">
						{#if stage}<span class="ln">{c.layers[stage - 1]}</span><span class="ls">{c.subs[stage - 1]}</span>{/if}
					</p>
					<p class="total" class:in={stage >= 3}>
						<b class="speedup">{fmtRatio(HERO_GAIN.total!.v, lang)}</b>
						<span>{c.total} · {HERO_CARD.name}</span>
						<SourceTip {lang} {src} {note} />
					</p>
					<Replay {lang} onclick={tl.replay} disabled={tl.playing} />
				</div>
				<div class="tower" style="--red:{REDLINE / DIAL_MAX}">
					<div class="redzone" class:flare={overRed} aria-hidden="true"><span>{REDLINE}</span></div>
					{#each segs as s, i (i)}
						<div class="seg seg--{s.key}" class:in={stage > i} style="--a:{s.from}; --b:{s.to}">
							<span class="tag">
								<span class="tv">{fmtTps(s.v.v, lang)}</span>
								{#if s.gain}<span class="tg speedup">{fmtRatio(s.gain.v, lang)}</span>{/if}
								<span class="tl">{s.label}</span>
							</span>
							<span class="mv" aria-hidden="true">{fmtTps(s.v.v, lang)}</span>
						</div>
					{/each}
				</div>
			</div>
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
		transition: opacity 1.1s var(--ease-out);
	}
	.t1 {
		background:
			radial-gradient(70% 55% at 50% 110%, rgb(110 124 140 / 0.22), transparent 70%),
			linear-gradient(180deg, transparent 50%, rgb(30 52 72 / 0.25));
	}
	.t2 {
		background:
			radial-gradient(80% 60% at 60% 115%, rgb(226 64 28 / 0.42), rgb(122 46 31 / 0.18) 45%, transparent 75%),
			linear-gradient(180deg, transparent 45%, rgb(122 46 31 / 0.22));
	}
	.t3 {
		background:
			radial-gradient(90% 70% at 60% 115%, rgb(255 122 26 / 0.5), rgb(226 64 28 / 0.25) 45%, transparent 78%),
			radial-gradient(60% 40% at 70% 0%, rgb(255 193 90 / 0.14), transparent 70%),
			linear-gradient(180deg, rgb(122 46 31 / 0.12), transparent 40%, rgb(226 64 28 / 0.25));
	}
	/* white-hot rim round the viewport once the speed is past the redline */
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
		grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.4fr);
		align-items: center;
		gap: clamp(2rem, 5vw, 6rem);
		padding-block: clamp(3rem, 2rem + 3vw, 5rem);
	}
	/* readout and tower side by side: the number climbs right next to the stack that drives it */
	.meter {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: center;
		gap: clamp(1.5rem, 3vw, 3rem);
		padding-right: clamp(8rem, 6rem + 4vw, 12rem);
	}
	.read {
		display: grid;
		gap: var(--sp-4);
		justify-items: start;
	}
	.readout {
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
	}
	/* the counter is set in the display face so it can widen: wdth 75 (cold) → 125 (white-hot) */
	.bignum {
		font-size: clamp(4rem, 1.5rem + 7vw, 8.5rem);
		line-height: 0.9;
		color: var(--before);
		font-stretch: 75%;
		font-weight: 300;
		letter-spacing: -0.04em;
		transition:
			font-stretch 1s var(--ease-out),
			font-weight 1s var(--ease-out),
			color 0.8s,
			filter 0.8s;
	}
	.bignum :global(.odo) {
		font-family: var(--font-display);
		font-variant-numeric: tabular-nums lining-nums;
	}
	[data-stage='2'] .bignum {
		font-stretch: 100%;
		font-weight: 500;
		color: var(--heat-4);
		filter: drop-shadow(0 0 22px rgb(255 122 26 / 0.35));
	}
	[data-stage='3'] .bignum {
		font-stretch: 125%;
		font-weight: 760;
		color: #fff;
		filter: drop-shadow(0 0 14px rgb(255 193 90 / 0.55)) drop-shadow(0 0 40px rgb(255 122 26 / 0.45));
	}
	.unit {
		font-family: var(--font-mono);
		font-size: var(--fs-sm);
		color: var(--text-mute);
		letter-spacing: 0.1em;
	}
	.layer-name {
		min-height: 2.8rem;
		display: grid;
		gap: 0.2rem;
	}
	.ln {
		font-weight: 700;
		font-stretch: 110%;
		font-size: var(--fs-lg);
		color: var(--text-hi);
	}
	.ls {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	/* ---- the tower: 0–100 t/s, red zone from 70 ---- */
	.tower {
		position: relative;
		width: clamp(6rem, 4rem + 4vw, 9rem);
		height: min(62svh, 36rem);
		border: 1px solid var(--line-strong);
		border-radius: var(--r-lg);
		background:
			repeating-linear-gradient(0deg, transparent 0 calc(10% - 1px), rgb(237 234 227 / 0.06) calc(10% - 1px) 10%),
			var(--bg-1);
	}
	.redzone {
		position: absolute;
		left: -10px;
		right: -10px;
		top: 0;
		height: calc((1 - var(--red)) * 100%);
		border-bottom: 2px solid var(--heat-2);
		background: linear-gradient(0deg, rgb(226 64 28 / 0.22), transparent);
		pointer-events: none;
		border-radius: var(--r-lg) var(--r-lg) 0 0;
		z-index: 1;
	}
	.redzone span {
		position: absolute;
		right: calc(100% + 0.5rem);
		bottom: -0.55rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: #ff6a4a;
	}
	.redzone.flare {
		animation: zone-flare 1.2s var(--ease-out) 0.7s both;
	}
	@keyframes zone-flare {
		20% {
			border-color: var(--heat-5);
			background: linear-gradient(0deg, rgb(255 193 90 / 0.55), rgb(255 122 26 / 0.12));
			box-shadow: 0 0 40px rgb(255 122 26 / 0.8);
		}
	}
	.seg {
		position: absolute;
		left: 6px;
		right: 6px;
		bottom: calc(var(--a) * 100%);
		height: calc((var(--b) - var(--a)) * 100%);
		border-radius: 4px;
		background: linear-gradient(0deg, #2a3038, var(--before));
		transform-origin: 50% 100%;
		transform: scaleY(0);
		transition: transform 0.9s var(--ease-spring);
	}
	.seg--warm {
		background: linear-gradient(0deg, var(--heat-2), var(--heat-3));
		box-shadow: 0 0 36px -4px var(--heat-3);
	}
	.seg--hot {
		background: linear-gradient(0deg, var(--heat-3), var(--heat-4) 50%, var(--heat-5));
		box-shadow:
			0 0 0 1px rgb(255 243 214 / 0.35) inset,
			0 0 48px -2px var(--heat-4);
	}
	.seg.in {
		transform: none;
	}
	.tag {
		position: absolute;
		top: 0;
		left: calc(100% + 1.4rem);
		display: grid;
		gap: 0.1rem;
		white-space: nowrap;
		opacity: 0;
		transform: translate3d(-0.6rem, 0, 0);
		transition:
			opacity 0.5s 0.35s,
			transform 0.6s var(--ease-out) 0.35s;
	}
	.seg.in .tag {
		opacity: 1;
		transform: none;
	}
	.tag::before {
		content: '';
		position: absolute;
		right: calc(100% + 0.4rem);
		top: 0.55rem;
		width: 1rem;
		height: 1px;
		background: var(--line-strong);
	}
	/* mobile only: each layer's value under the end of its segment */
	.mv {
		display: none;
	}
	.tv {
		font-family: var(--font-mono);
		font-size: var(--fs-md);
		color: var(--text-hi);
	}
	.tg {
		font-size: var(--fs-lg);
	}
	.tl {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.total {
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: 0.4rem 0.8rem;
		opacity: 0;
		transform: translate3d(0, 0.6rem, 0);
		transition:
			opacity 0.5s 0.6s,
			transform 0.6s var(--ease-spring) 0.6s;
		visibility: hidden;
	}
	.total.in {
		opacity: 1;
		transform: none;
		visibility: visible;
	}
	.total b {
		font-size: clamp(2rem, 1rem + 2.4vw, 3.2rem);
	}
	.total span {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text);
	}

	@media (max-width: 900px) {
		.layout {
			grid-template-columns: minmax(0, 1fr);
			align-content: start;
			gap: var(--sp-5);
		}
		.meter {
			grid-template-columns: minmax(0, 1fr);
			padding-right: 0;
			gap: var(--sp-5);
		}
		.bignum {
			font-size: 19vw;
		}
		/* tower lies down: a horizontal bar, red zone on the right from 70 */
		.tower {
			width: 100%;
			height: 3.5rem;
			background:
				repeating-linear-gradient(90deg, transparent 0 calc(10% - 1px), rgb(237 234 227 / 0.06) calc(10% - 1px) 10%),
				var(--bg-1);
		}
		.redzone {
			top: -8px;
			bottom: -8px;
			left: auto;
			right: 0;
			width: calc((1 - var(--red)) * 100%);
			height: auto;
			border-bottom: 0;
			border-left: 2px solid var(--heat-2);
			background: linear-gradient(270deg, rgb(226 64 28 / 0.22), transparent);
			border-radius: 0 var(--r-lg) var(--r-lg) 0;
		}
		.redzone span {
			right: auto;
			left: -0.6rem;
			top: auto;
			bottom: calc(100% + 0.3rem);
		}
		.seg {
			top: 6px;
			bottom: 6px;
			left: calc(var(--a) * 100%);
			right: auto;
			width: calc((var(--b) - var(--a)) * 100%);
			height: auto;
			transform-origin: 0 50%;
			transform: scaleX(0);
		}
		.tag {
			display: none;
		}
		.mv {
			display: block;
			position: absolute;
			top: calc(100% + 0.9rem);
			right: 0;
			font-family: var(--font-mono);
			font-size: var(--fs-2xs);
			color: var(--text-hi);
			white-space: nowrap;
		}
		.seg--cold .mv {
			color: var(--before);
		}
		.layer-name {
			min-height: 3rem;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.seg,
		.tag,
		.total,
		.temp,
		.rim,
		.bignum {
			transition: none;
		}
		.redzone.flare {
			animation: none;
		}
	}
</style>
