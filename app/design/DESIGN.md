# System projektowy

Stan: 2026-10-16. Źródło prawdy: `tokens.css` (zmienne) i `components.css` (klasy). Oba pliki importuje strona (`app/landing`), prototyp aplikacji desktop (`/[lang]/app/…`) i motyw czatu llama.cpp (`llama-ui-theme.css`). Nazwa produktu jest otwartą decyzją, patrz §2.

## 1. Idea

**Telemetria w nocy.** Produkt obiecuje jedną rzecz: ten sam model, szybciej, i to udowodnione. Wizualnie mówimy więc językiem pomiaru, nie magii:

- **ciemny, prawie czarny grafit** zamiast fioletowych gradientów „AI”;
- **jeden kolor sygnałowy**: volt (limonkowy `#C8FF3D`) znaczy „po”, „nasze”, „działa”; nigdy dekoracja;
- **mono do liczb**: wartości w Geist Mono z cyframi tabelarycznymi, jednostka mniejsza i przygaszona, jak na wyświetlaczu;
- **ramy HUD i podziałki**: narożniki kart, linie siatki 32 px, kreskowane separatory; to wyrafinowana wersja kart z REACTOR-a (`~/KERNEL/monitor`);
- **uczciwość jako element UI**: każda liczba ma znacznik statusu (zmierzone / szacunek / wkrótce) i przypis ze źródłem. To nie jest dopisek prawny, tylko część kompozycji (§8).

Czego unikamy: gradientów fioletowo-niebieskich, „świecących mózgów”, glassmorphismu, ilustracji 3D, wykrzykników marketingowych, mnożników „×2” bez pomiaru tym samym narzędziem.

Inspiracje: wskaźniki telemetryczne z motorsportu (shift lights, delta time), nakładki benchmarków GPU, nasz REACTOR. Wnioski UX z konkurencji (raport 01 §2, raport 06 §2.1.1): etykiety „Pasuje / Będzie wolno / Nie zmieści się” jak w Janie, jedna rekomendacja na start jak w LM Studio, „skan → szybciej” jak NVIDIA App, ale z tym, czego nikt nie pokazuje: przed → po z metodą (MTPLX pokazuje przed → po, ale tylko na Macu i dla jednej gałki).

## 2. Marka

### 2.1 Nazwa (otwarta decyzja)
Jedna stała: `app/landing/src/lib/brand.ts` → `BRAND.name` (dziś „Podkręt”), `BRAND.ascii` (`podkret`, do plików i CLI), `BRAND.cli`. Prototyp desktop, dokumenty prawne, meta tagi i TUI (`app/tui/tui_demo.py`, stała `BRAND` na górze pliku) biorą nazwę stamtąd. Kandydaci z raportu 06 §3.1: Podkręt, Nocna Zmiana / NightShift, Turbina, Rozpęd, Tuned. Przed wyborem: EUIPO (kl. 9 i 42), domeny, kolizje z „llama”, „NVIDIA”, „AMD”.

### 2.2 Znak „Tacho”
Plik: `logo/mark.svg` (kolor), `logo/mark-mono.svg` (jeden kolor, `currentColor`), `logo/favicon.svg` (na ciemnym kwadracie), `logo/lockup-dark.svg` (znak + nazwa jako żywy tekst).

Konstrukcja na siatce 32×32: łuk tarczy 270° (r = 11, kreska 3, zaokrąglone końce) w kolorze tekstu z kryciem 38%; ostatnie 75° łuku i wskazówka w kolorze volt, wskazówka „wbita” w czerwone pole; piasta r = 2,6. Znak nie zależy od nazwy, więc przeżyje jej zmianę.

