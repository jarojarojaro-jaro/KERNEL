# System projektowy

Stan: 2026-10-16, tożsamość v2 „Białe ciepło”. Brief kreatywny (koncept, moodboard, storyboard hero, sceny): **`REDESIGN.md`**; ten dokument opisuje system, na którym brief stoi. Źródło prawdy: `tokens.css` (zmienne), `components.css` (klasy wspólne) i `showcase.css` (warstwa pokazowa: strona główna, eksplorator kart). Tokeny i komponenty importuje strona (`app/landing`), prototyp aplikacji desktop (`/[lang]/app/…`) i motyw czatu llama.cpp (`llama-ui-theme.css`). Nazwa produktu jest otwartą decyzją, patrz §2.

## 1. Idea

**Szybkość to ciepło.** Produkt obiecuje jedną rzecz: ten sam model, szybciej, i to zmierzone. Strona jest ciemną komorą pomiarową:

- **ciepła, głęboka czerń** (`#050506`) i tekst w kolorze kości (`#EDEAE3`); głębia z warstw gradientów radialnych, ziarna (szum SVG, 4–5%) i linii 1 px; bez szkła poza przyklejonym nagłówkiem;
- **jedna rampa ciepła** (zimny → czerwony → pomarańcz → bursztyn → biały żar) i **znaczy wyłącznie prędkość** (tokeny/s): słupek „po”, wskazówka w czerwonym polu, odczyt naszego silnika. Nigdy dekoracja, nigdy przycisk, nigdy fokus;
- **zimna stal** (`--before`) dla „przed” / upstream; to jedyny chłodny ton;
- **CTA w kolorze kości**: pigułka kość na czerni (jasny motyw: czerń na kości), nie ciepło;
- **typografia z osią szerokości**: Mona Sans (nagłówki rozciągają się „przyspieszając”), Martian Mono do liczb i etykiet jak na przyrządzie;
- **uczciwość jako element UI**: każda liczba ma znacznik statusu (zmierzone / szacunek / wkrótce) i przypis ze źródłem `plik:linia` (§8).

Czego unikamy: gradientów fioletowo-niebieskich, glassmorphismu wszędzie, ikon-emoji, „Unlock the power of”, trzech identycznych kart w rzędzie, blobów, tabel jako głównej treści, mnożników „×2” bez pomiaru tym samym skryptem.

Inspiracje i to, co z nich bierzemy: `REDESIGN.md` §2 (Apple Pro-chip, Linear, Vercel Ship, Raycast, Nothing, Teenage Engineering, telemetria F1 / Porsche, Rimac).

## 2. Marka

### 2.1 Nazwa (otwarta decyzja)
Jedna stała: `app/landing/src/lib/brand.ts` → `BRAND.name` (dziś „Podkręt”), `BRAND.ascii` (`podkret`, do plików i CLI), `BRAND.cli`. Prototyp desktop, dokumenty prawne, meta tagi i TUI (`app/tui/tui_demo.py`, stała `BRAND` na górze pliku) biorą nazwę stamtąd. Kandydaci z raportu 06 §3.1: Podkręt, Nocna Zmiana / NightShift, Turbina, Rozpęd, Tuned. Przed wyborem: EUIPO (kl. 9 i 42), domeny, kolizje z „llama”, „NVIDIA”, „AMD”.

### 2.2 Znak „Tacho”
Plik: `logo/mark.svg` (kolor), `logo/mark-mono.svg` (jeden kolor, `currentColor`), `logo/favicon.svg` (na czarnym kwadracie `#050506`), `logo/lockup-dark.svg` (znak + nazwa jako żywy tekst).

Konstrukcja na siatce 32×32: łuk tarczy 270° (r = 11, kreska 3, zaokrąglone końce) w kolorze kości z kryciem 38–42%; ostatnie 75° łuku to czerwone pole w rampie ciepła (bursztyn `#FFC15A` → pomarańcz `#FF7A1A` → czerwień `#E2401C`), wskazówka pomarańczowa `#FF7A1A` „wbita” w czerwone pole; piasta r = 2,6 w kolorze kości. Znak nie zależy od nazwy, więc przeżyje jej zmianę. To jedyne miejsce, gdzie ciepło stoi bez liczby: znak mówi „szybciej”.

