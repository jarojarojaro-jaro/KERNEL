# 06: Produkt, UX, zaufanie, prawo, dystrybucja, licencje, biznes i go-to-market

**Data:** 2026-10-15. **Autor:** R6Product (research only, bez GPU, bez zmian w kodzie).
**Kontekst:** „Aplikacja” (nazwa robocza). Skanuje sprzęt, poleca i uruchamia model, mierzy baseline, a potem w nocy optymalizuje go, metodą z `~/KERNEL/qwen-opt` (bitowo identyczne wyjście, A/B, KLD gate).

**Konwencje:**
- `[INFERENCE]` oznacza wniosek własny, niezweryfikowany źródłem.
- `[STALE?]` oznacza źródło starsze niż 12 miesięcy.
- Ceny podaję w walucie źródła.
- Każde twierdzenie faktyczne ma link w tekście albo w sekcji „Źródła”.

---

## 1. TL;DR

1. **Rynek się konsoliduje i dostaje kapitał.**
   - Ollama zebrała 65 M$ w Series B (lipiec 2026; łącznie 88 M$, 8,9 mln developerów miesięcznie).
   - ggml.ai (llama.cpp) dołączyło w lutym 2026 do Hugging Face.
   - NVIDIA ogłosiła 3 września 2026 przejęcie Hugging Face za 12,93 mld $.
   - LM Studio jest darmowe, także do pracy, i zarabia na chmurze: Bionic+ za 20 $/mies., Pro za 100 $/mies.
   - Nikt z dużych graczy nie sprzedaje „lokalnego przyspieszenia twojej konkretnej karty”. To nasza nisza, ale wąska i łatwa do skopiowania. Obrona to dane (katalog profili per GPU×model×sterownik) i zaufanie (bitowa identyczność), nie same kernele.
2. **UX: mówić „słowa na sekundę” i „czas do pierwszego słowa”, nie „t/s”.**
   - Człowiek czyta w ciszy około 238 słów/min, czyli około 4 słów/s.
   - Tokenizer Qwen3 zużywa około 1,17 tokenu na słowo angielskie i 2,69 tokenu na słowo polskie. 109 t/s to więc około 90 słów/s po angielsku i tylko około 40 słów/s po polsku.
   - Powyżej tempa czytania wartość widać w **czasie ukończenia zadania**: długiej odpowiedzi, kodu, „myślenia” modelu, dokumentu. Tak należy pokazywać „przed → po”.
3. **Uczciwe „przed → po” to nasza przewaga zaufania.**
   - Ten sam model i ta sama kwantyzacja; ten sam zestaw promptów użytkownika; naprzemienne A/B; mediana i rozrzut.
   - Osobne liczby dla czatu, kodu i długiego dokumentu.
   - Plakietka „te same odpowiedzi, bit w bit”, przycisk „Cofnij”.
   - Optymalizacje bramkowane KLD tylko jako opt-in.
4. **Nocna optymalizacja wymaga state machine z checkpointami.**
   - Pauza, gdy użytkownik dotknie myszy lub uruchomi grę; stop na baterii; limity temperatury i hałasu.
   - Na Windows trzeba obejść watchdog GPU (TDR): domyślnie 2 s na kernel, a 5 TDR w 60 s kończy się crashem systemu.
   - Wzorzec referencyjny: NVIDIA App automatic tuning trwa 10–20 min, prosi o bezczynność i przerywa się przy obciążeniu.
5. **AI Act realnie nas dotyczy jako *providera systemu AI* (aplikacji czatu), nie jako providera GPAI.**
   - Art. 50(1) wymaga widocznej informacji „rozmawiasz z AI”.
   - Art. 50(2) wymaga oznaczania syntetycznego tekstu w formie machine-readable. Według finalnego Code of Practice z 2026 dotyczy to tekstu powyżej 200 tokenów, a dla free-form text wystarcza jedna technika (watermark).
   - Grace do **2 grudnia 2026** dotyczy tylko systemów już na rynku przed 2 sierpnia 2026, więc nowy produkt podlega temu od razu.
   - To najważniejsze otwarte pytanie prawne: watermark w samplerze kłóci się z marketingiem „bitowo identyczne z llama.cpp”.
6. **Prywatność:**
   - Skan sprzętu lokalnie, bez numerów seryjnych, hostname, logów i listy plików.
   - Wysyłka czegokolwiek tylko opt-in (art. 5(3) ePrivacy, w Polsce art. 399 PKE), z podglądem dokładnego JSON-a. Adres IP to dana osobowa.
   - Digital Omnibus dla RODO i ePrivacy jest wciąż w negocjacjach (stan z 11.09.2026).
7. **Dystrybucja:**
   - EV certificate już nie omija SmartScreen (od 2024).
   - **Azure Artifact Signing** kosztuje około 9,99 $/mies. i jest dostępny dla *organizacji* z UE, a dla osób fizycznych tylko w US i CA. Potrzebujemy spółki.
   - Microsoft Store: darmowa rejestracja, aplikacje Win32 dozwolone, instalacja ze Store bez SmartScreen.
   - macOS: 99 $/rok i notaryzacja. Homebrew od 1 września 2026 odrzuca niepodpisane cask.
   - Mac App Store zabrania pobierania kodu (2.5.2). Profile optymalizacji muszą więc być **danymi**, nie binarkami.
8. **Licencje modeli: większość topowych open-weights to Apache 2.0** (Qwen3.8-27B, Gemma 4, gpt-oss, Mistral Small 4, Bielik v3). Pułapki:
   - **LFM** (próg 10 M$ przychodu dotyczy *każdego* komercyjnego użytkownika, także naszych klientów B2B);
   - **Qwen Community License** (Qwen3.8-Flash-Next) wymaga osobnej licencji dla produktów „AI Work Assistant” i MaaS;
   - **Llama 4**: brak praw dla firm z siedzibą w UE dla modeli multimodalnych, a wszystkie Llama 4 są multimodalne;
   - **Gemma ≤3**: flow-down use restrictions i plik Notice.
9. **Model biznesowy (hipoteza):**
   - Darmowa aplikacja z katalogiem gotowych profili, bitowo bezpiecznych.
   - Płatny „Turbo”: osobista nocna optymalizacja plus ciągłe re-tuningi, około 39 €/rok lub 79 € lifetime early-bird.
   - B2B/OEM: profile per SKU dla integratorów (x-kom, Komputronik itd.).
   - Enterprise tuning-as-a-service: od 5 k€ za projekt; kotwica cenowa: UL Procyon od 5000 $/rok.
   - Open core: łatki silnika upstream (MIT), zamknięte: orkiestrator tuningu, harness weryfikacji, katalog profili.
10. **GTM:**
    - Najpierw wiarygodność: powtarzalne benchmarki 7900 XTX na r/LocalLLaMA (849 tys. członków, reguła 1/10 i jawna afiliacja), LocalMaxxing i LocalScore. Potem Show HN (bez rejestracji!).
    - **Wyraźny credit dla llama.cpp**: post „Ollama doesn't need…” zebrał 648 pkt na HN.
    - Polska: polski język ma „podatek tokenizera” około 2×, więc przyspieszenie liczy się bardziej. Współpraca z SpeakLeash (Bielik ma już drafter DFlash); kryzys cen RAM i GPU w 2026 każe „wycisnąć istniejący sprzęt”.

---

## 2. Ustalenia

### 2.1 UX dla nietechnicznych użytkowników

#### 2.1.1 Jak robią to inni (onboarding, rekomendacja, wydajność)

