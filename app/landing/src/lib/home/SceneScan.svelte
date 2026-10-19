<script lang="ts">
	/**
	 * Scene 01, Skan: our lab card, a Sapphire PULSE RX 7900 XTX (`PulseXtx`), shoots in as soon as the
	 * scene enters the viewport (motion blur, skids to a stop) with its fans spinning up, then a red scan
	 * beam crosses it on an auto-played timeline (`--p`, plays once, replay button). An x-ray band
	 * trails the beam: under the shroud, the board on the same grid, where every part the scan reads
	 * lights red. Each spec callout pops the moment the beam passes its part, so the readout fills
	 * left to right; the model name types into the readout first. The end state (and the server HTML,
	 * reduced motion) is the whole card with its four specs. Red is the Radeon accent here; heat
	 * colours stay reserved for speed.
	 */
	import { Autoplay } from '$lib/fx/autoplay.svelte';
	import { clamp01 } from '$lib/fx/motion';
	import Replay from '$lib/fx/Replay.svelte';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { fill, SCAN_BOARD as B, SCAN_CARD as C } from './data';
	import PulseXtx from './PulseXtx.svelte';
	import SceneHead from './SceneHead.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].how.scan);
	// starts as soon as the scene's top enters the viewport: the card is never waiting off-screen
	const tl = new Autoplay(2.8, '0px');
	const p = $derived(tl.p);
	/** The x-ray band behind the beam, as a fraction of the card width. */
	const BAND = 0.25;
	/** Beam position across the card: 0 → 1 + BAND, so the band leaves past the tail at the end. */
	const b = $derived(clamp01((p - 0.14) / 0.74) * (1 + BAND));
	/** Model name typing into the readout, before the beam starts. */
	const t = $derived(clamp01((p - 0.02) / 0.16));
	/** Fans spin up on arrival and coast to a stop (turns, eased out). */
	const spin = $derived(4 * (1 - (1 - p) ** 3));
	/** Card grid of `PulseXtx`. */
	const W = 800;
	const H = 330;

	const callouts = $derived(
		[
			{ id: 'arch', px: 290, py: 186, dir: 'down', end: false, value: B.chip.v, label: c.arch, d: C.arch.replace(/^RDNA(\d)\s+/, 'RDNA\u00a0$1 · ') },
			{ id: 'vram', px: 270, py: 59, dir: 'up', end: false, value: `${C.vramGB}\u00a0GB`, label: c.vram, d: `${B.memType.v} · ${B.busBits.v}-bit` },
			{ id: 'bw', px: 212, py: 175, dir: 'down', end: true, value: `${num(C.bwGBs.v, lang, 0)}\u00a0GB/s`, label: c.bw, d: `${B.gbps.v}\u00a0Gbps × ${B.busBits.v}\u00a0bit` },
			{ id: 'power', px: 528, py: 14, dir: 'up', end: false, value: `${num(B.tbpW.v, lang, 0)}\u00a0W`, label: c.power, d: `${B.pins8.v} × 8-pin` }
		].map((k) => ({ ...k, x: (k.px / W) * 100, y: (k.py / H) * 100, on: b >= k.px / W }))
	);
	const lit = $derived({ bus: b >= 172 / W, mem: b >= 215 / W, gpu: b >= 232 / W, pwr: b >= 440 / W });
	const found = $derived(callouts.filter((k) => k.on).length);
	/** One source chip for the four specs (in the readout), not a pill on every callout. */
	const specSrc = $derived([B.memType.src, C.bwGBs.src, B.chip.src, C.powerW.src]);
	const note = $derived(fill(c.note, { w: num(C.powerW.v, lang, 0) }));
</script>