Zasady: minimalny rozmiar 16 px (favicon czytelny), pole ochronne = promień piasty × 2 wokół znaku, na jasnym tle część „gorąca” przechodzi na `--accent-ink` (`#A8380B`, 5,8:1 na `--bg-0`). Wordmark to tekst w Mona Sans 760, szerokość 118%, tracking −0,02 em (`Logo.svelte`); finalny wordmark (ścieżki SVG) dopiero po wyborze nazwy.

## 3. Kolor

### 3.1 Paleta bazowa
| Token | Ciemny | Jasny | Rola |
|---|---|---|---|
| `--bg-0` | `#050506` | `#F4F2EE` | tło strony |
| `--bg-1` | `#0B0B0D` | `#EBE8E2` | pasy sekcji, pola formularzy, karty wpuszczone |
| `--bg-2` | `#131316` | `#FBFAF8` | karty, panele |
| `--bg-3` | `#1C1C21` | `#E4E0D8` | hover, wstawki, tor słupka |
| `--line` | `#26262C` | `#D8D4CB` | linie 1 px (dekoracyjne) |
| `--line-strong` | `#77746D` | `#807B72` | obramowania kontrolek (≥ 3:1) |
| `--text-hi` / `--text` / `--text-mute` | `#EDEAE3` / `#BDB9B1` / `#8E8A83` | `#0B0A09` / `#2C2A26` / `#5C5852` | tekst |

### 3.2 Kolory znaczeniowe
| Token | Znaczenie | Ciemny | Jasny (tekst) |
|---|---|---|---|
| `--heat-0…5`, `--heat-ramp`, `--heat-ramp-hot` | **prędkość** (i tylko ona): słupek „po”, czerwone pole, odczyt t/s naszego silnika | `#1E3448` → `#7A2E1F` → `#E2401C` → `#FF7A1A` → `#FFC15A` → `#FFF3D6` | jak w ciemnym; w jasnym słupek kończy się na bursztynie |
| `--accent` / `--accent-ink` | pojedynczy kolor ciepła: wypełnienie / tekst prędkości | `#FF7A1A` / `#FF8F3D` | `#E2541A` / `#A8380B` |
| `--before` | „przed”, upstream; zimna stal, celowo cicha | `#7D8794` | `#5E6874` |
| `--text-hi` jako wypełnienie | główne CTA, zaznaczenie, fokus, aktywna zakładka, przełącznik, znacznik „zmierzone” | `#EDEAE3` | `#0B0A09` |
| `--info` | „pomiar w toku”, prototyp (blada stal) | `#A9C7D8` | `#2D5870` |
| `--warn` | szacunek, ostrzeżenie, projekt prawny | `#E3CF7A` | `#7A5D00` |
| `--danger` | błąd, „nie zmieści się” | `#FF8A8A` | `#B42318` |
| `--ok` | „pasuje”, gotowe | `#7FD99A` | `#1F7A46` |

Zasady: kolor nigdy nie jest jedynym nośnikiem informacji (WCAG 1.4.1); każda plakietka ma tekst, każdy słupek ma liczbę. Linki są w kolorze `--text-hi` z podkreśleniem 38% (pełne przy hover), nie w kolorze akcentu.

### 3.3 Kontrast (policzony, WCAG 2.x)
Wyliczone z wartości w `tokens.css`:

| Para | Ciemny | Jasny |
|---|---|---|
| `--text-hi` na `--bg-0` | 17.0:1 | 17.7:1 |
| `--text` na `--bg-0` | 10.4:1 | 12.8:1 |
| `--text` na `--bg-2` | 9.5:1 | 13.7:1 |
| `--text-mute` na `--bg-0` | 5.9:1 | 6.3:1 |
| `--text-mute` na `--bg-2` | 5.4:1 | 6.8:1 |
| `--text-mute` na `--bg-3` | 4.9:1 | 5.4:1 |
| `--text-inv` na `--text-hi` (CTA) | 17.0:1 | 17.7:1 |
| `--accent-ink` na `--bg-0` | 9.0:1 | 5.8:1 |
| `--accent-ink` na `--bg-2` | 8.2:1 | 6.2:1 |
| `--on-accent` na `--accent` | 7.7:1 | 5.3:1 |
| `--info-ink` na `--bg-0` | 11.5:1 | 6.9:1 |
| `--warn-ink` na `--bg-0` | 13.1:1 | 5.5:1 |
| `--danger-ink` na `--bg-0` | 9.0:1 | 5.9:1 |
| `--ok-ink` na `--bg-0` | 11.9:1 | 4.8:1 |
| `--before` na `--bg-0` | 5.6:1 | 5.1:1 |
| `--before` na `--bg-2` | 5.1:1 | 5.4:1 |
| `--line-strong` na `--bg-2` | 4.0:1 | 4.0:1 |
| `--line-strong` na `--bg-1` | 4.2:1 | 3.4:1 |
| `--focus` na `--bg-0` | 17.0:1 | 17.7:1 |

