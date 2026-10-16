<script lang="ts">
	import { onMount } from 'svelte';
	import { BRAND } from '$lib/brand';

	onMount(() => {
		const en = !(navigator.languages ?? [navigator.language]).some((l) => l.toLowerCase().startsWith('pl'));
		location.replace(en ? '/en/' : '/pl/');
	});
</script>

<svelte:head>
	<title>{BRAND.name}</title>
	<meta http-equiv="refresh" content="2; url=/pl/" />
</svelte:head>

<main class="container--narrow section stack">
	<h1 class="h2">{BRAND.name}</h1>
	<p><a href="/pl/" hreflang="pl" lang="pl">Polski</a> · <a href="/en/" hreflang="en" lang="en">English</a></p>
</main>
