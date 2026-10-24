<script lang="ts">
	/**
	 * Screen heading: mono overline, the title with its ember words, the lead. The h1 receives focus on a
	 * screen change (tabindex -1, never in the tab order), so it shows no focus ring.
	 */
	let { id, overline, title, accent, lead }: { id: string; overline: string; title: string; accent: string; lead?: string } = $props();
</script>

<header class="screen-head">
	<p class="eyebrow">{overline}</p>
	<h1 {id} class="title" tabindex="-1" data-screen-title>{title} <span class="hx-accent">{accent}</span></h1>
	{#if lead}<p class="lede">{lead}</p>{/if}
</header>

<style>
	h1:focus {
		outline: none;
	}
</style>
