<script lang="ts">
	import { currentLang, href } from '$lib/i18n';
	import { BRAND } from '$lib/brand';
	import { findLegalDoc } from '$lib/legal/docs';

	let { data } = $props();
	const lang = $derived(currentLang());
	const doc = $derived(findLegalDoc(data.slug)!);
	const Doc = $derived(doc.component[lang]);
</script>

<svelte:head>
	<title>{doc.title[lang]} · {BRAND.name}</title>
	<meta name="description" content={doc.description[lang]} />
</svelte:head>

<section class="section">
	<div class="container container--narrow">
		<nav class="small back" aria-label={lang === 'pl' ? 'Nawigacja' : 'Breadcrumb'}>
			<a href={href(lang, '/legal')}>{lang === 'pl' ? '← Dokumenty prawne' : '← Legal documents'}</a>
		</nav>
		<Doc {lang} />
	</div>
</section>

<style>
	.back {
		margin-block-end: var(--sp-6);
	}
</style>
