<script lang="ts">
	/** The four benchmark stages with the one currently running (from the latest progress label). */
	import type { Phase } from '../../shared/types';
	import { BENCH_STEPS } from '../lib/bench';
	import { store } from '../lib/store.svelte';

	let { phase, finished = false }: { phase: Phase; finished?: boolean } = $props();
	const t = $derived(store.t.base);
	const p = $derived(store.state?.progress ?? null);
	const cur = $derived(p && p.phase === phase ? BENCH_STEPS.indexOf(p.label as (typeof BENCH_STEPS)[number]) : -1);
</script>

<ol class="steps-b">
	{#each BENCH_STEPS as s, i (s)}
		{@const st = finished || (cur >= 0 && i < cur) ? 'done' : i === cur ? 'run' : 'wait'}
		<li class={st} aria-current={st === 'run' ? 'step' : undefined}>
			<span class="m" aria-hidden="true">{#if st === 'done'}✓{:else if st === 'run'}<span class="ring"></span>{:else}{i + 1}{/if}</span>
			<span class="l">{t.phases[s]}</span>
			{#if st === 'run' && p && p.total > 1}<span class="n num">{p.done}/{p.total}</span>{/if}
		</li>
	{/each}
</ol>

<style>
	.steps-b {
		display: grid;
		gap: var(--sp-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}
	li {
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		padding: 0.55rem 0;
		color: var(--text-mute);
		font-size: var(--fs-sm);
	}
	.m {
		display: grid;
		place-items: center;
		flex: none;
		width: 1.6rem;
		height: 1.6rem;
		border-radius: 50%;
		border: 1px solid var(--line-strong);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
	}
	.m .ring {
		width: 0.75rem;
		height: 0.75rem;
	}
	.done {
		color: var(--text);
	}
	.done .m {
		background: var(--text-hi);
		border-color: var(--text-hi);
		color: var(--text-inv);
	}
	.run {
		color: var(--text-hi);
		font-weight: 600;
	}
	.run .m {
		border-color: var(--text-hi);
	}
	.n {
		margin-left: auto;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
</style>
