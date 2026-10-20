<script lang="ts">
	/**
	 * The hero's instrument cluster: one 240° dial on one scale for both sides. Our speed is a thick
	 * heat arc and a white-hot needle; the typical app is a ghost: a thin steel arc and needle parked
	 * at its speed. The centre reads our measured median, the open bottom the speed-up.
	 *
	 * One-shot entrance (`go`): the arcs sweep in, the needles swing up (ours lands with a small
	 * overshoot) and the speed-up counts up from 1×; after that only our needle lives, a tiny
	 * zero-mean jitter (±0,3 t/s) on the compositor. `still` stops the jitter (paused, off screen).
	 * Server HTML, no JS and reduced motion show the final state; with JS the dial reads 0 until `go`.
	 */
	import Ratio from '$lib/cards/Ratio.svelte';
	import { num } from '$lib/i18n';

	let {
		max,
		redline,
		cold,
		hot,
		gain,
		lang,
		unit,
		faster,
		go = false,
		still = false
	}: {
		max: number;
		redline: number;
		/** The typical app's measured t/s. */
		cold: number;
		/** Ours. */
		hot: number;
		gain: number;
		lang: 'pl' | 'en';
		unit: string;
		faster: string;
		go?: boolean;
		still?: boolean;
	} = $props();

	const C = 120;
	const R = 96;
	const SWEEP = 240;
	const angle = (v: number) => -SWEEP / 2 + (SWEEP * Math.min(max, Math.max(0, v))) / max;
	const polar = (deg: number, r: number) => {
		const a = (deg * Math.PI) / 180;
		return [C + r * Math.sin(a), C - r * Math.cos(a)] as const;
	};
	function arc(v0: number, v1: number, r: number) {
		const [x0, y0] = polar(angle(v0), r);
		const [x1, y1] = polar(angle(v1), r);
		const large = angle(v1) - angle(v0) > 180 ? 1 : 0;
		return `M${x0.toFixed(2)} ${y0.toFixed(2)}A${r} ${r} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
	}
	const step = $derived(max <= 160 ? 20 : 50);
	const ticks = $derived(
		Array.from({ length: Math.round(max / (step / 2)) + 1 }, (_, i) => {
			const v = (i * step) / 2;
			const major = i % 2 === 0;
			const [x0, y0] = polar(angle(v), 88);
			const [x1, y1] = polar(angle(v), major ? 79 : 84);
			const [tx, ty] = polar(angle(v), 112);
			return { v, major, x0, y0, x1, y1, tx, ty, red: v >= redline };
		})
	);
	const uid = $props.id();
</script>

<div class="cluster" class:go class:still>
	<svg viewBox="0 0 240 240" aria-hidden="true">
		<defs>
			<radialGradient id="face-{uid}" cx="50%" cy="44%" r="58%">
				<stop offset="0" stop-color="#17171b" />
				<stop offset=".72" stop-color="#0a0a0c" />
				<stop offset="1" stop-color="#050506" />
			</radialGradient>
			<linearGradient id="heat-{uid}" x1="0" y1="1" x2="1" y2="0">
				<stop offset="0" stop-color="#7a2e1f" />
				<stop offset=".3" stop-color="#e2401c" />
				<stop offset=".6" stop-color="#ff7a1a" />
				<stop offset=".85" stop-color="#ffc15a" />
				<stop offset="1" stop-color="#fff3d6" />
			</linearGradient>
		</defs>
		<circle cx={C} cy={C} r="119" fill="url(#face-{uid})" class="rim" />
		<path d={arc(redline, max, 103.5)} class="red" />
		<path d={arc(0, max, R)} class="track" />
		{#each ticks as t (t.v)}
			<line x1={t.x0} y1={t.y0} x2={t.x1} y2={t.y1} class="tick" class:major={t.major} class:redtick={t.red} />
			{#if t.major}<text x={t.tx} y={t.ty} class="num" class:redtick={t.red}>{t.v}</text>{/if}
		{/each}
		<!-- the typical app: a ghost arc and needle on the inner ring -->
		<path d={arc(0, max, 73)} class="ghost-track" />
		<path d={arc(0, max, 73)} pathLength="1" class="ghost-arc" style="stroke-dashoffset:{(1 - cold / max).toFixed(4)}" />
		<g class="needle ghost" style="transform:rotate({angle(cold).toFixed(2)}deg)">
			<path d="M{C - 1.6} {C + 10} L{C - 0.5} {C - 72} L{C + 0.5} {C - 72} L{C + 1.6} {C + 10} Z" />
		</g>
		<!-- ours: the heat arc and the white-hot needle -->
		<path d={arc(0, max, R)} pathLength="1" class="hot-arc" stroke="url(#heat-{uid})" style="stroke-dashoffset:{(1 - hot / max).toFixed(4)}" />
		<g class="needle hot" style="transform:rotate({angle(hot).toFixed(2)}deg)">
			<g class="jit">
				<path d="M{C - 4} {C + 14} L{C - 1.2} {C - 100} L{C + 1.2} {C - 100} L{C + 4} {C + 14} Z" class="halo" />
				<path d="M{C - 2.2} {C + 14} L{C - 0.6} {C - 99} L{C + 0.6} {C - 99} L{C + 2.2} {C + 14} Z" class="blade" />
			</g>
		</g>
		<circle cx={C} cy={C} r="7" class="hub" />
		<circle cx={C} cy={C} r="2.6" class="pin" />
	</svg>
	<p class="read"><b>{num(hot, lang, 1)}</b><span>{unit}</span></p>
	<p class="x"><Ratio value={gain} {lang} size="xl" replay={go ? 1 : 0} duration={1500} /><span>{faster}</span></p>
</div>

<style>
	.cluster {
		position: relative;
		width: 100%;
		aspect-ratio: 1;
		container-type: inline-size;
		-webkit-user-select: none;
		user-select: none;
	}
	svg {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		overflow: visible;
	}
	.rim {
		stroke: rgb(255 255 255 / 0.07);
		stroke-width: 1;
		filter: drop-shadow(0 18px 40px rgb(0 0 0 / 0.6));
	}
	.track {
		fill: none;
		stroke: #1b1b20;
		stroke-width: 10;
		stroke-linecap: round;
	}
	.red {
		fill: none;
		stroke: var(--heat-2);
		stroke-opacity: 0.85;
		stroke-width: 2;
	}
	.tick {
		stroke: #4a4a52;
		stroke-width: 1;
	}
	.tick.major {
		stroke: var(--text);
		stroke-width: 1.8;
	}
	.tick.redtick {
		stroke: var(--heat-2);
	}
	.num {
		font-family: var(--font-mono);
		font-size: 8.5px;
		fill: var(--text-mute);
		text-anchor: middle;
		dominant-baseline: middle;
	}
	.num.redtick {
		fill: #ff6a4a;
	}
	.ghost-track {
		fill: none;
		stroke: rgb(255 255 255 / 0.05);
		stroke-width: 2.5;
	}
	.ghost-arc {
		fill: none;
		stroke: #8d97a4;
		stroke-width: 2.5;
		stroke-linecap: round;
		stroke-dasharray: 1 2;
	}
	.hot-arc {
		fill: none;
		stroke-width: 10;
		stroke-linecap: round;
		stroke-dasharray: 1 2;
		filter: drop-shadow(0 0 5px rgb(255 122 26 / 0.75)) drop-shadow(0 0 16px rgb(226 64 28 / 0.45));
	}
	.needle {
		transform-box: view-box;
		transform-origin: 120px 120px;
	}
	.jit {
		transform-box: view-box;
		transform-origin: 120px 120px;
	}
	.ghost path {
		fill: #a9b1bc;
		opacity: 0.7;
	}
	.halo {
		fill: var(--heat-3);
		opacity: 0.45;
		filter: blur(1.5px);
	}
	.blade {
		fill: #fff6e4;
	}
	.hub {
		fill: #1c1c21;
		stroke: var(--heat-3);
		stroke-width: 1.5;
	}
	.pin {
		fill: var(--heat-4);
	}
	/* our measured median, in the centre */
	.read {
		position: absolute;
		left: 0;
		right: 0;
		top: 27%;
		margin: 0;
		display: grid;
		justify-items: center;
		gap: 0.15rem;
		line-height: 1;
		pointer-events: none;
	}
	.read b {
		font-family: var(--font-display);
		font-weight: 800;
		font-stretch: 115%;
		font-size: 11cqi;
		letter-spacing: -0.04em;
		font-variant-numeric: tabular-nums lining-nums;
		color: #fff6e4;
		text-shadow:
			0 0 3px #050506,
			0 0 18px rgb(255 122 26 / 0.55);
		padding: 0.04em 0.1em 0.1em;
	}
	.read span {
		font-family: var(--font-mono);
		font-size: max(0.6rem, 3.4cqi);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--heat-4);
	}
	/* the speed-up in the dial's open bottom: the cluster's loudest figure */
	.x {
		position: absolute;
		left: 0;
		right: 0;
		top: 66%;
		margin: 0;
		display: grid;
		justify-items: center;
		gap: 0.2rem;
		line-height: 1;
		pointer-events: none;
	}
	.cluster .x :global(.speedup) {
		--rx-fs: 21cqi;
		background: linear-gradient(180deg, #fff 8%, var(--heat-5) 30%, var(--heat-4) 55%, var(--heat-3) 80%, var(--heat-2));
		-webkit-background-clip: text;
		background-clip: text;
		filter: drop-shadow(0 0 18px rgb(255 122 26 / 0.5));
	}
	.x span {
		font-family: var(--font-mono);
		font-size: max(0.62rem, 3.5cqi);
		font-weight: 600;
		letter-spacing: 0.2em;
		text-transform: uppercase;
		color: var(--heat-4);
	}
	/* with JS, before the entrance: the dial reads 0 */
	:global(html.js) .cluster:not(.go) :is(.hot-arc, .ghost-arc) {
		stroke-dashoffset: 1 !important;
	}
	:global(html.js) .cluster:not(.go) .needle {
		transform: rotate(-120deg) !important;
	}
	@media (prefers-reduced-motion: no-preference) {
		.go .ghost-arc {
			transition: stroke-dashoffset 1.2s var(--ease-out) 0.1s;
		}
		.go .ghost {
			transition: transform 1.2s var(--ease-out) 0.1s;
		}
		.go .hot-arc {
			transition: stroke-dashoffset 1.6s var(--ease-out) 0.25s;
		}
		.go .hot {
			transition: transform 1.6s cubic-bezier(0.2, 1.12, 0.3, 1) 0.25s;
		}
		/* after landing, ours never quite rests: ±0,3 t/s (≈ ±0,5°), zero-mean */
		.go .jit {
			animation: jit 1.9s linear 2s infinite;
		}
		.still .jit {
			animation-play-state: paused;
		}
	}
	@keyframes jit {
		0%,
		100% {
			transform: rotate(0deg);
		}
		17% {
			transform: rotate(0.45deg);
		}
		31% {
			transform: rotate(-0.2deg);
		}
		52% {
			transform: rotate(0.3deg);
		}
		68% {
			transform: rotate(-0.5deg);
		}
		84% {
			transform: rotate(0.15deg);
		}
	}
</style>
