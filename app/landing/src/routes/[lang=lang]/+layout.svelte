<script lang="ts">
	import { page } from '$app/state';
	import { LANGS, localizePath } from '$lib/i18n';

	let { children } = $props();
</script>

<svelte:head>
	{#each LANGS as l (l)}
		<link rel="alternate" hreflang={l} href="{page.url.origin}{localizePath(page.url.pathname, l)}" />
	{/each}
	<link rel="alternate" hreflang="x-default" href="{page.url.origin}{localizePath(page.url.pathname, 'pl')}" />
	<link rel="canonical" href="{page.url.origin}{page.url.pathname}" />
</svelte:head>

{@render children()}
