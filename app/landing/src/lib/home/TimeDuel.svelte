<script lang="ts">
	/**
	 * Two answer times, shown as the result first (big, static: before → after), then replayed in
	 * real time as secondary: two bars on one shared time axis grow at the same real-time pace, so
	 * the hot one stops halfway; when it stops it is stamped and the gap lights up. The running
	 * Stopwatches sit under the bars. CSS-timed (no JS clock). At rest (server HTML, before `run`,
	 * reduced motion) everything shows the final state; the replay only runs while `run` is on and
	 * jumps to the final state if it leaves the viewport or the tab is hidden.
	 */
	import { onMount } from 'svelte';
	import { visible } from '$lib/fx/actions';
	import { onFinish } from '$lib/fx/motion';
	import Stopwatch from '$lib/fx/Stopwatch.svelte';
	import { num, type Lang } from '$lib/i18n';
	import { fill } from './data';

	type Side = { label: string; s: number };
	let {
		cold,
		hot,
		lang,
		run,
		runKey,
		done,
		gap,
		title
	}: { cold: Side; hot: Side; lang: Lang; run: boolean; runKey: string; done: string; gap: string; title: string } = $props();

	const top = $derived(Math.max(cold.s, hot.s));
	/** The replay was cut short (left the viewport, hidden tab): show the final state. */
	let cut = $state(false);
	$effect(() => {
		void runKey;
		cut = false;
	});
	onMount(() => onFinish(() => (cut = true)));
	const live = $derived(run && !cut);
	const diff = $derived(cold.s - hot.s);
</script>

<div class="td">
	<p class="th">{title}</p>
	<p class="targets">
		<span class="tc"><span class="tl">{cold.label}</span><b>{num(cold.s, lang)}<small>s</small></b></span>
		<span class="ar" aria-hidden="true">→</span>
		<span class="th2"><span class="tl">{hot.label}</span><b>{num(hot.s, lang)}<small>s</small></b></span>
	</p>
	{#key runKey}
		<div class="replay" class:go={live} use:visible={(v) => !v && live && (cut = true)} style="--c:{cold.s}s; --h:{hot.s}s; --fc:{cold.s / top}; --fh:{hot.s / top}">
			<div class="row">
				<span class="lanebar"><span class="fill"></span></span>
				<Stopwatch seconds={cold.s} run={live} {runKey} {lang} label={cold.label} />
			</div>
			<div class="row hot">
				<span class="lanebar"><span class="fill"></span><span class="stamp">{done}</span></span>
				<Stopwatch seconds={hot.s} run={live} {runKey} {lang} hot label={hot.label} />
			</div>
			{#if diff > 0}<p class="gap">{fill(gap, { s: num(diff, lang) })}</p>{/if}
		</div>
	{/key}
</div>

<style>
	.td {
		display: grid;
		gap: var(--sp-4);
	}
	.th {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--text-mute);
	}
	.targets {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		gap: var(--sp-2) var(--sp-5);
	}
	.tc,
	.th2 {
		display: grid;
		gap: 0.2rem;
	}
	.tl {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.targets b {
		font-family: var(--font-mono);
		font-weight: 400;
		font-size: clamp(2.2rem, 1.4rem + 2vw, 3.4rem);
		letter-spacing: -0.04em;
		line-height: 1;
		color: var(--before);
	}
	.th2 b {
		color: var(--heat-5);
	}
	.th2 .tl {
		color: var(--text-hi);
	}
	small {
		font-size: 0.4em;
		margin-left: 0.15em;
		color: var(--text-mute);
	}
	.ar {
		font-size: var(--fs-xl);
		color: var(--text-mute);
		padding-bottom: 0.3rem;
	}
	.replay {
		display: grid;
		gap: var(--sp-2);
		padding-top: var(--sp-3);
		border-top: 1px solid var(--line);
	}
	.row {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 6.5rem;
		align-items: center;
		gap: var(--sp-3);
	}
	.row :global(.sw) {
		gap: var(--sp-2);
		justify-content: flex-end;
	}
	.row :global(.sw svg) {
		width: 1.25rem;
		height: 1.25rem;
	}
	.row :global(.sw .v) {
		font-size: var(--fs-md);
		min-width: 0;
	}
	.lanebar {
		position: relative;
		height: 0.5rem;
		border-radius: var(--r-pill);
		background: var(--bg-3);
	}
	.fill {
		position: absolute;
		inset: 0;
		width: calc(var(--fc) * 100%);
		border-radius: inherit;
		transform-origin: 0 50%;
		background: linear-gradient(90deg, #2a3038, var(--before));
	}
	.hot .fill {
		width: calc(var(--fh) * 100%);
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 14px rgb(255 122 26 / 0.55);
	}
	.stamp {
		position: absolute;
		left: calc(var(--fh) * 100% + 0.4rem);
		padding: 0 0.4rem;
		background: var(--bg-1);
		top: 50%;
		translate: 0 -50%;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--heat-4);
		white-space: nowrap;
	}
	.gap {
		justify-self: start;
		margin-top: var(--sp-1);
		padding: 0.3rem 0.7rem;
		border: 1px solid var(--heat-3);
		border-radius: var(--r-pill);
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--heat-5);
		box-shadow: 0 0 20px -6px rgb(255 122 26 / 0.7);
	}
	@media (prefers-reduced-motion: no-preference) {
		/* both bars grow at real-time pace on the same axis; the hot one stops first */
		.go .fill {
			animation: grow var(--c) linear both;
		}
		.go.replay .hot .fill {
			animation-duration: var(--h);
		}
		.go .stamp,
		.go .gap {
			animation: pop 0.4s var(--ease-spring) var(--h) both;
		}
	}
	@keyframes grow {
		from {
			transform: scaleX(0);
		}
	}
	@keyframes pop {
		from {
			transform: translate3d(0, 0.3rem, 0) scale(0);
		}
	}
</style>
