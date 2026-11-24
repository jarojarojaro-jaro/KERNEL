---
typ: ekosystem
tags: [ekosystem, konkurencja, moe]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/product/research/21g-nowe-silniki.md:158-216; ~/KERNEL/product/research/21g-notatki/maya.md; https://github.com/mw00/project-maya (`a4e1ff0`, v1.1.15; `f26d8ba`, v1.1.26; `c167004`, v1.1.54; `c4effee6`, v1.1.55; `22fc101f`, v1.1.56; `30145b8`, v1.1.62 + CHANGELOG do v1.1.63, 2026-11-14; https://x.com/PeasantSmith/status/2121371735157264831); ~/KERNEL/product/research/32a-maya-1117-strata-020-gyro.md:14-20; ~/KERNEL/product/research/39a-maya-1119.md:14-30; ~/KERNEL/product/research/60d-serving-kernels-cache.md:196-213,232-239; ~/KERNEL/product/research/63b-colibri-maya-delta.md:166-220; ~/KERNEL/product/research/66a-strata-maya.md:206-226,300-353
status: aktualne
---
# Project Maya (mw00): silnik jednego modelu GLM-5.3-Flash

**Pochodna Straty (nie fork llama.cpp) uruchamiająca tylko GLM-5.3-Flash (321B, 18B aktywnych) z ekspertami w trzech warstwach VRAM → przypięty RAM → NVMe (O_DIRECT); 81 t/s na RTX PRO 6000 = 41% pasma; liczby z README to najlepsze wiersze z różnych wersji, bez llama.cpp (raport 21g, 2026-10-19).**

- Jakość: „97.7–99.2% dokładności FP8” to marketing (5 testów MC po 400 pytań); uczciwie KL Maya-S 0.428 / top-1 83.3%, Maya-L 0.188 / 90.0% – poziom ~q2_K.
- Determinizm: domyślnie tylko 17/70 par restartów daje identyczne tokeny, v1.1.13 i v1.1.15 zmieniły domyślne tokeny.
- v1.1.14 Pascal: `-Xptxas -dlcm=ca`, P40 dekod ×1.7–3.0; P100 (sm_60) najpewniej się nie kompiluje (`__dp4a` wymaga CC 6.1) `[INFERENCE]`; nowy typ ekspertów Q6_K_XL/Q8_0.
- Przypina cały RAM poza 6 GB; buduje się 20–40 min ze źródeł; XTX eksperymentalnie, niezmierzony; polskiego brak.
- Do skopiowania: pętla społeczności `--bench` → `--report` → issue → README, rozgrzewka cache ekspertów z profilu (+15% na świeżym starcie), kalibracja MTP/DFlash2 per maszyna.

## Aktualizacja 2026-10-21
- v1.1.17: bez nowych kerneli ([[raport-32a-maya-strata-gyro]]); v1.1.19: #318 pomija martwe obliczenia DeepSeek, nie przenosi się na Qwen3.8; rozgrzewka przed READY (#285) ([[raport-39a-maya-1119]]).

