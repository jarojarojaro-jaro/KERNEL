<script lang="ts">
	import { page } from '$app/state';
	import { LANGS } from '$lib/i18n';

	let { children } = $props();
	const rest = $derived(page.url.pathname.split('/').slice(2).join('/'));
</script>

<svelte:head>
	{#each LANGS as l (l)}
		<link rel="alternate" hreflang={l} href="{page.url.origin}/{l}/{rest}" />
	{/each}
	<link rel="alternate" hreflang="x-default" href="{page.url.origin}/pl/{rest}" />
	<link rel="canonical" href="{page.url.origin}{page.url.pathname}" />
</svelte:head>

{@render children()}
