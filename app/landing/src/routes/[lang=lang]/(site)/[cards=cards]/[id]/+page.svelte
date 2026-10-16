<script lang="ts">
	import CardPage from '$lib/cards/CardPage.svelte';
	import { cardsCopy } from '$lib/cards/copy';
	import { findEntry } from '$lib/cards/explorer';
	import QueuePage from '$lib/cards/QueuePage.svelte';
	import { currentLang } from '$lib/i18n';

	let { data } = $props();

	const lang = $derived(currentLang());
	const m = $derived(cardsCopy[lang].meta);
	const entry = $derived(findEntry(data.id)!);
	const name = $derived(entry.kind === 'measured' ? entry.card.name : entry.gpu.name);
	const title = $derived(entry.kind === 'measured' ? m.cardTitle(name) : m.queueTitle(name));
</script>

<svelte:head>
	<title>{title}</title>
	<meta name="description" content={m.cardDescription(name)} />
	<meta property="og:title" content={title} />
	<meta property="og:description" content={m.cardDescription(name)} />
</svelte:head>

{#key entry.id}
	{#if entry.kind === 'measured'}
		<CardPage card={entry.card} />
	{:else}
		<QueuePage gpu={entry.gpu} />
	{/if}
{/key}
