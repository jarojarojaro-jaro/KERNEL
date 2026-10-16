<script lang="ts">
	import { BRAND } from '$lib/brand';
	import { href, type Lang } from '$lib/i18n';
	import DraftBanner from '../DraftBanner.svelte';
	import CompanyData from '../CompanyData.svelte';
	import { LEGAL_VERSION } from '../docs';

	/** The document is written in one language; `lang` is accepted for a uniform registry API. */
	let { lang: _lang }: { lang?: Lang } = $props();
	const L: Lang = 'pl';
</script>

<article class="prose legal">
	<DraftBanner lang={L} />
	<h1 class="h1">Dane firmy</h1>
	<p class="source">{LEGAL_VERSION[L]}</p>
	<nav aria-labelledby="toc-title" class="card card--inset toc">
		<h2 id="toc-title" class="h3">Spis treści</h2>
		<ol>
			<li><a href="#uslugodawca">1. Usługodawca</a></li>
			<li><a href="#bezpieczenstwo">2. Zgłoszenia bezpieczeństwa</a></li>
			<li><a href="#dokumenty">3. Pozostałe dokumenty</a></li>
		</ol>
	</nav>
	<h2 id="uslugodawca" class="h2">1. Usługodawca</h2>
	<p>{BRAND.name} jest projektem spółki z ograniczoną odpowiedzialnością w organizacji. Dane wymagane przez art. 5 ustawy o świadczeniu usług drogą elektroniczną oraz art. 206 Kodeksu spółek handlowych uzupełnimy niezwłocznie po wpisie spółki do Krajowego Rejestru Sądowego.</p>
	<CompanyData lang={L} />
	<h2 id="bezpieczenstwo" class="h2">2. Zgłoszenia bezpieczeństwa</h2>
	<p>Podatności zgłaszaj poufnie na adres poniżej. Planujemy opublikować plik <code>/.well-known/security.txt</code> (RFC 9116) oraz politykę skoordynowanego ujawniania podatności, zgodnie z wymaganiami rozporządzenia (UE) 2024/2847 (Cyber Resilience Act). Do czasu rejestracji spółki kanał nie jest jeszcze dostępny.</p>
	<CompanyData lang={L} fields={['security']} />
	<h2 id="dokumenty" class="h2">3. Pozostałe dokumenty</h2>
	<ul>
		<li><a href={href(L, '/legal/terms')}>Regulamin</a></li>
		<li><a href={href(L, '/legal/privacy')}>Polityka prywatności</a></li>
		<li><a href={href(L, '/legal/cookies')}>Polityka cookies</a></li>
		<li><a href={href(L, '/legal/ai')}>Informacja o AI</a></li>
	</ul>
</article>

<style>
	.toc {
		margin-block: var(--sp-6);
	}
	.toc h2 {
		margin-top: 0;
	}
	.legal :global(h2[id]) {
		scroll-margin-top: var(--sp-16);
	}
</style>
