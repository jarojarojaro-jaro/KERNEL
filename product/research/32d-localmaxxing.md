# 32d — LocalMaxxing: API, weryfikacja, dane dla naszych kart i plan wpisów

Data: 2026-10-20. Autor: agent Res32dLocalmaxxing (tylko research, bez GPU i bez konta).
Zakres to **delta** względem R04 / R06 / R15b / R15c (`ZRODLA.md:112`). Nie powtarzam audytu tqLLM 273.1 z R15c, rankingu popularności GPU z R04 §2.4.2 ani taktyki „przycisk publikacji” z R06 §2.6.1.
Próbka danych: ~45 zapytań GET do publicznego API (`/api/leaderboard`, `/api/speed-tests`, `/api/agent-context`, `/api/openapi.json`), odstęp 1.5–2 s, 1 864 unikalne wiersze. Surowe pliki: `/tmp/res-localmaxxing/` (poza repo). Klon CLI: `/tmp/res-localmaxxing/cli` @ `fce3306` (2026-10-15).
Konwencje: `[INFERENCE]` = wniosek własny, niezmierzony. „mal” = średnia liczba tokenów na przebieg targetu (`specMeanAcceptedLength`).

## TL;DR

1. **Na RX 7900 XTX nie ma dziś ANI JEDNEGO runu `verifiedRun: true` dla żadnego modelu.** Zapytanie `hardwareName=7900 XTX&verifiedRun=true` zwraca `total: 0`. Dla Qwen3.8-27B jest na XTX 30 runów, wszystkie niezweryfikowane. Najwyższy to 318.2 t/s hipfire na prompcie merge-sort (157 tokenów, mal 14.3). Nasza topka przy T=0 na `reasoning-v1` powinna dać ok. **130–145 t/s** `[INFERENCE]`. Byłoby to pierwsze miejsce verified na XTX i wynik wyższy niż verified R9700 z hipfire (111.6). Koszt: ~10 min GPU i konto użytkownika (GitHub/HF, klucz `bhk_…`).
2. **Ich „Verified” to kontrola spójności, a nie dowód.** Sprawdzają hash kanonicznego promptu, batch 1, ≥256 tokenów, statystyki draftu i sufit pasma × mal × 1.15. Sufit da się jednak obliczyć tylko w 52 ze 177 zweryfikowanych runów w próbce: dla kwantów własnych (TQ3_4S, MQ4V2) dostajemy `unavailable` i kontrola nie działa. **Ciepła mapa n-gramów przechodzi weryfikację:** Bonsai 27B na 5080 ma „Verified” 854.5 t/s przy akceptacji 100%, zmierzone po powtórkach tego samego zadania. Nonce w pierwszej linii unieważnia tylko cache prefiksu, a nie cache n-gramów między zapytaniami. Dla nas wniosek: **publikować tylko runy „fresh”** (świeży serwer albo `LLAMA_SPEC_LOOKUP=0`), z jawną adnotacją.
3. **Te same kanoniczne prompty wystawiają nam uczciwą ocenę na NVIDIA.** Wyniki verified na 3090 (reasoning-v1, T=0):
   - upstream llama.cpp UD-Q4_K_XL: plain 41.3, MTP n=3 80.4, DFlash2 n=3 81.9;
   - vLLM MTP: 105.4;
   - exllamav3 + DFlash2: 164.6 (EXL3 3.5 bpw) i 242.1 (EXL3 4.0 bpw);
   - tqLLM: 273.1.

   Na 5060 Ti tqLLM ma **nowe** verified 156.2 / 100.5 (2026-10-10). Nasza cuda-topka2 (MTP n=4) zmieściłaby się szacunkowo w **110–125 t/s na 3090** i **75–85 t/s na 5060 Ti** `[INFERENCE]`. To pierwsze miejsce wśród GGUF/llama.cpp, ale nie w ogóle. Przewaga konkurencji to mal 6.0–6.8 (DFlash2 szerokości 7–9, drzewo) wobec ~4 przy MTP. Ta sama dźwignia jest już opisana u nas (R16i, R21a). LocalMaxxing jest po prostu publiczną tablicą, która ją pokazuje.
