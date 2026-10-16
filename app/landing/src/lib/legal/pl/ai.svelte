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
	<h1 class="h1">Informacja o sztucznej inteligencji</h1>
	<p class="source">{LEGAL_VERSION[L]}</p>
	<nav aria-labelledby="toc-title" class="card card--inset toc">
		<h2 id="toc-title" class="h3">Spis treści</h2>
		<ol>
			<li><a href="#system">1. Korzystasz z systemu AI</a></li>
			<li><a href="#bledy">2. Odpowiedzi mogą być błędne</a></li>
			<li><a href="#lokalnie">3. Modele działają lokalnie</a></li>
			<li><a href="#ujawnienie">4. Jak informujemy w interfejsie</a></li>
			<li><a href="#oznaczanie">5. Oznaczanie treści syntetycznych</a></li>
			<li><a href="#obrazy">6. Brak generowania obrazów i wideo</a></li>
			<li><a href="#rola">7. Nasza rola w świetle AI Act</a></li>
			<li><a href="#zglaszanie">8. Zgłaszanie problemów</a></li>
		</ol>
	</nav>
	<h2 id="system" class="h2">1. Korzystasz z systemu AI</h2>
	<p>{BRAND.name} uruchamia na Twoim komputerze modele językowe. Rozmawiając w Aplikacji, wchodzisz w interakcję z systemem sztucznej inteligencji, a nie z człowiekiem. Informujemy o tym zgodnie z art. 50 ust. 1 rozporządzenia (UE) 2024/1689 (AI Act).</p>
	<h2 id="bledy" class="h2">2. Odpowiedzi mogą być błędne</h2>
	<p>Modele językowe generują tekst statystycznie. Mogą podawać nieprawdziwe fakty, zmyślone źródła lub nieaktualne informacje. Sprawdzaj istotne odpowiedzi; nie traktuj ich jako porady prawnej, medycznej ani finansowej.</p>
	<h2 id="lokalnie" class="h2">3. Modele działają lokalnie</h2>
	<p>Model działa na Twoim urządzeniu. Treść rozmów nie jest wysyłana do nas ani do twórcy Modelu. Przyspieszenie, które oferujemy, dotyczy sposobu wykonania Modelu na Twoim sprzęcie; nie zmieniamy wag Modelu w celu zmiany jego zachowania.</p>
	<h2 id="ujawnienie" class="h2">4. Jak informujemy w interfejsie</h2>
	<p>Przy pierwszej interakcji w oknie rozmowy Aplikacja wyświetla jasny komunikat, że rozmawiasz z systemem AI. Zgodnie z art. 50 ust. 5 AI Act komunikat jest wyraźny, rozpoznawalny i dostępny: jest odczytywany przez czytniki ekranu, nie znika automatycznie i spełnia wymagania kontrastu WCAG 2.2 AA.</p>
	<h2 id="oznaczanie" class="h2">5. Oznaczanie treści syntetycznych</h2>
	<p>Art. 50 ust. 2 AI Act wymaga, aby dostawcy systemów AI generujących tekst zapewniali oznaczenie wyników w formacie nadającym się do odczytu maszynowego. Planujemy oznaczać znakiem wodnym teksty dłuższe niż 200 tokenów. Znak wodny będzie stosowany identycznie w trybie „przed” i „po” przyspieszeniu, tak aby oba tryby dawały porównywalne wyniki, a przyspieszenie pozostało weryfikowalne.</p>
	<p><strong>Stan:</strong> zakres tego obowiązku dla modeli uruchamianych lokalnie oraz wybór metody są przedmiotem oczekiwanej opinii prawnej oraz zapytania do Komisji Rozwoju i Bezpieczeństwa Sztucznej Inteligencji (KRiBSI). Rozwiązanie nie jest jeszcze wdrożone. Opiszemy je tutaj przed udostępnieniem Aplikacji.</p>
	<h2 id="obrazy" class="h2">6. Brak generowania obrazów i wideo</h2>
	<p>{BRAND.name} nie generuje obrazów, dźwięku ani wideo, w tym treści typu deepfake. Obowiązki z art. 50 ust. 4 AI Act w tym zakresie nas nie dotyczą.</p>
	<h2 id="rola" class="h2">7. Nasza rola w świetle AI Act</h2>
	<p>Nie jesteśmy dostawcą modelu AI ogólnego przeznaczenia (GPAI). Modele pochodzą od ich twórców. Nasze zmiany dotyczą wykonania modelu, a moc obliczeniowa ewentualnych modyfikacji jest wielokrotnie niższa od progu jednej trzeciej mocy obliczeniowej użytej do trenowania modelu pierwotnego, wskazanego w wytycznych Komisji Europejskiej jako wskaźnik stania się dostawcą GPAI. Jesteśmy natomiast dostawcą systemu AI (Aplikacji) i wykonujemy obowiązki przejrzystości z art. 50.</p>
	<p>W Polsce nadzór nad stosowaniem AI Act sprawuje Komisja Rozwoju i Bezpieczeństwa Sztucznej Inteligencji (KRiBSI), powołana ustawą o systemach sztucznej inteligencji.</p>
	<h2 id="zglaszanie" class="h2">8. Zgłaszanie problemów</h2>
	<p>Jeśli Model wygenerował szkodliwą lub bezprawną treść albo komunikat o AI nie był widoczny, napisz do nas na adres poniżej. Zgłoszenia dotyczące samego Modelu przekażemy jego twórcy, jeśli się na to zgodzisz.</p>
	<CompanyData lang={L} fields={['email']} />
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