Zasady: minimalny rozmiar 16 px (favicon czytelny), pole ochronne = promień piasty × 2 wokół znaku, na jasnym tle część „gorąca” przechodzi na `--accent-ink` (#3B6E00), bo czysty volt na bieli nie ma kontrastu. Wordmark to tekst w Geist 600, tracking −0,03 em; finalny wordmark (ścieżki SVG) dopiero po wyborze nazwy.

## 3. Kolor

### 3.1 Paleta bazowa
| Token | Ciemny | Jasny | Rola |
|---|---|---|---|
| `--bg-0` | `#07080D` | `#F5F6F9` | tło strony |
| `--bg-1` | `#0C0E16` | `#ECEEF3` | pasy sekcji, pola formularzy |
| `--bg-2` | `#121522` | `#FFFFFF` | karty |
| `--bg-3` | `#1A1E2F` | `#E8EBF1` | hover, wstawki |
| `--line` | `#232840` | `#DDE1EA` | linie 1 px (dekoracyjne) |
| `--line-strong` | `#5F6890` | `#7A8399` | obramowania kontrolek (≥ 3:1) |
| `--text-hi` / `--text` / `--text-mute` | `#F2F5FB` / `#C9D0E2` / `#939CB7` | `#0A0C12` / `#2A3042` / `#505971` | tekst |

### 3.2 Kolory znaczeniowe
| Token | Znaczenie | Ciemny (wypełnienie / tekst) | Jasny (tekst) |
|---|---|---|---|
| `--accent` / `--accent-ink` | „po”, nasz silnik, główne CTA, zmierzone | `#C8FF3D` | `#3B6E00` |
| `--before` | „przed”, punkt startowy; celowo cichy | `#7F89A6` | `#6A7390` |
| `--info` (ion) | linki, fokus, „pomiar w toku”, prototyp | `#3DD6FF` | `#006A8C` |
| `--warn` (amber) | szacunek, ostrzeżenie, projekt prawny | `#FFB23E` | `#8A5100` |
| `--danger` (heat) | błąd, „nie zmieści się”, temperatura | `#FF4D8D` / `#FF7AA8` | `#B0174F` |
| `--ok` | md5 równe, „pasuje”, gotowe | `#5BE49B` | `#1F7A46` |

Zasada: kolor nigdy nie jest jedynym nośnikiem informacji (WCAG 1.4.1). Każda plakietka ma tekst, każdy słupek ma liczbę.

### 3.3 Kontrast (policzony, WCAG 2.x)
Wyliczone skryptem z wartości w `tokens.css`:

| Para | Ciemny | Jasny |
|---|---|---|
| `--text-hi` na `--bg-0` | 18.3:1 | 18.1:1 |
| `--text` na `--bg-0` | 13.0:1 | 12.1:1 |
| `--text` na `--bg-2` | 11.8:1 | 13.1:1 |
| `--text-mute` na `--bg-0` | 7.3:1 | 6.5:1 |
| `--text-mute` na `--bg-2` | 6.6:1 | 7.0:1 |
| `--text-mute` na `--bg-3` | 6.0:1 | 5.8:1 |
| `--accent-ink` na `--bg-0` | 17.0:1 | 5.7:1 |
| `--accent-ink` na `--bg-2` | 15.4:1 | 6.1:1 |
| `--on-accent` na `--accent` | 16.6:1 | 16.6:1 |
| `--info-ink` na `--bg-0` | 11.7:1 | 5.6:1 |
| `--info-ink` na `--bg-2` | 10.6:1 | 6.1:1 |
| `--warn-ink` na `--bg-0` | 11.1:1 | 6.0:1 |
| `--warn-ink` na `--bg-2` | 10.1:1 | 6.4:1 |
| `--danger-ink` na `--bg-0` | 8.2:1 | 6.3:1 |
| `--danger-ink` na `--bg-2` | 7.4:1 | 6.8:1 |
| `--ok-ink` na `--bg-0` | 12.4:1 | 4.9:1 |
| `--ok-ink` na `--bg-2` | 11.3:1 | 5.3:1 |
| `--before` na `--bg-2` | 5.2:1 | 4.7:1 |
| `--line-strong` na `--bg-2` | 3.3:1 | 3.8:1 |
| `--line-strong` na `--bg-1` | 3.5:1 | 3.3:1 |
| `--focus` na `--bg-0` | 11.7:1 | 5.6:1 |
| `--focus` na `--bg-2` | 10.6:1 | 6.1:1 |

Cały tekst ≥ 4.5:1, kontrolki i fokus ≥ 3:1 w obu motywach.

### 3.4 Motywy
Ciemny jest domyślny (tożsamość). Jasny ma pełną jakość, nie jest „trybem awaryjnym”. Wybór: `html[data-theme]` ustawiany przed pierwszym malowaniem (skrypt w `app.html`): zapisany wybór użytkownika, a bez niego `prefers-color-scheme`. Zapis w `localStorage` tylko po kliknięciu przełącznika (żądanie użytkownika, wyjątek z art. 5(3) ePrivacy).

## 4. Typografia

- **Geist** (UI, nagłówki) i **Geist Mono** (liczby, kod, etykiety), licencja OFL 1.1, **hostowane lokalnie** (`static/fonts`, podzbiory latin + latin-ext z polskimi znakami, razem ok. 83 KB woff2, fonty zmienne). Zero zapytań do Google Fonts (RODO: wyrok LG München 3 O 17493/20 dotyczył właśnie Google Fonts).
- Skala 1,25, płynna u góry: `--fs-2xs` 11 px (tylko overline mono, wersaliki, tracking 0,14 em), `xs` 12, `sm` 14, `base` 16, `md` 18, `lg` 22, `xl` 28, `2xl` 30–40, `3xl` 36–56, `display` 42–80 px.
- Nagłówki: 600, tracking −0,02 do −0,038 em, `text-wrap: balance`. Akapity: `text-wrap: pretty`, interlinia 1,6, szerokość ≤ 44 rem.
- **Liczby**: zawsze `.num` (Geist Mono, `tabular-nums slashed-zero`), jednostka w `.stat__unit` (45%, przygaszona). Separator dziesiętny wg języka: „109,0 t/s” po polsku, „109.0 t/s” po angielsku (`num()` w `i18n.ts`).
- **Overline** (`.overline`): mono, wersaliki, kreska przed tekstem; nazwa sekcji jak etykieta kanału na wyświetlaczu.

## 5. Przestrzeń, siatka, kształt

- Siatka 4 px: `--sp-1` 4 px … `--sp-24` 96 px; odstęp sekcji `--section-y` 64–120 px; kontener 72 rem, wąski 46 rem; margines boczny 16–32 px.
- Promienie małe i precyzyjne: `--r-xs` 3, `sm` 6 (przyciski, pola), `md` 10, `lg` 14 (karty), `xl` 20. Pigułki tylko dla chipów i kroków.
- Elewacja minimalna: `--shadow-1` (wewnętrzna krawędź), `--shadow-2` (pływające panele). Akcent świetlny `--accent-glow` tylko dla głównego CTA i kart „zmierzone”.
- Tło `.bg-grid` (siatka 32 px, 5% krycia) tylko w hero.

## 6. Ruch

| Token | Czas | Użycie |
|---|---|---|
| `--dur-1` | 110 ms | hover, wciśnięcie |
| `--dur-2` | 180 ms | przełączniki, strzałki |
| `--dur-3` | 320 ms | panele, pojawianie się |
| `--dur-4` | 640 ms | wypełnianie słupków |

Krzywe: `--ease-out` (0.16, 1, 0.3, 1) dla wejść, `--ease-in-out` dla pętli. Zasady:

1. **Ruch niesie dane.** Animujemy tylko to, co coś mierzy: strumień tekstu w tempie t/s, słupki, wskaźnik postępu. Żadnych dekoracyjnych paralaks.
2. **`prefers-reduced-motion: reduce`** ustawia wszystkie `--dur-*` na 0,01 ms; animacja hero startuje wtedy w stanie końcowym (oba teksty gotowe, czasy ukończenia widoczne) i rusza tylko po kliknięciu „Odtwórz”.
3. **Pauza (WCAG 2.2.2).** Każdy ruch dłuższy niż 5 s ma widoczny przycisk pauzy; animacja zatrzymuje się poza ekranem (IntersectionObserver) i w ukrytej karcie.

**Animacja hero („pojedynek”).** Dwa panele piszą ten sam tekst. Tempo = zmierzone tokeny/s (38,8 upstream bez spekulacji, 109,0 nasz silnik z MTP, RX 7900 XTX, Qwen3.8-27B), przeliczone na znaki przez liczbę tokenów tekstu (2,69 tok/słowo PL, 1,17 EN; raport 06 §2.1.2). Licznik czasu, odczyt t/s i słów/s, słupek postępu; pętla z 2,8 s przerwy. Podpis pod animacją mówi: karta, model, źródła, że to odtworzenie tempa (nie nagranie), że liczby są z różnych skryptów i że spekulacja może zmienić tekst. Dla czytników ekranu jest tekstowe podsumowanie, a sama animacja jest `aria-hidden`.

## 7. Komponenty (`components.css`)

| Klasa | Opis |
|---|---|
| `.btn` `--primary` / `--secondary` / `--ghost`, `--sm` / `--lg` / `--block` | wysokość 44 px (cel dotyku ≥ 24 px, WCAG 2.5.8), primary = volt z ciemnym tekstem i poświatą |
| `.icon-btn` | 40×40, zawsze z `aria-label` |
| `.card`, `.card--inset`, `.card--interactive` | powierzchnie |
| `.hud` | rama z narożnikami (kolor `--hud-c`) |
| `.badge` + `--measured` / `--estimate` / `--soon` / `--progress` / `--prototype` / `--draft` / `--ok` / `--danger` | statusy uczciwości (§8) |
| `.notice` + `--info` / `--warn` / `--danger` / `--ok` / `--prototype` | komunikaty z ikoną w kolumnie |
| `.field`, `.label`, `.hint`, `.error-text`, `.input`, `.select`, `.textarea`, `.check`, `.segmented`, `.switch` | formularze; błędy tekstem + `aria-invalid` + `aria-describedby` |
| `.table-wrap` + `.table` | tabele danych, nagłówki mono, liczby do prawej |
| `.stat` (`__value`, `__unit`, `__label`) | duże odczyty |
| `.bar` (`--v`), `--before`, `--range`, `--tall` | słupki przed → po; `--range` (kreskowany) = szacunek z przedziałem |
| `.codeblock` (`__head`, `pre`, `.prompt`) | komendy do skopiowania |
| `.tabs` (`role=tab`) | zakładki ze strzałkami |
| `.disclosure` | FAQ, „Jak to policzyliśmy” (`details/summary`) |
| `.source` | przypis źródła: mono, 12 px |
| `.overline`, `.ticks`, `.bg-grid` | elementy telemetryczne |

Komponenty Svelte strony: `Header`, `Footer`, `Logo`, `ThemeToggle`, `CookieBanner`, `SpeedDuel` (hero), `Results`, `Waitlist` (`src/lib/site`); onboarding: `Shell` (kroki + pasek prototypu), `GpuCombobox` (wzorzec ARIA 1.2 combobox), `ScanCommands` (zakładki OS, komenda z bieżącym adresem, podgląd kodu skryptu), `CopyButton` (`src/lib/onboarding`).

## 8. Wzorce uczciwości

| Element | Kiedy | Wygląd |
|---|---|---|
| **ZMIERZONE** (`badge--measured`) | liczba z rejestru `measurements.ts` | volt |
| **SZACUNEK** (`badge--estimate`) | estymator, różne skrypty pomiarowe, ceny-hipotezy | amber, słupek kreskowany z przedziałem |
| **WKRÓTCE** (`badge--soon`) | nic nie zmierzono | przerywana ramka, bez liczby |
| **POMIAR W TOKU** (`badge--progress`) | kampania trwa | ion |
| **PROTOTYP** (`badge--prototype`, `notice--prototype`) | logowanie, pobieranie, lista oczekujących | ion w paski |
| **PROJEKT DO WERYFIKACJI PRAWNIKA** (`notice--warn`) | dokumenty prawne | amber na górze każdego dokumentu |
| Przypis `.source` | przy każdej liczbie | `plik:linia`, skrypt, data |

Reguły treści: rejestr liczb `landing/src/lib/data/measurements.ts` (każdy wpis: wartość, skrypt, metoda, plik:linia); bez porównań z Ollamą / LM Studio, dopóki nie zmierzymy ich tym samym skryptem; zakresy zamiast fałszywej precyzji; „brak istotnej zmiany” zamiast naciąganego zysku; wyniki z chmury pokazywane tylko z gotowego `scorecard.json`, razem z jego statusem md5 (dziś RTX 3090 ma „DIFF-BUILD”, co strona mówi wprost).

## 9. Język (PL / EN)

Słownik z raportu 06 §2.1.2: „Pisze: ~40 słów/s”, „Czyta: 50-stronicowy dokument w 8 s”, „Mózg: Mały / Średni / Duży”, kwantyzacja = „kompresja jak w JPG”, „Pasuje / Będzie wolno / Nie zmieści się”, spekulacja = „model zgaduje kilka słów naprzód i sprawdza je naraz”. Ton: rzeczowy, krótkie zdania, bez wykrzykników, liczby z jednostką. Polski jest językiem pierwszym, angielski pisany idiomatycznie (nie tłumaczenie słowo w słowo). Odmiana liczebników przez `plural()` (kategorie CLDR one / few / many).

## 10. Dostępność (WCAG 2.2 AA)

- Kontrast §3.3; fokus 2 px `--focus` z odstępem 2 px na wszystkim, co klikalne.
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

Budżet wydajności: HTML strony głównej ≤ 60 KB gzip, JS ≤ 60 KB gzip na pierwsze wejście, fonty ≤ 90 KB, zero zewnętrznych zapytań, LCP = tekst nagłówka (bez obrazów).

## 12. Czat (llama.cpp web UI) i aplikacja desktop

- `llama-ui-theme.css` mapuje nasze tokeny na zmienne shadcn używane przez `tools/ui/src/app.css` (`--background`, `--primary`, `--border`, `--ring`, `--chart-*`, `--sidebar-*` itd.) dla `:root` i `.dark`. Importujemy go po `app.css`; kod czatu zostaje upstreamowy, a nota MIT „© The ggml authors” zostaje w „O programie” i w NOTICE.
- Prototyp ekranów (kreator, Mój komputer, Wynik, Optymalizacja nocna, Modele, Dla programistów, Czat): `/[lang]/app/…`, komponenty w `landing/src/lib/desktop`. Te same tokeny; okno 1280×800, pasek boczny, pasek statusu jak w telemetrii.
- TUI: `app/tui/tui_demo.py` (makieta ANSI w stylu REACTOR, paleta z §3: tło `#07080D`, karta `#121522`, volt, ion, amber, heat), z trybem `--plain` dla czytników ekranu.

## 13. Mapa plików

```
app/design/
  tokens.css            zmienne: kolor, typografia, przestrzeń, promienie, ruch; ciemny + jasny
  components.css        klasy komponentów
  llama-ui-theme.css    mapowanie tokenów na motyw llama.cpp web UI
  logo/                 mark.svg, mark-mono.svg, favicon.svg, lockup-dark.svg
  DESIGN.md             ten dokument
  APP-ARCHITECTURE.md   architektura aplikacji i onboardingu
app/landing/            SvelteKit (strona, onboarding, prototyp aplikacji)
app/scan/               skrypty skanu (Linux, macOS, Windows)
app/tui/                makieta TUI
app/screens/            zrzuty ekranu
```