4. **API jest kompletne i publiczne (OpenAPI 3.1, v1.7.0), bez klucza do odczytu.** Zapis wymaga klucza i ma limit 30 runów na godzinę. **Nie ma otwartej licencji na dane:** treść należy do autorów, a serwis ma tylko prawo ją wyświetlać. Twierdzenie, że „kod strony jest MIT na GitHubie”, jest **fałszywe co do serwera**: publiczne jest tylko CLI. W katalogu Podkręt nie republikujemy ich wierszy. Możemy linkować i publikować własne runy, które pozostają naszą własnością.
5. **Baza sprzętu nie zawiera cen ani pasma w formie tabeli.** Strona `/en/hardware` pokazuje tylko liczbę runów i użytkowników oraz best/median/min tok/s z mieszanki modeli i batchy, więc „Best 5.0k tok/s” na 3090 nic nie znaczy. Pasmo z linkiem do źródła producenta jest w `decodeCeiling` każdego runu (XTX 960, 3090 936.2, 5090 1792, 3060 360 GB/s). Ceny są tylko jako rzadkie, osobiste `hardwareCost` (3 z ~1 900 wierszy). **LFM2.5-24B-A2B ma 0 runów** w całej bazie, więc to wolne miejsce.

## 1. Czym jest LocalMaxxing (delta od R04/R06)

