<script lang="ts">
	/**
	 * Memory plan as one stacked bar against the budget: weights, KV cache, compute buffers, headroom,
	 * free. Neutral tones only (heat is reserved for speed); every segment is also a labelled row.
	 */
	import type { MemPlan } from '../../shared/types';
	import { num } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	let { mem, title }: { mem: MemPlan; title: string } = $props();
	const t = $derived(store.t.rec);
	const lang = $derived(store.lang);
	const scale = $derived(Math.max(mem.budgetGiB, mem.totalGiB, 0.001));
	const segs = $derived([
		{ key: 'w', label: t.weights, v: mem.weightsGiB },
		{ key: 'kv', label: t.kv, v: mem.kvGiB },
		{ key: 'c', label: t.compute, v: mem.computeGiB },
		{ key: 'o', label: t.overhead, v: mem.overheadGiB }
	]);
</script>

<figure class="mem">
	<figcaption>
		<span class="ttl">{title}</span>
		<span class="tot num">{t.memOf(num(mem.totalGiB, lang, 1), num(mem.budgetGiB, lang, 1))}</span>
	</figcaption>
	<div class="track" aria-hidden="true">
		{#each segs as s (s.key)}
			{#if s.v > 0}<i class="seg {s.key}" style="width:{(s.v / scale) * 100}%"></i>{/if}
		{/each}
		{#if mem.freeGiB > 0}<i class="seg free" style="width:{(mem.freeGiB / scale) * 100}%"></i>{/if}
	</div>
	<ul class="legend">
		{#each segs as s (s.key)}
			<li><i class="sw {s.key}" aria-hidden="true"></i><span>{s.label}</span><span class="num v">{num(s.v, lang, 1)} GB</span></li>
		{/each}
		{#if mem.freeGiB >= 0}
			<li><i class="sw free" aria-hidden="true"></i><span>{t.free}</span><span class="num v">{num(mem.freeGiB, lang, 1)} GB</span></li>
		{:else}
			<li class="over"><i class="sw over" aria-hidden="true"></i><span>{t.over}</span><span class="num v">{num(-mem.freeGiB, lang, 1)} GB</span></li>
		{/if}
	</ul>
</figure>

<style>
	.mem {
		margin: 0;
		display: grid;
		gap: var(--sp-3);
	}
	figcaption {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--sp-3);
		flex-wrap: wrap;
	}
	.ttl {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.tot {
		font-size: var(--fs-sm);
		color: var(--text-hi);
	}
	.track {
		display: flex;
		height: 1.1rem;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		overflow: hidden;
		gap: 2px;
	}
	.seg {
		display: block;
		height: 100%;
		min-width: 2px;
		transition: width var(--dur-4) var(--ease-out);
	}
	.w {
		background: var(--text-hi);
	}
	.kv {
		background: var(--info);
	}
	.c {
		background: var(--before);
	}
	.o {
		background: var(--line-strong);
	}
	.free {
		background: repeating-linear-gradient(-45deg, color-mix(in srgb, var(--text-mute) 35%, transparent) 0 3px, transparent 3px 7px);
	}
	.legend {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
		gap: 0.35rem var(--sp-5);
		margin: 0;
		padding: 0;
		list-style: none;
		font-size: var(--fs-xs);
		color: var(--text);
	}
	.legend li {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.sw {
		flex: none;
		width: 0.7rem;
		height: 0.7rem;
		border-radius: 3px;
	}
	.sw.free {
		border: 1px solid var(--text-mute);
	}
	.sw.over {
		background: var(--danger-ink);
	}
	.v {
		margin-left: auto;
		color: var(--text-hi);
	}
	.over {
		color: var(--danger-ink);
	}
</style>
