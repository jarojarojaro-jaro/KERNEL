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
		margin-block-end: var(--sp-8);
	}
	.back a {
		color: var(--text-mute);
		text-decoration: none;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		font-stretch: 87.5%;
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}
	.back a:hover {
		color: var(--text-hi);
	}
	/* Shared typography of the legal documents (src/lib/legal/{pl,en}/*.svelte). */
	.section :global(.legal > h1.h1) {
		font-size: clamp(2.4rem, 1.4rem + 3.6vw, 4rem);
		margin-top: var(--sp-4);
	}
	.section :global(.legal h2.h2) {
		font-size: var(--fs-xl);
		font-weight: 680;
		margin-top: var(--sp-12);
		padding-top: var(--sp-6);
		border-top: 1px solid var(--line);
	}
	.section :global(.legal h3) {
		font-size: var(--fs-md);
	}
	.section :global(.legal .toc) {
		padding: var(--sp-6);
		border-radius: var(--r-xl);
	}
	.section :global(.legal .toc h2) {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		font-weight: 500;
		font-stretch: 87.5%;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
		margin: 0 0 var(--sp-3);
	}
	.section :global(.legal .toc ol) {
		list-style: none;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
		gap: 0 var(--sp-6);
	}
	.section :global(.legal .toc li) {
		margin: 0;
		border-bottom: 1px solid var(--line);
	}
	.section :global(.legal .toc a) {
		display: block;
		padding: var(--sp-2) 0;
		color: var(--text);
		text-decoration: none;
		font-size: var(--fs-sm);
	}
	.section :global(.legal .toc a:hover) {
		color: var(--text-hi);
	}
</style>
