<script lang="ts">
	/**
	 * The hero's large speedometer: a 240° dial driven every frame by its parent through `set(v)`.
	 * Built as stacked layers so a frame costs almost nothing: the face, ticks and numbers are one
	 * static SVG (never repainted); the needle is its own layer turned by a transform (compositor);
	 * the glow and the hot dial's outer aura are layers whose opacity follows the needle
	 * (compositor); only the value arc repaints (stroke-dashoffset). The hot dial wears a slowly
	 * turning heat edge (the hero CTA's language); the cold dial is muted steel.
	 * `value` is the server-rendered position (no JS: the dial rests there). With JS the dial reads
	 * 0 until the parent first calls `set`, so the needle can climb from 0 when the race starts.
	 * `children` renders in the open bottom of the dial (the measured readout).
	 */
	import type { Snippet } from 'svelte';

	let {
		value,
		max = 100,
		redline = 70,
		step = 20,
		tone = 'hot',
		children
	}: {
		value: number;
		max?: number;
		redline?: number;
		step?: number;
		tone?: 'hot' | 'cold';
		children?: Snippet;
	} = $props();

	const SWEEP = 240;
	const C = 100;
	const R = 74;
	const uid = $props.id();
	const fillId = `speedo-fill-${uid}`;
	const faceId = `speedo-face-${uid}`;

	const polar = (deg: number, r: number) => {
		const a = (deg * Math.PI) / 180;
		return [C + r * Math.sin(a), C - r * Math.cos(a)] as const;
	};
	const clampV = (v: number) => Math.min(max * 1.04, Math.max(0, v));
	const angle = (v: number) => -SWEEP / 2 + (SWEEP * clampV(v)) / max;
	function arc(v0: number, v1: number, r = R) {
		const [x0, y0] = polar(angle(v0), r);
		const [x1, y1] = polar(angle(v1), r);
		const large = angle(v1) - angle(v0) > 180 ? 1 : 0;
		return `M${x0.toFixed(2)} ${y0.toFixed(2)}A${r} ${r} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
	}
	// ticks inside the arc, numbers outside it: the needle never covers a label
	const ticks = $derived(
		Array.from({ length: Math.round(max / step) * 4 + 1 }, (_, i) => {
			const v = (i * step) / 4;
			const major = i % 4 === 0;
			const mid = !major && i % 2 === 0;
			const [x0, y0] = polar(angle(v), R - 8);
			const [x1, y1] = polar(angle(v), R - (major ? 19 : mid ? 15 : 12));
			const [tx, ty] = polar(angle(v), R + 15);
			return { v, major, mid, x0, y0, x1, y1, tx, ty, red: v >= redline };
		})
	);
	/** The value arc spans the whole scale; its visible length is a dash (pathLength 1). */
	const full = $derived(arc(0, max * 1.04));
	const frac = (v: number) => clampV(v) / (max * 1.04);
	const glowOf = (v: number) => (tone === 'hot' ? Math.min(1, Math.max(0, (v - redline * 0.6) / (max - redline * 0.6))) : 0);
	const auraOf = (v: number) => Math.min(1, Math.max(0, v / (max * 0.8)));

	let needleEl: HTMLElement | undefined = $state();
	let fillEl: SVGPathElement | undefined = $state();
	let glowEl: HTMLElement | undefined = $state();
	let auraEl: HTMLElement | undefined = $state();
	/** Driven by the parent (until then, with JS, the dial reads 0). */
	let live = $state(false);
	let last = Number.NaN;
	/** Move the dial to `v` t/s (direct DOM writes: no reactivity per frame). */
	export function set(v: number) {
		if (!live) live = true;
		const r = Math.round(v * 20) / 20;
		if (r === last) return;
		last = r;
		if (needleEl) needleEl.style.transform = `rotate(${angle(r).toFixed(2)}deg)`;
		if (fillEl) {
			fillEl.style.strokeDashoffset = (1 - frac(r)).toFixed(4);
			// a zero-length dash would still draw its round cap as a dot
			fillEl.style.opacity = r > 0.3 ? '' : '0';
		}
		if (glowEl) glowEl.style.opacity = glowOf(r).toFixed(3);
		if (auraEl) auraEl.style.opacity = auraOf(r).toFixed(3);
	}
</script>

<div class="speedo" class:hot={tone === 'hot'} class:live>
	{#if tone === 'hot'}
		<div class="aura" bind:this={auraEl} style="opacity:{auraOf(value).toFixed(3)}" aria-hidden="true"></div>
		<div class="edge" aria-hidden="true"></div>
	{/if}
	<div class="glow" bind:this={glowEl} style="opacity:{glowOf(value).toFixed(3)}" aria-hidden="true"></div>
	<svg class="dial" viewBox="0 0 200 200" aria-hidden="true">
		<defs>
			<radialGradient id={faceId} cx="50%" cy="42%" r="60%">
				<stop offset="0" stop-color="#18181c" />
				<stop offset=".7" stop-color="#0b0b0d" />
				<stop offset="1" stop-color="#050506" />
			</radialGradient>
			<linearGradient id={fillId} x1="0" y1="0" x2="1" y2="0">
				{#if tone === 'hot'}
					<stop offset="0" stop-color="#7a2e1f" />
					<stop offset=".35" stop-color="#e2401c" />
					<stop offset=".65" stop-color="#ff7a1a" />
					<stop offset=".88" stop-color="#ffc15a" />
					<stop offset="1" stop-color="#fff3d6" />
				{:else}
					<stop offset="0" stop-color="#3a4049" />
					<stop offset="1" stop-color="#a9b3c0" />
				{/if}
			</linearGradient>
		</defs>
		<circle cx={C} cy={C} r="98" fill="url(#{faceId})" class="rim" />
		<path d={arc(0, max)} class="track" />
		<path d={arc(redline, max, R + 6)} class="red" />
		{#each ticks as t (t.v)}
			<line x1={t.x0} y1={t.y0} x2={t.x1} y2={t.y1} class="tick" class:major={t.major} class:mid={t.mid} class:redtick={t.red} />
			{#if t.major}<text x={t.tx} y={t.ty} class="num" class:redtick={t.red}>{t.v}</text>{/if}
		{/each}
	</svg>
	<svg class="value" viewBox="0 0 200 200" aria-hidden="true">
		<path d={full} pathLength="1" class="fill" stroke="url(#{fillId})" bind:this={fillEl} style="stroke-dashoffset:{(1 - frac(value)).toFixed(4)}" />
	</svg>
	<div class="needle" bind:this={needleEl} style="transform:rotate({angle(value).toFixed(2)}deg)" aria-hidden="true">
		<svg viewBox="0 0 200 200">
			<path d="M{C - 4.5} {C + 16} L{C - 1.6} {C - R + 4} L{C + 1.6} {C - R + 4} L{C + 4.5} {C + 16} Z" class="halo" />
			<path d="M{C - 2.6} {C + 16} L{C - 0.8} {C - R + 5} L{C + 0.8} {C - R + 5} L{C + 2.6} {C + 16} Z" class="blade" />
		</svg>
	</div>
	<svg class="cap" viewBox="0 0 200 200" aria-hidden="true">
		<circle cx={C} cy={C} r="9" class="hub" />
		<circle cx={C} cy={C} r="3.2" class="pin" />
	</svg>
	{#if children}<div class="readout">{@render children()}</div>{/if}
</div>

<style>
	.speedo {
		position: relative;
		width: 100%;
		aspect-ratio: 1;
		container-type: inline-size;
		isolation: isolate;
	}
	.speedo > svg,
	.needle,
	.glow,
	.edge,
	.aura {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
	}
	svg {
		overflow: visible;
	}
	/* with JS, before the race drives it: the dial reads 0 (no JS: it rests on `value`) */
	:global(html.js) .speedo:not(.live) .needle {
		transform: rotate(-120deg) !important;
	}
	:global(html.js) .speedo:not(.live) :is(.value, .glow, .aura) {
		opacity: 0 !important;
	}
	/* the hot dial's heat aura: a soft ring of light around it, brighter the faster it runs */
	.aura {
		inset: -14%;
		width: auto;
		height: auto;
		z-index: -1;
		border-radius: 50%;
		background: radial-gradient(closest-side, transparent 66%, rgb(255 122 26 / 0.26) 73%, rgb(226 64 28 / 0.12) 84%, transparent 100%);
		pointer-events: none;
		will-change: opacity;
	}
	/* the hot dial's living heat edge: a conic ring turned by transform (compositor only) */
	.edge {
		inset: -1.5px;
		width: auto;
		height: auto;
		border-radius: 50%;
		background: conic-gradient(
			var(--heat-2),
			var(--heat-3) 12%,
			var(--heat-5) 20%,
			var(--heat-4) 28%,
			rgb(255 122 26 / 0.16) 42%,
			rgb(255 122 26 / 0.08) 78%,
			var(--heat-2)
		);
		-webkit-mask: radial-gradient(closest-side, transparent calc(100% - 2px), #000 calc(100% - 1.5px));
		mask: radial-gradient(closest-side, transparent calc(100% - 2px), #000 calc(100% - 1.5px));
		animation: edge-turn 5.5s linear infinite;
		will-change: transform;
	}
	@keyframes edge-turn {
		to {
			transform: rotate(1turn);
		}
	}
	/* the heat bloom behind the needle: its opacity follows the needle */
	.glow {
		z-index: 1;
		border-radius: 50%;
		background: radial-gradient(circle at 50% 50%, rgb(255 243 214 / 0.32), rgb(255 122 26 / 0.22) 30%, rgb(226 64 28 / 0.08) 55%, transparent 70%);
		mix-blend-mode: screen;
		pointer-events: none;
		will-change: opacity;
	}
	.dial {
		z-index: 0;
	}
	.value {
		z-index: 2;
	}
	.needle {
		z-index: 3;
		will-change: transform;
	}
	.cap {
		z-index: 4;
	}
	.rim {
		stroke: var(--line);
		stroke-width: 1;
	}
	.hot .rim {
		stroke: transparent;
	}
	.track {
		fill: none;
		stroke: #1c1c21;
		stroke-width: 9;
		stroke-linecap: round;
	}
	.red {
		fill: none;
		stroke: var(--heat-2);
		stroke-opacity: 0.85;
		stroke-width: 2.5;
	}
	/* the typical app's dial: muted steel, the red zone only hinted */
	.speedo:not(.hot) .red {
		stroke-opacity: 0.4;
	}
	.speedo:not(.hot) .tick.major {
		stroke: var(--text-mute);
	}
	.speedo:not(.hot) .num {
		fill: var(--text-mute);
	}
	.speedo:not(.hot) .num.redtick {
		fill: rgb(255 106 74 / 0.6);
	}
	.fill {
		fill: none;
		stroke-width: 9;
		stroke-linecap: round;
		/* gap 2 > path length 1: the path's end always falls inside a gap (no stray cap dot) */
		stroke-dasharray: 1 2;
	}
	.hot .fill {
		filter: drop-shadow(0 0 4px rgb(255 122 26 / 0.55));
	}
	.tick {
		stroke: #4a4a52;
		stroke-width: 1;
	}
	.tick.mid {
		stroke: #6a6a72;
		stroke-width: 1.3;
	}
	.tick.major {
		stroke: var(--text);
		stroke-width: 2;
	}
	.tick.redtick {
		stroke: var(--heat-2);
	}
	.num {
		font-family: var(--font-mono);
		font-size: 10.5px;
		font-weight: 500;
		fill: var(--text);
		text-anchor: middle;
		dominant-baseline: middle;
	}
	.num.redtick {
		fill: #ff6a4a;
	}
	.needle {
		transform-origin: 50% 50%;
	}
	.halo {
		fill: var(--before);
		opacity: 0.18;
	}
	.blade {
		fill: #a9b1bc;
	}
	.hot .halo {
		fill: var(--heat-3);
		opacity: 0.4;
	}
	.hot .blade {
		fill: var(--heat-5);
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
	.readout {
		position: absolute;
		z-index: 5;
		inset: 56% 0 auto 0;
		display: grid;
		justify-items: center;
		text-align: center;
		pointer-events: none;
	}
	@media (prefers-reduced-motion: reduce) {
		.edge {
			animation: none;
		}
	}
</style>
