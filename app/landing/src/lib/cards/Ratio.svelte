<script lang="ts">
	/**
	 * A speed-up factor in the site's one speed-up style (showcase.css `.speedup`: heat-gradient
	 * display numerals in Mona Sans; below ×1 it is steel, `.speedup--down`), text from format.ts
	 * `fmtRatio`. Every gain has the same heat colour; its size shows through size, weight and glow
	 * (`heatOf`): ×2,0 big and lit, ×1,05 smaller and lighter. At rest it always shows the measured value (never a half-counted one). Changing
	 * `replay` counts it up once from ×1 to the value; a throttled frame loop (hidden tab) still lands
	 * on the value. Reduced motion ignores it.
	 */
	import { untrack } from 'svelte';
	import { easeOutExpo, onFrame, reducedMotion } from '$lib/fx/motion';
	import { fmtRatio } from '$lib/format';
	import { heatOf } from './explorer';

	let {
		value,
		lang,
		size = 'md',
		replay = 0,
		duration = 900
	}: { value: number; lang: 'pl' | 'en'; size?: 'sm' | 'md' | 'lg' | 'xl'; replay?: number; duration?: number } = $props();

	// svelte-ignore state_referenced_locally
	let shown = $state(value);
	let seen = -1;

	$effect(() => {
		const key = replay;
		const target = value;
		return untrack(() => {
			const first = seen === -1;
			seen = key;
			if (first || reducedMotion()) {
				shown = target;
				return;
			}
			let t = 0;
			const stop = onFrame((dt) => {
				t = Math.min(1, t + (dt * 1000) / duration);
				shown = t >= 1 ? target : 1 + (target - 1) * easeOutExpo(t);
				if (t >= 1) return false;
			});
			const settle = setTimeout(() => {
				stop();
				shown = target;
			}, duration + 120);
			return () => {
				clearTimeout(settle);
				stop();
				shown = target;
			};
		});
	});
</script>

<span class="speedup rx rx--{size}" class:speedup--down={value < 1} style="--rm:{heatOf(value)}">{fmtRatio(shown, lang)}</span>

<style>
	.rx {
		display: inline-block;
		font-family: var(--font-display);
		font-variant-numeric: normal;
		font-feature-settings: normal;
		/*
		 * One heat colour for every gain (the full ramp; --rh pins the shared .speedup mix to it).
		 * The magnitude (--rm = heatOf) shows through size, weight and glow: ×2,0 is big, heavy and
		 * lit, ×1,05 smaller and lighter, never muted.
		 */
		--rh: 1;
		font-size: calc(var(--rx-fs) * (0.8 + var(--rm, 1) * 0.2));
		font-weight: calc(660 + var(--rm, 1) * 200);
	}
	.rx:not(.speedup--down) {
		filter: drop-shadow(0 0 calc(var(--rm) * 0.22em) rgb(var(--hot-rgb, 255 122 26) / calc(0.1 + var(--rm) * 0.4)));
	}
	.rx--sm {
		--rx-fs: var(--fs-lg);
		letter-spacing: -0.02em;
	}
	.rx--md {
		--rx-fs: clamp(1.9rem, 1.2rem + 1.8vw, 2.75rem);
	}
	.rx--lg {
		--rx-fs: clamp(2.6rem, 1.4rem + 3vw, 4.25rem);
	}
	.rx--xl {
		--rx-fs: clamp(5rem, 2rem + 9vw, 11rem);
		letter-spacing: -0.05em;
	}
</style>
