<script lang="ts">
	import CursorGlow from '$lib/fx/CursorGlow.svelte';
	import ResultsLab from '$lib/home/ResultsLab.svelte';
	import { BRAND } from '$lib/brand';
	import { currentLang, resultsHref } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import Seo from '$lib/site/Seo.svelte';
	import { breadcrumbs } from '$lib/site/jsonld';

	const lang = $derived(currentLang());
	const m = $derived(copy[lang].results.meta);
	const ld = $derived(
		breadcrumbs([
			{ name: BRAND.name, path: `/${lang}/` },
			{ name: copy[lang].nav.results, path: resultsHref(lang) }
		])
	);
</script>

<svelte:head>
	<title>{m.title}</title>
	<meta name="description" content={m.description} />
</svelte:head>

<Seo title={m.title} description={m.description} jsonld={ld ?? undefined} />

<div class="grain" aria-hidden="true"></div>
<div class="nav-fade" aria-hidden="true"></div>
<CursorGlow />

<div class="page">
	<ResultsLab {lang} />
</div>

<style>
	.page {
		padding-top: clamp(4.5rem, 3rem + 3vw, 6rem);
	}
</style>
