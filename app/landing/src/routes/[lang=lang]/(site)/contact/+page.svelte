<script lang="ts">
	import { cardsHref, currentLang, href } from '$lib/i18n';
	import { BRAND } from '$lib/brand';
	import CompanyData from '$lib/legal/CompanyData.svelte';

	const lang = $derived(currentLang());
	const T = {
		pl: {
			title: 'Kontakt',
			lead: 'Pytanie o Twoją kartę, wynik pomiaru albo współpracę? Napisz do nas.',
			company: 'Dane firmy',
			methodology: 'Jak mierzymy',
			cards: 'Sprawdź swoją kartę'
		},
		en: {
			title: 'Contact',
			lead: 'A question about your card, a measurement or working together? Write to us.',
			company: 'Company details',
			methodology: 'How we measure',
			cards: 'Check your card'
		}
	} as const;
	const t = $derived(T[lang]);
</script>

<svelte:head><title>{t.title} · {BRAND.name}</title><meta name="description" content={t.lead} /></svelte:head>

<section class="section heat-scope">
	<div class="container container--narrow">
		<header class="head">
			<h1 class="giga">{t.title}</h1>
			<p class="lede">{t.lead}</p>
		</header>
		<div class="panel">
			<h2 class="h3">{t.company}</h2>
			<CompanyData {lang} fields={['email', 'legalName', 'address']} />
		</div>
		<p class="links">
			<a class="btn btn--secondary" href={href(lang, '/methodology')}>{t.methodology}</a>
			<a class="btn btn--primary" href={cardsHref(lang)}>{t.cards} <span class="arrow" aria-hidden="true">→</span></a>
		</p>
	</div>
</section>

<style>
	.head {
		display: grid;
		gap: var(--sp-4);
		margin-bottom: var(--sp-8);
	}
	.panel {
		display: grid;
		gap: var(--sp-4);
		padding: var(--sp-6);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background: var(--bg-1);
	}
	.links {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-3);
		margin-top: var(--sp-8);
	}
</style>