## Aktualizacja 2026-10-24 (v1.1.21–1.1.26, tylko DeepSeek `maya-ds4`)
- Prefill AMD 2.35–2.53× (Strix Halo, v1.1.21): sparse attention na `wmma_f32_16x16x16_bf16_w32` z Q/P rozbitym na BF16 hi+lo (~16 bitów mantysy), dense GEMM przez hipBLASLt z wyborem per kształt. RDNA4 (#370): 1.16–1.40×. RTX 3090 MMA (#369): prefill ~30K 957–992 → 1104–1234 tok/s.
- v1.1.26: `DS4_FAT_ROWS` (gorący ekspert raz do FP16 + cuBLAS) 1.3–1.56× prefillu na 3× V100; dokładny softmax FP32 na `wmma` dla Volta/Turing.
- v1.1.22: TP bez P2P (copy engine → pinned host, `allreduce_dma`), 9 GPU PCIe 3.0: dekod 42.9 → 66.8 t/s; drafting 8.5 → 15.9 t/s (strumienie HIP).
- **2× RX 7900 XTX (#382):** jeden launch kwantyzacji q8 zamiast wielu: 12.5 vs 13.1 t/s, bez zysku (gap 3.3 µs, praca ~2 µs). v1.1.25: sesje przeżywają restart (`MAYA_DS4_SLOT_KEEP=1`).
- Dla Qwen3.8/gfx1100 nic do wzięcia ([[raport-60d-serving-kernels-cache]]).

## Aktualizacja 2026-11-05 (v1.1.27–1.1.54, R63b)
- Gęstego 27B dalej brak (GLM, DeepSeek, MiniMax, Flash-Next). Dla decode/prefill na gfx1100 nic.
- Do wzięcia dla ścieżki agenta: **#607 „wspólny początek”** (system + narzędzia jako osobny mały wpis, nowa rozmowa 19× szybciej) → [[wspolny-poczatek-promptu]]; #639 punkty przywracania; `tools/agent_bench.py` (#406) jako benchmark.
- Zasady: żadna warstwa pośrednia nie przepisuje prefiksu (#704: strażnik pętli psuł cache, 150K ~15× szybciej po poprawce); przerwanie nie gubi stanu (#573, #746). #625 stała kolejność narzędzi zmienia prompt, więc u nas tylko za zgodą ([[2026-11-05-tylko-bezstratne]]).
- v1.1.54 „follow-up czytał całą rozmowę” na Qwenie: ten sam błąd klasy co colibri #2517 ([[colibri]]).

## Aktualizacja 2026-11-07 (v1.1.55–1.1.56, R66a)
- **#864 (XTX, ROCm 7.2.4):** kernele ekspertów EXL3 na WMMA −39% przy ≥ 128 wierszach na eksperta, 108/108 wyjść bitowo. Koszt był w podawaniu operandów: 2× `ds_load_b128` zamiast 8 słów, słowa kafla przez `v_permlane16`, LDS 57 → 24 KB. Nasz audyt ISA tej lekcji znalazł Q6_K w MMQ topki ([[mmq-q6k-skale-lds]]).
- `MAYA_PROMPT_MEMO` domyślnie (przyrostowe przygotowanie promptu): follow-up po 115K −6%. Nasz odpowiednik `TOK_CACHE` jest w produkcji martwy ([[lekcja-flaga-bez-dowodu-dzialania]]).
- #840: przy nieudanym wczytaniu slotu następny slot, potem checkpoint ([[siatka-checkpointow-gdn]]). Dla Enigmy: Codex CLI na `/v1/responses` (#726), odpowiedź biegnie do końca bez czytelnika.
- Stratne (parked): GLM KV INT8 domyślnie, `DS4_CHUNK_GFX11=0`, #869/#870 RDNA2.

- **Delta v1.1.57–v1.1.63 (2026-11-09…14, Telegram „gpu”):**
  - **Główna nowość v1.1.62:** APU AMD Halo (ROCm) i karta NVIDIA (CUDA) liczą jeden model w jednym procesie, ze wspólną kopią wag w pamięci APU. Między kartami idą tylko aktywacje. Na NVIDIA trafia atencja, KV, draft i najczęstsze eksperty. Wyniki: GLM-5.3-Flash prefill 32K 293 → 901 t/s, dekod +21%; DeepSeek dekod +18%. Maya trzyma ten tryb tylko wtedy, gdy daje > 3%.
  - **Pozostałe:** GLM-5.3 744B, kwant Maya-XS ~1,6 bita, ablacja odmowy przełączana per żądanie, lookup promptu dla MiniMax (+6% na kodzie, mamy od 10.10), szybsze eksperty CPU.
  - **Werdykt:** dla gęstego Qwen 27B na XTX nic nowego. Zysk mieszanego trybu bierze się z MoE: atencja i gorące eksperty idą na szybszą kartę, a reszta wag zostaje w pamięci, której szybka karta nie ma. U nas cały model mieści się w XTX (960 GB/s). Dołożenie 5060 Ti (448 GB/s) przy podziale warstw dekod tylko spowolni ([[rtx-5060-ti]]). Ablacja per żądanie to ten sam pomysł co odrzucona K-082 w [[KOLEJKA-TESTOW]]. Nic do kolejki.

## Aktualizacja 2026-11-17 (v1.1.66, Telegram „gpu”)

Delta od v1.1.65:
- **GLM na parze APU AMD + NVIDIA: dekod +19%** (A/B na tym samym PC, V100 obok APU, te same odpowiedzi). Dwie przyczyny:
  - karta NVIDIA czytała każdą wagę dwa razy podczas weryfikacji draftów, teraz raz;
  - para wymienia całą warstwę weryfikacji jednym wywołaniem zamiast wywołania na token.
- **Strojenie w trakcie działania:** Maya mierzy obie kolejności na pierwszych odpowiedziach i zostawia szybszą, ale tylko tam, gdzie obie dają te same odpowiedzi.
- Reszta to poprawki (DeepSeek: dwa rozmiary obok siebie, eksperci draftu w profilu; uśpienie bezczynnego CPU jako ustawienie; diagnostyka faultów prefillu).

Dla gęstego 27B na XTX nic nowego do portu. Lekcja zgodna z naszym K-114/K-116: narzut wywołań na token w weryfikacji i drafcie kosztuje więcej niż bajty. U nas weryfikacja czyta wagi raz (MMVQ N=5), więc pierwszego błędu nie mamy.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
Wydania v1.1.27–v1.1.56 oceniliśmy wtedy zdaniem „nic dla gfx1100, gęstego 27B brak”. To był jeden filtr. Maya to cały produkt (silnik + serwer + instalator + UI) i od 2026-11-23 sami jej używamy: Maya `ik2` z naszymi łatkami HIP to produkcja Inklinga 2 Mini, 113,2 t/s przy T=0,7 ([[maya-ik2-inkling]]).
- **Serwer i ścieżka agenta (63b:183-198, 66a:212-226):** #607 wspólny początek, #639 punkty przywracania, #704 „nic nie przepisuje prefiksu”, #573/#746 przerwanie nie gubi stanu, #840 łańcuch fallbacku przy wczytaniu slotu (slot → następny slot → checkpoint). Nasz odpowiednik to serwer topki (`CACHE_SHARE_MIN`, checkpointy). Z tej listy wdrożone mamy tylko zasadę #704 (`SAFE_TOOLS`); #607 jest w [[wspolny-poczatek-promptu]] jako „w toku”, a `TOK_CACHE` (odpowiednik MEMO) dalej nie jest ustawiony w `qwen-opt/run-topka.sh`.
- **Pomiar:** `tools/agent_bench.py` (#406) mierzy całe tury agenta, a nie t/s jednego promptu. To lepsza miara naszego celu niż `spec_sweep` z 6 stałymi promptami (`qwen-opt/spec_sweep.py:18-25`).
- **Produkt (porównanie z Enigmą, `app/engine`):**
  - kalibracja per PC (chunk prefillu 1.4–1.75×, v1.1.30) i strojenie w trakcie działania (v1.1.66) — Enigma ma podobne Optimize, ale jednorazowe;
  - odpowiedź web-chatu biegnie do końca bez czytelnika i przeżywa restart (v1.1.55) — Enigma tylko przepuszcza strumień (`api.ts:104`), więc zamknięte okno najpewniej gubi odpowiedź `[INFERENCE]`;
  - zgodność klientów: Codex CLI na `/v1/responses` (#726), API w stylu Ollama (v1.1.50), załączniki (#837) — Enigma przepuszcza `/v1/*` do llama-server, API Ollamy nie ma, testu z Codexem nie znalazłem;
  - SIGTERM nie zawiesza serwera (`78c450a2`) — u nas łagodne zatrzymanie w `engine.ts:614` jest, ale bez watchdoga po `ready` ([[inference-stack]]).
- **Lekcja:** link o silniku, który „nie ma naszego modelu”, i tak trzeba czytać jako wzór serwera i produktu. Miesiąc później ten sam silnik okazał się 3× szybszy od nas na Inklingu przy T=0,7 (kontroler `SpecCtl`).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość): v1.1.62–v1.1.66
Trzy wiersze ZRODLA (v1.1.57–63, v1.1.64–65, v1.1.66) zamknęliśmy zdaniem „nic dla gęstego 27B na XTX”. Dla dekodu topki to dalej prawda, ale te wydania to głównie lekcje produktu i utrzymania (CHANGELOG w `~/kernel/zrodla/maya` @ `f9a053dc`):
- **Para APU AMD + karta NVIDIA w jednym procesie (v1.1.62, CHANGELOG.md:246-262):** ROCm i CUDA obok siebie, jedna kopia wag w RAM APU, między kartami tylko aktywacje. To sprzęt części klientów Enigmy (PC z APU i kartą). Enigma przy osobnej karcie pomija iGPU całkiem („only drives the display”, `app/engine/src/server/catalog/index.ts:96,102-106`), a APU bez karty już raz pomyliła z kartą ([[lekcja-enigma-apu-jako-karta]]).
- **Samostrojenie z progiem (CHANGELOG.md:251, 180):** pierwszy start mierzy APU samo i parę, tryb zostaje tylko przy > 3% zysku; w v1.1.66 kolejność wybierana na pierwszych prawdziwych odpowiedziach, tylko tam, gdzie obie dają te same odpowiedzi. Enigma robi to samo raz, w fazie `optimize` przed `ready` (`app/engine/CONTRACT.md:45,64`), z tym samym progiem 3% dla zmiany tekstu i potwierdzeniem drugim pomiarem (`app/engine/src/server/optimize.ts:12-20`). Różnica: Maya strojenie powtarza na ruchu użytkownika, a nasze kandydaty nie obejmują drugiego urządzenia.
- **Błąd silnika to błąd, nie „length” (v1.1.65 #827, CHANGELOG.md:204):** strumień zachowuje wysłany tekst i kończy się zdarzeniem błędu API, reszta dostaje HTTP 422 `engine_error`, którego SDK OpenAI/Anthropic nie ponawiają. Enigma: proxy zwraca 502 przy braku serwera (`api.ts:117`), awarii w trakcie odpowiedzi osobno nie nazywa `[INFERENCE: nie testowałem]`.
- **Pomiar pamięci na AMD Linux (#899, CHANGELOG.md:200):** wolna VRAM odczytana tuż po sprawdzeniu budżetu jeszcze liczyła sprawdzaną pamięć jako zajętą, pula ekspertów dostała 0 miejsc. Enigma liczy budżet z całkowitej VRAM minus stała rezerwa (`app/engine/src/server/catalog/index.ts:117-122`), więc tego błędu nie ma, ale też nie widzi pamięci zajętej przez inne programy.
- **Instalator (v1.1.64–66):** sprawdzanie sum plików, które już leżą w folderze (CHANGELOG.md:237), karta 19,98 GB liczona jako 20 GB i karty AMD w rekomendacji (CHANGELOG.md:188). Enigma sprawdza sumę przy pobraniu (`download.ts:163`).
- **Testy (v1.1.65, CHANGELOG.md:212):** każdy znany niestabilny test naprawiony co do przyczyny, testy bez plików modelu pomijane z powodem; „czerwony test zawsze coś znaczy”. Ta sama zasada co nasze bramki.
- Co bierzemy do Enigmy: (1) wykrywanie pary APU + karta i pomiar „karta sama / para” przy pierwszym starcie z progiem 3%; (2) nazwany błąd silnika w strumieniu z zachowaniem tekstu; (3) sprawdzanie sum istniejących plików. Dla topki nic.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość): v1.1.21–v1.1.26
Wiersz ZRODLA o tych wersjach brzmiał „tylko DeepSeek; nic dla gfx1100/Qwena”. Kerneli do portu nadal nie ma, ale „tylko DeepSeek” przestało opisywać ten silnik, bo dziś jest naszym silnikiem Inklinga ([[maya-ik2-inkling]]). Te wersje uczą też o serwerze i sprzęcie (tabela w `product/research/60d-serving-kernels-cache.md:3.5`):
- **Sesje przeżywają przełączenie modelu i restart (v1.1.25, `MAYA_DS4_SLOT_KEEP=1`, #356); powtórzona tura cofa się do checkpointów rozmowy (#394).** Topka trzyma cache tylko w RAM (`--cache-ram`, decyzja „tylko RAM” w [[cache-sesji-na-dysku]]), więc po restarcie keepera każda sesja agenta czyta wszystko od nowa (Qwen 53k ≈ 61,5 s prefillu wobec 2,5 s odczytu z dysku, `STAN-PRAC.md:47`). Enigma po restarcie też zaczyna od zera. Razem z brakiem watchdoga ([[inference-stack]]) to ta sama luka „po gotowe”.
- **Czekanie między strumieniami HIP kosztuje ~1 ms na warstwę na Windows (v1.1.22, `DS4_HC_STREAM`).** Enigma wydaje HIP na Windows (`app/engine/data/engines.json:218-225`). Każdy port drugiego strumienia (np. draft obok celu) trzeba tam zmierzyć osobno, nie przenosić wyniku z Linuksa.
- **All-reduce bez P2P przez copy engine i pamięć hosta (v1.1.22, `allreduce_dma`, bitowo):** 9 GPU na PCIe 3.0, dekod 42,9 → 66,8 t/s. W parze XTX + 5060 Ti (K-107) każda wymiana też idzie przez host, bo karty dwóch firm nie mają P2P; to wzór, jak to zrobić bez straty bitów.
- **#382 na 2 × XTX:** jedno uruchomienie kwantyzacji zamiast wielu dało 12,5 vs 13,1 t/s, bez zysku (przerwa 3,3 µs, praca ~2 µs). Przy tak małych krokach o czasie decydują uruchomienia i przerwy, nie bajty, podobnie jak w naszych K-114/K-116.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość): warstwa `serve/` i pętla zgłoszeń
Wiersz rejestru o 1.1.14–1.1.16 kończył się „nic dla naszych modeli; wracać tylko przy gęstym 27B albo pomiarze XTX”. Od 23.11 Maya `ik2` to nasz silnik Inklinga 2 Mini, a Maya jest silnikiem jednego autora (1605 commitów od 2026-10-07), budowanym przez rozszerzanie sprawdzonej bazy (Strata), nie od zera jak Enigma Turbo ([[enigma-turbo-gemini-2026-11-20]]). Klon `~/kernel/zrodla/maya` @ `f9a053dc` (v1.1.73); warstwa `serve/` to ~41,8 tys. linii Pythona z testami:
- **Fałszywe silniki do testów bez GPU:** `serve/fake_multi_engine.py:1-8` udaje `strata --serve` z wieloma rozmowami (przeplot tokenów, anulowanie, logprobs), więc kolejka, przeplot i API są testowane na CPU. To punkt 3 z [[inference-stack]] („symulator silnika”); Enigma i topka go nie mają.
- **Strażnik pętli na id tokenów** dla wszystkich modeli, w myśleniu i odpowiedzi (`serve/loop_guard.py:1-8`); powód: odpowiedź Maya-XS pisała ten sam ciąg liczb przez 12K tokenów.
- **Telemetria GPU w osobnym procesie** (`serve/telemetry.py:1-8`): awaria NVML (#136, SIGSEGV) zabijała cały serwer, teraz kończy tylko czytnik, a serwer uruchamia go ponownie bez tej funkcji.
- **Sprawiedliwy podział czasu między rozmowy** `MAYA_FAIR_SLICE_S` z testem na skryptowanym silniku (`serve/test_fair.py:1-5`).
- **Linia „Zaoszczędzono”** (`serve/savings.py:1-8`): ile kosztowałyby obsłużone tokeny w API producenta modelu, z rozbiciem na nowe wejście, wejście z cache i wyjście, sumowane między startami. Gotowy argument sprzedażowy dla Enigmy.
- **Pętla zgłoszeń:** `./maya.sh --bench` → `--report` → issue z plikiem raportu; zmiany AMD scalane na pomiarach zgłaszających, bo autorzy nie mają karty AMD (`CONTRIBUTING.md:5-27,37-38`). Enigma nie ma kanału pomiarów od użytkowników, a testujemy na naszym labie ([[lekcja-enigma-apu-jako-karta]]).
- Bierzemy do Enigmy: fałszywy silnik do testów całej ścieżki, strażnik pętli, licznik oszczędności, `enigma report` (sprzęt + bench + log w jednym pliku).

## Powiązane
- [[strata]]
- [[raport-21g-nowe-silniki]]
- [[lekcja-bit-exact-wobec-siebie]]
