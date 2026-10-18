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

<section class="section heat-scope">
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
		position: relative;
		font-size: var(--fs-xl);
		font-weight: 680;
		margin-top: var(--sp-12);
		padding-top: var(--sp-6);
		border-top: 1px solid transparent;
		border-image: linear-gradient(90deg, var(--heat-2), var(--heat-3) 15%, var(--line) 45%) 1;
	}
	.section :global(.legal h2.h2::before) {
		content: '';
		position: absolute;
		top: -2px;
		left: 0;
		width: 2.5rem;
		height: 3px;
		border-radius: var(--r-pill);
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 14px color-mix(in srgb, var(--heat-3) 80%, transparent);
	}
	/* Title stays bone/ink; heat only as a short underline. */
	.section :global(.legal > h1.h1) {
		position: relative;
		padding-bottom: var(--sp-4);
	}
	.section :global(.legal > h1.h1::after) {
		content: '';
		position: absolute;
		left: 0;
		bottom: 0;
		width: 4rem;
		height: 3px;
		border-radius: var(--r-pill);
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 55%, var(--heat-4));
	}
	.section {
		position: relative;
		overflow-x: clip;
		isolation: isolate;
	}
	.section::before {
		content: '';
		position: absolute;
		inset: 0 0 auto;
		height: 32rem;
		z-index: -1;
		pointer-events: none;
		background: radial-gradient(40% 55% at 65% 0%, color-mix(in srgb, var(--heat-3) 14%, transparent), transparent 70%);
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
		color: var(--accent-ink);
	}
</style>