| Produkt | Co robi na starcie | Co warto skopiować | Czego unikać |
|---|---|---|---|
| **LM Studio** | Przy pierwszym uruchomieniu proponuje jeden model (np. `gemma-4-e4b`, 6,33 GB Q4_K_M). Etykiety: „Full GPU offload possible”, „partial GPU offload”, „Likely too large”. Guardrails ostrzegają przed OOM i pozwalają „Load anyway” ([techjacksolutions](https://techjacksolutions.com/ai-tools/lm-studio/how-to-use-lm-studio/), [LM Studio 0.3.27](https://lmstudio.ai/blog/lmstudio-v0.3.27), [HF forum](https://discuss.huggingface.co/t/ram-usage-model-streaming-or-alternatives/173719)) | Jedna rekomendacja na start; estymacja pamięci na żywo przy zmianie kontekstu | Żargon („GPU offload”, „Q4_K_M”) widoczny dla laika |
| **Ollama app** (GUI od 30.07.2025) | Okno czatu, wybór modelu; model pobiera się przy pierwszej wiadomości ([Ollama blog](https://ollama.com/blog/new-app) `[STALE?]`, [Windows Central](https://www.windowscentral.com/artificial-intelligence/ollamas-new-app-makes-using-local-ai-llms-on-your-windows-11-pc-a-breeze-no-more-need-to-chat-in-the-terminal) `[STALE?]`) | „Zero konfiguracji”, pliki i obrazy drag & drop | Niejawne pobieranie wielu GB; użytkownicy narzekali na brak wyłączenia auto-update i na zamknięty magazyn blobów ([HN 47788385](https://news.ycombinator.com/item?id=47788385)) |
| **Jan** (0.8.5, 8.10.2026) | Kreator: welcome → engine → pierwszy model → **strona zgody**. Kolorowa etykieta „Fits / May be slow / Won't fit” i tag „Recommended”. Silnik llama.cpp **wbudowany w instalator**, bez pobierania backendu przy starcie ([freedom.tech Jan 0.8.5](https://freedom.tech/posts/2026-10-08-jan-0-8-5/), [Jan docs: Manage models](https://www.jan.ai/docs/desktop/manage-models)) | Etykieta „pasuje / wolno / nie zmieści się”; zgoda jako krok onboardingu; bundling silnika | Rezygnacja z Intel Mac pokazuje koszt wsparcia wielu platform |
| **Msty Studio** | Czat lokalny i chmurowy, wiele trybów; free plus Aurum ([Msty pricing](https://msty.ai/pricing/)) | Jasny podział free i płatne | Przeładowanie funkcjami: nasz target to laik |
| **Raycast AI: Local Models** (Pro) | Przycisk „Install Ollama app”, pole „Install Ollama Model” z nazwą (np. `qwen3.8:latest`), „Sync Models”; Raycast sam startuje serwer Ollama ([manual.raycast.com](https://manual.raycast.com/ai/local-models)) | Lokalny model jako „kolejny model w pickerze”; automatyczny start serwera | Wymaga znajomości nazwy modelu (zła ścieżka dla laika) |
| **NVIDIA App: Automatic Tuning** | Skan GPU 10–20 min, prośba o bezczynność, potem automatycznie bezpieczny OC i comiesięczny re-scan ([NVIDIA](https://www.nvidia.com/en-us/geforce/news/nvidia-app-download-and-features/) `[STALE?]`, [TechPowerUp](https://www.techpowerup.com/review/nvidia-app-v1-0/3.html) `[STALE?]`). Tuning przerywa się przy obciążeniu (gra) ([Wccftech](https://wccftech.com/nvidia-app-1-click-auto-gpu-tuning-120-fps-av1-recording-g-assist-dynamically-tune-gpu-record-statistics-change-game-settings/) `[STALE?]`) | **Najbliższy wzorzec dla nocnej optymalizacji**: jeden przycisk, szacowany czas, automatyczne wycofanie, okresowy re-check | Brak pokazania zysku: użytkownik nie widzi „przed → po” |
| **AMD Adrenalin 26.1.1: AI Bundle** | Opcjonalny instalator „1 klik”: PyTorch, ComfyUI, Ollama, LM Studio, Amuse; RX 7700+ / RX 9000 / Ryzen AI ([TweakTown](https://www.tweaktown.com/news/109821/amds-adrenalin-edition-software-for-radeon-now-includes-an-optional-ai-bundle/index.html), [Wccftech](https://wccftech.com/amd-rolls-out-adrenalin-edition-26-1-1-introducing-the-ai-bundle-and-support-for-ryzen-ai-400-series/)) | **Kanał dystrybucji**: AMD już dołącza LM Studio i Ollama do sterownika. To cel partnerski dla nas | Bundle to tylko instalator, bez strojenia |
| **Strata** (Qwen3.8-Flash-Next) | README dla laika: „A token is about ¾ of a word… 60 tokens per second is faster than you can read”. Dwie kolumny: „Writes answers” i „Reads your prompt”. Ostrzeżenie „PC może nie odpowiadać 1–3 min przy starcie”. Wznawiany download ([GitHub Strata](https://github.com/niko1221/strata)) | Język: „pisze odpowiedzi” vs „czyta twój prompt”; uczciwe ostrzeżenia | .bat i ZIP z GitHuba to nie produkt konsumencki |

**Wnioski UX:**
- Onboarding powinien mieć 4 kroki, a nie 10.
- Pierwsza rozmowa ma być możliwa w mniej niż 10 minut na typowym łączu, z jasnym czasem pobierania. To już reguła Apple 4.2.3(ii): ujawnić rozmiar i zapytać przed pobraniem ([App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)).
- Wzorzec Jana (bundling silnika i zgoda w kreatorze) jest najbardziej dojrzały.

#### 2.1.2 Jak tłumaczyć t/s, modele i kwantyzację

**Fakty do komunikatów:**
- Średnie ciche czytanie dorosłych po angielsku to **238 słów/min** (non-fiction), czyli około 4 słowa/s ([Brysbaert 2019, meta-analiza 190 badań](https://www.semanticscholar.org/paper/How-many-words-do-we-read-per-minute-A-review-and-Brysbaert/35bf5854514ee63095a6a3dc4a7bdaa2eb18929f) `[STALE?]`, ale to stała fizjologiczna).
- **Tokeny na słowo:**
  - Qwen3: 1,17 (EN) i 2,69 (PL); Llama 3.2: 1,17 (EN) i 2,81 (PL) ([arXiv 2604.10799, Bielik v3 tokenizer](https://arxiv.org/html/2604.10799v1));
  - średnio dla polskiego 2,25 ([arXiv 2605.24718, Tokenizer Tax 24 EU languages](https://arxiv.org/html/2605.24718));
  - tokenizer APT4 Bielika v3 obniża polski z 3,22 do 1,62 ([Dawidek](https://elzbietadawidek.substack.com/p/the-source-of-a-polish-tokenizer)).
- **Progi responsywności** ([Nielsen/NN/g](https://www.nngroup.com/articles/response-times-3-important-limits/)):
  - 0,1 s odczuwa się jako natychmiast;
  - 1 s nie przerywa toku myśli;
  - 10 s to limit uwagi; powyżej trzeba pokazać pasek procentowy i szacunek czasu.

**Przelicznik dla UI** (`[INFERENCE]` co do tokenizera Qwen3.8: zakładam, że jest taki sam jak w Qwen3):

| Szybkość silnika | EN (1,17 tok/słowo) | PL, tokenizer Qwen3 (2,69) | PL, Bielik APT4 (1,62) | Vs czytanie (4 słowa/s) |
|---|---|---|---|---|
| 40 t/s (stock, wg briefu) | 34 słowa/s | 15 słów/s | 25 słów/s | 4–8× szybciej niż czytasz |
| 109 t/s (nasz Qwen3.8-27B) | 93 słowa/s | 41 słów/s | 67 słów/s | 10–23× |
| 294 t/s (LFM2.5-24B-A2B) | 251 słów/s | 109 słów/s | – | 27–63× |

**Konsekwencja:** powyżej około 15–20 słów/s użytkownik **czytając** nie odczuje różnicy. Odczuje za to:
- **czas do pierwszego słowa** (TTFT, zwłaszcza z długim kontekstem i plikami);
- **czas ukończenia** długiej odpowiedzi, kodu i podsumowania dokumentu;
- **czas „myślenia”** modeli reasoning: tysiące ukrytych tokenów, gdzie 2× t/s to 2× krótsze czekanie;
- **czas agentów** (wiele wywołań).

`[INFERENCE]`

**Proponowany słownik w UI (PL / EN):**

| Pojęcie | Tekst w UI (PL) | Tekst w UI (EN) | Szczegóły dla ciekawych |
|---|---|---|---|
| decode t/s | „Pisze: ~40 słów/s (po polsku)” | „Writes: ~90 words/s” | „Technicznie: 109 tokenów/s; token ≈ ¾ słowa po angielsku, ≈ ⅓–½ słowa po polsku” |
| prefill t/s | „Czyta: 50-stronicowy dokument w 8 s” | „Reads a 50-page doc in 8 s” | tokeny/s prefill |
| TTFT | „Zaczyna odpowiadać po 0,4 s” | „Starts answering in 0.4 s” | ms |
| model | „Mózg”: „Mały (szybki) / Średni / Duży (mądrzejszy)” | „Small / Medium / Large” | liczba parametrów |
| kwantyzacja | „Kompresja jak w JPG: mniejsza = szybciej i lżej, minimalnie słabsza jakość” | „Like JPEG quality” | Q4_K_M itd. |
| VRAM fit | „Pasuje / Będzie wolno / Nie zmieści się” (jak Jan) | „Fits / May be slow / Won't fit” | GB |
| MTP/spekulacja | „Model zgaduje kilka słów naprzód i sprawdza je naraz” | „Guesses ahead, checks in one go” | acceptance rate |

#### 2.1.3 Uczciwe przedstawianie „przed → po”

**Problem:** speculative decoding (MTP, DFlash) daje zmienne przyspieszenie zależne od treści: kod i powtarzalny tekst przyspieszają bardziej niż proza. Z kolei prefill i decode skalują się inaczej przy długim kontekście. Nasze własne liczby rozjeżdżają się: Qwen3.8-27B ma 109 t/s na krótkich promptach i 101 t/s przy 94k kontekstu ([`~/KERNEL/README.md`](../../README.md)). Prawo konsumenckie UE zakazuje wprowadzających w błąd twierdzeń o cechach produktu, w tym o wynikach testów ([Dyrektywa 2005/29/WE, UCPD, art. 6](https://eur-lex.europa.eu/eli/dir/2005/29/oj)), więc „2× szybciej” musi być udowadnialne.

**Protokół „Uczciwy pomiar”** (`[INFERENCE]`, oparty na naszej metodzie z `NOTES.md`):
1. **Ten sam model, ta sama kwantyzacja, ten sam kontekst.** Nigdy nie porównujemy Q4 „po” z Q8 „przed”. Jeśli zmieniamy kwantyzację, to jest to *osobna* rekomendacja z osobnym opisem jakości.
2. **Zestaw promptów:**
   - stały, publiczny „Polski i angielski czat / kod / dokument 30k”;
   - plus **opcjonalnie prompty użytkownika**, które nigdy nie opuszczają maszyny.
3. **Naprzemienne A/B** (ABAB…, minimum 5 par), rozgrzewka, fresh server per wariant. Raportujemy **medianę i przedział** (np. „1,9–2,3×”), nie najlepszy run.
4. **Trzy liczby na karcie wyniku:**
   - czas do pierwszego słowa;
   - słowa/s przy pisaniu;
   - czas typowego zadania („Odpowiedź na 500 słów: 14 s → 6 s”).
   - Plus surowe t/s pod „Szczegóły”.
5. **Plakietka jakości:**
   - „Te same odpowiedzi, bit w bit” dla optymalizacji z bramką greedy md5;
   - „Praktycznie identyczne (KLD < x)” dla zmian numerycznych, **domyślnie wyłączonych** i tylko jako opt-in „Tryb maksymalny”.
6. **Cofnij jednym kliknięciem** i dziennik zmian („co zmieniliśmy”: lista przełączników, każda zmiana z env off-switchem, jak w naszych łatkach).
7. **Raport do pobrania** (HTML lub JSON) dla recenzentów i forów: wersje, sterownik, temperatura, seedy.
8. **Bez porównań z cudzymi narzędziami w UI** („2× szybciej niż Ollama”), chyba że mierzymy je tą samą procedurą na tej samej maszynie.

#### 2.1.4 UX długiej „nocnej optymalizacji”

**Ograniczenia techniczne, które UX musi ukryć:**
- **Windows TDR:** domyślnie `TdrDelay` wynosi 2 s. Po przekroczeniu sterownik GPU się resetuje (mignięcie ekranu). `TdrLimitCount` = 5 w `TdrLimitTime` = 60 s kończy się crashem systemu ([Microsoft Learn: TDR registry keys](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/tdr-registry-keys)). Kandydaci kernela w autotuningu muszą mieć twardy limit czasu i mniejsze rozmiary problemu na Windows. **Nigdy** nie zmieniamy kluczy TDR w rejestrze użytkownika `[INFERENCE]`.
- **Wzorzec rynkowy:** NVIDIA App wymaga 10–20 min bezczynności, a tuning przerywa się, gdy pojawi się obciążenie ([NVIDIA](https://www.nvidia.com/en-us/geforce/news/nvidia-app-download-and-features/)).

**Projekt** (`[INFERENCE]`):

| Element | Zachowanie |
|---|---|
| **Start** | „Zostaw komputer na noc (ok. 3–6 h). Możesz w każdej chwili przerwać; nic nie stracisz”. Szacunek oparty na liczbie kandydatów i czasie jednego pomiaru |
| **Harmonogram** | Domyślnie „gdy komputer jest bezczynny i podłączony do prądu”, opcjonalnie okno 1:00–7:00. Bezczynność wykrywana API systemu (np. [`GetLastInputInfo`](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getlastinputinfo) w Windows) |
| **Pauza natychmiast** | Ruch myszy lub klawisz, uruchomienie gry lub aplikacji pełnoekranowej, obciążenie GPU przez inny proces powyżej progu. Wznowienie po N min bezczynności |
| **Bateria** | Na baterii: stop. Laptop: tylko na zasilaczu i przy pokrywie otwartej lub w trybie „nie usypiaj” za zgodą |
| **Temperatura i hałas** | Limit temperatury GPU (np. 80 °C hotspot) i opcja „Cichy tryb” (limit mocy). Wykres temperatur w szczegółach. Pomiar zysku tylko w stanie termicznie ustalonym (rozgrzewka) |
| **Checkpointy** | Każdy zmierzony kandydat zapisany atomowo (SQLite lub JSON). Crash, restart, aktualizacja Windows lub reset sterownika oznaczają wznowienie od ostatniego punktu. Kandydat, który spowodował TDR lub hang, trafia na czarną listę |
| **Postęp** | „Krok 3/5: Testuję 42 z 180 wariantów · ~2 h 10 min do końca · już teraz +38%”. Wynik cząstkowy jest od razu używalny („najlepszy dotąd”) |
| **Rano** | Powiadomienie z kartą „przed → po” (sekcja 2.1.3) i przyciskiem „Zachowaj / Cofnij” |
| **Re-tuning** | Po aktualizacji sterownika, aplikacji lub modelu: szybka weryfikacja (5 min), czy profil nadal jest najlepszy i bitowo poprawny. Pełny tuning tylko gdy trzeba (jak comiesięczny re-scan w NVIDIA App) |
| **TUI/CLI** | `app tune --overnight --resume`, `app tune status`, czytelny log; zachowanie identyczne z GUI |

#### 2.1.5 Obsługa błędów

| Błąd | Detekcja | Komunikat (PL) | Automatyczna akcja |
|---|---|---|---|
| Brak lub za stary sterownik GPU | wersja sterownika vs minimalna dla backendu (np. Jan: CUDA 13 nie działa na Pascal i spada na Vulkan, [Jan 0.8.5](https://freedom.tech/posts/2026-10-08-jan-0-8-5/)) | „Twoja karta działa, ale sterownik jest z 2023 r. Z nowszym będzie ok. 30% szybciej. [Pokaż jak zaktualizować]” | Fallback na Vulkan lub CPU; nigdy nie instalujemy sterownika sami (ryzyko i odpowiedzialność) `[INFERENCE]` |
| OOM (VRAM/RAM) | estymacja przed ładowaniem (jak guardrails LM Studio) i łapanie błędu alokacji | „Ten model się nie zmieści. Proponuję wersję Średnią albo krótszą pamięć rozmowy (32k zamiast 128k)” | Auto-propozycja mniejszej kwantyzacji lub kontekstu; nigdy „zawieszenie PC” |
| Zawieszenie GPU / TDR | event log lub kod błędu backendu | „Karta graficzna się zrestartowała. Wyłączyliśmy ostatnią zmianę.” | Rollback profilu i zgłoszenie (opt-in) |
| Antywirus usunął plik | brak lub uszkodzony hash binarki przy starcie | „Windows Defender omyłkowo zablokował plik. [Napraw jednym klikiem]” plus link do zgłoszenia FP | Ponowne pobranie podpisanego pliku z weryfikacją sha256 |
| Przerwany download | HTTP Range i sha256 | „Wznawiam pobieranie od 63%” | Resume; weryfikacja hash |
| Brak miejsca | free space przed pobraniem | „Potrzebujemy 18 GB, masz 9 GB na C:. [Wybierz inny dysk]” | Wybór katalogu modeli (wspólny z innymi narzędziami) |
| Model „głupi” po złej konfiguracji | zbyt mały kontekst (znany problem Ollamy z domyślnymi 2k, [HN](https://news.ycombinator.com/item?id=47788385)) | – | Rozsądne domyślne kontekstu per VRAM |

#### 2.1.6 Dostępność i i18n
- **European Accessibility Act** stosuje się od 28 czerwca 2025 do usług e-commerce (sklep i ścieżka zakupu). Mikroprzedsiębiorstwa (poniżej 10 osób i do 2 M€ obrotu lub sumy bilansowej) są zwolnione **dla usług**, a próg nie ma okresu przejściowego. Standard to EN 301 549, który odsyła do WCAG 2.1 AA ([accessible.org](https://accessible.org/eaa-ecommerce-services-requirements/), [Going Stellar, art. 3(23)](https://goingstellar.ro/research/european-accessibility-act-online-stores/), [RaftLabs](https://www.raftlabs.com/blog/european-accessibility-act-guide)).
- Sama aplikacja desktopowa nie jest wprost w katalogu EAA `[INFERENCE]`, ale AI Act art. 50(5) wymaga, by informacja „to jest AI” spełniała wymogi dostępności ([art. 50](https://artificialintelligenceact.eu/article/50/)).
- **Rekomendacja:** od początku WCAG 2.2 AA ([W3C](https://www.w3.org/TR/WCAG22/)): pełna obsługa klawiaturą, kontrast, czytniki ekranu (a11y tree w Tauri lub Electron), animacje strumieniowania z `prefers-reduced-motion`. TUI musi działać z czytnikiem ekranu: tryb „plain log” bez rysowania ramek `[INFERENCE]`.
- **PL/EN:** polska odmiana liczebników ma 4 kategorie CLDR (one / few / many / other: „1 model, 2 modele, 5 modeli, 1,5 modelu”) ([CLDR plural rules](https://www.unicode.org/cldr/charts/latest/supplemental/language_plural_rules.html)), więc trzeba użyć ICU MessageFormat, a nie konkatenacji. Formaty liczb: „40,5 słowa/s”. Ceny w PLN i EUR.

### 2.2 Zaufanie i prywatność

#### 2.2.1 Co może zbierać „spec scan” i jak to pokazać

**Zasada:** skan wykonuje się **lokalnie** i sam w sobie nic nie wysyła. Dostęp do informacji na urządzeniu w celu świadczenia usługi, o którą użytkownik wprost prosi, to wyjątek „strictly necessary” z art. 5(3) ePrivacy. Wysyłka do nas to już inny cel i wymaga zgody. EDPB w Guidelines 2/2023 (przyjęte 16.10.2024) potwierdza, że art. 5(3) obejmuje informacje nieosobowe, fingerprinting, „certain local processing” i raportowanie IoT ([Hunton](https://www.hunton.com/privacy-and-information-security-law/edpb-adopts-guidelines-on-scope-of-eprivacy-directive) `[STALE?]`, [gdprbuzz](https://gdprbuzz.com/resources/edpb-guidelines-eprivacy-directive/)). W Polsce reguluje to **art. 399 Prawa komunikacji elektronicznej** (od 10.11.2024; kary Prezesa UKE do 3% przychodu, [witly.ai](https://witly.ai/news/cookie-consent), [mkz partnerzy](https://mkzpartnerzy.pl/prawo-komunikacji-elektronicznej/)).

| Zbieramy lokalnie (potrzebne) | Nigdy nie zbieramy |
|---|---|
| OS i wersja; CPU (model, rdzenie, AVX2/AVX-512); RAM łącznie | hostname, nazwa użytkownika, ścieżki domowe |
| GPU: vendor, model, VRAM, sterownik (major.minor), compute capability / `gfx` target, PCIe gen×width | **numery seryjne**, GPU UUID (`nvidia-smi` je podaje), MAC, numery dysków |
| Dostępne backendy (CUDA, ROCm, Vulkan, Metal) i ich wersje | `/proc/cmdline`, `dmesg`, logi systemowe (nasz `scripts/sysinfo.sh` czyta oba; w produkcie **nie wolno**) |
| Wolne miejsce na wybranym dysku | lista plików, zainstalowanych aplikacji, historii |
| Zasilanie (AC / bateria), temperatury (tylko na żywo, lokalnie) | lokalizacja, IP-geolokacja, treść promptów i czatów |

**UI:** panel „Co wiemy o Twoim komputerze”, z dokładnie tym, co zostało odczytane, i przyciskiem „Pokaż, co *wysłalibyśmy*”. Ten przycisk pokazuje dokładny JSON przed jakąkolwiek wysyłką. Wzór: kreator Jana z osobnym krokiem zgody ([Jan 0.8.5](https://freedom.tech/posts/2026-10-08-jan-0-8-5/)).

#### 2.2.2 Telemetria, RODO/GDPR, ePrivacy
- **Adres IP to dana osobowa.** TSUE w sprawie Breyer (C-582/14, 2016) uznał za daną osobową nawet dynamiczny IP ([EUR-Lex C-582/14](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62014CJ0582) `[STALE?]`). Każde połączenie z naszym backendem przetwarza więc dane osobowe.
- **Pseudonimizacja:** TSUE w sprawie EDPS v SRB (C-413/23 P, 4.09.2025) orzekł, że silnie spseudonimizowane dane mogą nie być osobowe *dla odbiorcy*, który nie ma klucza. Obowiązek informacyjny administratora oceniamy jednak w chwili zbierania ([Bird & Bird](https://www.twobirds.com/en/insights/2025/eu-the-srb-decision-a-new-era-for-personal-data-and-data-processing-agreements), [EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A62023CJ0413)). Katalog profili (GPU×model×sterownik → parametry) można więc zaprojektować tak, by po stronie serwera był **anonimowy**: bez ID instalacji, z agregacją i odrzuceniem IP przy ingest `[INFERENCE]`.
- **Digital Omnibus (RODO + ePrivacy):** nadal w negocjacjach. Proponowano m.in. przeniesienie cookies z art. 5(3) do RODO (art. 88a) i listę celów bez zgody. Kompromis prezydencji irlandzkiej z 3.09.2026 przywrócił reguły do art. 5(3) z sześcioma wyjątkami ([Usercentrics](https://usercentrics.com/knowledge-hub/eu-digital-omnibus-package/), [ppc.land](https://ppc.land/eprivacy-directive/)). **Projektujemy pod obecne prawo**: zgoda opt-in.
- **Rekomendowany model telemetrii** (`[INFERENCE]`), trzy niezależne przełączniki, wszystkie **domyślnie wyłączone**:
  1. „Wyślij raport o awarii” (pytanie per crash, z podglądem);
  2. „Udostępnij mój profil przyspieszenia społeczności” (anonimowe GPU×model×sterownik×parametry×zysk);
  3. statystyki użycia: **nie zbierać wcale** w wersji konsumenckiej. LM Studio buduje markę na „No data collection” ([App Store: Locally AI](https://apps.apple.com/us/app/locally-ai-by-lm-studio/id6741426692)).
- Hosting backendu w UE; retencja raportów 90 dni; RoPA; umowy powierzenia (DPA) z dostawcami; polityka prywatności PL i EN.
- Kary RODO: do 20 M€ lub 4% światowego obrotu ([cenkier.pl](https://cenkier.pl/artykuly/rodo-w-2026-co-kontroluje-uodo-i-jakie-kary-naklada/)). Nie znalazłem kar UODO za telemetrię aplikacji desktopowych (2025–2026).

#### 2.2.3 EU AI Act: kim jesteśmy?
- **Nie jesteśmy providerem GPAI.** Downstream modifier staje się providerem modelu, gdy modyfikacja zużywa ponad ⅓ compute treningowego oryginału. Gdy ten compute jest nieznany, próg to ⅓ z 10²³ FLOP ([Orrick](https://www.orrick.com/en/Insights/2025/08/EU-Commission-Guidelines-on-the-scope-of-the-obligation-for-GPAI-models-under-the-AI-Act) `[STALE?]`, [Modulos](https://docs.modulos.ai/frameworks/eu-ai-act/commission-guidance/gpai-models)). Kwantyzacja, kernele, sampler, a nawet trening małego draftera (DFlash, MTP) są wiele rzędów wielkości poniżej `[INFERENCE]`.
- **Jesteśmy providerem *systemu AI*** (aplikacja czatu wprowadzona na rynek pod naszą nazwą). Użytkownik prywatny nie jest deployerem: definicja deployera wyłącza „personal non-professional activity” ([art. 3(4) przez art. 50](https://artificialintelligenceact.eu/article/50/)).
- **Art. 50(1):** od 2.08.2026 trzeba jasno poinformować, że to AI, najpóźniej przy pierwszej interakcji. Wyjątek „to oczywiste” Komisja tłumaczy wąsko: nie wystarczy ogólna świadomość AI, a disclaimer w regulaminie czy formuła „this system uses LLMs” są niewystarczające ([Paul Weiss, 4.08.2026](https://www.paulweiss.com/insights/client-memos/eu-finalises-transparency-rules-for-ai-generated-content)).
- **Art. 50(2): machine-readable marking syntetycznego tekstu.**
  - Finalny Code of Practice (10.06.2026; uznany za adekwatny) wymaga dla free-form text jednej techniki, w praktyce watermarku.
  - Teksty poniżej 200 tokenów są zwolnione; wyłączony jest też kod źródłowy.
  - Trzeba udostępnić darmowy mechanizm detekcji (dopuszczalna opłata za duży wolumen przy < 1 mln użytkowników miesięcznie) i interoperacyjność detekcji do 2.02.2027.
  - Grace do 2.12.2026 tylko dla systemów na rynku przed 2.08.2026. Kary do 15 M€ lub 3% obrotu.
  - Źródła: [Paul Weiss](https://www.paulweiss.com/insights/client-memos/eu-finalises-transparency-rules-for-ai-generated-content), [Code of Practice, EC](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content), [Cooley](https://cdp.cooley.com/digital-ai-omnibus-delays-key-deadlines-introduces-new-rules/).
  - Wytyczne odróżniają „open-source AI systems”, które podlegają art. 50, od samych „components”, które są poza zakresem ([Reed Smith](https://www.reedsmith.com/our-insights/blogs/viewpoints/102nbz0/transparency-obligations-for-ai-generated-content-the-code-of-practice-adequacy/)). Zwolnienie open-source z art. 2(12) nigdy nie obejmowało art. 50 ([OpenForum Europe](https://openforumeurope.org/understanding-the-ai-act-open-source-key-updates-march-2025/)).
  - **Konflikt:** watermark tekstu żyje w samplerze ([explainx](https://explainx.ai/blog/will-all-ai-models-watermark-output-2026)), więc zmienia rozkład tokenów, a nasza marka to „bit w bit”. **Rozwiązanie robocze** `[INFERENCE]`:
    - watermark jako warstwa samplera stosowana identycznie w trybie „przed” i „po”, więc identyczność stock vs zoptymalizowany jest zachowana;
    - deterministyczny klucz;
    - w API serwera lokalnego (dla developerów) przełącznik z ostrzeżeniem.
  - **To wymaga opinii prawnej przed launchem w UE.** Jak to robią LM Studio, Ollama i Jan, nie ustaliłem.
- **Art. 4 (AI literacy):** Omnibus (Rozp. 2026/1744) zmienił obowiązek z „zapewnić” na „Komisja i państwa wspierają” ([Cooley](https://cdp.cooley.com/digital-ai-omnibus-delays-key-deadlines-introduces-new-rules/)).
- **Nowy zakaz w art. 5** (od 2.12.2026): systemy generujące NCII lub CSAM. Dla providera wystarczy, że generacja jest „reasonably foreseeable” bez skutecznych zabezpieczeń ([Cooley](https://cdp.cooley.com/digital-ai-omnibus-delays-key-deadlines-introduces-new-rules/)). **Wniosek: żadnej generacji obrazów w MVP.**
- **Polska:** ustawa o systemach sztucznej inteligencji z 3.07.2026 (Dz.U. 27.07.2026). Organ: **KRiBSI**. Kontrole i kary obowiązują od 28.10.2026, skargi może składać każdy, piaskownice regulacyjne są darmowe dla MŚP ([gov.pl](https://www.gov.pl/web/cyfryzacja/ustawa-o-systemach-ai--bezpieczny-rozwoj-sztucznej-inteligencji-w-polsce), [ktzr.pl](https://www.ktzr.pl/ustawa-o-systemach-sztucznej-inteligencji/), [infor.pl](https://www.infor.pl/prawo/nowosci-prawne/7668177,ustawa-o-systemach-sztucznej-inteligencji-od-28-pazdziernika-2026-obowiazki-firm-i-kary-co-to-jest-kribsi.html)). **Procedura opinii KRiBSI przed wdrożeniem** to tani sposób na pewność w sprawie art. 50(2) `[INFERENCE]`.

#### 2.2.4 Inne regulacje UE, które nas dotyczą
- **Cyber Resilience Act:** od **11.09.2026** obowiązuje raportowanie aktywnie wykorzystywanych podatności (24 h early warning, 72 h notification) przez ENISA Single Reporting Platform. Główne obowiązki od **11.12.2027** ([Komisja: CRA](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act), [CRA reporting](https://digital-strategy.ec.europa.eu/en/policies/cra-reporting)). Aplikacja sprzedawana komercyjnie to „product with digital elements” `[INFERENCE]`. Potrzebne są SBOM, proces CVD i aktualizacje bezpieczeństwa.
- **Nowa dyrektywa o odpowiedzialności za produkt (2024/2853):** oprogramowanie jest „produktem”; transpozycja do 9.12.2026. Zwolnienie OSS obowiązuje tylko poza działalnością gospodarczą ([EUR-Lex](https://eur-lex.europa.eu/eli/dir/2024/2853/oj/eng), [IBA](https://www.ibanet.org/European-Product-Liability-Directive-liability-for-software)). Odpowiadamy też za llama.cpp wbudowane w nasz produkt.
- **Prawa konsumenta (PL):**
  - Obowiązek dostarczania aktualizacji, w tym bezpieczeństwa, przez czas wynikający z umowy (art. 43k i n. u.p.k.).
  - Utrata prawa odstąpienia dla treści cyfrowych tylko za wyraźną zgodą i po pouczeniu (art. 38 pkt 13) ([lexlege art. 43k](https://lexlege.pl/ustawa-o-prawach-konsumenta/art-43k/), [Sejm, nowelizacja 2022](https://orka.sejm.gov.pl/proc9.nsf/ustawy/2425_u.htm) `[STALE?]`).
  - Auto-update jest więc obowiązkiem, nie tylko wygodą; trzeba też checkbox przy zakupie.

#### 2.2.5 Modele „uncensored”
- Na HF jest ponad 11 tys. modeli uncensored. Część repozytoriów jest dziś za bramką „research only”, a HF wyłączył model reklamowany jako „offensive cyber” ([slash-digital](https://slash-digital.io/en/insights/uncensored-models/), [aiidelist](https://aiidelist.com/blog/hugging-face-disabled-offensive-cyber-glm-5-3-model); źródła drugorzędne).
- Licencje często przenoszą ograniczenia użycia na dalszych użytkowników:
  - Gemma Terms wymagają, by use restrictions z §3.2 były **wykonalnym postanowieniem** w naszym EULA, plus pliku Notice ([Gemma Terms](https://ai.google.dev/gemma/terms.md.txt));
  - Llama 4 ma AUP ([Llama 4 AUP](https://www.llama.com/llama4/use-policy/)).
- Sami używamy wariantów Uncensored (Qwen3.8-27B Uncensored 115,5 t/s; [`README`](../../README.md)).
- **Rekomendacja** `[INFERENCE]`:
  - (a) katalog „polecanych” tylko z oficjalnych wag producenta;
  - (b) „Importuj własny plik GGUF” jako funkcja zaawansowana, z oświadczeniem użytkownika i AUP w EULA;
  - (c) nie promować uncensored w marketingu ani w sklepach;
  - (d) brak obrazów i wideo (art. 5);
  - (e) profile przyspieszenia działają na architekturze, więc działają też dla fine-tune'ów; nie musimy ich wymieniać z nazwy.
- Bezpieczeństwo: ponad 1100 wystawionych publicznie serwerów Ollama ([The Register / Cisco Talos](https://www.theregister.com/2025/09/02/exposed_ollama_servers_insecure_research/) `[STALE?]`). Jan od 0.8.5 egzekwuje Trusted Hosts przy bind `0.0.0.0` (GHSA-x6p8-7cp8-c3p6) ([Jan 0.8.5](https://freedom.tech/posts/2026-10-08-jan-0-8-5/)). Nasz serwer musi domyślnie słuchać tylko na localhost.

### 2.3 Dystrybucja

#### 2.3.1 Windows: podpisywanie w 2026

| Opcja | Koszt | Dostępność | SmartScreen | Uwagi |
|---|---|---|---|---|
| **Microsoft Store (MSIX)** | 0 (re-signing przez MS) | świat | ✅ brak ostrzeżeń | MS hostuje plik i robi auto-update ([MS Learn](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options)) |
| **Microsoft Store (Win32 MSI/EXE)** | koszt certyfikatu | świat | ✅ brak SmartScreen przy instalacji ze Store | Każdy PE podpisany certyfikatem z Trusted Root Program; wymagana cicha instalacja; wersjonowany URL ([Store policies](https://learn.microsoft.com/en-us/windows/apps/publish/store-policies)) |
| **Azure Artifact Signing** (ex Trusted Signing) | ok. **9,99 $/mies.** Basic (5000 podpisów), Premium 100 000; naliczane od utworzenia konta | **Organizacje: US, CA, UE, UK, AU, NZ, JP, KR, SG, CH, NO, IL. Osoby fizyczne: tylko US i CA**. Region Poland Central dostępny | ⚠️ reputacja budowana w czasie | Walidacja trwa „kilka dni roboczych”; 3 próby dokumentów; bez tokenu USB; GitHub Actions ([Quickstart](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart), [FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq), [Pricing](https://azure.microsoft.com/en-us/pricing/details/artifact-signing/)) |
| **OV (DigiCert, Sectigo…)** | **150–300 $/rok** | świat | ⚠️ jak wyżej | Klucz w HSM lub na tokenie od 06.2023; od 1.03.2026 maks. ważność około 458–460 dni ([MS Learn](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options), [SSL.com](https://www.ssl.com/faqs/which-code-signing-certificate-do-i-need-ev-ov), [DigiCert](https://docs.digicert.com/en/certcentral/order-and-manage-certificates/reports-and-advisories/end-of-2-and-3-year-public-code-signing-certificates.html)) |
| **EV** | 400 $+/rok | świat | ⚠️ **od 2024 to samo co OV**, brak natychmiastowego obejścia | „No longer recommended for SmartScreen” ([MS Learn: distribution status](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/distribution-feature-status)) |
| SignPath Foundation | 0 | projekty OSS | jak OV | Tylko jeśli dystrybuujemy otwarty kod ([MS Learn](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options)) |

**Konsekwencje:**
- (1) **Potrzebujemy spółki** (sp. z o.o.) albo zweryfikowanej działalności jako „organizacji”. Autónomo z Hiszpanii pyta o ten sam problem na MS Q&A, a odpowiedź (AI-generated) sugeruje ścieżkę „Organization” z dokumentem rejestrowym. Pewności brak ([MS Q&A](https://learn.microsoft.com/en-us/answers/questions/6034844/azure-artifact-signing-eligibility-of-a-spanish-so?page=1)).
- (2) **Smart App Control** w Windows 11 blokuje niepodpisany i nieznany kod. Podpisany musi być **każdy** `.exe` i `.dll`, także instalatory tymczasowe i uninstaller ([MS Q&A](https://learn.microsoft.com/en-us/answers/questions/5791210/application-signed-and-blocked-by-smart-app-contro), [Windows Security Book](https://learn.microsoft.com/en-us/windows/security/book/application-security-application-and-driver-control)). Pobieranie backendów llama.cpp w runtime to proszenie się o blokady.
- (3) Reputacja SmartScreen może się **resetować przy odnowieniu certyfikatu** ([MS Q&A](https://learn.microsoft.com/en-us/answers/questions/5900208/smartscreen-reputation-reset-following-ev-certific)). Przemawia to za Artifact Signing, które zachowuje stałą tożsamość wydawcy.

#### 2.3.2 macOS
- Apple Developer Program: **99 $/rok**. Konto firmowe wymaga D-U-N-S (bezpłatny; do 5 dni roboczych w D&B i do 2 dni na przekazanie do Apple). Apple **nie akceptuje DBA ani nazw handlowych** ([Apple: membership](https://developer.apple.com/programs/whats-included/), [Apple: enroll](https://developer.apple.com/programs/enroll/), [Apple: D-U-N-S](https://developer.apple.com/support/D-U-N-S/)).
- Developer ID i notaryzacja to w praktyce obowiązek:
  - od Sequoii zniknął Ctrl-klik obejścia Gatekeepera; trzeba wejść w Ustawienia → Prywatność → „Open Anyway” i wpisać hasło admina ([AppleInsider](https://appleinsider.com/articles/24/08/06/apple-removes-control-click-option-for-skipping-gatekeeper-in-macos-sequoia) `[STALE?]`);
  - **Homebrew od 1.09.2026 wyłącza casks, które nie przechodzą Gatekeepera**, i usunął `--no-quarantine` ([Workbrew: Homebrew 5.0](https://workbrew.com/blog/homebrew-5-0-0), [GitHub fleetdm#43484](https://github.com/fleetdm/fleet/issues/43484)).
- **Mac App Store:**
  - sandbox pozwala na Metal i MLX: „Locally AI by LM Studio” jest w MAS ([App Store](https://apps.apple.com/us/app/locally-ai-by-lm-studio/id6741426692));
  - **2.5.2 zabrania pobierania i wykonywania kodu**, który zmienia funkcje aplikacji;
  - aplikacje Mac nie mogą pobierać „additional code” ani mieć własnego mechanizmu aktualizacji;
  - modele (dane) są dozwolone po ujawnieniu rozmiaru (4.2.3(ii));
  - prowizja 30% albo 15% w Small Business Program ([App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/), [Apple](https://developer.apple.com/programs/whats-included/)).
  - **Wersja MAS jest możliwa tylko wtedy, gdy wszystkie warianty kerneli są w paczce, a optymalizacja dobiera parametry (dane).**

#### 2.3.3 Linux
- **AppImage:** jeden plik i brak sandboxa, więc GPU działa jak w systemie. Najprostsza droga dla CUDA, ROCm i Vulkan.
- **Flatpak:** sandbox wymaga rozszerzeń sterownika NVIDIA dopasowanych do wersji. **ROCm wymaga `/dev/kfd`**, którego nie daje `--device=dri`, więc trzeba `--device=all` ([rocm-flatpak](https://github.com/night199uk/rocm-flatpak), [Flathub Blender #180](https://github.com/flathub/org.blender.Blender/issues/180)). Flatpak 1.18 ogłasza integrację ROCm ([dev.to](https://dev.to/soytuber/linux-71-boosts-intel-arc-flatpak-integrates-rocm-vintage-amd-driver-refined-174k); źródło drugorzędne).
- **.deb i .rpm:** Jan publikuje deb i AppImage ([Jan 0.8.5](https://freedom.tech/posts/2026-10-08-jan-0-8-5/)).
- **Rekomendacja:** AppImage + .deb + .rpm na start, Flathub dopiero po weryfikacji ROCm w sandboxie.

#### 2.3.4 winget, Homebrew, sklepy

| Kanał | Wymagania | Przydatność |
|---|---|---|
| **winget** | Manifest YAML, sha256 instalatora; skan Defender i SmartScreen URL; walidacja w VM; instalacja i deinstalacja bez interakcji ([MS Learn](https://learn.microsoft.com/en-us/windows/package-manager/package/winget-validation), [MSEndpointMgr](https://msendpointmgr.com/2026/07/30/is-winget-enterprise-ready/)) | Tak (power users, firmy przez Intune) |
| **Homebrew cask** | Podpis i notaryzacja (od 1.09.2026) | Tak |
| **Microsoft Store** | Darmowa rejestracja dla osób i firm (od 09.2025); Win32 OK; dla aplikacji (nie gier) własna płatność z 0% prowizji; dynamiczne doładowywanie kodu niezgodne z opisem jest zakazane (10.2.2) ([Windows Dev Blog](https://blogs.windows.com/windowsdeveloper/2025/09/10/free-developer-registration-for-individual-developers-on-microsoft-store/) `[STALE?]`, [Store policies](https://learn.microsoft.com/en-us/windows/apps/publish/store-policies)) | **Bardzo dobra**: 250 mln MAU, brak SmartScreen |
| **Mac App Store** | Patrz 2.3.2 | Tylko edycja „Lite” bez pobierania kodu |
| **Steam** | 100 $ za produkt (zwrotne po 1000 $ AGR); aplikacje nie-gry tylko w wybranych kategoriach; ujawnienie AI content dla live-generated ([Steamworks](https://partner.steamgames.com/steamdirect), [onboarding](https://partner.steamgames.com/doc/gettingstarted/onboarding)) | Niepewna akceptacja kategorii. Lossless Scaling (6,99 $, 2–5 mln właścicieli wg SteamSpy) pokazuje, że gracze kupują „boost” na Steamie ([tech-insider](https://tech-insider.org/lossless-scaling-setup-2026/)) |

#### 2.3.5 Auto-update
- **Tauri updater:** podpis aktualizacji jest obowiązkowy i **nie da się go wyłączyć**; utrata klucza prywatnego oznacza brak aktualizacji dla obecnych instalacji; TLS wymuszony ([Tauri](https://v2.tauri.app/plugin/updater/)).
- **Velopack:** delta updates, cross-platform, podpis i notaryzacja w buildzie ([velopack.io](https://velopack.io/)).
- **Rekomendacja:**
  - podpisane aktualizacje z deltami (silnik plus kernele to setki MB);
  - **kanały stable i beta**;
  - wyłącznik auto-update, bo jego brak był powodem odejść od Ollamy ([HN](https://news.ycombinator.com/item?id=47788385));
  - zatrzymanie silnika przed instalacją (Jan 0.8.5 naprawiał właśnie ten błąd).
  - Obowiązek z u.p.k. dotyczy aktualizacji bezpieczeństwa (sekcja 2.2.4).

#### 2.3.6 Fałszywe alarmy antywirusów
- Udokumentowane przypadki:
  - Defender oznaczył binarki llama.cpp jako `Trojan:Win32/Wacatac.B!ml` ([llama.cpp #28224](https://github.com/ggml-org/llama.cpp/issues/28224));
  - LM Studio 0.4.7 dostało `Trojan:JS/GlassWorm.ZZ!MTB` (1/62 na VirusTotal) ([lmstudio #1686](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1686));
  - koboldcpp był kasowany przez Defendera ([koboldcpp #1649](https://github.com/LostRuins/koboldcpp/issues/1649)).
- **Mitigacje** `[INFERENCE]`:
  - (1) podpis każdego PE stałą tożsamością;
  - (2) brak pobierania wykonywalnych backendów w runtime: wszystko w instalatorze, jak Jan 0.8.5;
  - (3) brak packerów i obfuskacji, symbole w osobnym pliku;
  - (4) wysyłka każdego release'u do Microsoft Defender Submission *przed* publikacją ([winget docs wskazują tę ścieżkę](https://learn.microsoft.com/en-us/windows/package-manager/package/winget-validation));
  - (5) sha256 i podpisy publikowane na stronie;
  - (6) automatyczna naprawa w aplikacji (sekcja 2.1.5).

#### 2.3.7 Hosting modeli
- **HF rate limits** (wrzesień 2025, `[STALE?]`, wciąż w docs): okna 5-minutowe, „resolvers” (pobieranie plików): anonim **3000 na IP**, free user 5000, PRO 12 000. Dokumentacja wprost wymienia LM Studio, Jan i Ollama jako klientów resolverów ([HF rate limits](https://github.com/huggingface/hub-docs/blob/main/docs/hub/rate-limits.md)). Dla pojedynczego użytkownika pobierającego kilka plików to wystarczy.
- **Xet** jest domyślny od 23.05.2025: deduplikacja chunków i równoległe pobieranie ([HF docs: storage backends](https://huggingface.co/docs/hub/storage-backends) `[STALE?]`).
- **Checksumy:** API `tree/main` zwraca `lfs.oid` = **sha256** pliku i rozmiar. Zweryfikowane na `speakleash/Bielik-11B-v3.0-Instruct-GGUF`: Q4_K_M ma 6 724 051 584 B, sha256 `c16841…23a8` ([HF API](https://huggingface.co/api/models/speakleash/Bielik-11B-v3.0-Instruct-GGUF/tree/main)). Wznawianie przez HTTP Range, weryfikacja sha256 po zakończeniu. **Przypinać konkretną rewizję (commit)**, nie `main`.
- **Ryzyko dostawcy:** HF jest przejmowane przez NVIDIA (12,93 mld $; deklaracja „remain open”, „NVIDIA compute will not be required”) ([NVIDIA blog](https://blogs.nvidia.com/blog/nvidia-to-acquire-hugging-face/)). Dla produktu kluczowego na AMD to ryzyko strategiczne, choć niskie w krótkim terminie.
- **Mirror:** Cloudflare R2 kosztuje **0,015 $/GB-mies.**, a **egress jest darmowy**; 1 TB to około 15 $/mies. ([mecanik](https://mecanik.dev/en/posts/cloudflare-r2-pricing-explained-real-costs-vs-s3-and-backblaze/), [filebase](https://filebase.com/blog/cloudflare-r2-pricing-costs-savings-and-alternatives-in-2026/)). Mirror wolno robić tylko dla licencji pozwalających na redystrybucję. Trzeba dołączyć LICENSE, NOTICE oraz, dla Gemmy ≤3, plik Notice (sekcja 2.4).

### 2.4 Licencje

#### 2.4.1 llama.cpp, nasze łatki, upstream
- **llama.cpp i ggml: MIT.** Wymagają tylko zachowania noty copyright. ggml.ai dołączyło do HF (02.2026) ([HF blog](https://huggingface.co/blog/ngxson/ggml-and-llama-cpp-join-hugging-face), [Simon Willison](https://simonwillison.net/2026/Feb/20/ggmlai-joins-hugging-face/)), a HF przechodzi do NVIDIA. MIT daje nam prawo forka zawsze.
- **Lekcja reputacyjna:** post „The local LLM ecosystem doesn't need Ollama” (648 pkt, 207 komentarzy, 16.04.2026) zarzucał Ollamie brak atrybucji llama.cpp, zamknięty magazyn blobów i wolniejsze działanie. Komentarze chwaliły LM Studio za „proper credit” mimo zamkniętego kodu ([HN 47788385](https://news.ycombinator.com/item?id=47788385)).
- **Rekomendacja:**
  - „Powered by llama.cpp” widoczne w UI i w „O programie”;
  - **uniwersalne łatki upstream** (mniejszy koszt rebase'u 70 łatek, wiarygodność na r/LocalLLaMA);
  - profile, orkiestrator i harness pozostają nasze;
  - pliki GGUF w zwykłym katalogu, współdzielonym z innymi narzędziami.

#### 2.4.2 Licencje modeli: co można bundlować, pobierać i polecać w komercyjnej aplikacji

| Model | Licencja (stan 10.2026) | Komercyjnie | Bundle / mirror | Warunki krytyczne | Rekomendacja |
|---|---|---|---|---|---|
| **Qwen3.8-27B** | Apache-2.0 (tag HF) ([HF API](https://huggingface.co/api/models?search=Qwen3.8&author=Qwen&limit=20)) | ✅ | ✅ | LICENSE i NOTICE | **Flagowy**, polecać |
| **Qwen3.8-Flash-Next, Qwen3.8-2.4T** | **Qwen Community License 1.0** ([LICENSE](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/raw/main/LICENSE)) | ⚠️ | ✅ z notą | Powyżej 100 M MAU lub 20 M$ **miesięcznego** przychodu: nazwa modelu na UI. **„Model as a Service” lub „AI Work Assistant”** (produkt *przede wszystkim* do kodowania lub pracy biurowej) wymaga **osobnej licencji od Qwen** | Polecać tylko, jeśli nie pozycjonujemy się jako asystent kodowania lub biura; serwer API dla firm to ryzyko MaaS |
| **LFM2.5-24B-A2B** (i rodzina LFM) | **LFM Open License v1.0** ([LICENSE](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/raw/main/LICENSE), [liquid.ai](https://www.liquid.ai/lfm-license)) | ⚠️ tylko poniżej **10 M$ rocznego przychodu** (cały „Legal Entity”, z podmiotami powiązanymi) | ✅ (redystrybucja wprost dozwolona, także przez duże platformy) | Licencja **wygasa automatycznie** po przekroczeniu progu. Próg dotyczy *każdego* komercyjnego użytkownika, w tym naszych klientów B2B | Konsumenci OK; w edycji Business pytać o przychód lub wyłączyć LFM |
| **Gemma 4** | **Apache 2.0** (od 2.04.2026) ([Google](https://ai.google.dev/gemma/docs/gemma_4_license), [9to5Google](https://9to5google.com/2026/04/02/google-gemma-4)) | ✅ | ✅ | standard Apache | Polecać |
| **Gemma 3 i starsze** | Gemma Terms of Use ([terms](https://ai.google.dev/gemma/terms.md.txt)) | ✅ z ograniczeniami | ⚠️ | Use restrictions (Prohibited Use Policy) jako **wykonalne postanowienie** w naszym EULA; plik „Notice”; Google zastrzega prawo zdalnego ograniczenia | Nie bundlować; zastąpić Gemmą 4 |
| **Llama 4** | Llama 4 Community License + AUP | ❌ **dla nas** | ❌ | AUP: dla modeli multimodalnych prawa z §1(a) **nie są udzielane** osobom i firmom z siedzibą w UE (wyjątek: end users produktu); wszystkie Llama 4 są multimodalne. 700 M MAU; „Built with Llama” ([Llama 4 AUP](https://www.llama.com/llama4/use-policy/), [licencja](https://www.llama.com/llama4/license/) `[STALE?]`) | **Wykluczyć** z katalogu (polska spółka = podmiot z UE) |
| **Mistral Small 4, Large 3, Ministral 3, Magistral Small** | Apache 2.0 ([Mistral 3](https://mistral.ai/news/mistral-3/), [Magistral](https://mistral.ai/news/magistral/)) | ✅ | ✅ | – | Polecać (europejski dostawca to argument marketingowy w PL) |
| Mistral Medium 3.5 | zmodyfikowane MIT z limitem 20 M$ (wg [datanorth](https://datanorth.ai/blog/the-complete-guide-to-mistral-ai), źródło drugorzędne) | ⚠️ | ⚠️ | do weryfikacji w LICENSE | Pominąć w MVP |
| Ministral 8B (2024) | Mistral Commercial / Research License ([Mistral](https://mistral.ai/news/ministraux/)) | ❌ bez umowy | ❌ | – | Pominąć |
| **gpt-oss-20b / 120b** | Apache 2.0 + gpt-oss usage policy ([OpenAI](https://openai.com/index/introducing-gpt-oss/) `[STALE?]`, [HF](https://huggingface.co/openai/gpt-oss-120b)) | ✅ | ✅ | dołączyć USAGE_POLICY | Polecać |
| **Bielik 11B v3** | Apache 2.0 ([HF](https://huggingface.co/speakleash/Bielik-11B-v3.0-Instruct-GGUF)) | ✅ | ✅ | – | **Polecać na rynek PL**; istnieje `Bielik-11B-v3.0-DFlash` ([HF](https://huggingface.co/speakleash/Bielik-11B-v3.0-DFlash)), więc nasze DFlash pasuje |
| **PLLuM** (11 wariantów, 05.2026) | mieszane: Apache 2.0 / **CC-BY-NC-4.0** / Llama 3.3 ([pl.wikipedia](https://pl.wikipedia.org/wiki/PLLuM)) | per wariant | per wariant | NC = zakaz komercji | Tylko warianty Apache |

**Uwaga:** produkt „pobierz model z HF na życzenie użytkownika” ma słabszą pozycję niż „bundlujemy plik”. Gdy *polecamy* i *uruchamiamy* model w komercyjnym produkcie, my także „używamy” go komercyjnie (np. LFM: „any use … for direct or indirect commercial advantage”) `[INFERENCE]`.

#### 2.4.3 CUDA i ROCm
- **CUDA EULA:**
  - Redystrybuować wolno tylko pliki z **Attachment A**: m.in. `cudart`, `cublas`, `cublasLt`, cuFFT, NVRTC.
  - Warunki:
    - aplikacja musi mieć „material additional functionality”;
    - pliki mogą być używane wyłącznie przez naszą aplikację;
    - nasze warunki muszą chronić IP NVIDIA;
    - SDK jest licencjonowane **tylko do systemów z GPU NVIDIA**;
    - nie wolno łączyć SDK z licencją OSS wymagającą ujawnienia kodu lub darmowej redystrybucji (§1.2(5));
    - zakaz reverse engineeringu outputu w celu przeniesienia na nie-NVIDIA (§1.2(8)) ([CUDA EULA](https://docs.nvidia.com/cuda/eula/index.html)).
  - **Wniosek:** w repo OSS nie trzymamy binarek CUDA; dokładamy je w instalatorze z osobnym EULA.
- **ROCm:** komponenty takie jak hipBLAS, hipBLASLt i rocBLAS są na **MIT** ([ROCm license](https://rocm.docs.amd.com/en/latest/about/license.html) `[STALE?]`). Binarki **Windows HIP SDK** podlegają EULA AMD; AMD *zaleca* ISV dołączenie bibliotek HIP SDK do instalatora ([AMD deployment guidelines](https://rocm.docs.amd.com/projects/install-on-windows/en/docs-6.1.2/conceptual/deployment-guidelines.html) `[STALE?]`, [audio.cpp note](https://github.com/0xShug0/audio.cpp/blob/main/docs/build/windows-hip-distribution.md)). Treść EULA HIP SDK dla 2026 jest **do weryfikacji przez prawnika**.

### 2.5 Model biznesowy

#### 2.5.1 Ceny porównywalnych narzędzi (10.2026)

| Produkt | Licencja kodu | Free | Płatne |
|---|---|---|---|
| **LM Studio** | aplikacja zamknięta | lokalnie za darmo, **także w pracy** (od 07.2025) | Bionic+ 20 $/mies., Pro 100 $/mies. (chmura OSS-modeli w US) ([pricing](https://lmstudio.ai/pricing), [free for work](https://lmstudio.ai/blog/free-for-work) `[STALE?]`) |
| **Ollama** | MIT ([GitHub](https://github.com/ollama/ollama)) | lokalnie bez limitu, starter credits | Pro 20 $/mies. (60 $ kredytów), Max 100 $/mies., Team 500 $/mies., Enterprise (custom) ([pricing](https://ollama.com/pricing)) |
| **Jan** | Apache 2.0 ([GitHub](https://github.com/janhq/jan)) | całość | brak (Menlo Research, robotyka) |
| **Msty Studio** | zamknięta | Free | Aurum 149 $/rok, **Lifetime 349 $**, Teams od 5 stanowisk ([pricing](https://msty.ai/pricing/)) |
| **Raycast** | zamknięta | – | Pro „starting at 8 $/month”; local models tylko w Pro ([raycast.com/pro](https://www.raycast.com/pro), [manual](https://manual.raycast.com/ai/local-models)) |
| **Lossless Scaling** (analogia „boost FPS”) | zamknięta | – | **6,99 $ jednorazowo** (Steam), 2–5 mln właścicieli ([tech-insider](https://tech-insider.org/lossless-scaling-setup-2026/)) |
| **3DMark** (analogia „benchmark”) | zamknięta | demo | 34,99 $ ([steambase](https://steambase.io/games/3dmark/price/)) |
| **UL Procyon AI** (B2B benchmark) | zamknięta | – | site license **od 5000 $/rok** ([FPS Review](https://www.thefpsreview.com/2024/03/26/ul-launches-procyon-ai-image-generation-benchmark-for-5000/) `[STALE?]`) |
| **TensorFold** | Apache-2.0 | całość (beta) | „Buy me a coffee”, NVIDIA Inception, „investment & partnerships” ([tensorfold.dev](https://tensorfold.dev/)) |
| **Strata** | MIT, 25,4 tys. gwiazdek | całość | „Buy me a coffee” ([GitHub](https://github.com/niko1221/strata)) |

**Obserwacja:** cena lokalnej inferencji spadła do zera. Gracze monetyzują **chmurę** (Ollama, LM Studio) albo **funkcje power-user** (Msty, Raycast). Nikt nie sprzedaje „przyspieszenia lokalnego”. Najbliższa analogia konsumencka to Lossless Scaling i NVIDIA Auto-Tuning (w tym drugim przypadku za darmo, od producenta GPU).

#### 2.5.2 Finansowanie local AI (2024–2026)

| Firma | Runda | Uwagi |
|---|---|---|
| **Ollama** | Series B **65 M$** (07.2026, Theory Ventures), łącznie **88 M$** | 8,9 mln developerów miesięcznie, „85% Fortune 500”, prawie 1 mln instalacji tygodniowo ([HPCwire/BusinessWire](https://www.hpcwire.com/aiwire/2026/07/09/ollama-raises-65m-series-b-funding-to-grow-its-open-source-ai-platform/)) |
| **LM Studio (Element Labs)** | około 19,3 M$ (05.2025, wg CB Insights) | `[INFERENCE]`: dane agregatora, niepotwierdzone przez firmę ([CB Insights](https://www.cbinsights.com/company/lm-studio/financials)) |
| **ggml.ai** | pre-seed (Nat Friedman, Daniel Gross) → **dołączenie do HF 02.2026** | ([ggml.ai](https://ggml.ai/), [HF blog](https://huggingface.co/blog/ngxson/ggml-and-llama-cpp-join-hugging-face)) |
| **Hugging Face** | **przejęcie przez NVIDIA za 12,93 mld $** (ogł. 3.09.2026) | ([NVIDIA](https://blogs.nvidia.com/blog/nvidia-to-acquire-hugging-face/)) |
| **Mirai** (on-device SDK, Apple Silicon) | seed 10 M$ (02.2026, Uncork) | ([dealroom](https://dealroom.co/companies/mirai/)) |
| **Jan / Menlo Research** | brak rundy wg Tracxn | ([Tracxn](https://tracxn.com/d/companies/menlo-research/__8OKLZO_Y_maeRUjmI2gryIqUc6TgG6fu0UDV9jVx3nw)) |

**Wniosek:** kapitał płynie do *platform dystrybucji modeli*, nie do optymalizacji. Optymalizacja to raczej **feature do przejęcia** (ggml → HF → NVIDIA) albo usługa B2B `[INFERENCE]`.

#### 2.5.3 Warianty modelu przychodów

| Wariant | Za | Przeciw | Ocena |
|---|---|---|---|
| Całość za darmo + donacje (Strata, TensorFold) | max zasięg | brak przychodu | tylko na fazę 0 |
| **Freemium: free = katalog gotowych profili; płatne „Turbo” = osobisty nocny tuning + re-tuning** | wartość płatna jest mierzalna (karta „przed → po”); koszt krańcowy ≈ 0 (liczy GPU klienta) | jeśli katalog jest za dobry, Turbo jest zbędne; ryzyko kopiowania | **Rekomendowany rdzeń** |
| Jednorazowy zakup (jak Lossless Scaling) | gracze to lubią; prosto | brak finansowania re-tuningu przy każdym nowym modelu i sterowniku; obowiązek aktualizacji (u.p.k.) | jako „Lifetime” early-bird |
| Subskrypcja | finansuje ciągłe strojenie nowych modeli (nowy top model co kilka tygodni) | opór konsumentów wobec subskrypcji „za szybkość” | roczna, tania |
| **B2B / OEM** (integratorzy, producenci laptopów) | profil per SKU wytworzony raz w labie; „AI-ready, tuned” jako argument sprzedaży PC; AMD już bundluje LM Studio i Ollama w Adrenalin | długi cykl sprzedaży; brak potwierdzonych umów OEM z LM Studio lub Ollamą ([wyszukiwanie](https://www.popularai.org/p/best-prebuilt-ai-pcs-for-local-llms-2026), brak dowodów) | **Druga noga**, pilotaż w PL |
| **Tuning-as-a-service / enterprise on-prem** | duże stawki; nasza metoda (agenci + bramki bitowe) skaluje się na nowe modele | sprzedaż konsultingowa; LFM i Qwen-CL wymagają licencji od klientów powyżej progów | **Trzecia noga** |
| Chmura inferencji (jak Ollama, LM Studio) | rynek sprawdzony | sprzeczne z tożsamością „lokalnie”; kapitałochłonne | nie |

#### 2.5.4 Open core czy zamknięty optymalizator?
- **Otwarte (MIT/Apache):** uniwersalne łatki silnika (upstream), CLI do uruchamiania, format profilu, benchmark „Uczciwy pomiar”, czyli wszystko, co buduje zaufanie i społeczność.
- **Zamknięte:** orkiestrator tuningu (agenci, przestrzeń wyszukiwania, bramki KLD/md5), **katalog profili** (dane: efekt sieciowy, każdy opt-in tuning ulepsza free tier dla tej samej karty), harness weryfikacji, panel B2B.
- **Ryzyko:** konkurent (Ollama ma 88 M$, LM Studio) skopiuje zmierzone parametry z otwartych łatek. Fosą są **dane, szybkość dostarczania profili dla nowych modeli i wiarygodność**, nie kod `[INFERENCE]`.

### 2.6 Go-to-market

#### 2.6.1 Społeczności i launch
- **r/LocalLLaMA:** około 849 tys. członków; zasady „Limit Self-Promotion”, wytyczna 1/10 i ujawnienie afiliacji; płatne pitche są źle przyjmowane ([gummysearch](https://gummysearch.com/r/LocalLLaMA/), [intoru](https://intoru.ai/subreddits/localllama); źródła drugorzędne).
  - **Taktyka:** najpierw posty techniczne z powtarzalnymi pomiarami, np. „Qwen3.8-27B 109 t/s na 7900 XTX, bit-identical, 70 łatek, metoda”, z linkiem do otwartych łatek i harnessu. Produkt dopiero później.
- **Hacker News, Show HN:** coś, co ludzie mogą uruchomić; **bez rejestracji i maili**; zakaz proszenia o upvote ([Show HN guidelines](https://news.ycombinator.com/showhn.html)). Społeczność HN karze brak atrybucji i lock-in ([HN 47788385](https://news.ycombinator.com/item?id=47788385)).
- **Leaderboardy jako marketing:**
  - **LocalMaxxing:** 2730 użytkowników, 8726 runów, 629 konfiguracji sprzętu, filtry po silniku i kwantyzacji, API ([localmaxxing.com](https://www.localmaxxing.com/en), [API docs](https://localmaxxing.com/api-docs));
  - **LocalScore** (Mozilla Builders): prompt processing, generation, TTFT; oparty na llamafile ([GitHub](https://github.com/mozilla-ai/llamafile/tree/main/localscore), [HF](https://huggingface.co/Mozilla/LocalScore)).
  - **Taktyka:** przycisk „Opublikuj mój wynik na LocalMaxxing” (opt-in) po nocnym tuningu daje wiralną pętlę `[INFERENCE]`.
- **YouTube:** recenzenci GPU i local AI potrzebują „repro kit” (instalator, skrypt pomiaru, karta wyników). Konkretnych kanałów i ich zasięgów nie weryfikowałem.

#### 2.6.2 Specyfika polska
- **Język:** polski tekst kosztuje około 2,25–2,8 tokenu na słowo, a angielski około 1,2 ([arXiv 2605.24718](https://arxiv.org/html/2605.24718), [arXiv 2604.10799](https://arxiv.org/html/2604.10799v1)). Polak dostaje więc ok. 2× mniej słów/s z tego samego t/s. Hasło: **„Po polsku AI pisze 2× wolniej. Naprawiamy to.”** `[INFERENCE]`
- **Modele PL:**
  - Bielik v3 (Apache 2.0; wydany 1.01.2026; SpeakLeash i ACK Cyfronet AGH) ([pl.wikipedia](https://pl.wikipedia.org/wiki/Bielik_(model_j%C4%99zykowy)));
  - drafter DFlash dla Bielika już istnieje, więc współpraca z SpeakLeash przy przyspieszeniu Bielika na kartach AMD i NVIDIA to naturalny PR;
  - PLLuM tylko w wariantach Apache.
  - Wg promptowy.pl na kartach 8 GB najlepsza po polsku jest Gemma 4 12B (72,3 pkt) ([promptowy](https://promptowy.com/lokalne-ai/); źródło drugorzędne).
- **Media i społeczności:**
  - PurePC (poradnik Ollamy, [link](https://www.purepc.pl/stworz-wlasnego-chatbota-w-5-minut-lokalna-instalacja-modeli-jezykowych-na-linuksie-i-windowsie-poradnik-krok-po-kroku) `[STALE?]`);
  - benchmark.pl (PC do AI, [link](https://www.benchmark.pl/msi-pokazalo-malego-potwora-ten-komputer-kosztuje-20-tys-zl-7337139389696448a));
  - x-kom „Jaki komputer AI” ([link](https://www.x-kom.pl/poradniki/9627-jaki-komputer-ai-co-to-jest-i-do-czego-sluzy.html));
  - AI_devs i Mateusz Chrobok ([aidevs.pl](https://www.aidevs.pl/));
  - SpeakLeash.
- **Kontekst cen sprzętu:**
  - DRAM drożeje o 89% kw/kw (Q2 2026), 64 GB DDR5 kosztuje 1118 $ wobec 191 $ rok wcześniej, RTX 5090 jest około 145% ponad MSRP ([TweakTown](https://www.tweaktown.com/news/112358/dram-prices-surged-by-up-to-89-percent-in-q2-2026-destroying-the-consumer-segment/index.html), [tech-insider](https://tech-insider.org/dram-ram-price-crisis-2026/), [mangothrive](https://mangothrive.com/gpu-shortage-statistics/); część źródeł drugorzędna).
  - **„Nie kupuj nowej karty, podkręć AI na tej, którą masz”** to mocny przekaz w 2026 `[INFERENCE]`.
- **B2B PL:** integratorzy (x-kom, Komputronik, Morele) sprzedają „komputery AI”. Pilotaż „profil przyspieszenia w zestawie” `[INFERENCE]`.
- **Podatki i ulgi:**
  - **IP Box 5%** (wymaga B+R i ewidencji od początku; nexus = 1 dla samodzielnego twórcy; zapowiadane zmiany na 2027) ([interpretacje-podatkowe.org](https://interpretacje-podatkowe.org/ip-box/));
  - piaskownica KRiBSI darmowa dla MŚP ([ktzr.pl](https://www.ktzr.pl/ustawa-o-systemach-sztucznej-inteligencji/)).

---

## 3. Co to znaczy dla naszego produktu

### 3.1 Rekomendowany kształt produktu

**Nazwy robocze** (do sprawdzenia w EUIPO, w domenach i pod kątem kolizji z „llama”, „NVIDIA”, „AMD”):
- **Podkręt** (PL: od „podkręcania”, gra słów z overclockingiem);
- **Nocna Zmiana / NightShift**;
- **Turbina**;
- **Tuned**;
- **Rozpęd**.

Unikać „Llama” w nazwie (znak Meta, a licencja Llama wymaga prefiksu „Llama” tylko dla modeli pochodnych) `[INFERENCE]`.

**Pozycjonowanie:** „Twoje AI, na Twoim komputerze, nawet 2× szybciej. Te same odpowiedzi, bit w bit.”

**Edycje:**

| Edycja | Dla kogo | Zawartość | Cena (hipoteza) |
|---|---|---|---|
| **Free** | laik, gracz | GUI + CLI/TUI; skan sprzętu; 1 polecany model; pobieranie z weryfikacją; baseline; **gotowe profile z katalogu** dla popularnych kart (bitowo bezpieczne); czat; lokalny serwer API (localhost) | 0 |
| **Turbo** | entuzjasta | **Nocny tuning na Twojej maszynie**; re-tuning po aktualizacji sterownika lub modelu; „Tryb maksymalny” (zmiany z bramką KLD, opt-in); raport do LocalMaxxing; priorytet nowych modeli | **39 €/rok** lub **79 € lifetime** (early-bird, pierwsze 1000 sztuk); w PL **149 zł/rok**, **299 zł lifetime** |
| **Business** | MŚP i zespoły | Licencja komercyjna aplikacji; profile flotowe (ta sama konfiguracja na N maszynach); filtr licencji modeli (LFM powyżej 10 M$, Qwen-CL); wsparcie e-mail | **8 €/stanowisko/mies.** (min. 5) |
| **OEM / Integrator** | x-kom, Komputronik, producenci | Profile per SKU z naszego labu, white-label lub co-brand, preinstalacja | **1–3 € za urządzenie** albo ryczałt roczny |
| **Tuning Lab** (usługa) | enterprise on-prem | Strojenie konkretnego modelu × sprzętu klienta (także nowe GPU), raport bitowy i KLD, łatki | **od 5 k€ za model×platformę**; retainer |

**Uzasadnienie cen:**
- Turbo plasuje się między Lossless Scaling (6,99 $) i 3DMark (34,99 $) a Msty Aurum (149 $/rok). Odpowiada mniej więcej jednemu miesiącowi Bionic+ lub Ollama Pro, ale rocznie.
- Kotwica B2B: Procyon od 5000 $/rok.
- **Do walidacji przez fake-door test i A/B cen** `[INFERENCE]`.
- Płatności przez Merchant of Record **Paddle: 5% + 0,50 $**, który rozlicza VAT OSS ([dodopayments](https://dodopayments.com/blogs/paddle-alternatives)).
- Lemon Squeezy migruje do Stripe Managed Payments, około 6,4% + 0,30 $ ([paritydeals](https://www.paritydeals.com/lemon-squeezy-vs-stripe-fees/)). Źródła drugorzędne, do potwierdzenia na stronach dostawców.

**MVP (zakres twardy):**
- **W zakresie:**
  - Windows 11 i Linux; NVIDIA (CUDA) i AMD (ROCm na Linuksie, HIP lub Vulkan na Windows; do decyzji z R3).
  - 4–5 modeli Apache: Qwen3.8-27B, Gemma 4 (rozmiar wg VRAM), gpt-oss-20b, Bielik 11B v3, Mistral Small 4. LFM2.5 tylko w Free i Turbo (konsumenci).
  - GUI (Tauri) i TUI/CLI.
  - Podpisany instalator **z wbudowanym silnikiem** (bez pobierania binarek).
  - Pobieranie z HF z pinem rewizji i sha256.
  - Karta „przed → po” wg protokołu z 2.1.3.
  - Nocny tuning z checkpointami, pauzą, regułami baterii i temperatury oraz limitem TDR.
  - Rollback.
  - PL i EN.
  - Disclosure „AI” (art. 50(1)).
  - Decyzja i implementacja art. 50(2) dla tekstu powyżej 200 tokenów.
  - Telemetria wyłączona domyślnie.
  - Zgłaszanie podatności (CRA).
- **Poza zakresem (faza 2+):**
  - macOS (Metal; DMG z Developer ID, potem ewentualnie MAS „Lite”);
  - Intel Arc, ROCm na Windows w natywnym HIP (jeśli niestabilny);
  - generacja obrazów;
  - RAG i agenci;
  - telefon;
  - chmurowy tuning na wynajętych GPU (R5);
  - katalog uncensored.

**Architektura decyzji wynikających z prawa i dystrybucji** `[INFERENCE]`:
- (a) Profil optymalizacji to **dane** (JSON z parametrami i wyborem wariantów prekompilowanych kerneli), podpisane naszym kluczem. Dzięki temu zgadzamy się z MAS 2.5.2 i MS Store 10.2.2, a SAC się nie odpala.
- (b) Jeżeli lokalny tuning wymaga JIT, to przez NVRTC (redystrybuowalne wg Attachment A) lub hipRTC (MIT), w procesie silnika, bez zapisywania nowych PE.
- (c) Każdy plik PE podpisany.
- (d) Serwer API tylko na localhost, Trusted Hosts.

### 3.2 Checklista prawna (koszty i terminy)

| # | Zadanie | Koszt | Czas | Blokuje |
|---|---|---|---|---|
| 1 | **Spółka z o.o.** przez S24 (opłata sądowa 250 zł; ogłoszenie w MSiG zniesione od 29.11.2025; PCC 0,5% kapitału) ([biurodlamisia](https://blog.biurodlamisia.pl/rejestracja-spolki-z-o-o-przez-s24-z-adresem-wirtualnego-biura-krok-po-kroku/), [kgmlegalit](https://kgmlegalit.pl/jak-zarejestrowac-spolke-w-systemie-s24/)) | około 275 zł + księgowość `[INFERENCE: 500–1000 zł/mies.]` | 1–3 dni rob. | Artifact Signing, Apple (org.), umowy B2B |
| 2 | **D-U-N-S** dla spółki | 0 | do 5 + 2 dni rob. ([Apple](https://developer.apple.com/support/D-U-N-S/)) | Apple org. |
| 3 | **Apple Developer Program** | 99 $/rok | dni (weryfikacja) | macOS, Homebrew |
| 4 | **Azure Artifact Signing** (Basic) | około 9,99 $/mies.; naliczane od utworzenia konta | „kilka dni” walidacji; 3 próby | Windows direct download, winget |
| 4b | Alternatywa: certyfikat OV | 150–300 $/rok + token/HSM | dni–tygodnie | – |
| 5 | **Konto Microsoft Store** | 0 | minuty–dni (ID + selfie) | Store |
| 6 | Steam (opcja) | 100 $ (zwrotne) | 30 dni review `[INFERENCE]` | – |
| 7 | **Znak towarowy EUIPO** (kl. 9 + 42) | 850 € + 50 € ([thaonco](https://thaonco.com/translation-times/legal/eu-trademark-cost/)) + ewentualnie rzecznik | około 4–6 mies. do rejestracji `[INFERENCE]` | nazwa |
| 8 | **EULA, Regulamin (u.ś.u.d.e.), Polityka prywatności PL i EN**, checkbox z art. 38 pkt 13 u.p.k., AUP z flow-down (Gemma ≤3, gpt-oss usage policy) | `[INFERENCE: 8–20 tys. zł]` kancelaria | 2–4 tyg. | sprzedaż |
| 9 | **RODO:** RoPA, DPA z MoR, hostingiem i Sentry, LIA dla interesu prawnego (o ile występuje), mechanizm zgód art. 399 PKE | w pkt 8 | 2 tyg. | telemetria, katalog |
| 10 | **AI Act art. 50:** disclosure w UI; **opinia prawna lub opinia KRiBSI o watermarku tekstu**; ewentualne przystąpienie do Code of Practice | `[INFERENCE: 5–15 tys. zł]`; KRiBSI ma procedurę opinii ([gov.pl](https://www.gov.pl/web/cyfryzacja/ustawa-o-systemach-ai--bezpieczny-rozwoj-sztucznej-inteligencji-w-polsce)) | 1–3 mies. | **launch w UE** |
| 11 | **CRA:** polityka CVD (`security.txt`), SBOM per release, konto ENISA SRP, plan aktualizacji bezpieczeństwa | czas zespołu | przed launchem (raportowanie już obowiązuje) | – |
| 12 | **Odpowiedzialność za produkt (PLD 2024/2853):** OC produktu / OC IT | `[INFERENCE: 2–6 tys. zł/rok]` | 2 tyg. | B2B |
| 13 | **Licencje 3rd-party:** NOTICE (llama.cpp MIT, CUDA Attachment A, ROCm MIT, **EULA HIP SDK do weryfikacji**), LICENSE każdego modelu w katalogu, blokada Llama 4 | czas zespołu + 1 h prawnika | 1 tydz. | release |
| 14 | **Merchant of Record** (Paddle): KYC, VAT OSS po stronie MoR | 5% + 0,50 $ za transakcję | 1–2 tyg. | płatne edycje |
| 15 | **IP Box:** ewidencja B+R od pierwszego dnia, umowy przenoszące prawa autorskie od współpracowników | doradca `[INFERENCE: 2–5 tys. zł/rok]` | ciągłe | optymalizacja podatku |
| 16 | **Dostępność:** WCAG 2.2 AA dla sklepu i aplikacji (EAA: mikrofirma usługowa zwolniona, ale bez okresu przejściowego po przekroczeniu progu) | czas zespołu | przed launchem | sklep |
| 17 | **Umowy B2B** (OEM, Tuning Lab): licencja na profile, SLA, klauzula licencji modeli (LFM i Qwen-CL po stronie klienta) | `[INFERENCE: 5–10 tys. zł]` wzór | 1 mies. | B2B |

**Budżet startowy prawno-dystrybucyjny (rok 1)** `[INFERENCE]`:
- Opłaty twarde: około 99 $ + 120 $ + 900 € + 275 zł ≈ **5,8 tys. zł**.
- Z kancelarią i ubezpieczeniem: **około 30–55 tys. zł**.

**Ścieżka krytyczna:** spółka → D-U-N-S i Artifact Signing → podpisany beta. Równolegle: opinia o art. 50(2) (najdłuższa, 1–3 mies.).

### 3.3 Rejestr ryzyk

| ID | Ryzyko | P | W | Mitigacja | Sygnał wczesny |
|---|---|---|---|---|---|
| R1 | **Ollama, LM Studio, Jan lub NVIDIA wbudują auto-tuning** (NVIDIA ma Auto-Tuning GPU i teraz HF; Jan ma już MTP i router) | W | W | Szybkość profili dla nowych modeli, katalog danych, wiarygodność bitowa, AMD-first (słabiej obsłużone); pozycja „partner” (bundle AMD) | changelogi Jan, LM Studio, Ollamy |
| R2 | **Art. 50(2) AI Act**: obowiązek watermarku tekstu koliduje z „bit w bit” albo wymaga detektora | Ś | W | Opinia prawna lub KRiBSI; watermark jako warstwa identyczna przed i po; monitoring praktyki konkurencji | wytyczne AI Office, decyzje KRiBSI |
| R3 | **Fałszywe alarmy AV i SmartScreen** przy launchu (reputacja od zera) | W | Ś | Podpis każdego PE, Artifact Signing, MS Store jako główny kanał Windows, zgłoszenia do Defendera przed release | zgłoszenia userów, VirusTotal |
| R4 | **Zysk nie generalizuje** poza 7900 XTX i Qwen3.8 (inne GPU, sterowniki, modele) | Ś | W | Mierzyć w labie top 10 GPU przed obietnicą; komunikować „do X%”; pokazywać medianę | pierwsze profile społeczności |
| R5 | **Niestabilność podczas nocnego tuningu** (TDR, crash systemu, przegrzanie laptopa) | Ś | W | Limity kandydatów, blacklista, checkpointy, tryb laptop, brak zmian w rejestrze TDR, temperatury | crash reports (opt-in) |
| R6 | **Zarzut wprowadzania w błąd** („2×”) | Ś | Ś | Protokół „Uczciwy pomiar”, raport do pobrania, brak porównań z konkurencją w UI | recenzje, UOKiK |
| R7 | **Licencje modeli zmieniają się** (np. Qwen przeszedł częściowo na Community License; LFM ma próg) | Ś | Ś | Licencja jako metadana w katalogu; automatyczna blokada; przegląd przy każdym nowym modelu | LICENSE diff w CI |
| R8 | **Zależność od HF** (przejęcie przez NVIDIA, zmiana rate limits) | N–Ś | W | Mirror R2 dla modeli Apache; pin rewizji; pobieranie wieloźródłowe | zmiany w HF ToS |
| R9 | **Utrata klucza podpisu aktualizacji** (Tauri: brak aktualizacji dla istniejących instalacji) | N | W | Klucz w HSM lub Key Vault, procedura rotacji (pubkey w runtime) | – |
| R10 | **Backlash społeczności** (atrybucja, zamknięty kod, „closed fork llama.cpp”) | Ś | Ś | Credit w UI, upstream łatek, otwarty harness i format profilu, model folder współdzielony | wątki r/LocalLLaMA i HN |
| R11 | **Treści szkodliwe / uncensored** w naszej marce lub sklepach | Ś | Ś | Brak w katalogu i marketingu; import GGUF jako „advanced” z AUP; brak obrazów (art. 5 od 2.12.2026) | zgłoszenia, odrzucenia w Store |
| R12 | **RODO/ePrivacy** (telemetria bez ważnej zgody; IP w logach) | N | Ś | Opt-in, podgląd JSON, odrzucanie IP przy ingest, hosting w UE | audyt |
| R13 | **CRA i PLD**: incydent bezpieczeństwa (np. serwer API wystawiony na LAN) | N–Ś | W | localhost-only, Trusted Hosts, SBOM, CVD, aktualizacje | raporty bezpieczeństwa |
| R14 | **Brak kwalifikacji do Artifact Signing** (forma prawna, dokumenty) | N | Ś | Spółka z o.o. z D-U-N-S; plan B: OV z HSM | odrzucenie walidacji |
| R15 | **Koszt wsparcia platform** (Jan porzucił Intel Mac; ROCm na Windows) | W | Ś | Twarde MVP (Win + Linux, NV + AMD), macOS w fazie 2 | liczba ticketów per platforma |
| R16 | **Kanibalizacja**: darmowy katalog profili czyni Turbo zbędnym | Ś | Ś | Free: profile „bezpieczne, uśrednione”; Turbo: profil *twojej* maszyny, re-tuning, tryb max; mierzyć konwersję | konwersja < 1% |
| R17 | **Ceny sprzętu** zmniejszają bazę nowych GPU (mniej kart 24 GB+) | Ś | N–Ś | To wzmacnia przekaz „wyciśnij stary sprzęt”; wspierać 8–16 GB | dane z katalogu |

P/W: W = wysokie, Ś = średnie, N = niskie.

### 3.4 Otwarte pytania (do decyzji Main lub prawnika)
1. **Art. 50(2):** watermark tekstu w lokalnej aplikacji: obowiązek, sposób, wpływ na bit-identyczność. Kto pyta KRiBSI lub kancelarię i kiedy?
2. **Windows AMD:** HIP SDK (EULA, redystrybucja DLL) czy Vulkan jako backend MVP? (z R3/R4)
3. **Forma prawna** (sp. z o.o. vs JDG plus IP Box): wpływa na Artifact Signing (organizacja) i Apple (D-U-N-S).
4. **Czy profil jest „kodem”?** Jeśli tuning potrzebuje generacji nowych kerneli (JIT) per maszyna, to MAS odpada, a MS Store wymaga opisania funkcji.
5. **Katalog profili jako dane:** czy anonimowy ingest (bez IP i ID) wystarczy, by wyjść spod RODO po stronie serwera? (SRB C-413/23 P mówi „zależy”.)
6. **Polityka Llama 4 i Qwen-CL:** wykluczenie czy osobne licencje?
7. **Ceny:** fake-door test 149 zł/rok vs 299 zł lifetime vs 19 zł/mies. przed implementacją płatności.

---

## 4. Źródła

**Produkty i UX**
- LM Studio: [pricing](https://lmstudio.ai/pricing) · [free for work (07.2025)](https://lmstudio.ai/blog/free-for-work) · [0.3.27 guardrails](https://lmstudio.ai/blog/lmstudio-v0.3.27) · [onboarding (techjacksolutions)](https://techjacksolutions.com/ai-tools/lm-studio/how-to-use-lm-studio/) · [Locally AI, App Store](https://apps.apple.com/us/app/locally-ai-by-lm-studio/id6741426692) · [Defender FP #1686](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1686)
- Ollama: [pricing](https://ollama.com/pricing) · [new app (07.2025)](https://ollama.com/blog/new-app) · [GitHub (MIT)](https://github.com/ollama/ollama) · [Series B (HPCwire)](https://www.hpcwire.com/aiwire/2026/07/09/ollama-raises-65m-series-b-funding-to-grow-its-open-source-ai-platform/) · [HN: „doesn't need Ollama”](https://news.ycombinator.com/item?id=47788385) · [Windows Central](https://www.windowscentral.com/artificial-intelligence/ollamas-new-app-makes-using-local-ai-llms-on-your-windows-11-pc-a-breeze-no-more-need-to-chat-in-the-terminal)
- Jan: [0.8.5 release notes (freedom.tech)](https://freedom.tech/posts/2026-10-08-jan-0-8-5/) · [Manage models](https://www.jan.ai/docs/desktop/manage-models) · [GitHub (Apache 2.0)](https://github.com/janhq/jan) · [Menlo (Tracxn)](https://tracxn.com/d/companies/menlo-research/__8OKLZO_Y_maeRUjmI2gryIqUc6TgG6fu0UDV9jVx3nw)
- Msty: [pricing](https://msty.ai/pricing/) · Raycast: [Local Models](https://manual.raycast.com/ai/local-models) · [Pro](https://www.raycast.com/pro)
- NVIDIA App: [launch](https://www.nvidia.com/en-us/geforce/news/nvidia-app-download-and-features/) · [TechPowerUp](https://www.techpowerup.com/review/nvidia-app-v1-0/3.html) · [Wccftech](https://wccftech.com/nvidia-app-1-click-auto-gpu-tuning-120-fps-av1-recording-g-assist-dynamically-tune-gpu-record-statistics-change-game-settings/)
- AMD AI Bundle: [TweakTown](https://www.tweaktown.com/news/109821/amds-adrenalin-edition-software-for-radeon-now-includes-an-optional-ai-bundle/index.html) · [Wccftech](https://wccftech.com/amd-rolls-out-adrenalin-edition-26-1-1-introducing-the-ai-bundle-and-support-for-ryzen-ai-400-series/)
- Strata: [GitHub](https://github.com/niko1221/strata) · TensorFold: [tensorfold.dev](https://tensorfold.dev/)
- Czytanie i percepcja: [Brysbaert 2019](https://www.semanticscholar.org/paper/How-many-words-do-we-read-per-minute-A-review-and-Brysbaert/35bf5854514ee63095a6a3dc4a7bdaa2eb18929f) · [NN/g response times](https://www.nngroup.com/articles/response-times-3-important-limits/)
- Tokenizery: [arXiv 2604.10799 (Bielik v3 tokenizer)](https://arxiv.org/html/2604.10799v1) · [arXiv 2605.24718 (Tokenizer Tax)](https://arxiv.org/html/2605.24718) · [Dawidek](https://elzbietadawidek.substack.com/p/the-source-of-a-polish-tokenizer)
- Windows TDR: [MS Learn](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/tdr-registry-keys) · [GetLastInputInfo](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getlastinputinfo)
- Dostępność i i18n: [WCAG 2.2](https://www.w3.org/TR/WCAG22/) · [CLDR plural rules](https://www.unicode.org/cldr/charts/latest/supplemental/language_plural_rules.html) · [EAA e-commerce](https://accessible.org/eaa-ecommerce-services-requirements/) · [EAA microenterprise](https://goingstellar.ro/research/european-accessibility-act-online-stores/) · [EAA apps](https://www.raftlabs.com/blog/european-accessibility-act-guide)

**Prywatność, AI Act, regulacje**
- [EDPB Guidelines 2/2023 (Hunton)](https://www.hunton.com/privacy-and-information-security-law/edpb-adopts-guidelines-on-scope-of-eprivacy-directive) · [gdprbuzz](https://gdprbuzz.com/resources/edpb-guidelines-eprivacy-directive/)
- [PKE art. 399 (witly)](https://witly.ai/news/cookie-consent) · [PKE (mkz)](https://mkzpartnerzy.pl/prawo-komunikacji-elektronicznej/)
- [TSUE C-582/14 Breyer](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62014CJ0582) · [TSUE C-413/23 P SRB](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A62023CJ0413) · [Bird & Bird o SRB](https://www.twobirds.com/en/insights/2025/eu-the-srb-decision-a-new-era-for-personal-data-and-data-processing-agreements)
- [Digital Omnibus (Usercentrics)](https://usercentrics.com/knowledge-hub/eu-digital-omnibus-package/) · [ppc.land ePrivacy](https://ppc.land/eprivacy-directive/) · [kary RODO (cenkier)](https://cenkier.pl/artykuly/rodo-w-2026-co-kontroluje-uodo-i-jakie-kary-naklada/)
- AI Act: [art. 50](https://artificialintelligenceact.eu/article/50/) · [Paul Weiss: Guidelines + Code (08.2026)](https://www.paulweiss.com/insights/client-memos/eu-finalises-transparency-rules-for-ai-generated-content) · [EC Code of Practice](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content) · [Reed Smith](https://www.reedsmith.com/our-insights/blogs/viewpoints/102nbz0/transparency-obligations-for-ai-generated-content-the-code-of-practice-adequacy/) · [Cooley: Omnibus 2026/1744](https://cdp.cooley.com/digital-ai-omnibus-delays-key-deadlines-introduces-new-rules/) · [Orrick: GPAI guidelines](https://www.orrick.com/en/Insights/2025/08/EU-Commission-Guidelines-on-the-scope-of-the-obligation-for-GPAI-models-under-the-AI-Act) · [Modulos](https://docs.modulos.ai/frameworks/eu-ai-act/commission-guidance/gpai-models) · [OpenForum Europe (OSS)](https://openforumeurope.org/understanding-the-ai-act-open-source-key-updates-march-2025/) · [explainx (watermark w samplerze)](https://explainx.ai/blog/will-all-ai-models-watermark-output-2026)
- Polska ustawa o AI: [gov.pl](https://www.gov.pl/web/cyfryzacja/ustawa-o-systemach-ai--bezpieczny-rozwoj-sztucznej-inteligencji-w-polsce) · [ktzr.pl](https://www.ktzr.pl/ustawa-o-systemach-sztucznej-inteligencji/) · [infor.pl](https://www.infor.pl/prawo/nowosci-prawne/7668177,ustawa-o-systemach-sztucznej-inteligencji-od-28-pazdziernika-2026-obowiazki-firm-i-kary-co-to-jest-kribsi.html)
- CRA: [Komisja](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act) · [CRA reporting](https://digital-strategy.ec.europa.eu/en/policies/cra-reporting) · PLD: [EUR-Lex 2024/2853](https://eur-lex.europa.eu/eli/dir/2024/2853/oj/eng) · [IBA](https://www.ibanet.org/European-Product-Liability-Directive-liability-for-software)
- UCPD: [Dyrektywa 2005/29/WE](https://eur-lex.europa.eu/eli/dir/2005/29/oj) · Prawa konsumenta: [art. 43k](https://lexlege.pl/ustawa-o-prawach-konsumenta/art-43k/) · [nowelizacja 2022](https://orka.sejm.gov.pl/proc9.nsf/ustawy/2425_u.htm)
- Uncensored i bezpieczeństwo: [slash-digital](https://slash-digital.io/en/insights/uncensored-models/) · [aiidelist](https://aiidelist.com/blog/hugging-face-disabled-offensive-cyber-glm-5-3-model) · [The Register / Cisco Talos](https://www.theregister.com/2025/09/02/exposed_ollama_servers_insecure_research/)

**Dystrybucja**
- Windows: [Code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options) · [Distribution feature status (EV)](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/distribution-feature-status) · [Artifact Signing quickstart](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart) · [FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq) · [Pricing](https://azure.microsoft.com/en-us/pricing/details/artifact-signing/) · [MS Q&A autónomo](https://learn.microsoft.com/en-us/answers/questions/6034844/azure-artifact-signing-eligibility-of-a-spanish-so?page=1) · [SmartScreen reset](https://learn.microsoft.com/en-us/answers/questions/5900208/smartscreen-reputation-reset-following-ev-certific) · [Smart App Control (Q&A)](https://learn.microsoft.com/en-us/answers/questions/5791210/application-signed-and-blocked-by-smart-app-contro) · [Windows Security Book](https://learn.microsoft.com/en-us/windows/security/book/application-security-application-and-driver-control) · [SSL.com 458 dni](https://www.ssl.com/faqs/which-code-signing-certificate-do-i-need-ev-ov) · [DigiCert 459 dni](https://docs.digicert.com/en/certcentral/order-and-manage-certificates/reports-and-advisories/end-of-2-and-3-year-public-code-signing-certificates.html)
- Microsoft Store: [free registration](https://blogs.windows.com/windowsdeveloper/2025/09/10/free-developer-registration-for-individual-developers-on-microsoft-store/) · [Store policies](https://learn.microsoft.com/en-us/windows/apps/publish/store-policies) · winget: [validation](https://learn.microsoft.com/en-us/windows/package-manager/package/winget-validation) · [MSEndpointMgr](https://msendpointmgr.com/2026/07/30/is-winget-enterprise-ready/)
- Apple: [membership](https://developer.apple.com/programs/whats-included/) · [enroll](https://developer.apple.com/programs/enroll/) · [D-U-N-S](https://developer.apple.com/support/D-U-N-S/) · [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) · [Sequoia Gatekeeper](https://appleinsider.com/articles/24/08/06/apple-removes-control-click-option-for-skipping-gatekeeper-in-macos-sequoia) · Homebrew: [Workbrew](https://workbrew.com/blog/homebrew-5-0-0) · [fleetdm #43484](https://github.com/fleetdm/fleet/issues/43484)
- Linux: [rocm-flatpak](https://github.com/night199uk/rocm-flatpak) · [Flathub Blender #180](https://github.com/flathub/org.blender.Blender/issues/180)
- Steam: [Steam Direct](https://partner.steamgames.com/steamdirect) · [onboarding](https://partner.steamgames.com/doc/gettingstarted/onboarding)
- Updater: [Tauri updater](https://v2.tauri.app/plugin/updater/) · [Velopack](https://velopack.io/)
- AV FP: [llama.cpp #28224](https://github.com/ggml-org/llama.cpp/issues/28224) · [koboldcpp #1649](https://github.com/LostRuins/koboldcpp/issues/1649)
- Hosting: [HF rate limits](https://github.com/huggingface/hub-docs/blob/main/docs/hub/rate-limits.md) · [HF storage/Xet](https://huggingface.co/docs/hub/storage-backends) · [HF API tree (sha256)](https://huggingface.co/api/models/speakleash/Bielik-11B-v3.0-Instruct-GGUF/tree/main) · [NVIDIA → HF](https://blogs.nvidia.com/blog/nvidia-to-acquire-hugging-face/) · [R2 pricing (mecanik)](https://mecanik.dev/en/posts/cloudflare-r2-pricing-explained-real-costs-vs-s3-and-backblaze/) · [R2 (filebase)](https://filebase.com/blog/cloudflare-r2-pricing-costs-savings-and-alternatives-in-2026/)

**Licencje**
- llama.cpp/ggml: [HF blog](https://huggingface.co/blog/ngxson/ggml-and-llama-cpp-join-hugging-face) · [Simon Willison](https://simonwillison.net/2026/Feb/20/ggmlai-joins-hugging-face/) · [ggml.ai](https://ggml.ai/)
- Qwen: [Qwen3.8 HF API](https://huggingface.co/api/models?search=Qwen3.8&author=Qwen&limit=20) · [Qwen Community License 1.0](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/raw/main/LICENSE)
- LFM: [LFM2.5-24B-A2B LICENSE](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/raw/main/LICENSE) · [liquid.ai/lfm-license](https://www.liquid.ai/lfm-license)
- Gemma: [Gemma 4 Apache](https://ai.google.dev/gemma/docs/gemma_4_license) · [9to5Google](https://9to5google.com/2026/04/02/google-gemma-4) · [Gemma Terms](https://ai.google.dev/gemma/terms.md.txt)
- Llama: [Llama 4 AUP](https://www.llama.com/llama4/use-policy/) · [Llama 4 license](https://www.llama.com/llama4/license/)
- Mistral: [Mistral 3](https://mistral.ai/news/mistral-3/) · [Magistral](https://mistral.ai/news/magistral/) · [Ministraux](https://mistral.ai/news/ministraux/) · [datanorth](https://datanorth.ai/blog/the-complete-guide-to-mistral-ai)
- gpt-oss: [OpenAI](https://openai.com/index/introducing-gpt-oss/) · [HF](https://huggingface.co/openai/gpt-oss-120b)
- Bielik: [GGUF (Apache 2.0)](https://huggingface.co/speakleash/Bielik-11B-v3.0-Instruct-GGUF) · [DFlash](https://huggingface.co/speakleash/Bielik-11B-v3.0-DFlash) · [pl.wikipedia](https://pl.wikipedia.org/wiki/Bielik_(model_j%C4%99zykowy)) · PLLuM: [pl.wikipedia](https://pl.wikipedia.org/wiki/PLLuM)
- CUDA: [EULA + Attachment A](https://docs.nvidia.com/cuda/eula/index.html) · ROCm: [license](https://rocm.docs.amd.com/en/latest/about/license.html) · [Windows deployment guidelines](https://rocm.docs.amd.com/projects/install-on-windows/en/docs-6.1.2/conceptual/deployment-guidelines.html) · [audio.cpp HIP note](https://github.com/0xShug0/audio.cpp/blob/main/docs/build/windows-hip-distribution.md)

**Biznes i GTM**
- [CB Insights: LM Studio](https://www.cbinsights.com/company/lm-studio/financials) · [Mirai (dealroom)](https://dealroom.co/companies/mirai/) · [Lossless Scaling](https://tech-insider.org/lossless-scaling-setup-2026/) · [3DMark](https://steambase.io/games/3dmark/price/) · [UL Procyon 5000 $](https://www.thefpsreview.com/2024/03/26/ul-launches-procyon-ai-image-generation-benchmark-for-5000/)
- Płatności: [Paddle (dodopayments)](https://dodopayments.com/blogs/paddle-alternatives) · [Lemon Squeezy / SMP (paritydeals)](https://www.paritydeals.com/lemon-squeezy-vs-stripe-fees/)
- Społeczności: [r/LocalLLaMA stats](https://gummysearch.com/r/LocalLLaMA/) · [r/LocalLLaMA rules (intoru)](https://intoru.ai/subreddits/localllama) · [Show HN guidelines](https://news.ycombinator.com/showhn.html) · [LocalMaxxing](https://www.localmaxxing.com/en) · [LocalMaxxing API](https://localmaxxing.com/api-docs) · [LocalScore](https://github.com/mozilla-ai/llamafile/tree/main/localscore) · [LocalScore HF](https://huggingface.co/Mozilla/LocalScore)
- Polska: [PurePC](https://www.purepc.pl/stworz-wlasnego-chatbota-w-5-minut-lokalna-instalacja-modeli-jezykowych-na-linuksie-i-windowsie-poradnik-krok-po-kroku) · [benchmark.pl](https://www.benchmark.pl/msi-pokazalo-malego-potwora-ten-komputer-kosztuje-20-tys-zl-7337139389696448a) · [x-kom poradnik](https://www.x-kom.pl/poradniki/9627-jaki-komputer-ai-co-to-jest-i-do-czego-sluzy.html) · [AI_devs](https://www.aidevs.pl/) · [promptowy: lokalne AI](https://promptowy.com/lokalne-ai/) · [IP Box](https://interpretacje-podatkowe.org/ip-box/) · [S24 (biurodlamisia)](https://blog.biurodlamisia.pl/rejestracja-spolki-z-o-o-przez-s24-z-adresem-wirtualnego-biura-krok-po-kroku/) · [S24 (kgmlegalit)](https://kgmlegalit.pl/jak-zarejestrowac-spolke-w-systemie-s24/) · [EUIPO fees (thaonco)](https://thaonco.com/translation-times/legal/eu-trademark-cost/)
- Ceny sprzętu: [TweakTown DRAM](https://www.tweaktown.com/news/112358/dram-prices-surged-by-up-to-89-percent-in-q2-2026-destroying-the-consumer-segment/index.html) · [tech-insider DRAM](https://tech-insider.org/dram-ram-price-crisis-2026/) · [mangothrive GPU](https://mangothrive.com/gpu-shortage-statistics/)
- Materiały wewnętrzne: [`~/KERNEL/README.md`](../../README.md) · `~/KERNEL/scripts/sysinfo.sh` · `~/KERNEL/qwen-opt/NOTES.md`
