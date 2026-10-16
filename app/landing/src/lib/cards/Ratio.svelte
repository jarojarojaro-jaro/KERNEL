<script lang="ts">
	/**
	 * A speed-up factor in the site's one speed-up style (showcase.css `.speedup`: heat-gradient
	 * display numerals in Mona Sans; below ×1 it is steel, `.speedup--down`), text from format.ts
	 * `fmtRatio`. At rest it always shows the measured value (never a half-counted one). Changing
	 * `replay` counts it up once from ×1 to the value (gallery hover); reduced motion ignores it.
	 */
	import { untrack } from 'svelte';
	import { easeOutExpo, onFrame, reducedMotion } from '$lib/fx/motion';
	import { fmtRatio } from '$lib/format';

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
			return onFrame((dt) => {
				t = Math.min(1, t + (dt * 1000) / duration);
				shown = t >= 1 ? target : 1 + (target - 1) * easeOutExpo(t);
				if (t >= 1) return false;
			});
		});
	});
</script>

<span class="speedup rx rx--{size}" class:speedup--down={value < 1}>{fmtRatio(shown, lang)}</span>

<style>
	.rx {
		display: inline-block;
		font-family: var(--font-display);
		font-variant-numeric: normal;
		font-feature-settings: normal;
	}
	.rx--sm {
		font-size: var(--fs-lg);
		letter-spacing: -0.02em;
	}
	.rx--md {
		font-size: clamp(1.9rem, 1.2rem + 1.8vw, 2.75rem);
	}
	.rx--lg {
		font-size: clamp(2.6rem, 1.4rem + 3vw, 4.25rem);
	}
	.rx--xl {
		font-size: clamp(5rem, 2rem + 9vw, 11rem);
		letter-spacing: -0.05em;
		filter: drop-shadow(0 0 30px rgb(255 122 26 / calc(0.1 + var(--glow, 0.6) * 0.4)));
	}
</style>
