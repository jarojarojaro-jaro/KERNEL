<script lang="ts">
	/**
	 * Two answer times side by side. The measured targets are always printed big at the end of each
	 * track; the tracks fill in real time (a 34,5 s answer really takes 34,5 s), with a small running
	 * clock as secondary information. When the faster lane stops it is stamped done and the time it
	 * saved is marked on the slower lane's track. The race runs only while `run` is true (the parent
	 * starts and interrupts it); otherwise, and on SSR and under reduced motion, the lanes show the
	 * final state.
	 */
	import { untrack } from 'svelte';
	import { num } from '$lib/i18n';
	import { onFrame, reducedMotion } from '$lib/fx/motion';

	let {
		lanes,
		run = true,
		runKey = '',
		lang,
		labels
	}: {
		lanes: { label: string; seconds: number; hot: boolean }[];
		run?: boolean;
		runKey?: string;
		lang: 'pl' | 'en';
		labels: { done: string; saved: (s: string) => string };
	} = $props();

	const max = $derived(Math.max(...lanes.map((l) => l.seconds)));
	// svelte-ignore state_referenced_locally
	let t = $state(max);
	const fast = $derived(Math.min(...lanes.map((l) => l.seconds)));

	$effect(() => {
		void runKey;
		const go = run;
		const end = max;
		return untrack(() => {
			if (!go || reducedMotion()) {
				t = end;
				return;
			}
			t = 0;
			return onFrame((dt) => {
				t = Math.min(end, t + dt);
				if (t >= end) return false;
			});
		});
	});
	const gapOn = $derived(t >= fast && max > fast);
</script>

<div class="tr" role="img" aria-label={lanes.map((l) => `${l.label}: ${num(l.seconds, lang)} s`).join(', ')}>
	{#each lanes as l, i (l.label)}
		{@const done = t >= l.seconds}
		<div class="lane" class:hot={l.hot} class:done aria-hidden="true">
			<div class="who">
				<span class="name">{l.label}</span>
				<span class="clock mono">{#if done && t > 0}{labels.done}{/if}</span>
			</div>
			<div class="track">
				<div class="fill" style="transform:scaleX({Math.min(t, l.seconds) / max})"></div>
				<div class="end" style="left:{(l.seconds / max) * 100}%"></div>
				<!-- one playhead runs across both tracks; the running time rides under the bottom one -->
				{#if t < max}
					<div class="head" style="left:{(t / max) * 100}%">{#if i === lanes.length - 1}<span class="mono">{num(t, lang)} s</span>{/if}</div>
				{/if}
				{#if l.seconds > fast}
					<div class="gap" class:on={gapOn} style="left:{(fast / max) * 100}%; width:{((l.seconds - fast) / max) * 100}%">
						<span class="mono">{labels.saved(num(l.seconds - fast, lang))}</span>
					</div>
				{/if}
			</div>
			<p class="target mono">{num(l.seconds, lang)}<span>s</span></p>
		</div>
	{/each}
</div>

<style>
	.tr {
		display: grid;
		gap: var(--sp-6);
		padding-bottom: 0.8rem;
	}
	.lane {
		display: grid;
		grid-template-columns: minmax(8rem, 12rem) minmax(0, 1fr) 9.5rem;
		align-items: center;
		gap: var(--sp-2) var(--sp-5);
	}
	.who {
		display: grid;
		gap: 0.15rem;
	}
	.name {
		font-size: var(--fs-sm);
		color: var(--text);
	}
	.hot .name {
		color: var(--text-hi);
		font-weight: 650;
	}
	.clock {
		min-height: 1.1em;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		letter-spacing: 0.06em;
		text-transform: uppercase;
	}
	.done .clock {
		color: var(--text);
	}
	.hot.done .clock {
		color: var(--text-hi);
	}
	.head {
		position: absolute;
		top: -0.5rem;
		bottom: -0.5rem;
		width: 1px;
		background: rgb(237 234 227 / 0.55);
		pointer-events: none;
	}
	.head span {
		position: absolute;
		top: calc(100% + 0.2rem);
		left: 0;
		transform: translateX(-50%);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		white-space: nowrap;
	}
	.track {
		position: relative;
		height: 1.1rem;
		border-radius: var(--r-pill);
		background: var(--bg-2);
		box-shadow: inset 0 0 0 1px var(--line);
	}
	.fill {
		position: absolute;
		inset: 0;
		border-radius: inherit;
		background: linear-gradient(90deg, #2a3038, var(--before));
		transform-origin: left center;
	}
	.hot .fill {
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 18px rgb(255 122 26 / 0.35);
	}
	.end {
		position: absolute;
		top: -0.35rem;
		bottom: -0.35rem;
		width: 2px;
		margin-left: -1px;
		background: var(--line-strong);
	}
	.done .end {
		background: var(--text-hi);
	}
	/* the time the faster lane saved, marked on the slower track */
	.gap {
		position: absolute;
		top: -0.45rem;
		bottom: -0.45rem;
		border: 1px solid var(--text-hi);
		border-radius: var(--r-sm);
		background: rgb(237 234 227 / 0.1);
		opacity: 0;
		transform: scaleY(0.4);
		transition:
			opacity 0.5s var(--ease-out),
			transform 0.5s var(--ease-spring);
	}
	.gap.on {
		opacity: 1;
		transform: none;
	}
	.gap span {
		position: absolute;
		left: 50%;
		bottom: calc(100% + 0.3rem);
		transform: translateX(-50%);
		white-space: nowrap;
		font-size: var(--fs-xs);
		font-weight: 600;
		color: var(--text-hi);
	}
	.target {
		margin: 0;
		text-align: right;
		font-size: var(--fs-2xl);
		font-weight: 600;
		line-height: 1;
		color: var(--before);
	}
	.hot .target {
		color: var(--text-hi);
	}
	.target span {
		margin-left: 0.15em;
		font-size: 0.45em;
		color: var(--text-mute);
	}
	@media (max-width: 40rem) {
		.lane {
			grid-template-columns: minmax(0, 1fr) auto;
		}
		.track {
			grid-column: 1 / -1;
			grid-row: 2;
		}
		.target {
			grid-row: 1;
			grid-column: 2;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.gap {
			transition: none;
		}
	}
</style>
