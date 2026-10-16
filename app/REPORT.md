# Raport: pierwsze elementy produktu (2026-10-16, noc)

Wszystko jest lokalnie w `~/KERNEL/app/`. Nic nie zostało wdrożone ani opublikowane. Lokalnego GPU nie używano: Chrome do zrzutów działał z `--disable-gpu` i bez sondowania VA-API, a `strace` potwierdził, że nie otwierał `/dev/dri` ani `/dev/kfd`. Skan Linuksa czyta tylko sysfs, procfs i lspci.

## 1. Co powstało

| Element | Gdzie | Stan |
|---|---|---|
| System projektowy: tokeny (kolor, typografia, przestrzeń, promienie, ruch), motyw ciemny i jasny, komponenty, znak „Tacho” | `design/tokens.css`, `design/components.css`, `design/logo/*.svg`, `design/DESIGN.md` | gotowe; kontrast policzony dla obu motywów (tekst ≥ 4,5:1, kontrolki ≥ 3:1) |
| Motyw czatu llama.cpp | `design/llama-ui-theme.css` | mapowanie tokenów na zmienne shadcn w `tools/ui` |
| Strona (SvelteKit 2.70 + Svelte 5, adapter-static, PL i EN) | `landing/` | 47 statycznych stron |
| Strona główna | `/pl/`, `/en/` | hero z animacją „pojedynek prędkości”, liczby z labu, 3 kroki z warstwami L0–L3, tabela wyników ze źródłami, karty NVIDIA z chmury, „bit w bit”, sprzęt, prywatność, cennik (hipoteza) z listą oczekujących typu fake-door, FAQ, stopka |
| Metodologia | `/methodology/` | surowe liczby z plikiem i linią źródła, opis skryptów, md5, wyjątki KLD, surowy scorecard 3090, wzory estymatora, lista tego, czego nie zmierzyliśmy |
| Onboarding (prototyp) | `/start/`, `paths`, `hardware`, `result`, `download`, `terminal`, `/scan/` | konto (Google, GitHub, e-mail, bez backendu), 3 drogi, formularz z autouzupełnianiem GPU (59 pozycji), wklejanie kodu skanu z sumą kontrolną, wynik z przedziałami |
| Skrypty skanu | `scan/scan.sh`, `scan-macos.sh`, `scan.ps1`, `TEST-linux.txt` | tylko odczyt, wypisują specyfikację i kod `HW1;…;sum=XXXX`; strona serwuje te same pliki |
| Dokumenty prawne PL i EN | `/legal/{terms,privacy,cookies,ai,imprint}/` | prawdziwe projekty, każdy z banerem „Projekt do weryfikacji przez prawnika”; pola danych spółki puste i opisane |
| Baner cookies | całe `(site)` | „Odrzucam” i „Akceptuję” mają równą wagę; kategoria analityki jest pusta, nic nie ładuje się przed zgodą ani po niej |
| Prototyp aplikacji desktop | `/[lang]/app/…`, kod w `landing/src/lib/desktop` | 8 ekranów: przegląd, kreator, Mój komputer, Wynik (L0–L3, miejsce na przedział ufności, md5/KLD, raport JSON), Optymalizacja nocna, Modele, Dla programistów, Czat |
| Makieta TUI | `tui/tui_demo.py` | czysty Python w stylu REACTOR; 5 scen, tryby `--plain`, `--snapshot` i `--html` |
| Architektura | `design/APP-ARCHITECTURE.md` | procesy, API, maszyna stanów onboardingu, łączenie konta kodem urządzenia (RFC 8628), dane lokalne i wysyłane, stany błędów, protokół uczciwego pomiaru w UI |

**Liczby.** Wszystkie wydajnościowe liczby na stronie pochodzą z jednego rejestru, `landing/src/lib/data/measurements.ts`, z plikiem i linią źródła: 38,8 / 85,6 / 68,6 / 109,0 / 43,2 / 1115 t/s dla Qwena, 169,3 → 289,7 / 293,7 t/s dla LFM i 4,4 vs 92 t/s przy BACO. Przy każdym porównaniu z dwóch różnych skryptów pomiarowych strona mówi to wprost. Nie ma mnożników „×”, nie ma słupka „typowa aplikacja” i nie ma liczb dla kart bez scorecardu.

**Wyniki z chmury.** Krok `bun scripts/sync-results.ts`, uruchamiany przed każdym buildem, wczytuje `~/qwen-opt/cloud/results/*/scorecard.json`. Dziś jest tylko scorecard RTX 3090. Strona pokazuje go jako „wstępne” i razem z jego statusem md5 („DIFF-BUILD”). Dlatego sekcja „bit w bit” mówi wprost, że na NVIDIA tej obietnicy jeszcze nie składamy.

## 2. Weryfikacja

