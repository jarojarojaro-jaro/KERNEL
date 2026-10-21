<script lang="ts">
	import { SITE_PUBLIC } from '$lib/site/public';
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
	<h1 class="h1">Regulamin świadczenia usług drogą elektroniczną</h1>
	<p class="source">{LEGAL_VERSION[L]}</p>
	<nav aria-labelledby="toc-title" class="card card--inset toc">
		<h2 id="toc-title" class="h3">Spis treści</h2>
		<ol>
			<li><a href="#postanowienia">§ 1. Postanowienia ogólne</a></li>
			<li><a href="#definicje">§ 2. Definicje</a></li>
			<li><a href="#zakres">§ 3. Rodzaje i zakres Usług</a></li>
			<li><a href="#wymagania">§ 4. Wymagania techniczne</a></li>
			<li><a href="#konto">§ 5. Konto</a></li>
			<li><a href="#edycje">§ 6. Edycja bezpłatna i edycja płatna</a></li>
			<li><a href="#konsument">§ 7. Prawa Konsumenta</a></li>
			<li><a href="#korzystanie">§ 8. Zasady korzystania i licencje Modeli</a></li>
			<li><a href="#ai">§ 9. Sztuczna inteligencja i rzetelność deklaracji wydajności</a></li>
			<li><a href="#odpowiedzialnosc">§ 10. Odpowiedzialność</a></li>
			<li><a href="#reklamacje">§ 11. Reklamacje</a></li>
			<li><a href="#pozasadowe">§ 12. Pozasądowe rozwiązywanie sporów</a></li>
			<li><a href="#prawo">§ 13. Prawo właściwe</a></li>
			<li><a href="#zmiany">§ 14. Zmiany Regulaminu</a></li>
		</ol>
	</nav>
	<h2 id="postanowienia" class="h2">§ 1. Postanowienia ogólne</h2>
	<p>Niniejszy regulamin („Regulamin”) określa zasady świadczenia usług drogą elektroniczną w ramach serwisu i oprogramowania {BRAND.name}, w rozumieniu art. 8 ustawy z dnia 18 lipca 2002 r. o świadczeniu usług drogą elektroniczną (u.ś.u.d.e.).</p>
	<p>Usługodawcą jest spółka z ograniczoną odpowiedzialnością w organizacji, której dane zostaną wskazane poniżej po jej wpisie do Krajowego Rejestru Sądowego:</p>
	<CompanyData lang={L} />
	<p>Regulamin jest udostępniany nieodpłatnie przed zawarciem umowy, w sposób umożliwiający jego pozyskanie, odtwarzanie i utrwalanie (wydruk lub zapis do pliku).</p>
	<h2 id="definicje" class="h2">§ 2. Definicje</h2>
	<ul>
		<li><strong>Usługodawca</strong> — podmiot wskazany w § 1.</li>
		<li><strong>Użytkownik</strong> — osoba fizyczna, osoba prawna albo jednostka organizacyjna korzystająca z Usług; <strong>Konsument</strong> — Użytkownik będący konsumentem w rozumieniu art. 22<sup>1</sup> Kodeksu cywilnego, a także osoba fizyczna, o której mowa w art. 38a ustawy o prawach konsumenta (u.p.k.).</li>
		<li><strong>Serwis</strong> — strona internetowa Usługodawcy wraz z podstronami.</li>
		<li><strong>Aplikacja</strong> — aplikacja desktopowa {BRAND.name} instalowana na urządzeniu Użytkownika, wraz z interfejsem wiersza poleceń (<strong>CLI</strong>) oraz lokalnym interfejsem programistycznym (<strong>Lokalne API</strong>) dostępnym wyłącznie na urządzeniu Użytkownika.</li>
		<li><strong>Konto</strong> — zbiór danych w systemie Usługodawcy umożliwiający korzystanie z funkcji wymagających logowania.</li>
		<li><strong>Model</strong> — model językowy osoby trzeciej, pobierany przez Użytkownika i uruchamiany lokalnie, udostępniany na licencji jego twórcy.</li>
		<li><strong>Treść cyfrowa</strong> — dane wytwarzane i dostarczane w postaci cyfrowej, w szczególności Aplikacja i profile przyspieszenia.</li>
		<li><strong>Skan sprzętu</strong> — skrypt lub funkcja Aplikacji odczytująca lokalnie parametry sprzętu w celu doboru Modelu.</li>
	</ul>
	<h2 id="zakres" class="h2">§ 3. Rodzaje i zakres Usług</h2>
	<p>Usługodawca świadczy następujące Usługi:</p>
	<ol>
		<li>udostępnianie treści Serwisu, w tym opisów produktu, wyników pomiarów i strony {#if SITE_PUBLIC}Metodologia{:else}<a href={href(L, '/methodology')}>Metodologia</a>{/if};</li>
		<li>formularz listy oczekujących (zapis na powiadomienie o wydaniu) — <em>obecnie formularz nie przesyła żadnych danych, ponieważ zaplecze techniczne nie zostało uruchomione</em>;</li>
		<li>narzędzie doboru Modelu działające w przeglądarce na podstawie danych wpisanych przez Użytkownika lub wklejonego kodu Skanu sprzętu;</li>
		<li>prowadzenie Konta;</li>
		<li>udostępnienie Aplikacji, CLI i Lokalnego API do pobrania i używania na urządzeniu Użytkownika.</li>
	</ol>
	<p>Modele działają lokalnie na urządzeniu Użytkownika. Usługodawca nie przetwarza treści rozmów ani poleceń (promptów) Użytkownika, które nie opuszczają jego urządzenia.</p>
	<h2 id="wymagania" class="h2">§ 4. Wymagania techniczne</h2>
	<p>Do korzystania z Serwisu wymagane jest urządzenie z dostępem do Internetu i aktualną przeglądarką internetową obsługującą JavaScript. Do korzystania z Aplikacji wymagany jest komputer z systemem Linux, Windows lub macOS spełniający wymagania sprzętowe właściwe dla wybranego Modelu, wskazywane przez Aplikację przed pobraniem Modelu.</p>
	<p>Usługodawca informuje, że korzystanie z usług świadczonych drogą elektroniczną wiąże się z typowymi zagrożeniami (np. złośliwe oprogramowanie, phishing). Pliki Aplikacji pobieraj wyłącznie z Serwisu i weryfikuj ich sumy kontrolne lub podpisy, gdy są udostępnione.</p>
	<h2 id="konto" class="h2">§ 5. Konto</h2>
	<ol>
		<li>Założenie Konta jest dobrowolne i nieodpłatne. Aplikacja w edycji bezpłatnej działa bez Konta.</li>
		<li>Konto można założyć, logując się przez Google, GitHub lub Hugging Face, albo podając wyłącznie nazwę użytkownika i hasło, bez adresu e-mail. Przy logowaniu zewnętrznym pobieramy wyłącznie minimalny zakres danych: identyfikator konta u dostawcy, nazwę użytkownika i — jeśli dostawca go przekaże — adres e-mail. Do Konta bez adresu e-mail nie da się odzyskać dostępu po utracie hasła.</li>
		<li>Użytkownik zobowiązuje się nie udostępniać danych dostępowych osobom trzecim.</li>
		<li>Użytkownik może w każdej chwili usunąć Konto jednym przyciskiem w ustawieniach Konta, bez podawania przyczyny. Usunięcie Konta jest równoznaczne z rozwiązaniem umowy o prowadzenie Konta ze skutkiem natychmiastowym.</li>
		<li>Usługodawca może rozwiązać umowę o prowadzenie Konta z zachowaniem 14-dniowego terminu wypowiedzenia z ważnych przyczyn (rażące naruszenie § 8), informując o przyczynie na adres e-mail Użytkownika, a jeśli Konto go nie ma — komunikatem po zalogowaniu.</li>
	</ol>
	<h2 id="edycje" class="h2">§ 6. Edycja bezpłatna i edycja płatna</h2>
	<ol>
		<li>Edycja bezpłatna Aplikacji jest udostępniana bez opłat i bez ograniczenia czasowego.</li>
		<li>Edycja płatna jest planowana, lecz <strong>nie jest obecnie sprzedawana</strong>. Ceny prezentowane w Serwisie stanowią hipotezę badawczą; wybór opcji cenowej w formularzu listy oczekujących nie jest ofertą ani zamówieniem i nie rodzi obowiązku zapłaty.</li>
		<li>Przed rozpoczęciem sprzedaży Regulamin zostanie uzupełniony o zasady zawierania umów odpłatnych, ceny, sposoby płatności (planowany pośrednik płatności działający jako sprzedawca — Merchant of Record), czas trwania umowy i zasady jej wypowiadania.</li>
	</ol>
	<h2 id="konsument" class="h2">§ 7. Prawa Konsumenta</h2>
	<ol>
		<li>Konsumentowi, który zawarł umowę na odległość, przysługuje prawo odstąpienia od umowy w terminie 14 dni bez podania przyczyny (art. 27 u.p.k.).</li>
		<li>W przypadku umowy o dostarczanie treści cyfrowej niedostarczanej na nośniku materialnym, za którą Konsument zobowiązany jest do zapłaty ceny, prawo odstąpienia nie przysługuje, jeżeli spełnianie świadczenia rozpoczęło się za wyraźną i uprzednią zgodą Konsumenta, który został poinformowany przed jego rozpoczęciem, że po spełnieniu świadczenia utraci prawo odstąpienia od umowy, i przyjął to do wiadomości, a przedsiębiorca przekazał potwierdzenie (art. 38 ust. 1 pkt 13 u.p.k.). Zgoda ta będzie zbierana osobnym, niezaznaczonym domyślnie polem.</li>
		<li>Usługodawca odpowiada za zgodność Treści cyfrowej z umową na zasadach rozdziału 5b u.p.k. i zapewnia aktualizacje, w tym aktualizacje zabezpieczeń, niezbędne do zachowania zgodności Aplikacji z umową, przez okres, którego Konsument może rozsądnie oczekiwać (art. 43k u.p.k.), oraz informuje o nich.</li>
		<li>Postanowienia dotyczące Konsumenta stosuje się również do osoby fizycznej zawierającej umowę bezpośrednio związaną z jej działalnością gospodarczą, gdy z treści umowy wynika, że nie posiada ona dla niej charakteru zawodowego (art. 38a u.p.k.).</li>
	</ol>
	<h2 id="korzystanie" class="h2">§ 8. Zasady korzystania i licencje Modeli</h2>
	<ol>
		<li>Zabronione jest dostarczanie i wytwarzanie przy użyciu Usług treści o charakterze bezprawnym oraz korzystanie z Usług w sposób naruszający prawo, dobre obyczaje lub prawa osób trzecich.</li>
		<li>Każdy Model jest udostępniany na licencji jego twórcy, którą Aplikacja wyświetla przed pobraniem. Użytkownik zobowiązuje się przestrzegać tej licencji, w szczególności: dla modeli Gemma (do wersji 3 włącznie) — <em>Gemma Prohibited Use Policy</em>; dla modeli gpt-oss — zasad użytkowania wskazanych przez ich twórcę.</li>
		<li>Modele Llama 4 nie są oferowane w Aplikacji ze względu na warunki licencyjne. Usługodawca nie oferuje modeli o usuniętych zabezpieczeniach (tzw. „uncensored”).</li>
		<li>Zabronione jest obchodzenie zabezpieczeń Aplikacji, zakłócanie działania Serwisu oraz dekompilacja w zakresie wykraczającym poza dozwolony przez bezwzględnie obowiązujące przepisy prawa.</li>
	</ol>
	<h2 id="ai" class="h2">§ 9. Sztuczna inteligencja i rzetelność deklaracji wydajności</h2>
	<p>Aplikacja jest systemem sztucznej inteligencji. Odpowiedzi Modeli mogą być nieprawdziwe, niepełne lub nieaktualne; nie stanowią porady prawnej, medycznej ani finansowej. Szczegóły zawiera <a href={href(L, '/legal/ai')}>Informacja o AI</a>.</p>
	<p>Zgodnie z zakazem nieuczciwych praktyk rynkowych (ustawa z dnia 23 sierpnia 2007 r. o przeciwdziałaniu nieuczciwym praktykom rynkowym, dyrektywa 2005/29/WE) każda deklaracja dotycząca szybkości jest pomiarem na wskazanym sprzęcie, z podaniem źródła, konfiguracji i metody, opisanej na stronie {#if SITE_PUBLIC}Metodologia{:else}<a href={href(L, '/methodology')}>Metodologia</a>{/if}. Wartości nieprzetestowane oznaczamy jako szacunek albo „wkrótce”. Wynik na sprzęcie Użytkownika może się różnić.</p>
	<h2 id="odpowiedzialnosc" class="h2">§ 10. Odpowiedzialność</h2>
	<ol>
		<li>Usługodawca dokłada staranności, aby Usługi działały nieprzerwanie, z zastrzeżeniem przerw technicznych.</li>
		<li>Wobec Użytkowników niebędących Konsumentami odpowiedzialność Usługodawcy ogranicza się do szkody rzeczywistej i jest wyłączona za utracone korzyści, w granicach dopuszczalnych przez prawo.</li>
		<li>Wobec Konsumentów postanowienia Regulaminu nie wyłączają ani nie ograniczają odpowiedzialności Usługodawcy w zakresie, w jakim byłoby to sprzeczne z bezwzględnie obowiązującymi przepisami prawa, w szczególności nie naruszają uprawnień z tytułu braku zgodności Treści cyfrowej z umową.</li>
		<li>Usługodawca nie odpowiada za treść wytworzoną przez Model na żądanie Użytkownika ani za sposób jej wykorzystania, o ile nie wynika to z niezgodności Aplikacji z umową.</li>
	</ol>
	<h2 id="reklamacje" class="h2">§ 11. Reklamacje</h2>
	<ol>
		<li>Reklamacje można składać na adres e-mail Usługodawcy wskazany w § 1 (zostanie podany po rejestracji spółki).</li>
		<li>Reklamacja powinna zawierać dane kontaktowe, opis problemu i żądanie. Brak tych elementów nie powoduje odrzucenia reklamacji.</li>
		<li>Usługodawca rozpatruje reklamację w terminie 14 dni od jej otrzymania. Brak odpowiedzi w tym terminie Konsumentowi oznacza uznanie reklamacji, w zakresie przewidzianym przepisami.</li>
	</ol>
	<h2 id="pozasadowe" class="h2">§ 12. Pozasądowe rozwiązywanie sporów</h2>
	<p>Konsument może skorzystać z pozasądowych sposobów rozpatrywania reklamacji, w tym z pomocy miejskiego lub powiatowego rzecznika konsumentów, organizacji społecznych, wojewódzkich inspektoratów Inspekcji Handlowej oraz informacji udostępnianych przez Prezesa UOKiK pod adresem <a href="https://polubowne.uokik.gov.pl/" rel="noopener">polubowne.uokik.gov.pl</a>.</p>
	<p>Platforma ODR Komisji Europejskiej została wycofana z dniem 20 lipca 2025 r. na mocy rozporządzenia (UE) 2024/3228; informujemy o tym zamiast linku do platformy.</p>
	<h2 id="prawo" class="h2">§ 13. Prawo właściwe</h2>
	<p>Do umów stosuje się prawo polskie. Wybór prawa nie pozbawia Konsumenta ochrony przysługującej mu na podstawie przepisów, których nie można wyłączyć w drodze umowy, prawa państwa jego zwykłego pobytu (art. 6 ust. 2 rozporządzenia Rzym I).</p>
	<p>Spory z Użytkownikami niebędącymi Konsumentami rozstrzyga sąd właściwy dla siedziby Usługodawcy.</p>
	<h2 id="zmiany" class="h2">§ 14. Zmiany Regulaminu</h2>
	<p>Usługodawca może zmienić Regulamin z ważnych przyczyn: zmiany przepisów, zmiany zakresu Usług lub wymogów bezpieczeństwa. O zmianie Użytkownicy posiadający Konto zostaną powiadomieni co najmniej 14 dni przed jej wejściem w życie: e-mailem, jeśli Konto ma adres e-mail, a w pozostałych przypadkach komunikatem po zalogowaniu. Użytkownik, który nie akceptuje zmian, może usunąć Konto przed tym dniem.</p>
	<p>Zmiany nie naruszają praw nabytych przed ich wejściem w życie.</p>
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
