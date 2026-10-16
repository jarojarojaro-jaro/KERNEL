<script lang="ts">
	import { cardsCopy } from '$lib/cards/copy';
	import Gallery from '$lib/cards/Gallery.svelte';
	import { currentLang } from '$lib/i18n';

	const lang = $derived(currentLang());
	const m = $derived(cardsCopy[lang].meta);
</script>

<svelte:head>
	<title>{m.title}</title>
	<meta name="description" content={m.description} />
	<meta property="og:title" content={m.title} />
	<meta property="og:description" content={m.description} />
</svelte:head>

<Gallery />
