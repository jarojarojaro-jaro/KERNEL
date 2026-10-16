<script lang="ts">
	/**
	 * `fill()` for running text whose placeholders include speed-up factors: the keys listed in
	 * `speed` render in the global `.speedup` face (`.speedup--down` below 1×), everything else is
	 * plain text. The whole sentence goes through `nb()` once, so non-breaking glue is unchanged.
	 */
	import { fill } from './data';

	let { text, vars, speed = {} }: { text: string; vars: Record<string, string | number>; speed?: Record<string, { text: string; v: number }> } = $props();

	const parts = $derived.by(() => {
		const marked: Record<string, string | number> = { ...vars };
		for (const k of Object.keys(speed)) marked[k] = `\u0001${k}\u0002`;
		return fill(text, marked)
			.split(/\u0001(\w+)\u0002/)
			.map((t, i) => (i % 2 ? { s: speed[t] } : { t }));
	});
</script>

{#each parts as part, i (i)}{#if part.s}<b class="speedup" class:speedup--down={part.s.v < 1}>{part.s.text}</b>{:else}{part.t}{/if}{/each}
