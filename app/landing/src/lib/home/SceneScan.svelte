<script lang="ts">
	/**
	 * Scene 01, Skan: the same product render as the cards explorer (`GpuArt`) launches in as soon as
	 * the scene enters the viewport (fast slide with motion blur, skids to a stop), then a light bar
	 * sweeps it on an auto-played timeline (`--p`, plays once, replay button). Behind the bar the
	 * shroud gives way to an x-ray of the board, drawn on the render's own grid; four spec callouts
	 * pop at p = .3 / .45 / .6 / .75, each with its source. A scan readout (track, parameters found) replaces a bare percentage. Bone light only:
	 * heat colour is reserved for speed.
	 */
	import GpuArt from '$lib/cards/GpuArt.svelte';
	import { Autoplay } from '$lib/fx/autoplay.svelte';
	import { clamp01 } from '$lib/fx/motion';
	import Replay from '$lib/fx/Replay.svelte';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { HERO_CARD } from './data';
	import Gpu3090 from './Gpu3090.svelte';
	import SceneHead from './SceneHead.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].how.scan);
	// starts as soon as the scene's top enters the viewport: the card is never waiting off-screen
	const tl = new Autoplay(4.6, '0px');
	const p = $derived(tl.p);
	const s = $derived(clamp01((p - 0.16) / 0.66));

	const callouts = $derived([
		{ id: 'vram', at: 0.3, x: 50, y: 16.7, dir: 'up', value: `${HERO_CARD.vramGB}\u00a0GB`, label: c.vram, src: HERO_CARD.hwSrc },
		{ id: 'bw', at: 0.45, x: 33, y: 80, dir: 'down', value: `${num(HERO_CARD.bwGBs.v, lang, 0)}\u00a0GB/s`, label: c.bw, src: HERO_CARD.bwGBs.src },
		{ id: 'power', at: 0.6, x: 89.4, y: 5.7, dir: 'up', value: `${num(HERO_CARD.powerW.v, lang, 0)}\u00a0W`, label: c.power, src: HERO_CARD.powerW.src },
		{ id: 'arch', at: 0.75, x: 57.5, y: 50, dir: 'down', value: HERO_CARD.arch, label: c.arch, src: HERO_CARD.hwSrc }
	]);
	const found = $derived(callouts.filter((k) => p >= k.at).length);
	const hwNote = $derived(HERO_CARD.hwLine?.[lang] ?? '');
</script>

