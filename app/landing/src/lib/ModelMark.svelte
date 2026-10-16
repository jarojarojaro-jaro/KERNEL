<script lang="ts">
	/** The model's identity mark: its categorical colour + its shape (colour-blind safe). Decorative. */
	import type { ModelKey } from '$lib/data/measurements';
	import { MODEL_STYLE } from '$lib/modelStyle';

	let { model, size = '0.8em' }: { model: ModelKey; size?: string } = $props();
	const s = $derived(MODEL_STYLE[model]);
</script>

<svg class="mark" viewBox="0 0 10 10" width={size} height={size} style="color:{s.color}" aria-hidden="true">
	{#if s.shape === 'circle'}<circle cx="5" cy="5" r="4.2" fill="currentColor" />
	{:else if s.shape === 'triangle'}<path d="M5 .8 9.4 9H.6Z" fill="currentColor" />
	{:else if s.shape === 'square'}<rect x="1" y="1" width="8" height="8" rx=".6" fill="currentColor" />
	{:else if s.shape === 'diamond'}<path d="M5 .4 9.6 5 5 9.6.4 5Z" fill="currentColor" />
	{:else}<path d="M5 .5 9 2.75v4.5L5 9.5 1 7.25v-4.5Z" fill="currentColor" />{/if}
</svg>

<style>
	.mark {
		display: inline-block;
		flex: none;
		vertical-align: -0.05em;
	}
</style>
