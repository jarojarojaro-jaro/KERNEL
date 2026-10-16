<script lang="ts">
	import { currentLang, href } from '$lib/i18n';
	import { BRAND } from '$lib/brand';
	import { LEGAL_DOCS, LEGAL_VERSION } from '$lib/legal/docs';
	import DraftBanner from '$lib/legal/DraftBanner.svelte';

	const lang = $derived(currentLang());
	const T = {
		pl: { title: 'Dokumenty prawne', lead: 'Regulamin, prywatność, cookies, informacja o AI i dane firmy.', open: 'Czytaj' },
		en: { title: 'Legal documents', lead: 'Terms, privacy, cookies, AI notice and company details.', open: 'Read' }
	} as const;
	const t = $derived(T[lang]);
</script>

<svelte:head><title>{t.title} · {BRAND.name}</title><meta name="description" content={t.lead} /></svelte:head>

<section class="section">
	<div class="container container--narrow stack">
		<p class="overline">{LEGAL_VERSION[lang]}</p>
		<h1 class="h1">{t.title}</h1>
		<p class="lead">{BRAND.name}: {t.lead}</p>
		<DraftBanner {lang} />
		<ul class="docs stack" role="list">
			{#each LEGAL_DOCS as d (d.slug)}
				<li class="card">
					<h2 class="h3"><a href={href(lang, `/legal/${d.slug}`)}>{d.title[lang]}</a></h2>
					<p class="mute">{d.description[lang]}</p>
					<p class="source">{d.version[lang]}</p>
				</li>
			{/each}
		</ul>
	</div>
</section>

<style>
	.docs {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.docs h2 {
		margin: 0 0 var(--sp-2);
	}
	.docs p {
		margin: 0 0 var(--sp-2);
	}
</style>
