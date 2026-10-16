<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		overline,
		title,
		lead,
		actions
	}: { overline?: string; title: string; lead?: string; actions?: Snippet } = $props();
</script>

<header class="head">
	<div class="text">
		{#if overline}<p class="overline">{overline}</p>{/if}
		<h1 class="h2">{title}</h1>
		{#if lead}<p class="lead">{lead}</p>{/if}
	</div>
	{#if actions}<div class="actions">{@render actions()}</div>{/if}
</header>

<style>
	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--sp-4) var(--sp-8);
		padding-bottom: var(--sp-6);
		margin-bottom: var(--sp-6);
		border-bottom: 1px solid transparent;
		border-image: linear-gradient(90deg, var(--heat-2), var(--heat-3) 20%, var(--heat-4) 35%, var(--line) 60%) 1;
	}
	.text {
		display: grid;
		gap: var(--sp-2);
		max-width: 46rem;
	}
	.lead {
		font-size: var(--fs-base);
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
	}
</style>
