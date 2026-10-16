<script lang="ts">
	/**
	 * Tachometer: a 240° dial, needle on a damped spring (one small overshoot), redline zone and a
	 * glow once the needle is in it. The arc behind the needle takes its colour from the heat ramp
	 * at the needle's position, so a hotter colour always means a higher t/s.
	 * `children` renders in the dial centre (usually an Odometer).
	 */
	import type { Snippet } from 'svelte';
	import { untrack } from 'svelte';
	import { heatColor, onFrame, reducedMotion, Spring } from './motion';

	let {
		value,
		max = 100,
		redline = 70,
		step = 10,
		tone = 'hot',
		label,
		size = '100%',
		/** Redline glow; turn off to show a "cooled" needle resting at a final value. */
		glowing = true,
		/** Hard launch: a stiff, under-damped needle that slams past the value and bounces, and a
		 * dial shake when it crosses into the red zone. */
		slam = false,
		children
	}: {
		value: number;
		max?: number;
		redline?: number;
		step?: number;
		tone?: 'hot' | 'cold';
		/** Accessible name, e.g. "Nasz silnik: 78,0 tokenu na sekundę". */
		label: string;
		size?: string;
		glowing?: boolean;
		slam?: boolean;
		children?: Snippet;
	} = $props();

	const SWEEP = 240;
	const uid = $props.id();
	const glowId = `tacho-glow-${uid}`;
	const R = 74;
	const C = 100;
	// svelte-ignore state_referenced_locally
	const spring = slam ? new Spring(value, 340, 10) : new Spring(value, 120, 13);
	// svelte-ignore state_referenced_locally
	let shown = $state(value);

	$effect(() => {
		spring.target = Math.min(max * 1.04, Math.max(0, value));
		if (reducedMotion()) {
			spring.snap();
			shown = spring.x;
			return;
		}
		return untrack(() =>
			onFrame((dt) => {
				shown = spring.step(dt);
				if (spring.settled) return false;
			})
		);
	});

	const polar = (deg: number, r: number) => {
		const a = (deg * Math.PI) / 180;
		return [C + r * Math.sin(a), C - r * Math.cos(a)] as const;
	};
	const angle = (v: number) => -SWEEP / 2 + (SWEEP * Math.min(max * 1.04, Math.max(0, v))) / max;
	function arc(v0: number, v1: number, r = R) {
		const [x0, y0] = polar(angle(v0), r);
		const [x1, y1] = polar(angle(v1), r);
		const large = angle(v1) - angle(v0) > 180 ? 1 : 0;
		return `M${x0.toFixed(2)} ${y0.toFixed(2)}A${r} ${r} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
	}
	// Ticks sit inside the arc, numbers outside it: the needle never covers a label.
	const ticks = $derived(
		Array.from({ length: Math.round(max / step) * 2 + 1 }, (_, i) => {
			const v = (i * step) / 2;
			const major = i % 2 === 0;
			const [x0, y0] = polar(angle(v), R - 7);
			const [x1, y1] = polar(angle(v), R - (major ? 17 : 12));
			const [tx, ty] = polar(angle(v), R + 14);
			return { v, major, x0, y0, x1, y1, tx, ty, red: v >= redline };
		})
	);
	const hot = $derived(tone === 'hot' ? heatColor(0.25 + (0.75 * shown) / max) : 'var(--before)');
	const glow = $derived(tone === 'hot' && glowing ? Math.min(1, Math.max(0, (shown - redline) / (max - redline))) : 0);

	/* Redline flare: the red ticks flash once when a hot needle crosses into the red zone. */
	const over = $derived(tone === 'hot' && glowing && shown >= redline);
	let flash = $state(false);
	let wasOver = false;
	$effect(() => {
		const o = over;
		if (o && !wasOver && !reducedMotion()) {
			flash = true;
			const t = setTimeout(() => (flash = false), 900);
			wasOver = o;
			return () => clearTimeout(t);
		}
		wasOver = o;
	});
</script>

<div class="tacho" class:flash class:slam style="--size:{size}" role="img" aria-label={label}>
	<svg viewBox="0 0 200 200" aria-hidden="true">
		<defs>
			<radialGradient id={glowId}>
				<stop offset="0" stop-color="#fff3d6" stop-opacity=".9" />
				<stop offset=".35" stop-color="#ff7a1a" stop-opacity=".45" />
				<stop offset="1" stop-color="#e2401c" stop-opacity="0" />
			</radialGradient>
		</defs>
		<circle cx={C} cy={C} r="99" class="face" />
		<path d={arc(0, max)} class="track" />
		<!-- red zone on its own outer ring, so the hot fill never hides where it starts -->
		<path d={arc(redline, max, R + 6)} class="red" />
		{#if shown > 0.05}<path d={arc(0, shown)} class="fill" style="stroke:{hot}" />{/if}
		{#each ticks as t (t.v)}
			<line x1={t.x0} y1={t.y0} x2={t.x1} y2={t.y1} class="tick" class:major={t.major} class:redtick={t.red} />
			{#if t.major && (t.v % (step * 2) === 0 || t.v === redline)}<text x={t.tx} y={t.ty} class="num" class:redtick={t.red}>{t.v}</text>{/if}
		{/each}
		<circle cx={C} cy={C} r="46" fill="url(#{glowId})" style="opacity:{glow}" class="glow" />
		<g style="transform: rotate({angle(shown)}deg)" class="needle">
			<path d="M{C - 2} {C + 11} L{C} {C - R + 9} L{C + 2} {C + 11} Z" style="fill:{tone === 'hot' ? hot : 'var(--before)'}" />
		</g>
		<circle cx={C} cy={C} r="5" class="hub" />
	</svg>
	{#if children}<div class="readout">{@render children()}</div>{/if}
</div>

<style>
	.tacho {
		position: relative;
		width: var(--size);
		aspect-ratio: 1;
	}
	svg {
		width: 100%;
		height: 100%;
		overflow: visible;
	}
	.face {
		fill: color-mix(in srgb, var(--bg-1) 70%, transparent);
		stroke: var(--line);
	}
	.track {
		fill: none;
		stroke: var(--bg-3);
		stroke-width: 6;
		stroke-linecap: round;
	}
	.red {
		fill: none;
		stroke: var(--heat-2);
		stroke-opacity: 0.9;
		stroke-width: 3;
	}
	.fill {
		fill: none;
		stroke-width: 6;
		stroke-linecap: round;
	}
	.tick {
		stroke: var(--text-mute);
		stroke-width: 1;
	}
	.tick.major {
		stroke: var(--text);
		stroke-width: 1.6;
	}
	.redtick {
		stroke: var(--heat-2);
		fill: #ff6a4a;
	}
	.num {
		font-family: var(--font-mono);
		font-size: 10px;
		fill: var(--text);
		text-anchor: middle;
		dominant-baseline: middle;
	}
	.num.redtick {
		fill: #ff6a4a;
	}
	.needle {
		transform-origin: 100px 100px;
		transform-box: view-box;
	}
	.hub {
		fill: var(--bg-3);
		stroke: var(--text-mute);
		stroke-width: 1.5;
	}
	.glow {
		mix-blend-mode: screen;
	}
	/* redline flare: the red zone and its ticks flash white-hot once */
	.flash .red {
		animation: red-flash 0.9s var(--ease-out);
	}
	.flash .redtick {
		animation: tick-flash 0.9s var(--ease-out);
	}
	@keyframes red-flash {
		15% {
			stroke: var(--heat-5);
			stroke-opacity: 1;
			filter: drop-shadow(0 0 6px #ff7a1a);
		}
	}
	@keyframes tick-flash {
		15% {
			stroke: var(--heat-5);
			fill: var(--heat-5);
		}
	}
	/* slam: the whole dial takes the hit when the needle lands in the red */
	.slam.flash svg {
		animation: dial-hit 0.45s var(--ease-out);
	}
	@keyframes dial-hit {
		15% {
			transform: translate3d(2px, -1px, 0) rotate(0.8deg);
		}
		35% {
			transform: translate3d(-2px, 1px, 0) rotate(-0.6deg);
		}
		60% {
			transform: translate3d(1px, 0, 0);
		}
	}
	.readout {
		position: absolute;
		inset: auto 0 6% 0;
		display: grid;
		place-items: center;
		text-align: center;
	}
</style>
