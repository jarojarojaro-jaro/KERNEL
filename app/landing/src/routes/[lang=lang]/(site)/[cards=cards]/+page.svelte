<script lang="ts">
	import { cardsCopy } from '$lib/cards/copy';
	import VendorHub from '$lib/cards/VendorHub.svelte';
	import { cardsHref, currentLang } from '$lib/i18n';
	import { BRAND } from '$lib/brand';
	import Seo from '$lib/site/Seo.svelte';
	import { breadcrumbs, CARD_CRUMBS } from '$lib/site/jsonld';

	const lang = $derived(currentLang());
	const m = $derived(cardsCopy[lang].meta);
	const ld = $derived(
		breadcrumbs([
			{ name: BRAND.name, path: `/${lang}/` },
			{ name: CARD_CRUMBS[lang].root, path: cardsHref(lang) }
		])
	);
</script>

<svelte:head>
	<title>{m.title}</title>
	<meta name="description" content={m.description} />
</svelte:head>

<Seo title={m.title} description={m.description} jsonld={ld ?? undefined} />

<VendorHub />