- **Build:** `svelte-check` przechodzi bez błędów i ostrzeżeń (249 plików). Prerender kończy się błędem przy każdym zepsutym linku lub kotwicy.
- **Linki:** 50 wewnętrznych ścieżek zwraca 200, 99 kotwic `#` istnieje.
- **Konsola:** zero błędów i ostrzeżeń na wszystkich 47 stronach (ciemny i jasny motyw).
- **axe-core 4.14** (WCAG 2.0, 2.1, 2.2 A i AA oraz best-practice): 0 naruszeń na wszystkich stronach przy 1280 px w obu motywach i przy 390 px w obu motywach. Przy 390 px żadna strona nie przewija się w poziomie. Po drodze poprawiłem m.in.:
  - nazwę linku zmiany języka;
  - kontrast kroków onboardingu w jasnym motywie;
  - przewijane tabele, które teraz dostają fokus i nazwę regionu;
  - kolizję klasy `.bar`;
  - przepełnienia siatek.
- **Klawiatura:** link „Przejdź do treści” → nawigacja → CTA → pauza animacji, fokus widoczny wszędzie. W formularzu sprzętu combobox działa strzałkami i Enterem, a wysłanie Enterem prowadzi do wyniku.
  - Kod skanu z tej maszyny wypełnił formularz poprawnie: RX 7900 XTX, 24 GB, 64 GB RAM, Linux.
  - Kod z ręcznie zmienioną wartością został odrzucony przez sumę kontrolną.
- **Ograniczony ruch (`prefers-reduced-motion`):** hero pokazuje stan końcowy i stoi, dopóki ktoś nie kliknie „Odtwórz”. Przycisk pauzy zatrzymuje animację.
- **Lighthouse 13.5** (`screens/lighthouse.md`):
  - mobile: wydajność 96–98, dostępność, dobre praktyki i SEO po 100;
  - desktop: wydajność 100 (EN: 96–100, bo przy części przebiegów zostaje przesunięcie układu CLS do 0,12 z panelu animacji);
  - SEO 54 na `/app/*` wynika z celowego `noindex` dla prototypu.
- **Skan Linuksa:** pod `strace` przy uruchomieniu przez `sh` nie otworzył żadnej ścieżki `/dev/*`; dowód jest w `scan/TEST-linux.txt`. PowerShell 7 parsuje skrypt bez błędów, a self-test daje `E787`, tak samo jak w JS. Na prawdziwym Windowsie i Macu skryptów nie uruchamiałem.
- **Serwery:** stronę serwował `bun scripts/serve.ts` na 127.0.0.1:18433 z gzip, a Chrome z CDP działał na 127.0.0.1:18499. Oba są zatrzymane.

## 3. Zrzuty ekranu (`screens/`, 56 plików)

- **Strona główna:**
  - `landing-{pl,en}-{dark,light}-{desktop,mobile}.png` (8 plików);
  - `landing-pl-dark-cookie-banner.png`, `landing-pl-dark-waitlist-thanks.png`, `landing-pl-dark-reduced-motion.png`.
- **Onboarding:**
  - `onboarding-account-pl-dark-desktop.png`, `onboarding-account-en-light-mobile.png`;
  - `onboarding-paths-{pl-dark,en-light}-desktop.png`;
  - `onboarding-hardware-pl-dark-desktop.png` (wypełniony kodem skanu), `onboarding-hardware-en-light-mobile.png` (lista podpowiedzi);
  - `onboarding-result-pl-dark-{desktop,mobile}.png` (RX 7900 XTX, zmierzone), `onboarding-result-en-light-desktop.png` (RTX 4070, szacunek), `onboarding-result-pl-light-apple-m4pro.png`;
  - `onboarding-download-pl-dark-desktop.png`, `onboarding-terminal-en-dark-desktop.png`;
  - `scan-pl-light-desktop.png` (z podglądem kodu skryptu).
- **Treść:**
  - `methodology-pl-dark-desktop.png`, `methodology-en-light-mobile.png`;
  - `legal-privacy-pl-dark-desktop.png`, `legal-terms-en-light-mobile.png`, `legal-imprint-pl-light-desktop.png`, `legal-ai-pl-dark-desktop.png`.
- **Aplikacja:**
  - `app-{index,wizard,computer,result,night,models,developers,chat}-pl-dark.png`;
  - `app-{result,chat,night}-en-light.png`, `app-wizard-pl-dark-mobile.png`, `app-result-en-dark-fullpage.png`.
- **TUI:** `tui-{scan,recommend,calibrate,result,night}-pl.png` i `tui-result-en.png`, plus ich źródła HTML.

## 4. Decyzje, które podjąłem

1. **SvelteKit, nie Astro.** To ten sam stos i te same wersje co web UI llama.cpp (kit 2.70.2, svelte 5.56.1, vite 7.3.6) oraz aplikacja w Tauri. Komponenty, tokeny i i18n przenoszą się bez przepisywania. Uzasadnienie jest w DESIGN.md §11.
2. **Tożsamość wizualna: „telemetria w nocy”.**
   - Grafitowe tło `#07080D`, jeden kolor sygnałowy: volt `#C8FF3D`, który znaczy „po” i „nasze”.
   - Ion `#3DD6FF` dla informacji i fokusu, amber dla szacunków, heat dla błędów.
   - Fonty Geist i Geist Mono hostowane lokalnie, żeby nie wysyłać zapytań do Google Fonts (RODO).
   - Znak „Tacho” to tarcza ze wskazówką w czerwonym polu i nie zależy od nazwy produktu.