<div class="wrap" use:tl.view style="--b:{b}; --t:{t}">
	<div class="layout">
		<div class="side">
			<SceneHead id="scene-scan" k={c.k} step={c.title} head={c.head} body={c.body} />
			<!-- scan readout: what the scan read, then the instrument -->
			<div class="readout">
				<p class="det">
					<span class="dl">{c.detected}</span>
					<span class="dn">{C.name}</span>
					<span class="dm">{B.maker} {B.series} · {c.lab}</span>
				</p>
				<div class="ctl">
					<span class="rl" aria-hidden="true">{c.title}</span>
					<span class="track" aria-hidden="true"><span class="fillbar"></span></span>
					<span class="found" aria-hidden="true" class:done={found === callouts.length}>
						{#each callouts as k, i (k.id)}<i class:on={i < found}></i>{/each}
						<b>{found}/{callouts.length}</b>
					</span>
					<span class="rsrc"><SourceTip {lang} src={specSrc} {note} /></span>
					<Replay {lang} onclick={tl.replay} disabled={tl.playing} />
				</div>
			</div>
		</div>
		<div class="stage">
			<div class="gpu" class:go={p > 0} style="--spin:{spin}">
				<div class="layer shroud"><PulseXtx part="shroud" /></div>
				<div class="layer xray"><PulseXtx part="xray" {lit} /></div>
				<div class="sweep" aria-hidden="true"><span class="beam"></span></div>
				<ul class="callouts" role="list">
					{#each callouts as k (k.id)}
						<li class="callout {k.dir}" class:end={k.end} class:on={k.on} style="--x:{k.x}%; --y:{k.y}%; --yn:{k.y}">
							<span class="pin" aria-hidden="true"></span>
							<span class="tag">
								<span class="v">{k.value}</span>
								<span class="l">{k.label}</span>
								<span class="d">{k.d}</span>
							</span>
						</li>
					{/each}
				</ul>
			</div>
		</div>
	</div>
</div>

<style>
	/* the launch slide and the sweep travel past the right edge: never widen the page */
	.wrap {
		--amd: #ff3b4f;
		position: relative;
		overflow-x: clip;
		scroll-margin-top: var(--header-clear);
	}
	/* heading + readout on the left, the card with its callout ring on the right; the whole scene
	 * fits one viewport (the card shrinks with the viewport height, never the other way round) */
	.layout {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		grid-template-columns: minmax(0, 0.78fr) minmax(0, 1.5fr);
		align-items: center;
		gap: clamp(2rem, 4vw, 5rem);
		padding-block: var(--header-clear) clamp(1.25rem, 3vh, 2.5rem);
	}
	.side {
		display: grid;
		gap: clamp(1.25rem, 3vh, 2.25rem);
		align-content: center;
	}
	/* room above and under the card for the callout ring */
	.stage {
		display: grid;
		padding-block: 7.5rem 7rem;
	}
	/* card and x-ray share one box and one 3D pose; 1rem + 16rem: header, padding and the ring */
	.gpu {
		position: relative;
		container-type: size;
		justify-self: center;
		width: min(100%, (100svh - var(--header-clear) - 17.5rem) * 800 / 330);
		aspect-ratio: 800 / 330;
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
	/* a soft red floor light under the card */
	.shroud::after {
		content: '';
		position: absolute;
		inset: 70% 8% -14%;
		background: radial-gradient(50% 50% at 50% 50%, rgb(255 59 79 / 0.18), transparent 70%);
		z-index: -1;
	}
	/* the x-ray band trails the beam (BAND = 0.25 of the card) */
	.xray {
		clip-path: inset(-12% calc(clamp(0, 1 - var(--b), 1) * 100%) -12% calc((var(--b) - 0.25) * 100%));
	}
	.sweep {
		position: absolute;
		inset: -10% 0;
		transform: translate3d(calc(min(var(--b), 1) * 100%), 0, 0);
		opacity: clamp(0, calc(min(var(--b), 1.04 - var(--b)) * 25), 1);
		pointer-events: none;
	}
	.beam {
		position: absolute;
		top: 0;
		bottom: 0;
		left: -1px;
		width: 2px;
		background: #fff1f2;
		box-shadow:
			0 0 10px 2px rgb(255 120 135 / 0.95),
			0 0 44px 14px rgb(255 59 79 / 0.45);
	}
	.beam::before {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		right: 0;
		width: 7rem;
		background: linear-gradient(90deg, transparent, rgb(255 59 79 / 0.18));
	}
	.callouts {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	/* revealed by clip + transform, never by opacity: the text is full contrast in every frame */
	/* every leader runs from its pin to just outside the card edge (container units of .gpu), so the
	 * tags form a ring above and below the card instead of covering it */
	.callout {
		--len: calc(var(--yn) * 1cqh + 1.2rem);
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
		border: 2px solid var(--amd);
		background: var(--bg-0);
		box-shadow: 0 0 14px rgb(255 59 79 / 0.75);
	}
	.pin::after {
		content: '';
		position: absolute;
		left: 50%;
		width: 1px;
		height: var(--len);
		background: linear-gradient(var(--amd), rgb(255 59 79 / 0.1));
	}
	.up .pin::after {
		bottom: 100%;
		background: linear-gradient(rgb(255 59 79 / 0.1), var(--amd));
	}
	.down {
		--len: calc((100 - var(--yn)) * 1cqh + 1.2rem);
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
		padding: 0.5rem 0.8rem 0.55rem;
		border: 1px solid rgb(255 59 79 / 0.5);
		box-shadow: 0 0 26px -10px rgb(255 59 79 / 0.8);
		border-radius: var(--r-md);
		background: rgb(11 11 13 / 0.92);
	}
	.up .tag {
		bottom: calc(var(--len) + 6px);
	}
	.down .tag {
		top: calc(var(--len) + 6px);
	}
	.v {
		font-family: var(--font-display);
		font-size: clamp(1.3rem, 0.8rem + 1.1vw, 1.95rem);
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
		color: var(--text);
	}
	.d {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.04em;
		color: var(--text-mute);
	}
	.callout.end .tag {
		left: auto;
		right: -0.6rem;
		justify-items: end;
	}
	/* ---- scan readout ---- */
	.readout {
		display: grid;
		gap: var(--sp-3);
		padding: var(--sp-4) var(--sp-4) var(--sp-3) var(--sp-5);
		border: 1px solid var(--line);
		border-left: 2px solid var(--amd);
		border-radius: var(--r-lg);
		background: linear-gradient(90deg, rgb(255 59 79 / 0.07), transparent 60%), rgb(11 11 13 / 0.7);
	}
	.det {
		display: grid;
		gap: 0.2rem;
		margin: 0;
	}
	.dl,
	.dm,
	.ctl {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}
	.dl {
		color: var(--amd);
	}
	/* the model name types in (clip, full contrast) */
	.dn {
		justify-self: start;
		font-family: var(--font-display);
		font-weight: 780;
		font-stretch: 110%;
		font-size: clamp(1.35rem, 1rem + 0.9vw, 1.9rem);
		letter-spacing: -0.02em;
		line-height: 1.1;
		color: var(--text-hi);
		clip-path: inset(-0.2em calc((1 - var(--t)) * 100%) -0.2em 0);
	}
	.dm {
		color: var(--text-mute);
		letter-spacing: 0.08em;
	}
	/* not `.bar`: design/components.css owns that class globally */
	.ctl {
		display: grid;
		grid-template-columns: auto minmax(3rem, 1fr) auto auto auto;
		align-items: center;
		gap: var(--sp-4);
		padding-top: var(--sp-3);
		border-top: 1px solid var(--line);
	}
	.rl {
		color: var(--text-hi);
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
		transform: scaleX(min(var(--b), 1));
		background: linear-gradient(90deg, #8f1b29, var(--amd) 60%, #ffd5da);
		box-shadow: 0 0 8px rgb(255 59 79 / 0.8);
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
		background: var(--amd);
		border-color: var(--amd);
		box-shadow: 0 0 6px rgb(255 59 79 / 0.7);
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
		.side {
			gap: var(--sp-4);
		}
		/* the 2 × 2 callout grid sits under the card */
		.stage {
			padding-block: 0 9.75rem;
		}
		.gpu {
			width: 100%;
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
			padding: var(--sp-3) var(--sp-3) var(--sp-2) var(--sp-4);
			gap: var(--sp-2);
		}
		.dm {
			letter-spacing: 0.03em;
		}
		.ctl {
			grid-template-columns: auto minmax(2rem, 1fr) auto auto auto;
			gap: var(--sp-3);
			padding-top: var(--sp-2);
		}
		/* icon-only source chip: the control row stays one line */
		.rsrc :global(.src-btn span) {
			display: none;
		}
		.callouts {
			position: absolute;
			top: calc(100% + var(--sp-4));
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
		.callout.end .tag {
			position: static;
			height: 100%;
			justify-items: start;
			text-align: left;
			white-space: normal;
			padding: 0.45rem 0.65rem 0.5rem;
		}
		.v {
			font-size: 1.15rem;
		}
		.l,
		.d {
			font-size: 0.625rem;
			letter-spacing: 0.04em;
		}
	}
	/* tablets: a smaller card and the four specs in one row keep the scene within one screen */
	@media (min-width: 600px) and (max-width: 900px) {
		.stage {
			padding-bottom: 6.5rem;
		}
		.gpu {
			width: min(100%, 36rem);
		}
		.callouts {
			grid-template-columns: repeat(4, minmax(0, 1fr));
		}
	}
	@media (max-width: 360px) {
		.found b {
			display: none;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.gpu.go {
			animation: none;
		}
	}
</style>
