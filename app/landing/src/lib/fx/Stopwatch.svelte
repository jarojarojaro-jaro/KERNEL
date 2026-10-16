<script lang="ts">
	/**
	 * A stopwatch that really runs: counts 0 → `seconds` in real time once `run` turns true (and
	 * restarts whenever `runKey` changes), then stamps the measured value. Under reduced motion it
	 * shows the final value. The accessible text is always the measured value.
	 */
	import { untrack } from 'svelte';
	import { num } from '$lib/i18n';
	import { visible } from './actions';
	import { onFrame, reducedMotion } from './motion';

	let {
		seconds,
		run = true,
		runKey = '',
		lang,
		hot = false,
		label
	}: { seconds: number; run?: boolean; runKey?: string; lang: 'pl' | 'en'; hot?: boolean; label: string } = $props();

	let t = $state(0);
	let onScreen = true;
	let done = $state(false);

	$effect(() => {
		void runKey;
		const go = run;
		const target = seconds;
		return untrack(() => {
			if (reducedMotion()) {
				t = target;
				done = true;
				return;
			}
			t = 0;
			done = false;
			if (!go) return;
			return onFrame((dt) => {
				if (!onScreen) return; // offscreen: the clock holds, nothing paints
				t = Math.min(target, t + dt);
				if (t >= target) {
					done = true;
					return false;
				}
			});
		});
	});
	const pct = $derived(seconds > 0 ? t / seconds : 0);
</script>

<div class="sw" class:hot class:done role="img" use:visible={(v) => (onScreen = v)} aria-label="{label}: {num(seconds, lang, 1)} s">
	<svg viewBox="0 0 40 40" aria-hidden="true">
		<circle cx="20" cy="20" r="17" class="ring" />
		<circle cx="20" cy="20" r="17" class="arc" style="stroke-dashoffset:{106.8 * (1 - pct)}" />
	</svg>
	<span class="v" aria-hidden="true">{num(t, lang, 1)}<span class="s">s</span></span>
</div>

<style>
	.sw {
		display: inline-flex;
		align-items: center;
		gap: var(--sp-3);
	}
	svg {
		width: 2.25rem;
		height: 2.25rem;
		transform: rotate(-90deg);
	}
	.ring {
		fill: none;
		stroke: var(--bg-3);
		stroke-width: 3;
	}
	.arc {
		fill: none;
		stroke: var(--before);
		stroke-width: 3;
		stroke-dasharray: 106.8;
		stroke-linecap: round;
	}
	.hot .arc {
		stroke: var(--heat-3);
	}
	.v {
		font-family: var(--font-mono);
		font-variant-numeric: tabular-nums;
		font-size: var(--fs-2xl);
		color: var(--text);
		min-width: 4.5ch;
	}
	.hot .v {
		color: var(--text-hi);
	}
	.done.hot .v {
		color: var(--heat-4);
	}
	.s {
		font-size: 0.5em;
		margin-left: 0.15em;
		color: var(--text-mute);
	}
</style>