Cały tekst ≥ 4.5:1, kontrolki i fokus ≥ 3:1 w obu motywach. Tekst w gradiencie ciepła (`.heat-text`) stosujemy tylko w ciemnym motywie i w dużych stopniach (≥ 24 px).

### 3.4 Motywy
Ciemny jest domyślny (tożsamość). Strona główna i eksplorator kart są **tylko ciemne** (sceny kinowe nie mają jasnej wersji; `app.html` ustawia `data-theme="dark"` i `data-showcase`). Pozostałe strony (metodologia, dokumenty prawne, skan, onboarding, prototyp aplikacji) mają pełnoprawny jasny motyw „kość” (`#F4F2EE`). Wybór: `html[data-theme]` ustawiany przed pierwszym malowaniem (skrypt w `app.html`): zapisany wybór użytkownika, a bez niego `prefers-color-scheme`. Zapis w `localStorage` tylko po kliknięciu przełącznika (żądanie użytkownika, wyjątek z art. 5(3) ePrivacy). `meta[name=theme-color]`: `#050506` / `#F4F2EE`.

## 4. Typografia

- **Mona Sans** (GitHub, OFL 1.1; zmienny: grubość 200–900, szerokość 75–125%) do nagłówków i tekstu oraz **Martian Mono** (Evil Martians, OFL 1.1; grubość 100–800, szerokość 75–112,5%) do liczb, kodu i etykiet. **Hostowane lokalnie** (`static/fonts`, podzbiory latin + latin-ext z polskimi znakami, licencje `OFL-MonaSans.txt`, `OFL-MartianMono.txt`), łacina wstępnie ładowana w `app.html`. Zero zapytań do Google Fonts (RODO: wyrok LG München 3 O 17493/20 dotyczył właśnie Google Fonts). Geist usunięty.
- Skala 1,25, płynna u góry: `--fs-2xs` 11 px (etykiety mono, wersaliki, tracking 0,12 em), `xs` 12, `sm` 14, `base` 16, `md` 18, `lg` 22, `xl` 28, `2xl` 30–40, `3xl` 36–56, `display` 42–80 px; warstwa pokazowa: `--fs-giga` 40–100 px, `--fs-mega` 50–168 px.
- Nagłówki: grubość 650–800, tracking −0,015 do −0,038 em, `text-wrap: balance`. Akapity: `text-wrap: pretty`, interlinia 1,6, szerokość ≤ 44 rem. **Dwie rodziny, bez mieszania szerokości**: w komponentach i na stronach drugorzędnych nie zmieniamy `font-stretch` (jedyny wyjątek to tytuły pokazowe `.giga`/`.mega` z `showcase.css`); żadnych cienkich (200–300) cyfr ani zestawień „wąski + bardzo gruby”.
- **Liczby**: zawsze `.num` (Martian Mono, `tabular-nums slashed-zero`), duże odczyty grubością 400–600; jednostka mniejsza i przygaszona. Separator dziesiętny wg języka: „109,0 t/s” po polsku, „109.0 t/s” po angielsku (`num()` w `i18n.ts`).
- **Overline** (`.overline`, w warstwie pokazowej `.eyebrow`): mono, wersaliki, kreska 1,6 rem przed tekstem; nazwa sekcji jak etykieta kanału na przyrządzie.

## 5. Przestrzeń, siatka, kształt

