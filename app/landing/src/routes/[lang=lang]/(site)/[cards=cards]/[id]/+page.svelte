<script lang="ts">
	import CardPage from '$lib/cards/CardPage.svelte';
	import { cardsCopy } from '$lib/cards/copy';
	import { findEntry } from '$lib/cards/explorer';
	import QueuePage from '$lib/cards/QueuePage.svelte';
	import { BRAND } from '$lib/brand';
	import { cardsHref, currentLang } from '$lib/i18n';
	import Seo from '$lib/site/Seo.svelte';
	import { breadcrumbs, CARD_CRUMBS } from '$lib/site/jsonld';

	let { data } = $props();

	const lang = $derived(currentLang());
	const m = $derived(cardsCopy[lang].meta);
	const entry = $derived(findEntry(data.id)!);
	const name = $derived(entry.kind === 'measured' ? entry.card.name : entry.gpu.name);
	const title = $derived(entry.kind === 'measured' ? m.cardTitle(name) : m.queueTitle(name));
	const desc = $derived(m.cardDescription(name));
	const ld = $derived(
		breadcrumbs([
			{ name: BRAND.name, path: `/${lang}/` },
			{ name: CARD_CRUMBS[lang].root, path: cardsHref(lang) },
			{ name, path: `${cardsHref(lang)}${data.id}/` }
		])
	);
</script>

<svelte:head>
	<title>{title}</title>
	<meta name="description" content={m.cardDescription(name)} />
</svelte:head>

<Seo title={title} description={desc} jsonld={ld ?? undefined} />

{#key entry.id}
	{#if entry.kind === 'measured'}
		<CardPage card={entry.card} />
	{:else}
		<QueuePage gpu={entry.gpu} />
	{/if}
{/key}
