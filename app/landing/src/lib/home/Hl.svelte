<script lang="ts">
	/**
	 * Heading text with accents: words wrapped in *…* in the copy render in the shared `.hx-accent` ember
	 * (design/components.css). Plain text otherwise; never parses HTML.
	 */
	let { text }: { text: string } = $props();
	const parts = $derived(text.split(/\*([^*]+)\*/));
</script>

{#each parts as p, i (i)}{#if i % 2}<span class="hx-accent">{p}</span>{:else}{p}{/if}{/each}
