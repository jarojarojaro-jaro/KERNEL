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
	<h1 class="h1">Polityka prywatności</h1>
	<p class="source">{LEGAL_VERSION[L]}</p>
	<nav aria-labelledby="toc-title" class="card card--inset toc">
		<h2 id="toc-title" class="h3">Spis treści</h2>
		<ol>
			<li><a href="#administrator">1. Administrator danych</a></li>
			<li><a href="#zasada">2. Zasada: przetwarzamy jak najmniej</a></li>
			<li><a href="#strona">3. Strona internetowa</a></li>
			<li><a href="#lista">4. Lista oczekujących</a></li>
			<li><a href="#konto">5. Konto</a></li>
			<li><a href="#skan">6. Skan sprzętu</a></li>
			<li><a href="#aplikacja">7. Aplikacja desktopowa</a></li>
			<li><a href="#odbiorcy">8. Odbiorcy i podmioty przetwarzające</a></li>
			<li><a href="#transfer">9. Przekazywanie danych poza EOG</a></li>
			<li><a href="#okresy">10. Okresy przechowywania</a></li>
			<li><a href="#prawa">11. Twoje prawa</a></li>
			<li><a href="#automatyzacja">12. Zautomatyzowane podejmowanie decyzji</a></li>
			<li><a href="#zmiany">13. Zmiany polityki</a></li>
		</ol>
	</nav>
	<h2 id="administrator" class="h2">1. Administrator danych</h2>
	<p>Administratorem danych osobowych przetwarzanych w związku z {BRAND.name} będzie spółka, której dane wskażemy po rejestracji:</p>
	<CompanyData lang={L} fields={['legalName', 'address', 'krs', 'nip', 'email', 'dpo']} />
	<p>Ocenimy, czy wyznaczenie inspektora ochrony danych jest obowiązkowe (art. 37 RODO); przy obecnym zakresie przetwarzania prawdopodobnie nie jest.</p>
	<h2 id="zasada" class="h2">2. Zasada: przetwarzamy jak najmniej</h2>
	<p>Produkt jest projektowany tak, aby działać lokalnie. Modele, polecenia (prompty) i rozmowy pozostają na Twoim urządzeniu i nigdy do nas nie trafiają. Telemetria w Aplikacji jest domyślnie wyłączona. Strona nie używa narzędzi analitycznych ani śledzących.</p>
	<h2 id="strona" class="h2">3. Strona internetowa</h2>
	<p>Nie stosujemy analityki, pikseli reklamowych ani profilowania. Serwer hostingu zapisuje techniczne logi żądań, w tym adres IP. Adres IP może stanowić daną osobową (wyrok TSUE z 19 października 2016 r., C-582/14, Breyer), dlatego traktujemy logi jako dane osobowe. Szczegóły dotyczące pamięci przeglądarki: <a href={href(L, '/legal/cookies')}>Polityka cookies</a>.</p>
	<h2 id="lista" class="h2">4. Lista oczekujących</h2>
	<p>Jeśli zapiszesz się na listę oczekujących, przetwarzamy Twój adres e-mail oraz wybraną opcję cenową. Zapis wymaga potwierdzenia linkiem wysłanym e-mailem (double opt-in). Podstawą jest Twoja zgoda (art. 6 ust. 1 lit. a RODO), którą możesz wycofać w każdej chwili linkiem w każdej wiadomości lub e-mailem, bez wpływu na zgodność z prawem wcześniejszego przetwarzania.</p>
	<p><strong>Stan obecny:</strong> zaplecze formularza nie zostało uruchomione — formularz na stronie nie wysyła obecnie żadnych danych.</p>
	<h2 id="konto" class="h2">5. Konto</h2>
	<p>Przy zakładaniu Konta przetwarzamy adres e-mail, a przy logowaniu przez Google lub GitHub — identyfikator konta u tego dostawcy i adres e-mail. Żądamy wyłącznie minimalnych zakresów uprawnień (np. <code>openid email</code> w Google, <code>user:email</code> w GitHub). Nie pobieramy listy kontaktów, repozytoriów ani innych danych.</p>
	<h2 id="skan" class="h2">6. Skan sprzętu</h2>
	<p>Skan wykonuje się lokalnie i sam w sobie niczego nie wysyła. Wynikiem jest jednolinijkowy kod, który widzisz w całości. Jeśli wkleisz go do formularza na stronie, jest on przetwarzany wyłącznie w Twojej przeglądarce i nie trafia na nasz serwer.</p>
	<div class="table-wrap">
		<table class="table">
			<caption class="sr-only">Zakres skanu sprzętu</caption>
			<thead><tr><th scope="col">Odczytujemy lokalnie (potrzebne do doboru)</th><th scope="col">Nigdy nie odczytujemy</th></tr></thead>
			<tbody>
				<tr><td>system operacyjny i jego wersja; procesor (model, liczba wątków, AVX2/AVX-512); łączna pamięć RAM</td><td>nazwa komputera (hostname), nazwa użytkownika, ścieżki katalogów domowych</td></tr>
				<tr><td>GPU: producent, model, VRAM, sterownik (wersja), docelowa architektura, generacja i szerokość PCIe</td><td>numery seryjne, identyfikatory UUID GPU, adresy MAC, numery dysków</td></tr>
				<tr><td>dostępne backendy obliczeniowe (CUDA, ROCm, Vulkan, Metal) i ich wersje</td><td>parametry rozruchu jądra, dmesg, logi systemowe</td></tr>
				<tr><td>wolne miejsce na wybranym dysku</td><td>listy plików, zainstalowanych programów, historia</td></tr>
				<tr><td>zasilanie (sieć / bateria), temperatury — wyłącznie na żywo i lokalnie</td><td>lokalizacja, geolokalizacja IP, treść promptów i rozmów</td></tr>
			</tbody>
		</table>
	</div>
	<p>Odczyt informacji z Twojego urządzenia następuje wyłącznie w celu świadczenia usługi, o którą wprost prosisz (dobór Modelu), co mieści się w wyjątku z art. 399 ust. 2 ustawy Prawo komunikacji elektronicznej oraz art. 5 ust. 3 dyrektywy 2002/58/WE. Każde przesłanie danych do nas wymaga osobnej zgody.</p>
	<h2 id="aplikacja" class="h2">7. Aplikacja desktopowa</h2>
	<p>Telemetria jest domyślnie wyłączona. Telemetrię dzielimy na trzy niezależne kategorie; zgoda na każdą jest osobna i domyślnie wyłączona:</p>
	<ol>
		<li><strong>Raporty awarii</strong> — przed wysłaniem każdego raportu widzisz jego dokładną treść i możesz go odrzucić.</li>
		<li><strong>Udostępnij profil przyspieszenia anonimowo</strong> — wysyłamy parametry sprzętu, Modelu i wynik pomiaru, bez adresu IP i bez identyfikatora instalacji. Przy przyjęciu danych do bazy profili adres IP jest odrzucany i nie jest zapisywany.</li>
		<li><strong>Statystyki użycia</strong> — nie zbieramy ich w ogóle; przełącznik nie istnieje, ponieważ nie ma czego włączać. Informujemy o tym, abyś wiedział(a), że brak tej opcji jest celowy.</li>
	</ol>
	<p>Treść rozmów i promptów nigdy nie opuszcza urządzenia, niezależnie od ustawień. Lokalne API nasłuchuje wyłącznie na interfejsie lokalnym Twojego komputera.</p>
	<h2 id="odbiorcy" class="h2">8. Odbiorcy i podmioty przetwarzające</h2>
	<ul>
		<li>dostawca hostingu z siedzibą i serwerami w EOG — <span class="badge badge--soon">do wyboru</span>; dane powierzymy na podstawie umowy z art. 28 RODO;</li>
		<li>dostawca wysyłki e-maili (lista oczekujących, Konto) — <span class="badge badge--soon">do wyboru</span>, preferencyjnie w EOG;</li>
		<li>Google i GitHub — wyłącznie jeśli wybierzesz logowanie przez nich; działają jako odrębni administratorzy w zakresie własnych usług;</li>
		<li>planowany pośrednik płatności działający jako sprzedawca (Merchant of Record), np. Paddle — dopiero po rozpoczęciu sprzedaży; jest odrębnym administratorem danych płatniczych.</li>
	</ul>
	<h2 id="transfer" class="h2">9. Przekazywanie danych poza EOG</h2>
	<p>Logowanie przez Google lub GitHub może wiązać się z przekazaniem danych do USA. Przekazanie opiera się na decyzji Komisji Europejskiej stwierdzającej odpowiedni stopień ochrony (EU-US Data Privacy Framework), o ile dostawca jest certyfikowany, a w pozostałym zakresie — na standardowych klauzulach umownych. Jeśli tego nie chcesz, użyj logowania adresem e-mail.</p>
	<h2 id="okresy" class="h2">10. Okresy przechowywania</h2>
	<div class="table-wrap">
		<table class="table">
			<caption class="sr-only">Tabela okresów przechowywania</caption>
			<thead><tr><th scope="col">Kontekst</th><th scope="col">Dane</th><th scope="col">Cel i podstawa prawna</th><th scope="col">Okres przechowywania</th></tr></thead>
			<tbody>
				<tr><td>Strona (logi serwera)</td><td>adres IP, data i godzina, żądany adres, kod odpowiedzi, User-Agent</td><td>bezpieczeństwo i ciągłość działania — prawnie uzasadniony interes (art. 6 ust. 1 lit. f RODO)</td><td>do 14 dni, następnie usunięcie (do potwierdzenia z dostawcą hostingu)</td></tr>
				<tr><td>Lista oczekujących</td><td>adres e-mail, wybrana opcja cenowa, data i potwierdzenie zgody (double opt-in)</td><td>powiadomienie o wydaniu i badanie cen — zgoda (art. 6 ust. 1 lit. a RODO)</td><td>do wycofania zgody albo do 30 dni po wydaniu edycji płatnej; niepotwierdzone zapisy — 7 dni</td></tr>
				<tr><td>Konto</td><td>adres e-mail, identyfikator konta Google/GitHub, data utworzenia</td><td>prowadzenie Konta — wykonanie umowy (art. 6 ust. 1 lit. b RODO)</td><td>do usunięcia Konta; kopie zapasowe nadpisywane w ciągu 30 dni</td></tr>
				<tr><td>Raporty awarii (opcjonalne)</td><td>zrzut stosu, wersja Aplikacji, system, model GPU — po podglądzie przez Ciebie</td><td>usuwanie błędów — zgoda (art. 6 ust. 1 lit. a RODO)</td><td>90 dni</td></tr>
				<tr><td>Profil przyspieszenia (opcjonalny)</td><td>model GPU, sterownik, Model, parametry i wynik pomiaru; bez IP i bez ID instalacji</td><td>rozwój bazy profili — zgoda (art. 6 ust. 1 lit. a RODO); po anonimizacji dane przestają być osobowe</td><td>bezterminowo jako dane anonimowe</td></tr>
				<tr><td>Reklamacje i korespondencja</td><td>dane kontaktowe, treść zgłoszenia</td><td>rozpatrzenie — obowiązek prawny i ustalenie, dochodzenie lub obrona roszczeń (art. 6 ust. 1 lit. c i f RODO)</td><td>do upływu terminu przedawnienia roszczeń</td></tr>
			</tbody>
		</table>
	</div>
	<h2 id="prawa" class="h2">11. Twoje prawa</h2>
	<p>Masz prawo do:</p>
	<ul>
		<li>dostępu do danych i uzyskania ich kopii (art. 15 RODO);</li>
		<li>sprostowania (art. 16);</li>
		<li>usunięcia (art. 17);</li>
		<li>ograniczenia przetwarzania (art. 18);</li>
		<li>przenoszenia danych (art. 20);</li>
		<li>sprzeciwu wobec przetwarzania opartego na prawnie uzasadnionym interesie (art. 21);</li>
		<li>wycofania zgody w dowolnym momencie, bez wpływu na zgodność z prawem przetwarzania przed jej wycofaniem;</li>
		<li>wniesienia skargi do Prezesa Urzędu Ochrony Danych Osobowych (ul. Stawki 2, 00-193 Warszawa, uodo.gov.pl).</li>
	</ul>
	<p>Żądania kieruj na adres e-mail administratora wskazany w punkcie 1. Odpowiemy bez zbędnej zwłoki, nie później niż w ciągu miesiąca.</p>
	<h2 id="automatyzacja" class="h2">12. Zautomatyzowane podejmowanie decyzji</h2>
	<p>Nie podejmujemy decyzji opartych wyłącznie na zautomatyzowanym przetwarzaniu, w tym profilowaniu, które wywoływałyby wobec Ciebie skutki prawne lub w podobny sposób istotnie na Ciebie wpływały (art. 22 RODO). Dobór Modelu do sprzętu jest rekomendacją, którą możesz zmienić.</p>
	<h2 id="zmiany" class="h2">13. Zmiany polityki</h2>
	<p>O istotnych zmianach poinformujemy na stronie, a posiadaczy Konta — e-mailem, z wyprzedzeniem.</p>
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