<div class="wrap" use:tl.view style="--p:{p}">
	<div class="layout">
			<SceneHead id="scene-scan" k={c.k} step={c.title} head={c.head} body={c.body} />
			<div class="stage">
				<div class="gpu" class:go={p > 0}>
					<div class="layer shroud"><GpuArt label={HERO_CARD.short} vendor={HERO_CARD.vendor} vram={HERO_CARD.vramGB} flat /></div>
					<div class="layer xray"><Gpu3090 /></div>
					<div class="sweep" aria-hidden="true"><span class="beam"></span></div>
					<ul class="callouts" role="list">
						{#each callouts as k (k.id)}
							<li class="callout {k.dir}" class:on={p >= k.at} style="--x:{k.x}%; --y:{k.y}%">
								<span class="pin" aria-hidden="true"></span>
								<span class="tag">
									<span class="v">{k.value}</span>
									<span class="l">{k.label}</span>
									<SourceTip {lang} src={k.src} note={hwNote} />
								</span>
							</li>
						{/each}
					</ul>
				</div>
				<!-- scan readout: a designed instrument, not a debug percentage -->
				<div class="readout">
					<span class="rl" aria-hidden="true">{c.title}</span>
					<span class="rn" aria-hidden="true">{HERO_CARD.name}</span>
					<span class="track" aria-hidden="true"><span class="fillbar" style="--s:{s}"></span></span>
					<span class="found" aria-hidden="true" class:done={found === callouts.length}>
						{#each callouts as k, i (k.id)}<i class:on={i < found}></i>{/each}
						<b>{found}/{callouts.length}</b>
					</span>
					<Replay {lang} onclick={tl.replay} disabled={tl.playing} />
				</div>
			</div>
	</div>
</div>

<style>
	/* the launch slide and the sweep travel past the right edge: never widen the page */
	.wrap {
		position: relative;
		overflow-x: clip;
		--s: clamp(0, calc((var(--p) - 0.16) / 0.66), 1);
	}
	.layout {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.4fr);
		align-items: start;
		gap: clamp(2rem, 5vw, 6rem);
		padding-block: var(--header-clear) clamp(2rem, 1.5rem + 2vw, 3.5rem);
	}
	/* room above and under the render for the callouts, then the scan readout */
	.stage {
		display: grid;
		gap: 7rem;
		/* room above the render for the upward callouts (300 W sits highest) */
		padding-top: 7rem;
	}
	/* render and x-ray share one box and one 3D pose */
	.gpu {
		position: relative;
		aspect-ratio: 640 / 300;
		transform: perspective(1500px) rotateY(-12deg) rotateX(6deg);
		transform-style: preserve-3d;
	}
	/* launch: the card shoots in from the right with motion blur, overshoots and skids to rest */
	.gpu.go {
		animation: launch 0.85s cubic-bezier(0.16, 1, 0.3, 1) both;
	}
	@keyframes launch {
		0% {
			filter: blur(8px);
			transform: perspective(1500px) rotateY(-12deg) rotateX(6deg) translate3d(60%, 0, 0) skewX(-14deg);
		}
		45% {
			filter: blur(1.5px);
			transform: perspective(1500px) rotateY(-12deg) rotateX(6deg) translate3d(-4%, 0, 0) skewX(4deg);
		}
		75% {
			filter: none;
			transform: perspective(1500px) rotateY(-12deg) rotateX(6deg) translate3d(1%, 0, 0) skewX(-1deg);
		}
		100% {
			transform: perspective(1500px) rotateY(-12deg) rotateX(6deg);
		}
	}
	.layer {
		position: absolute;
		inset: 0;
	}
	.shroud {
		clip-path: inset(-20% -20% -20% calc(var(--s) * 100%));
	}
	.xray {
		clip-path: inset(-10% calc((1 - var(--s)) * 100%) -10% -5%);
	}
	.sweep {
		position: absolute;
		inset: -8% 0;
		transform: translate3d(calc(var(--s) * 100%), 0, 0);
		opacity: clamp(0, calc(min(var(--s), 1 - var(--s)) * 25), 1);
		pointer-events: none;
	}
	.beam {
		position: absolute;
		top: 0;
		bottom: 0;
		left: -1px;
		width: 2px;
		background: #fff;
		box-shadow:
			0 0 10px 2px rgb(255 255 255 / 0.85),
			0 0 40px 10px rgb(237 234 227 / 0.25);
	}
	.beam::before {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		right: 0;
		width: 9rem;
		background: linear-gradient(90deg, transparent, rgb(237 234 227 / 0.08));
	}
	.callouts {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	/* revealed by clip + transform, never by opacity: the text is full contrast in every frame */
	.callout {
		position: absolute;
		left: var(--x);
		top: var(--y);
		visibility: hidden;
		clip-path: inset(50% 50% 50% 50%);
		transform: scale(0.85);
		transition:
			clip-path 0.35s var(--ease-out),
			transform 0.5s var(--ease-spring),
			visibility 0s linear 0.35s;
	}
	.callout.on {
		visibility: visible;
		clip-path: inset(-40rem -40rem -40rem -40rem);
		transform: none;
		transition:
			clip-path 0.35s var(--ease-out),
			transform 0.5s var(--ease-spring),
			visibility 0s;
	}
	.pin {
		position: absolute;
		left: -6px;
		top: -6px;
		width: 12px;
		height: 12px;
		border-radius: 50%;
		border: 2px solid var(--text-hi);
		background: var(--bg-0);
		box-shadow: 0 0 14px rgb(237 234 227 / 0.6);
	}
	.pin::after {
		content: '';
		position: absolute;
		left: 50%;
		width: 1px;
		height: 2.6rem;
		background: linear-gradient(var(--text-hi), rgb(237 234 227 / 0.1));
	}
	.up .pin::after {
		bottom: 100%;
		background: linear-gradient(rgb(237 234 227 / 0.1), var(--text-hi));
	}
	.down .pin::after {
		top: 100%;
	}
	.tag {
		position: absolute;
		left: -0.6rem;
		display: grid;
		justify-items: start;
		gap: 0.15rem;
		white-space: nowrap;
		padding: 0.55rem 0.8rem 0.6rem;
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: rgb(11 11 13 / 0.9);
	}
	.up .tag {
		bottom: 2.6rem;
	}
	.down .tag {
		top: 2.6rem;
	}
	.v {
		font-family: var(--font-display);
		font-size: clamp(1.3rem, 0.8rem + 1.2vw, 2rem);
		font-weight: 760;
		font-stretch: 110%;
		letter-spacing: -0.02em;
		color: var(--text-hi);
		line-height: 1.05;
	}
	.l {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-mute);
		margin-bottom: 0.3rem;
	}
	.callout:nth-child(3) .tag {
		left: auto;
		right: -0.6rem;
		justify-items: end;
	}
	/* ---- scan readout ---- */
	.readout {
		display: grid;
		grid-template-columns: auto auto minmax(4rem, 1fr) auto auto;
		align-items: center;
		gap: var(--sp-4);
		padding: var(--sp-2) var(--sp-2) var(--sp-2) var(--sp-4);
		border: 1px solid var(--line);
		border-radius: var(--r-pill);
		background: rgb(11 11 13 / 0.7);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}
	.rl {
		color: var(--text-hi);
	}
	.rn {
		color: var(--text-mute);
	}
	.track {
		position: relative;
		height: 2px;
		background: var(--bg-3);
		overflow: hidden;
	}
	.fillbar {
		position: absolute;
		inset: 0;
		transform-origin: 0 50%;
		transform: scaleX(var(--s));
		background: var(--text-hi);
		box-shadow: 0 0 8px rgb(237 234 227 / 0.8);
	}
	.found {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		color: var(--text-mute);
	}
	.found i {
		width: 0.5rem;
		height: 0.5rem;
		border: 1px solid var(--line-strong);
		border-radius: 1px;
		transition: background 0.3s;
	}
	.found i.on {
		background: var(--text-hi);
		border-color: var(--text-hi);
	}
	.found b {
		margin-left: 0.3rem;
		font-weight: 500;
		color: var(--text-hi);
		font-variant-numeric: tabular-nums;
	}

	@media (max-width: 900px) {
		.layout {
			grid-template-columns: minmax(0, 1fr);
			gap: var(--sp-5);
		}
		.stage {
			gap: var(--sp-4);
			padding-top: 0;
		}
		.gpu {
			transform: none;
		}
		@keyframes launch {
			0% {
				filter: blur(6px);
				transform: translate3d(70%, 0, 0) skewX(-14deg);
			}
			45% {
				filter: blur(1px);
				transform: translate3d(-5%, 0, 0) skewX(4deg);
			}
			75% {
				filter: none;
				transform: translate3d(1%, 0, 0);
			}
			100% {
				transform: none;
			}
		}
		.readout {
			order: -1;
			grid-template-columns: auto minmax(3rem, 1fr) auto auto;
		}
		.rn {
			display: none;
		}
		.callouts {
			position: absolute;
			top: calc(100% + var(--sp-5));
			left: 0;
			right: 0;
			display: grid;
			grid-template-columns: 1fr 1fr;
			gap: var(--sp-2);
		}
		.callout {
			position: static;
		}
		.pin {
			display: none;
		}
		.tag,
		.callout:nth-child(3) .tag {
			position: static;
			grid-template-columns: minmax(0, 1fr) auto;
			align-items: center;
			justify-items: start;
			text-align: left;
			white-space: normal;
			padding: 0.5rem 0.6rem;
		}
		.tag :global(.src-btn) {
			grid-column: 2;
			grid-row: 1;
			padding-inline: 0.4rem;
		}
		.tag :global(.src-btn span) {
			display: none;
		}
		.l {
			grid-column: 1 / -1;
			margin: 0;
		}
		.v {
			font-size: 1.15rem;
		}
		.stage {
			padding-bottom: 9.5rem;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.gpu.go {
			animation: none;
		}
	}
</style>
