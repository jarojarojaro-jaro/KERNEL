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
	<h1 class="h1">Polityka cookies</h1>
	<p class="source">{LEGAL_VERSION[L]}</p>
	<nav aria-labelledby="toc-title" class="card card--inset toc">
		<h2 id="toc-title" class="h3">Spis treści</h2>
		<ol>
			<li><a href="#krotko">1. W skrócie</a></li>
			<li><a href="#podstawa">2. Podstawa prawna</a></li>
			<li><a href="#lista">3. Co zapisujemy</a></li>
			<li><a href="#analityka">4. Kategoria „analityka”</a></li>
			<li><a href="#zmiana">5. Jak zmienić decyzję</a></li>
		</ol>
	</nav>
	<h2 id="krotko" class="h2">1. W skrócie</h2>
	<p>Strona {BRAND.name} nie ustawia śledzących plików cookies ani nie używa narzędzi analitycznych czy reklamowych. W pamięci Twojej przeglądarki zapisujemy wyłącznie kilka technicznych informacji, wymienionych poniżej, które są niezbędne albo o które sam(a) prosisz.</p>
	<h2 id="podstawa" class="h2">2. Podstawa prawna</h2>
	<p>Przechowywanie informacji i uzyskiwanie do nich dostępu w urządzeniu końcowym wymaga zgody, chyba że jest niezbędne do świadczenia usługi, której wyraźnie żądasz (art. 399 ustawy Prawo komunikacji elektronicznej, art. 5 ust. 3 dyrektywy 2002/58/WE). Wszystkie wpisy wymienione w punkcie 3 korzystają z tego wyjątku. Zasada ta obejmuje także localStorage i sessionStorage, nie tylko pliki cookies.</p>
	<h2 id="lista" class="h2">3. Co zapisujemy</h2>
	<div class="table-wrap">
		<table class="table">
			<caption class="sr-only">Lista zapisywanych danych</caption>
			<thead><tr><th scope="col">Nazwa i miejsce</th><th scope="col">Cel</th><th scope="col">Okres</th><th scope="col">Podstawa</th></tr></thead>
			<tbody>
				<tr><td><code>theme</code> — localStorage</td><td>zapamiętanie motywu jasnego lub ciemnego; zapisywany dopiero po kliknięciu przełącznika motywu</td><td>do usunięcia danych strony w przeglądarce lub ponownej zmiany</td><td>żądanie użytkownika — niezbędne</td></tr>
				<tr><td><code>consent</code> — localStorage</td><td>zapis Twojej decyzji z banera zgody (wersja, kategoria analityczna tak/nie, data)</td><td>do usunięcia danych strony lub zmiany wersji banera</td><td>niezbędne do respektowania Twojego wyboru</td></tr>
				<tr><td>stan prototypu onboardingu — sessionStorage</td><td>zachowanie kroków prototypu aplikacji przy przechodzeniu między ekranami</td><td>do zamknięcia karty przeglądarki</td><td>żądanie użytkownika — niezbędne</td></tr>
			</tbody>
		</table>
	</div>
	<p>Żaden z tych wpisów nie jest przesyłany na nasz serwer ani do podmiotów trzecich.</p>
	<h2 id="analityka" class="h2">4. Kategoria „analityka”</h2>
	<p>Baner zgody zawiera kategorię „analityka”, abyśmy w przyszłości mogli zapytać o zgodę we właściwy sposób. <strong>Obecnie nie jest zainstalowane żadne narzędzie analityczne</strong>: ani przed, ani po wyrażeniu zgody nic się nie ładuje. Jeśli wybierzemy takie narzędzie, najpierw wymienimy je w tej polityce (dostawca, zapisywane dane, okres, ewentualny transfer poza EOG) i ponownie zapytamy o zgodę.</p>
	<h2 id="zmiana" class="h2">5. Jak zmienić decyzję</h2>
	<p>W stopce każdej strony znajduje się odnośnik „Ustawienia cookies”. Kliknięcie go ponownie otwiera baner zgody, w którym możesz zmienić lub wycofać decyzję; odrzucenie jest równie łatwe jak akceptacja. Możesz też w każdej chwili usunąć dane strony w ustawieniach przeglądarki — wtedy baner pojawi się ponownie.</p>
	<p>Więcej o przetwarzaniu danych: <a href={href(L, '/legal/privacy')}>Polityka prywatności</a>.</p>
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
