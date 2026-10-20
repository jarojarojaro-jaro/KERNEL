<script lang="ts">
	/**
	 * One side's speedometer in the hero: a 240° dial on the scale both sides share (0–140, red from
	 * 100), the needle and the value arc on the side's measured median, the number in the centre.
	 * `tone`: the typical app is steel, ours ember with a heat arc and a white-hot needle.
	 *
	 * One-shot entrance (`go`): the arc sweeps in and the needle swings up (ours lands with a small
	 * overshoot); then only ours lives, a tiny zero-mean jitter (±0,3 t/s) on the compositor. `still`
	 * stops it (paused, off screen). Server HTML, no JS and reduced motion show the final state; with
	 * JS the dial reads 0 until `go`.
	 */
	import { num } from '$lib/i18n';

	let {
		value,
		max,
		redline,
		tone,
		lang,
		unit,
		go = false,
		still = false
	}: {
		/** The measured t/s. */
		value: number;
		max: number;
		redline: number;
		tone: 'cold' | 'hot';
		lang: 'pl' | 'en';
		unit: string;
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

<div class="dial {tone}" class:go class:still>
	<svg viewBox="0 0 240 240" aria-hidden="true">
		<defs>
			<radialGradient id="face-{uid}" cx="50%" cy="44%" r="58%">
				<stop offset="0" stop-color="#17171b" />
				<stop offset=".72" stop-color="#0a0a0c" />
				<stop offset="1" stop-color="#050506" />
			</radialGradient>
			<linearGradient id="arc-{uid}" x1="0" y1="1" x2="1" y2="0">
				{#if tone === 'hot'}
					<stop offset="0" stop-color="#7a2e1f" />
					<stop offset=".3" stop-color="#e2401c" />
					<stop offset=".6" stop-color="#ff7a1a" />
					<stop offset=".85" stop-color="#ffc15a" />
					<stop offset="1" stop-color="#fff3d6" />
				{:else}
					<stop offset="0" stop-color="#3a4049" />
					<stop offset="1" stop-color="#b8c0ca" />
				{/if}
			</linearGradient>
		</defs>
		<circle cx={C} cy={C} r="119" fill="url(#face-{uid})" class="rim" />
		<path d={arc(redline, max, 103.5)} class="red" />
		<path d={arc(0, max, R)} class="track" />
		{#each ticks as t (t.v)}
			<line x1={t.x0} y1={t.y0} x2={t.x1} y2={t.y1} class="tick" class:major={t.major} class:redtick={t.red} />
			{#if t.major}<text x={t.tx} y={t.ty} class="num" class:redtick={t.red}>{t.v}</text>{/if}
		{/each}
		<path d={arc(0, max, R)} pathLength="1" class="arc" stroke="url(#arc-{uid})" style="stroke-dashoffset:{(1 - value / max).toFixed(4)}" />
		<g class="needle" style="transform:rotate({angle(value).toFixed(2)}deg)">
			<g class="jit">
				<path d="M{C - 4} {C + 14} L{C - 1.2} {C - 100} L{C + 1.2} {C - 100} L{C + 4} {C + 14} Z" class="halo" />
				<path d="M{C - 2.2} {C + 14} L{C - 0.6} {C - 99} L{C + 0.6} {C - 99} L{C + 2.2} {C + 14} Z" class="blade" />
			</g>
		</g>
		<circle cx={C} cy={C} r="7" class="hub" />
		<circle cx={C} cy={C} r="2.6" class="pin" />
	</svg>
	<p class="read"><b>{num(value, lang, 1)}</b><span>{unit}</span></p>
</div>

<style>
	.dial {
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
	.hot .rim {
		stroke: rgb(255 122 26 / 0.35);
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
	.cold .red {
		stroke-opacity: 0.4;
	}
	.tick {
		stroke: #4a4a52;
		stroke-width: 1;
	}
	.tick.major {
		stroke: var(--text);
		stroke-width: 1.8;
	}
	.cold .tick.major {
		stroke: var(--text-mute);
	}
	.tick.redtick {
		stroke: var(--heat-2);
	}
	.num {
		font-family: var(--font-mono);
		font-size: 9px;
		fill: var(--text-mute);
		text-anchor: middle;
		dominant-baseline: middle;
	}
	.num.redtick {
		fill: #ff6a4a;
	}
	.cold .num.redtick {
		fill: rgb(255 106 74 / 0.6);
	}
	.arc {
		fill: none;
		stroke-width: 10;
		stroke-linecap: round;
		stroke-dasharray: 1 2;
	}
	.hot .arc {
		filter: drop-shadow(0 0 5px rgb(255 122 26 / 0.75)) drop-shadow(0 0 16px rgb(226 64 28 / 0.45));
	}
	.needle,
	.jit {
		transform-box: view-box;
		transform-origin: 120px 120px;
	}
	.halo {
		fill: var(--before);
		opacity: 0.25;
		filter: blur(1.5px);
	}
	.blade {
		fill: #b8c0ca;
	}
	.hot .halo {
		fill: var(--heat-3);
		opacity: 0.45;
	}
	.hot .blade {
		fill: #fff6e4;
	}
	.hub {
		fill: #1c1c21;
		stroke: #6a6a72;
		stroke-width: 1.5;
	}
	.hot .hub {
		stroke: var(--heat-3);
	}
	.pin {
		fill: var(--before);
	}
	.hot .pin {
		fill: var(--heat-4);
	}
	/* the side's measured median, in the dial's open bottom */
	.read {
		position: absolute;
		left: 0;
		right: 0;
		top: 60%;
		margin: 0;
		display: grid;
		justify-items: center;
		gap: 0.1rem;
		line-height: 1;
		pointer-events: none;
	}
	.read b {
		font-family: var(--font-display);
		font-weight: 800;
		font-stretch: 115%;
		font-size: 15cqi;
		letter-spacing: -0.04em;
		font-variant-numeric: tabular-nums lining-nums;
		color: var(--before);
		text-shadow: 0 0 3px #050506;
		padding: 0.04em 0.1em 0.1em;
	}
	.hot .read b {
		color: #fff6e4;
		text-shadow:
			0 0 3px #050506,
			0 0 18px rgb(255 122 26 / 0.55);
	}
	.read span {
		font-family: var(--font-mono);
		font-size: max(0.55rem, 5cqi);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.hot .read span {
		color: var(--heat-4);
	}
	/* with JS, before the entrance: the dial reads 0 */
	:global(html.js) .dial:not(.go) .arc {
		stroke-dashoffset: 1 !important;
	}
	:global(html.js) .dial:not(.go) .needle {
		transform: rotate(-120deg) !important;
	}
	@media (prefers-reduced-motion: no-preference) {
		.go .arc {
			transition: stroke-dashoffset 1.3s var(--ease-out) 0.15s;
		}
		.cold.go .needle {
			transition: transform 1.3s var(--ease-out) 0.15s;
		}
		.hot.go .arc {
			transition-duration: 1.6s;
		}
		.hot.go .needle {
			transition: transform 1.6s cubic-bezier(0.2, 1.12, 0.3, 1) 0.15s;
		}
		/* after landing, ours never quite rests: ±0,3 t/s (≈ ±0,5°), zero-mean */
		.hot.go .jit {
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
