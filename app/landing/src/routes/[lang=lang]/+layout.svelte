<script lang="ts">
	import { page } from '$app/state';
	import { LANGS, localizePath } from '$lib/i18n';
	import { SITE_ORIGIN } from '$lib/site/public';

	let { children } = $props();
</script>

<svelte:head>
	{#each LANGS as l (l)}
		<link rel="alternate" hreflang={l} href="{SITE_ORIGIN}{localizePath(page.url.pathname, l)}" />
	{/each}
	<link rel="alternate" hreflang="x-default" href="{SITE_ORIGIN}{localizePath(page.url.pathname, 'pl')}" />
	<link rel="canonical" href="{SITE_ORIGIN}{page.url.pathname}" />
	{#if SITE_ORIGIN}<meta property="og:url" content="{SITE_ORIGIN}{page.url.pathname}" />{/if}
</svelte:head>

{@render children()}