3. **Nazwa w jednym miejscu:** `landing/src/lib/brand.ts` (`BRAND.name = "Podkręt"`) oraz stała `BRAND` w `tui_demo.py`.
4. **Hero: 38,8 → 109,0 t/s.** Ten sam tekst jest odtwarzany w zmierzonym tempie. Podpis mówi, że te dwie liczby pochodzą z różnych skryptów pomiarowych i że spekulacja może zmienić tekst.
5. **„Bit w bit” napisane uczciwie.** Większość łatek jest bitowo identyczna. Trzy zmiany przeszły bramkę KLD zamiast md5. Spekulacja MTP daje inne md5 niż tryb bez niej (upstream też). Na CUDA scorecard pokazuje dziś „DIFF”.
6. **Estymator na stronie.**
   - Pamięć liczona wzorem z raportu 04 z zapasem 1 GiB.
   - Prędkość przed optymalizacją: η·BW/B_tok z η zmierzonym u nas (0,55–0,67 dla modeli gęstych, 0,31–0,55 dla MoE).
   - Po L1: ×1,5–2,2 tylko dla modeli ze zmierzonym MTP. L3: „wkrótce” poza RX 7900 XTX.
   - Zawsze pokazujemy przedział, nie pojedynczą liczbę.
7. **Kod skanu jest czytelnym tekstem** (`HW1;os=…;gpu=…;sum=XXXX`), żeby użytkownik widział każde pole przed wklejeniem. Na Linuksie przy kartach NVIDIA VRAM jest „?”, bo odczyt wymagałby otwarcia urządzenia; formularz bierze wtedy wartość z listy kart.
8. **Prototyp jest wszędzie opisany jako prototyp:**
   - logowanie odbywa się tylko w sessionStorage tej karty przeglądarki;
   - formularz listy oczekujących niczego nie wysyła i mówi to wprost;
   - przycisk pobierania jest nieaktywny;
   - komendy terminala są opisane jako projekt, który jeszcze nie działa.
9. **Narzędzia pomocnicze są lokalne i nie trafiają do repo.** W `app/.tools/` (wpisane do `.gitignore`) leżą: wrapper bun, biblioteki do Chrome z paczek .deb, PowerShell i axe-core.

## 5. Pytania do Ciebie

1. **Nazwa:** Podkręt, Nocna Zmiana / NightShift, Turbina, Rozpęd czy Tuned? Trzeba ją sprawdzić w EUIPO i w domenach. Po wyborze zrobię finalny wordmark w SVG.
2. **Kolory:** czy volt jako jedyny akcent ci odpowiada? Alternatywa to ion jako główny kolor, a volt tylko dla „po”. Ciemny motyw jako domyślny czy według ustawień systemu (tak jest teraz)?
3. **Ceny w teście fake-door:**
   - PL: 149 zł/rok, 299 zł dożywotnio, 19 zł/mies.;
   - EN: 39 €/rok, 79 € dożywotnio; w EN miesięcznej ceny nie podałem, bo nie ma jej w źródłach;
   - pytanie: czy pokazywać ceny przy zapisie na listę, czy dopiero po zapisie?
4. **Konto przed pobraniem** (tak jest teraz, zgodnie z §8.1.1) czy pobieranie bez konta? To kandydat do testu A/B.
5. **Sprawy prawne:**
   - kancelaria i KRiBSI w sprawie art. 50(2) AI Act (znak wodny tekstu a „bit w bit”);
   - okresy retencji danych zaproponowałem sam;
   - czy potrzebny jest inspektor ochrony danych (IOD);
   - zakresy OAuth;
   - status platformy ODR;
   - kiedy zakładamy spółkę (dane firmy są dziś celowo puste).
6. **Numer portu lokalnego API:** 11500 to propozycja z prototypu (stała `BRAND.apiPort`).
7. **Domena:** `SITE_ORIGIN` ustawia adresy `hreflang` i `canonical`. Bez niej build wskazuje na `127.0.0.1:18433`.

## 6. Co zostało do zrobienia

- Uruchomić `scan.ps1` na prawdziwym Windowsie (5.1 i 7) i `scan-macos.sh` na Macu.
- Znaleźć źródło sporadycznego przesunięcia układu w EN hero na desktopie (CLS do 0,12).
- Uzupełnić tabelę wyników i sekcję sprzętu, gdy pojawią się scorecardy 5060 Ti i 3060 oraz finalny 3090. Robi się to samo przy kolejnym buildzie.
- Pomiar E1 (Ollama i LM Studio tym samym skryptem pomiarowym). Bez niego słupek „typowa aplikacja” zostaje ukryty.

**Uruchomienie:**
```
cd ~/KERNEL/app/landing
~/KERNEL/app/.tools/bun run build
~/KERNEL/app/.tools/bun scripts/serve.ts 18433
```