- Siatka 4 px: `--sp-1` 4 px … `--sp-24` 96 px; odstęp sekcji `--section-y` 64–120 px; kontener 72 rem, wąski 46 rem; margines boczny 16–32 px.
- Promienie: `--r-xs` 3 (kod), `sm` 6 (pola), `md` 10, `lg` 14 (ramy, komunikaty), `xl` 20 (karty, tabele, panele). **Przyciski, plakietki, przełączniki segmentowe = pigułki** (`--r-pill`).
- Elewacja minimalna: `--shadow-1` (wewnętrzna krawędź), `--shadow-2` (pływające panele); karta ma u góry 2,5% poświaty w kolorze kości. Poświata ciepła (`--accent-glow`) tylko przy odczytach prędkości.
- Tło `.bg-grid` (siatka 32 px, 5% krycia) i ziarno `.grain` tylko na stronach pokazowych.

## 6. Ruch

| Token | Czas | Użycie |
|---|---|---|
| `--dur-1` | 110 ms | hover, wciśnięcie |
| `--dur-2` | 180 ms | przełączniki, strzałki |
| `--dur-3` | 320 ms | panele, pojawianie się |
| `--dur-4` | 640 ms | wypełnianie słupków |

Krzywe: `--ease-out` (0.16, 1, 0.3, 1) dla wejść, `--ease-in-out` dla pętli, `--ease-spring` (wskazówka z małym przestrzeleniem), `--ease-drop` (grawitacja). Zasady:

1. **Ruch niesie dane.** Animujemy tylko to, co coś mierzy: strumień tekstu w tempie t/s, słupki, wskaźnik postępu. Żadnych dekoracyjnych paralaks.
2. **`prefers-reduced-motion: reduce`** ustawia wszystkie `--dur-*` na 0,01 ms; animacja hero startuje wtedy w stanie końcowym (oba teksty gotowe, czasy ukończenia widoczne) i rusza tylko po kliknięciu „Odtwórz”.
3. **Pauza (WCAG 2.2.2).** Każdy ruch dłuższy niż 5 s ma widoczny przycisk pauzy; animacja zatrzymuje się poza ekranem (IntersectionObserver) i w ukrytej karcie.

**Animacja hero („wyścig”) i sceny przewijania** są opisane w `REDESIGN.md` §6–7: ta sama karta (RTX 3090), ten sam model, ta sama odpowiedź pisana dwa razy w zmierzonym tempie, tylko z liczb tego samego skryptu. Dla czytników ekranu jest tekstowe podsumowanie, a sama animacja ma pauzę i stan końcowy przy `prefers-reduced-motion`.

## 7. Komponenty (`components.css`)

| Klasa | Opis |
|---|---|
| `.btn` `--primary` / `--secondary` / `--ghost`, `--sm` / `--lg` / `--block` | pigułki, wysokość 44 px (cel dotyku ≥ 24 px, WCAG 2.5.8); primary = kość na czerni / czerń na kości, secondary = obrys `--line-strong`; nigdy ciepło. W warstwie pokazowej odpowiednik `.cta--bone` / `.cta--line` |
| `.icon-btn` | 40×40, zawsze z `aria-label` |
| `.card`, `.card--inset`, `.card--interactive` | powierzchnie |
| `.hud` | rama przyrządu z dwoma narożnikami (domyślnie `--line-strong`; `--hud-c` dla statusu) |
| `.badge` + `--measured` / `--estimate` / `--soon` / `--progress` / `--prototype` / `--draft` / `--ok` / `--danger` | statusy uczciwości (§8) |
| `.notice` + `--info` / `--warn` / `--danger` / `--ok` / `--prototype` | komunikaty z ikoną w kolumnie |
| `.field`, `.label`, `.hint`, `.error-text`, `.input`, `.select`, `.textarea`, `.check`, `.segmented`, `.switch` | formularze; błędy tekstem + `aria-invalid` + `aria-describedby` |
| `.table-wrap` + `.table` | tabele danych, nagłówki mono, liczby do prawej |
| `.stat` (`__value`, `__unit`, `__label`) | duże odczyty |
| `.bar` (`--v`), `--before`, `--range`, `--tall` | słupki przed → po; domyślne wypełnienie = rampa ciepła (prędkość), `--before` = zimna stal, `--range` (kreskowany) = szacunek z przedziałem |
| `.codeblock` (`__head`, `pre`, `.prompt`) | komendy do skopiowania |
| `.tabs` (`role=tab`) | zakładki ze strzałkami |
| `.disclosure` | FAQ, „Jak to policzyliśmy” (`details/summary`) |
| `.source` | przypis źródła: mono, 12 px |
| `.overline`, `.ticks`, `.bg-grid` | elementy telemetryczne |

