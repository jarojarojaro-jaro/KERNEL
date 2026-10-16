<script lang="ts">
	import CursorGlow from '$lib/fx/CursorGlow.svelte';
	import ResultsLab from '$lib/home/ResultsLab.svelte';
	import { currentLang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';

	const lang = $derived(currentLang());
	const m = $derived(copy[lang].results.meta);
</script>

<svelte:head>
	<title>{m.title}</title>
	<meta name="description" content={m.description} />
	<meta property="og:title" content={m.title} />
	<meta property="og:description" content={m.description} />
</svelte:head>

<div class="grain" aria-hidden="true"></div>
<CursorGlow />

<div class="page">
	<ResultsLab {lang} />
</div>

<style>
	.page {
		padding-top: clamp(4.5rem, 3rem + 3vw, 6rem);
	}
</style>