- **Operator:** „LocalMaxxing” / [@lottolabs](https://x.com/lottolabs), org GitHub [LottoLottoLotto](https://github.com/LottoLottoLotto). Konto `Lottolabs` samo publikuje raporty: dual 3090, Tenstorrent P150, Terminal-Bench. Ta sama org ma fork Strata (`LottoLottoLotto/Strata`, push 2026-10-13).
  - CLI dodaje Strata, FreeToken, NInfer i „Actual Computer's e” jako silniki „first-class” z domyślnymi repozytoriami (`cmd/lmx/main.go:3793-3803`).
  - Model biznesowy: Pro przez Stripe, wypożyczalnia endpointów z prowizją, marketplace sprzętu, reklamy (polityka prywatności).
  - Możliwy konflikt interesów: operator promuje część silników. Na liczby to nie wpływa, bo są zgłoszeniami użytkowników.
- **Skala (strona główna 2026-10-20):** 2 796 użytkowników, 9 445 runów, 666 konfiguracji sprzętu, 839 uruchomionych modeli, 1 174 runy ewaluacji, 9 suit, 1 aktywna wypożyczalnia. R04 (2026-10-15) podawał 2 757 / 8 928, czyli **+517 runów w ~5 dni (~100 dziennie)**.
- **Pochodzenie danych:** wyłącznie zgłoszenia użytkowników przez CLI `lmx`, API albo formularz. Brak własnych pomiarów serwisu. Automatyczne kontrole opisuje §3. Admini mogą ukrywać i przywracać runy oraz nadawać status „verified user” (warunki, `/en/terms`, 2026-10-04).
- **Świeżość:** najnowsze runy w próbce są z 2026-10-19 (NInfer 5090, vLLM 3090). Rozkład miesięczny próbki: kwiecień 96 → lipiec 399 → październik 166 (do 19.10). Ostatni commit CLI `fce3306` z 2026-10-15. `llms.txt` ma „Last Updated 2026-06-12”, więc jest nieaktualny wobec API 1.7.0.

## 2. API, CLI, licencja i jak się podłączyć

| element | stan | dowód |
|---|---|---|
| OpenAPI 3.1 | `GET /api/openapi.json`, „LocalMaxxing API” 1.7.0, 44 ścieżki | `/tmp/res-localmaxxing/openapi.json` |
| Bootstrap dla agentów | `GET /api/agent-context`: enumy, 160 kanonicznych nazw GPU, schematy, kanoniczne prompty z SHA-256, reguły verified | `api_agent-context` |
| Odczyt publiczny | `/api/leaderboard` (filtry: `hfId` jako substring, `hardwareName`, `memTier`, `engineName`, `quantization`, `verifiedRun=true`, `backend`, `batchSize`, `contextLen`, `since`, `limit`, `offset`), `/api/speed-tests` (`gpuName` dokładnie, `specOnly`, `mtpOnly`, `date*`, `username`), `/api/models/search`, `/api/inference-benchmarks?hfId=` | OpenAPI `paths` |
| Zapis | `POST /api/speed-tests` (+ `/dry-run`, które nie zużywa limitu), `PATCH/DELETE /api/runs/{id}` (edycja do 24 h), `POST /api/models/{org}/{name}/reports` (raport GFM), `POST /api/inference-benchmarks` (macierze vLLM/SGLang) | `llms.txt`, `_meta` w agent-context |
| Auth | `Authorization: Bearer bhk_<40 hex>`, logowanie tylko przez GitHub/HF, 10 kluczy (Pro 25) | `/en/terms` |
| Limity | speed-testy i ewaluacje 30/h (Pro 300), raporty 3/24 h i 25 łącznie (Pro 30/500), komentarze 60/h; nagłówki `X-RateLimit-Remaining` / `-Reset`. **Brak udokumentowanego limitu odczytu**: 45 zapytań przeszło bez 429. | `/en/terms`, `_meta.rateLimitHeaders` |
| robots.txt | `Allow: /`. Zakazane strony szczegółów `/*/models/*`, `/*/hardware/*`, `/*/runs`, `/*/user`, `/*/benchmarks/*` (wymagają logowania). **`/api/` jest dozwolone** poza `/api/admin/`. Boty AI są wprost zaproszone. | `robots.txt` |
| Sitemap | `sitemap.xml` (351 KB) | — |
| Licencja danych | „You keep ownership… you give LocalMaxxing permission to store it and show it publicly”. **Brak licencji dla stron trzecich** (ani CC, ani ODbL). | `/en/terms` § Content you post |
| Licencja kodu | CLI MIT ([localmaxxing-cli](https://github.com/LottoLottoLotto/localmaxxing-cli), 40★). Serwera **nie ma** w żadnym publicznym repo org (6 repo, API GitHub). | `/en/privacy` mówi „site's source code is open source”, link prowadzi do repo CLI |
| Pełne treści raportów | tylko po zalogowaniu (strona `/en/models/.../reports/<id>`), brak `GET /api/reports/{id}` w OpenAPI (jest tylko `PATCH`) | OpenAPI |

**Jak się podłączyć (uczciwie wobec ToS):**
- *Odczyt do śledzenia konkurencji:* raz dziennie po kilka zapytań `GET /api/leaderboard?hfId=Qwen3.8-27B&hardwareName=<karta>&verifiedRun=true` dla naszych 6–8 kart, z cache po naszej stronie. To ~10 zapytań dziennie, dozwolone przez robots. Danych nie republikujemy. W Podkręcie pokazujemy najwyżej link „porównaj na LocalMaxxing” albo agregat z atrybucją `[INFERENCE: interpretacja prawna; przy wątpliwości zapytać @lottolabs przez issue w repo CLI]`.
- *Wysyłanie naszych wyników:* konto użytkownika, potem `POST /api/speed-tests/dry-run`, odczyt `verification.issues`, potem `POST /api/speed-tests`. Treść należy do nas, więc ten sam JSON możemy opublikować u siebie.
- **CLI nie generuje dowodów do verified.** `toBenchmarkSubmit` tylko przepisuje pola `promptSha256`, `promptSample`, `outputSha256`, `outputSample` i `engineTimingsRaw` (`cmd/lmx/main.go:5333-5345`). Dokumentacja wprost mówi: „The CLI preserves supplied evidence; it does not create missing measurements” (`skill/references/speed-tests.md:157`). Tryb remote dokleja tylko nonce (`main.go:6512-6519`) i nie czyta `timings.draft_n`. **Potrzebny jest nasz mały skrypt** (opis w §5). Pole `--canonical-prompt` z R15c X2 w CLI nie istnieje, to była nadinterpretacja.

## 3. Weryfikacja: co naprawdę sprawdzają (adwersaryjnie)

Reguły (`/api/agent-context` → `verifiedRun.requirements`):
1. sha256 promptu bez linii nonce równa się jednemu z `canonicalPrompts`. Sprawdziłem: sha256 tekstu z kontekstu zgadza się z opublikowanym, zarówno dla `reasoning-v1`, jak i `code-v1`;
2. `promptSample` równa się tekstowi kanonicznemu, `outputSample` jest niepusty, `engineTimingsRaw` jest obecny;
3. `batchSize` = 1, `concurrency` ≤ 1, `outputTokens` ≥ 256;
4. przy spec/MTP: `specDraftTokens` + `specAcceptedTokens`. Gdy podano `specNumTokens`: accepted + draft/num ≈ outputTokens; mal jest obcinane do num+1;
5. `tokSOut` ≤ sufit × 1.15, gdzie sufit = (pasmo / bajty wag) × mal. **Tylko gdy sufit da się policzyć.**

Konto staje się „Verified user” automatycznie po 3 approved runach z `verifiedRun: true`.

| twierdzenie | źródło | werdykt | dowód |
|---|---|---|---|
| „Server can independently check that the reported tok/s was measured…” | agent-context `verifiedRun.description` | **częściowo** | Sprawdzane są tylko prompt i spójność liczb. `engineTimingsRaw` to JSON od zgłaszającego, a serwer niczego nie mierzy. 92 ze 177 verified w próbce ma `decodeCeiling.status = unavailable` (kwanty własne, brak statystyk draftu, brak `params`), czyli kontrola sufitu w ogóle nie zadziałała. |
| Kanoniczny prompt + nonce = zimny pomiar | `speed-tests.md:25` | **częściowo** | Nonce zabija prefix cache (`main.go:6512`), ale nie cache n-gramów ani lookupu między zapytaniami. Bonsai-2-27B na 5080: „854.5 tok/s, 100% acceptance — Verified”, zmierzone na „server whose n-gram map has seen the content (runs 3–6 of a repeat series)” ([README zotowata](https://huggingface.co/zotowata/bonsai2-dflash2-fastfork)). Ten sam stos „fresh” daje 146.4 t/s. |
| Runy powyżej 10× sufitu są ukrywane (SUSPICIOUS) | agent-context `suspiciousRuns` | **prawdziwe, ale słabe** | Przy nieznanej szerokości przyjmują do 64 tokenów na przebieg. Na 5090 jest APPROVED run 4 778 t/s (SGLang n-gram 512, prompt 20 tokenów, „ignore EOS to 2048”), czyli degeneracja powtórzeń. |
| Strona `/en/hardware` pokazuje prędkość karty | `/en/hardware` | **mylące** | Best/median/min liczone są ze wszystkich modeli, batchy i konfiguracji multi-GPU: 3090 „Best 5.0k”, RTX PRO 6000 „Best 306.1k tok/s”. Nie ma pól pasma, VRAM ani ceny. |
| „Site's source code is open source under MIT on GitHub” | `/en/privacy`, `/en/terms` | **fałsz (dla serwera)** | Link prowadzi do `localmaxxing-cli`. W org nie ma kodu serwera ani weryfikatora (lista 6 repo przez API GitHub). |
| Remote decode = okno od pierwszego do ostatniego tokenu, mediana z 3 po 1 rozgrzewce | `speed-tests.md:23-25` | **potwierdzone (kod CLI)** | `measureOpenAIEndpoint`, `main.go:6525+`. Uwaga: zgłoszenia ręczne (tqLLM, exllamav3) deklarują własną metodę w `notes`. |
| tqLLM 273.1 „approved” (R15c) | R15c | **potwierdzone i doprecyzowane** | `verifiedRun: true`, ale `decodeCeiling: unavailable` (TQ3_4S), więc kontrola sufitu nie zadziałała. Prompt 346 tokenów = reasoning-v1, thinking on, `specNumTokens` 7, mal 6.15. |
| Na XTX brak verified Qwen3.8-27B (R15c, 10-16) | R15c | **potwierdzone i rozszerzone** | 2026-10-20: na XTX brak verified dla **jakiegokolwiek** modelu. |

**Adwersaryjnie o porównywalności z naszymi liczbami:**
- Kanoniczny `reasoning-v1` jest w praktyce **thinking on**: verified outputy zaczynają się od „We need answer user's…”. To telegraficzny tekst myślenia, bardzo przewidywalny. mal na nim jest wyższe niż na naszym spec_sweep: exllamav3 MTP n=4 ma 4.04, a tqLLM ma 6.15 na reasoning wobec 4.56 na code.
- T=0, 256–520 tokenów, kontekst ~350 tokenów. Nasz spec_sweep (T=1, 6 promptów PL/EN × 3 seedy, 400 tokenów) to **inne warunki**: 114.8 t/s z XTX nie wolno stawiać obok ich liczb. Nasz najbliższy odpowiednik to long_ctx_bench 1.7k przy T=0: 136.5 t/s (`REKORDY.md:107`), ale tam prompt jest długi, a tekst nie jest tekstem myślenia.
- Ich pomiar decode przez HTTP obejmuje strumieniowanie. Nasze `predicted_per_second` jest od strony serwera i bywa o 5–15% wyższe od end-to-end (zotowata podaje taki rozjazd). **Zgłaszać należy liczbę klienta.**

## 4. Dane dla naszych kart i modeli (próbka 2026-10-20)

Pełna tabela per karta (dla raportu 33): `local://localmaxxing-per-karta.md`, kopia w `/tmp/res-localmaxxing/out/localmaxxing-per-karta.md`.

### 4.1 Qwen3.8-27B, runy verified (reasoning-v1 ≈ 346 tokenów promptu, code-v1 ≈ 277), 1×GPU

| karta | silnik / kwant | spec (szer.) | mal | t/s | util. pasma¹ | data |
|---|---|---|---|---|---|---|
| 3090 | tqLLM `8c12e1a` TQ3_4S (prywatny) | DFlash2 drzewo (7) | 6.15 / 4.56 | **273.1** / 199.5 | n/d | 10-03 |
| 3090 | exllamav3 1.5.0 EXL3-4.00bpw | DFlash2 (7) | 6.04 / 4.27 | 242.1 / 169.6 | 0.68 / 0.65 | 09-29 |
| 3090 | exllamav3 1.4.2 (fork Mia) EXL3-3.5bpw | DFlash2 / MTP(4) / DSpark(4) / brak | 5.67 / 4.04 / 4.07 / — | 164.6 / 115.5 / 115.1 / 47.6 | 0.43 / 0.41 / 0.41 / **0.64** | 09-04 |
| 3090 | vLLM 0.32.0 W4A16 | MTP | — | 105.4 / 100.8 | 0.43 / 0.42 | **10-19** |
| 3090 | **llama.cpp upstream `d7bd3bf`** UD-Q4_K_XL, KV q8_0 | DSpark(3) / DFlash2(3) / MTP(3) / DFlash(2) / brak | 3.54 / 3.67 / 3.54 / 2.38 / — | 82.7 / 81.9 / 80.4 / 64.8 / **41.3** | 0.42 / 0.40 / 0.41 / 0.48 / **0.71** | 09-04 |
| 5060 Ti 16G | tqLLM `75d4` TQ_S | DFlash2 (7) | 6.23 / 4.13 | **156.2 / 100.5** | n/d | **10-10** |
| 5090 | NInfer NVFP4 (+ QUASAR-QAT NVFP4) | DFlash2 K=9 + zredukowany słownik draftu | 5.17–6.83 | 334.4 / 211.8; QAT **510.7** / 348.7 | 0.56 | **10-19** |
| R9700 | hipfire 0.3.1 MQ4V2 | DFlash2 | 6.34 | 111.6 | n/d | 09-15 |
| M5 Pro 48G | custom „qwen38-megakernel” MLX-4bit | — | — | 72.4 | n/d | — |
| **XTX** | — | — | — | **brak verified** | — | — |

¹ `decodeCeiling.measuredUtilization` = (przebiegi targetu na sekundę) / (pasmo / bajty wag). Przy wagach szacowanych z nazwy kwantu (UD-Q4_K_XL → 4.5 bit → 15.75 GB). Dla porównania nasze 3090 plain to 77% pasma (R15c).

**Ciekawostka:** w upstream llama.cpp DFlash2 przy `--spec-draft-n-max 3` (mal 3.67) nie wygrywa z MTP n=3 (mal 3.54): 81.9 wobec 80.4 t/s. Zysk konkurencji bierze się z **szerokości 7–9 i drzewa**, a nie z samego draftera. Zgadza się to z R16i / R21a (sufit bloku 7.3–7.8). Nowa wiedza jest tylko taka, że da się to teraz pokazać na publicznej, jednolitej tablicy.

### 4.2 Pozostałe nasze pary

- **XTX, Qwen3.8-27B:** 30 runów, 0 verified. Rekord 318.2 t/s hipfire DFlash2 (merge-sort bez myślenia, 157 tokenów wyjścia, mal 14.27 przy szerokości 16, czyli prawie kopia). Dalej: fork `stew675/llama-cpp-rdna-boosts` (1337Hero) 2×XTX Q8_0 MTP 117.1 i 1×XTX plain 38.1 t/s (Q4_K_M, ROCm), upstream Vulkan MTP 90.7 (Q4_K_XL, Windows, sterownik AMD). **Nikt na XTX nie pokazuje >91 t/s na 1×XTX z MTP na GGUF.**
- **3090, LFM2.5-24B-A2B i XTX, LFM2.5-24B-A2B:** **0 runów w całej bazie**. Wpis „pierwszy w bazie” kosztuje 2 minuty. Nasze rekordy: XTX 293.8, 3090 291.6 / 263.9, 5060 Ti 207.9 / 226.8 t/s, ale w naszych warunkach.
- **5060 Ti, Qwen3.8-27B:** poza tqLLM tylko 2×GPU (vLLM NVFP4 63.2) i llama.cpp 2×GPU ok. 26 t/s.
- **Mac:** Qwen3.8-27B najwyżej 133.3 (M5 Max 128G, custom „butter” DFlash2, niezweryfikowany) i verified 72.4 (M5 Pro 48G, custom megakernel MLX). Na Macu 16 GB nie ma runów docelowych modeli.
- **Katalog sprzętu (do Podkrętu):** pasmo z `decodeCeiling.hardwareBandwidthGbps` z linkiem do producenta. W próbce: 3060 360, 3060 Ti 448, 3080 760.3, 3090 936.2, 3090 Ti 1008, 5070 672, 5070 Ti 896, 5090 1792, XTX 960, Ryzen AI Max 395 256, GB10 273, H200 4800 GB/s. Nasze karty (`wiki/karty/*`) mają te same liczby producenta, więc nie ma czego przejmować. Ceny: tylko pojedyncze `hardwareCost`, np. XTX używany 630–750 USD i nowy 900 USD (2026). To za mało na cennik.
- **Formaty raportów:** GFM v1 plus tokeny `[[report-image:<id>]]` i `[[report-embed:<url-encoded>]]`, bez surowego HTML. Raport może podpinać runy (`--benchmark-run-ids`). Tagi to wolne słowa (`rocm`, `speculative-decoding`, `verified`…). Wzór dobrego raportu to Strata dual-16 GB: 15 verified wierszy plus 3 pełne ewaluacje.
- **Silniki w bazie (próbka 1 864):** llama.cpp 838, vLLM 333, MLX 64, Ollama 59, hipfire 38, custom 35, LM Studio 29, NInfer 21, exllamav3 12, SGLang 10, Strata 6, lucebox 2.

## 5. Co z tego możemy UŻYĆ (ranking)

| # | pomysł | zysk | koszt / ryzyko | uwagi |
|---|---|---|---|---|
| 1 | **Verified runy XTX Qwen3.8-27B** (reasoning-v1 + code-v1, po 3 runy, więc auto „Verified user”) | 0% t/s; **pierwsze miejsce verified na XTX** (dziś 0 runów verified), szac. 130–145 / 110–120 t/s `[INFERENCE]` | ~10 min GPU + konto użytkownika; ryzyko: wynik code-v1 < hipfire 318 (nie-verified) wygląda słabo | mal 3.9–4.1 × przy ~28–29 ms/krok ⇒ 135–145. Sufit wg ich wzoru: 960/15.75 = 61 przebiegów/s × 5 × 1.15 ≈ 350, więc mieścimy się z zapasem |
| 2 | **LFM2.5-24B-A2B na XTX** (pierwszy wpis w bazie) | 0% t/s; widoczność modelu z naszego katalogu | 2 min GPU | plain decode, więc nie trzeba statystyk draftu do verified |
| 3 | **Monitoring konkurencji przez API** (cron 1×/dzień, ≤10 GET) | wykrycie nowych rekordów: NInfer 5090 510.7 i tqLLM 5060 Ti 156.2 przeoczyliśmy | 1 h pracy, 0 GPU | `verifiedRun=true&since=7d&hfId=Qwen3.8-27B`, diff po `id` do `KERNEL/wiki/log.md` |
| 4 | **Metryka „util. pasma” w naszym raporcie i Podkręcie** wzorem `decodeCeiling` | wiarygodność; ten sam język co społeczność | 0.5 dnia | (przebiegi targetu/s) ÷ (pasmo/bajty wag). U nas plain 0.71–0.78, czyli tyle co najlepsi |
| 5 | **NInfer do przebadania** (Apache-2.0, 3 105★, push 2026-10-20) | na NVIDIA: DFlash2 K=9 + zredukowany słownik draftu, mal 6.8 na reasoning; sufit dla cuda-topka2 na reasoning to +50–60% przy mal 6 wobec 4 i kroku ×1.1 | osobny raport (nie w tym zakresie) | brak wiersza w ZRODLA jako przedmiotu badania |
| 6 | Wysyłka macierzy `/api/inference-benchmarks` | — | — | **nie dotyczy**: tylko vLLM/SGLang (README CLI:621), a my mamy jedno zapytanie naraz |

**Czego NIE robić / co nie dotyczy:**
- Runów „warm” z lookupem i `CACHE_SHARE` na powtórkach tego samego kanonicznego promptu. Przeszłyby weryfikację jak u zotowaty, ale to gra pod benchmark, sprzeczna z naszą zasadą dwóch klas obciążenia (`wiki/metody/pomiar-abba.md:21`). Code-edit (mvs 430 t/s) publikujemy **tylko w raporcie**, jako osobną klasę „copy/edit” z opisem, a nie jako speed-test.
- Porównywania 114.8 t/s (spec_sweep T=1) z ich liczbami: inne T, prompt, długość i miejsce pomiaru.
- Przejmowania ich danych do katalogu Podkręt: brak licencji. Pasmo i tak mamy od producentów.
- Macierzy współbieżności, wypożyczalni i marketplace: poza naszym profilem (jeden użytkownik, decode).

## 6. Następne kroki: eksperymenty ≤10 min GPU

Wspólny skrypt (do napisania, ~60 linii Python): `qwen-opt/tools/lmx_submit.py`.
- Wczytuje `canonicalPrompts` z `/api/agent-context`.
- Dla każdego z promptów robi 1 rozgrzewkę i 3 pomiary przez `POST /v1/chat/completions` z `stream: true`, `temperature: 0`, `max_tokens: 512`, z pierwszą linią `[LocalMaxxing cache-bust nonce: <hex>]`.
- Wysyła `chat_template_kwargs: {"enable_thinking": true}`, bo tak mierzyli verified konkurenci.
- `tokSOut` liczy jako mediana z okna od pierwszego do ostatniego tokenu po stronie klienta.
- `engineTimingsRaw` bierze z obiektu `timings` serwera; `specDraftTokens`/`specAcceptedTokens` z `timings.draft_n` / `draft_n_accepted` (`tools/server/server-common.cpp:102-103` w `cuda-topka2`).
- Ustawia `promptSha256` = sha256 tekstu kanonicznego (bez nonce), `outputSha256`/`outputSample` z wyjścia, `specNumTokens` **pomija**, jeśli szerokość draftu jest zmienna.
- Na końcu `POST /api/speed-tests/dry-run` i wypisanie `verification.issues`.

| # | eksperyment | przełączniki | czas | kryterium |
|---|---|---|---|---|
| E1 | XTX Qwen3.8-27B, **fresh**, sam MTP | `run-topka.sh qwen` + `LLAMA_SPEC_LOOKUP=0`, `-c 32768`, świeży serwer przed każdym z 2 promptów | 6 min | dry-run `verified: true`; reasoning ≥120 t/s, inaczej nie publikujemy i sprawdzamy step-cost przy T=0 |
| E2 | XTX Qwen3.8-27B, lookup W16 w trybie fresh (restart serwera przed **każdym** pomiarem) | `run-topka.sh qwen` (W16 + share), 4 restarty × 2 prompty | 8 min | publikujemy tę z wersji E1/E2, która jest szybsza na świeżym serwerze, i opisujemy obie w `notes` |
| E3 | XTX LFM2.5-24B-A2B Q5_K_M | `run-llm.sh lfm` (plain) | 3 min | pierwszy wpis w bazie, `verified: true` |
| E4 (chmura, przy najbliższej kampanii NVIDIA) | 3090 / 5060 Ti, cuda-topka2 `2a261101b`, ten sam skrypt | `LLAMA_SPEC_LOOKUP=0` | 5 min na kartę | 3090 ≥ 105.4 (vLLM MTP verified), żeby być najszybszym GGUF/MTP |

Po E1–E3: trzeci approved verified run daje „Verified user”. Raport GFM (`lmx report create --draft`) podpina run IDs i zawiera tabelę dwóch klas obciążenia (fresh i edit/copy) oraz jawną afiliację. Publikację zatwierdza użytkownik (konto, marka).

## Do bazy wiedzy

Proponowane wiersze `wiki/ZRODLA.md`:

| źródło | wersja / commit | data | raport | werdykt | następnym razem |
|---|---|---|---|---|---|
| LocalMaxxing (localmaxxing.com) **4×** | API 1.7.0, CLI `fce3306`, ToS 2026-10-04; 2 796 użytk. / 9 445 runów | 2026-10-20 | R32d | API publiczne (odczyt bez klucza, zapis 30/h); **„Verified” = spójność, nie dowód**: sufit tylko w 52/177 verified, warm n-gram przechodzi; brak licencji danych; serwer nie jest open source (tylko CLI MIT); **XTX: 0 verified runów**; LFM2.5-24B: 0 runów | `leaderboard?verifiedRun=true&since=7d&hfId=Qwen3.8-27B` dla 3090/XTX/5060 Ti; czy pojawił się verified XTX; czy zmieniły się reguły `verifiedRun` (warm n-gram) |
| localmaxxing-cli (github.com/LottoLottoLotto/localmaxxing-cli) | `fce3306` | 2026-10-15 | R32d | CLI MIT w Go; **nie generuje dowodów do verified** (`main.go:5333-5345`), nonce `main.go:6512`; brak `--canonical-prompt` | czy dodali automatyczne `promptSha256` / `draft_n` dla llama-server |
| zotowata/bonsai2-dflash2-fastfork (HF) | `f5e587f` | 2026-09-21 | R32d | 854.5 „Verified” = ciepła mapa n-gramów (fresh 146.4); łatki 0001/0002 (embedding na GPU, async staging wejść) już mamy (łatka 59 `GGML_HIP_INPUT_BATCH`) | — |
| NInfer (github.com/Neroued/ninfer) | push 2026-10-20, 3 105★, Apache-2.0 | 2026-10-20 | R32d (tylko wzmianka) | verified 5090 Qwen3.8-27B 334.4 (NVFP4) / 510.7 (QUASAR-QAT NVFP4), DFlash2 K=9 + zredukowany słownik draftu, util 0.56 | **przebadać** pod cuda-topka2: szerokość 9, redukcja słownika, koszt weryfikacji |

## Źródła

- https://www.localmaxxing.com/en (statystyki), https://www.localmaxxing.com/en/reports, https://www.localmaxxing.com/en/hardware, https://www.localmaxxing.com/en/terms, https://www.localmaxxing.com/en/privacy, https://www.localmaxxing.com/robots.txt, https://www.localmaxxing.com/llms.txt
- https://www.localmaxxing.com/api/agent-context, https://www.localmaxxing.com/api/openapi.json, `GET /api/leaderboard` i `GET /api/speed-tests` (zapytania wymienione w §4 i w `local://localmaxxing-per-karta.md`)
- https://github.com/LottoLottoLotto/localmaxxing-cli @ `fce3306`: `cmd/lmx/main.go:3793-3803,5333-5345,6455-6519`; `cmd/lmx/skill/references/speed-tests.md:23-25,147-163,238`; `reports.md`; `hardware-and-setups.md`
- https://api.github.com/users/LottoLottoLotto/repos (brak repo serwera)
- https://huggingface.co/zotowata/bonsai2-dflash2-fastfork (README: metodologia warm/fresh, łatki)
- https://github.com/Neroued/ninfer (metadane repo)
- Nasze: `wiki/REKORDY.md:74-116`, `product/research/15c-nowe-silniki.md:24,72,317-321`, `product/research/31-5060ti.md:8-12`, `~/wt/cuda-topka2/tools/server/server-common.cpp:102-103`