Warstwa pokazowa (`showcase.css`, komponenty `src/lib/fx`: `Tacho`, `RaceLanes`, `Odometer`, `HeatBar`, `HeatField`…) jest opisana w `REDESIGN.md` §5–8.

Komponenty Svelte strony: `Header`, `Footer`, `Logo`, `ThemeToggle`, `CookieBanner`, `Waitlist` (`src/lib/site`), sceny strony głównej (`src/lib/home`), eksplorator kart (`src/lib/cards`); onboarding: `Shell` (kroki + pasek prototypu), `GpuCombobox` (wzorzec ARIA 1.2 combobox), `ScanCommands` (zakładki OS, komenda z bieżącym adresem, podgląd kodu skryptu), `CopyButton` (`src/lib/onboarding`).

## 8. Wzorce uczciwości

| Element | Kiedy | Wygląd |
|---|---|---|
| **ZMIERZONE** (`badge--measured`) | liczba z rejestru `measurements.ts` | kość (fakt, nie prędkość) |
| **SZACUNEK** (`badge--estimate`) | estymator, różne skrypty pomiarowe, ceny-hipotezy | amber, słupek kreskowany z przedziałem |
| **WKRÓTCE** (`badge--soon`) | nic nie zmierzono | przerywana ramka, bez liczby |
| **POMIAR W TOKU** (`badge--progress`) | kampania trwa | blada stal (`--info`) |
| **PROTOTYP** (`badge--prototype`, `notice--prototype`) | logowanie, pobieranie, lista oczekujących | blada stal w paski |
| **PROJEKT DO WERYFIKACJI PRAWNIKA** (`notice--warn`) | dokumenty prawne | amber na górze każdego dokumentu |
| Przypis `.source` | przy każdej liczbie | `plik:linia`, skrypt, data |

Reguły treści: rejestr liczb `landing/src/lib/data/measurements.ts` (każdy wpis: wartość, skrypt, metoda, plik:linia); bez porównań z Ollamą / LM Studio, dopóki nie zmierzymy ich tym samym skryptem; zakresy zamiast fałszywej precyzji; „brak istotnej zmiany” zamiast naciąganego zysku; wyniki kart NVIDIA tylko z zestawienia `KERNEL/product/BENCHMARKI-NVIDIA-2026-10-16.md` (generowane do `cards.json`, sprawdzane z `scorecard.json`; rozbieżności pokazujemy, `SHEET.checks`). **Nigdy „bit w bit identyczne z upstream”**: zwykły greedy naszego silnika różni się od upstreamu (łatki 0001/0002/0013); jakość sprawdzamy KLD (na RTX 3060 w granicach szumu samego upstreamu). Hasło: „Ten sam model, ta sama jakość — zmierzone”, z linkiem do metodologii.

## 9. Język (PL / EN)

Słownik z raportu 06 §2.1.2: „Pisze: ~40 słów/s”, „Czyta: 50-stronicowy dokument w 8 s”, „Mózg: Mały / Średni / Duży”, kwantyzacja = „kompresja jak w JPG”, „Pasuje / Będzie wolno / Nie zmieści się”, spekulacja = „model zgaduje kilka słów naprzód i sprawdza je naraz”. Ton: rzeczowy, krótkie zdania, bez wykrzykników, liczby z jednostką. Polski jest językiem pierwszym, angielski pisany idiomatycznie (nie tłumaczenie słowo w słowo). Odmiana liczebników przez `plural()` (kategorie CLDR one / few / many).

## 10. Dostępność (WCAG 2.2 AA)

- Kontrast §3.3; fokus 2 px `--focus` (kość / czerń) z odstępem 2 px na wszystkim, co klikalne.
- Link „Przejdź do treści”, landmarki (`header`, `nav` z etykietą, `main`, `footer`), hierarchia nagłówków, `lang` na `<html>` per język i `hreflang` dla przełącznika.
- Formularze: etykiety, podpowiedzi przez `aria-describedby`, błędy tekstem i `aria-invalid`, fokus na pierwszym błędnym polu.
- Combobox GPU: wzorzec ARIA 1.2 (strzałki, Enter, Escape, `aria-activedescendant`). Zakładki skanu: strzałki, Home, End.
- Ruch: §6 (reduced motion, pauza). Baner cookies nie kradnie fokusu przy pierwszej wizycie; przyciski „Akceptuję” i „Odrzucam” mają równą wagę.
- Cele dotyku ≥ 24×24 px (2.5.8), bez przeciągania (2.5.7), bez CAPTCHA w logowaniu (3.3.8).

## 11. Wybór technologii strony: SvelteKit 2 + adapter-static (nie Astro)

1. **Jeden stos z produktem.** Czat bazuje na web UI z llama.cpp (`tools/ui`: SvelteKit 2.70 / Svelte 5), aplikacja desktop to Tauri 2 + Svelte. Strona używa tych samych wersji (`@sveltejs/kit` 2.70.2, `svelte` 5.56.1, `vite` 7.3.6, `adapter-static` 3.0.10 jak w `tools/ui/package.json`). Komponenty, tokeny i i18n przechodzą bez przepisywania; prototyp ekranów aplikacji żyje już w tym samym projekcie (`src/lib/desktop`).
2. **Statyczny wynik.** Każda strona jest prerenderowana do HTML (`trailingSlash = 'always'`, czyli `ścieżka/index.html`), działa z dowolnego hostingu statycznego w UE, bez serwera.
3. **Lekkość.** Svelte kompiluje do małego JS bez runtime'u wirtualnego DOM; interaktywne są tylko wyspy, które tego potrzebują (animacja, formularze, combobox). Astro dałoby podobny wynik na stronie, ale dodałoby drugi framework obok Svelte i nic nie wniosło dla onboardingu, który jest w całości interaktywny.
4. Bez Tailwinda: czyste CSS na tokenach (mniej zależności, ten sam plik tokenów działa w llama.cpp UI przez mapowanie w `llama-ui-theme.css`).

Budżet wydajności: Lighthouse mobile ≥ 85, LCP < 2,5 s, zero zewnętrznych zapytań, LCP = tekst nagłówka (bez obrazów); animujemy tylko `transform`/`opacity`, canvas/WebGL z limitem DPR 1,5 i pauzą poza ekranem (`REDESIGN.md` §5).

## 12. Czat (llama.cpp web UI) i aplikacja desktop

- `llama-ui-theme.css` mapuje nasze tokeny na zmienne shadcn używane przez `tools/ui/src/app.css` (`--background`, `--primary`, `--border`, `--ring`, `--chart-*`, `--sidebar-*` itd.) dla `:root` i `.dark`. Importujemy go po `app.css`; kod czatu zostaje upstreamowy, a nota MIT „© The ggml authors” zostaje w „O programie” i w NOTICE.
- Prototyp ekranów (kreator, Mój komputer, Wynik, Optymalizacja nocna, Modele, Dla programistów, Czat): `/[lang]/app/…`, komponenty w `landing/src/lib/desktop`. Te same tokeny; okno 1280×800, pasek boczny, pasek statusu jak w telemetrii.
- TUI: `app/tui/tui_demo.py` (makieta ANSI), z trybem `--plain` dla czytników ekranu. Jej paleta jest jeszcze z v1 (limonka); przy następnej zmianie TUI przejść na §3 (czerń `#050506`, kość, ciepło tylko dla t/s).

## 13. Mapa plików

```
app/design/
  tokens.css            zmienne: kolor, typografia, przestrzeń, promienie, ruch; ciemny + jasny
  components.css        klasy komponentów
  showcase.css          warstwa pokazowa (strona główna, eksplorator kart)
  REDESIGN.md           brief kreatywny v2 „Białe ciepło”
  llama-ui-theme.css    mapowanie tokenów na motyw llama.cpp web UI
  logo/                 mark.svg, mark-mono.svg, favicon.svg, lockup-dark.svg
  DESIGN.md             ten dokument
  APP-ARCHITECTURE.md   architektura aplikacji i onboardingu
app/landing/            SvelteKit (strona, onboarding, prototyp aplikacji)
app/scan/               skrypty skanu (Linux, macOS, Windows)
app/tui/                makieta TUI
app/screens/            zrzuty ekranu
```
