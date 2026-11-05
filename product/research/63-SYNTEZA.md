# 63 — synteza: 44 wątki z pakietu 2026-11-03, werdykty, akcje i plan

Data: 2026-11-05. Synteza raportów [63a](63a-silniki-lokalne.md), [63b](63b-colibri-maya-delta.md), [63c](63c-amd-rocm-llamacpp.md), [63d](63d-atencja-spec-kwant.md), [63e](63e-metodologia-agenci.md) oraz rejestru [63-WATKI](63-WATKI.md). Praca tylko na CPU: bez GPU, bez pobierania.

**Reguła użytkownika z 2026-11-05: tylko optymalizacje bezstratne** („nie chcę zmieniać jakości – mieliśmy tylko optymalizować”; wiki: `decyzje/2026-11-05-tylko-bezstratne`). Dozwolone są zmiany bitowo identyczne albo różniące się tylko kolejnością działań na floatach, sprawdzane naszą bramką greedy md5 (c4708318 / 6f14e814 / 894e56e4) i KLD tak jak dotąd. Wszystko, co zmienia wyjście albo jakość (rzadka atencja, stratna weryfikacja, inne kwanty wag lub KV, przycinanie ekspertów, zmiana treści promptu), trafia do sekcji 4 i **nie jest rankingowane**.

Nasze punkty odniesienia (XTX, Qwen3.8-27B UD-Q4_K_XL, topka; [REKORDY](../../wiki/REKORDY.md), [WYNIKI-XTX](../WYNIKI-XTX-2026-10-19.md)):
- spec_sweep T=1: **114.8 t/s**;
- long_ctx (T=0, MTP4 + W16): 1.7k 136.5 / **94k 105.6 / 199k 74.5 t/s**; TTFT 94k 123 s;
- LFM2.5-24B-A2B tg: **~296 t/s**;
- proza E0 78.93 t/s; `mvs` 433.8 t/s; pp4096 1123 t/s.

Oznaczenia wymagań: **GPU** (pomiar na karcie, przez kolejkę), **zgoda** (decyzja użytkownika: pobranie, restart serwera :8080, zmiana konfiguracji produkcji, root), **$** (chmura), **CPU** (tylko kod lub analiza). `[SZACUNEK]` = arytmetyka z raportów, nie pomiar.

## 1. TL;DR

1. **Największy zysk dla użytkownika nie leży w kernelach, tylko w cache promptu** ([63b §0.1](63b-colibri-maya-delta.md)). 74% czasu prefillu w logach serwera (3536 s z 4753 s) to 38 tur, w których prompt ≥20k był czytany od zera. Przyczyna: wpis Qwena 75–120k waży 7–14 GB, a limit `--cache-ram` to 16 384 MiB, więc drugi wątek wyrzuca pierwszy. Zmiana jednej liczby (16384 → 40960) i chude checkpointy dają **tury 85–200 s → ~4–8 s**, bitowo.
2. **Długi kontekst ma zapas, który da się wziąć bezstratnie.** qwen-warp na 3090 po normalizacji pasma daje ~96–105 t/s przy 190–262k wobec naszych 74.5 przy 199k ([63a §14](63a-silniki-lokalne.md)). Między 1.7k a 199k przybywa ~18 ms na krok, z czego tylko ~5 ms to odczyt KV ([63d E7](63d-atencja-spec-kwant.md)). Najpierw profil jednego kroku (30 min GPU), potem jedno przejście KV w `kvq`.
3. **QSA (przełom z 4090) jest odstawione**: zmienia wyjście, a liczby 114.7 vs 40.6 t/s przy 255K pochodzą z RTX 4090, nie z XTX. Port (QSAPort) zaparkowany.
4. **Audyt benchmarku aplikacji Enigma znalazł lukę krytyczną (G1)**: kandydat `enigma` dekoduje inny prompt niż baseline ([63e §6.1](63e-metodologia-agenci.md)). Poprawka w toku (EngineBenchFair).
5. **Prawie wszystkie „rekordy” z pakietu po normalizacji to parytet albo reklama**: YASAKANI 1220 t/s = ~11–12 tokenów na krok na kopiowaniu (edycja 462 vs nasze 433.8), LithosAI 2116 t/s = 6 / czas kroku przy założonej akceptacji, Strata PR #4366 +39% → +2–6% (ciepłe vs zimne), LSA 72.4× dotyczy 10M tokenów, colibri „256k w szybkości 64k” to planer pamięci.

## 2. Werdykty dla każdego wątku (#1–#44)

Werdykt: **przełom** / **przydatne** / **nie dla nas** / **reklama-zawyżone**. Akcje oznaczone 🚫 łamią regułę bezstratności i są w sekcji 4.

| # | Wątek | Werdykt i kluczowy dowód | Akcja |
|---|---|---|---|
| 1 | gpu.nz: tabela VRAM | **przydatne**: liczby f16 zgadzają się z naszym modelem (64 KiB/token, 8k→32k +1.50 GiB), ale tabela pomija warstwę MTP, bufory spekulacji i nasz zmierzony nadmiar 10.7 KiB/token (29.1 vs 18.4) ([63a §16](63a-silniki-lokalne.md)) | CPU: znaleźć w `llama-context` źródło 10.7 KiB/token i przyciąć (≈ +2.7 GiB zapasu przy 262k); estymator Enigmy na zmierzonym nachyleniu 29.1 KiB/token + MTP (plan #9, #17) |
| 2 | Open Kernel Challenge | **przydatne** (metoda): publiczny sędzia rodzi dopasowanie do sędziego (kernele >10k linii pod kształty); „człowiek-koordynator ×2” to cytat bez danych ([63e §2.1](63e-metodologia-agenci.md)) | holdout promptów w `spec_sweep` (plan #13) |
| 3 | Auto-research-agent PR #6 | **reklama-zawyżone** (benchmark): wiersze „Gemini 3.8 Flash” mają syntetyczny baseline 100.0 µs i wyniki z leaderboardu floty; PR #9 ma dobre reguły integracji ([63e §2.2–2.3](63e-metodologia-agenci.md)) | do `spec_sweep.jsonl` hash buildu i env; reguła „nie powtarzaj niezmienionego kodu” (plan #13) |
| 4 | getsupers „experiments” | **nie dla nas**: tylko H200, kolejka per sekunda to nasza `gpu.lock` lokalnie ([63e §2.5](63e-metodologia-agenci.md)) | nic |
| 5 | NVIDIA Flash-Next-NVFP4 | **nie dla nas**: W4A4 ModelOpt pod B200/B300, 132.7 GB, na 24 GB wymaga ≥128 GB RAM i daje ~30–50 t/s `[SZACUNEK]` ([63d §7](63d-atencja-spec-kwant.md)) | nic (inny kwant: 🚫) |
| 6 | LithosAI MI355X 2100 t/s | **reklama-zawyżone**: 2116 = 6 / 2.83 ms przy założonej akceptacji 75%, silnik zamknięty; techniki znamy z 15a/16a ([63c §4](63c-amd-rocm-llamacpp.md)) | nic |
| 7 | Strata PR #4366 | **reklama-zawyżone**: autor sam sprostował +39% na +2–6% (ciepły vs zimny przebieg) ([63a §4](63a-silniki-lokalne.md)) | przypadek dopisany do lekcji higieny pomiaru (wiki, zrobione) |
| 8 | Strata 0.2.7 KVA | **przydatne jako wiedza, ale stratne**: u nas ~−20% TTFT ≥8k `[SZACUNEK]`, u Straty decode −11% przez spadek akceptacji MTP; needle nie wykrywa szkód ([63a §3](63a-silniki-lokalne.md), [63d §3](63d-atencja-spec-kwant.md)) | 🚫 odrzucone (zmienia wyjście); lekcja „needle to nie bramka” do wiki |
| 9 | wafer-ai gpu-perf-resources | **nie dla nas**: HEAD `6aa00fc` starszy niż nasze R21b, delta zero ([63e §1](63e-metodologia-agenci.md)) | nic |
| 10 | gau-nernst QR na B200 | **przydatne** (zasady): rejestry > LDS > globalna, producent „fire and forget”, odporność na strukturę wejścia ([63e §9](63e-metodologia-agenci.md)) | CPU: `klab isa` czy stan GDN w weryfikacji zostaje w VGPR między tokenami (wejście do plan #21); `mvs` zawsze raportować obok czatu |
| 11 | elpis (262k na 3090) | **przydatne** (metoda): decode przy 262K ~80 t/s ≈ nasze 74.5 przy 199k; bramki rejestrowane przed pomiarem, spisane porażki ([63a §7](63a-silniki-lokalne.md)) | wzór „bramka przed danymi” do fabryki; kernelowo pokrywa plan #8 |
| 12 | MTP: głębokość zależna od karty | **przydatne**: najlepsze n = 3 na 5090, 1 na 4060 (n=3: 32 vs 46 t/s); Enigma ma stałe `--spec-draft-n-max 4` (`optimize.ts:110`) ([63d §4](63d-atencja-spec-kwant.md), [63e G8](63e-metodologia-agenci.md)) | kandydaci MTP n=1…4 w optymalizatorze (plan #4) |
| 13 | CUDA-and-Kernels | **nie dla nas**: 3 notatki, tematy 2–20 puste ([63e §10.2](63e-metodologia-agenci.md)) | nic |
| 14 | Soft-MTP | **nie dla nas**: przy zamrożonym pniu = samodestylacja KL głowicy, którą zrobiliśmy (±0.2–2%) ([63d §5](63d-atencja-spec-kwant.md)) | nic |
| 15 | RTP-LLM / MNN-LLM | **przydatne** (wzorce): RTP #1574 trzyma stan liniowy tylko na ogonie promptu (= chude checkpointy), CRC32C w oknie kopii; MNN dla nas nic ([63b §4–5](63b-colibri-maya-delta.md)) | chude checkpointy według #1574 (plan #6); CRC32C przy cache sesji na SSD |
| 16 | cheaptokens: q5_1 → CPU | **nie dla nas** (nieaktualne): dotyczy buildu 10791, od #28079 brakujące pary FA konwertują się do f16 na GPU; Enigma wybiera tylko K=V ∈ {q4_0, q8_0, f16}. Ryzyko: Vulkan bez subgroup ops ([63c §7](63c-amd-rocm-llamacpp.md)) | strażnik `splits = N` > 3 w Enigmie (plan #12) |
| 17 | basalt vs Strata | **reklama-zawyżone**: 6950/273 vs 5250/164 nie występuje w repo; technika: dokładna dwustopniowa głowica Q8_0 (bitowo dla greedy), dla Q6_K nie ([63a §6](63a-silniki-lokalne.md)) | CPU 10 min: typ `output.weight` w GGUF LFM; Q8_0 → pilot sita (plan #23) |
| 18 | colibri v2.1.0 | **reklama-zawyżone** (nagłówek): „256k w szybkości 64k” to poprawka planera i KV f32→f16; przydatne `COLI_PREFIX_LOG` i „park” ([63b §1](63b-colibri-maya-delta.md)) | `LLAMA_SERVER_PREFIX_LOG` (plan #12); planer Enigmy wycenia bufor na ubatch, nie na ctx (plan #17) |
| 19 | TensorFold + cuda.fast/mlx.fast | **nie dla nas**: HIP rusza tylko na gfx1151/1201, gfx1100 nieuruchamiane; prompt konkursu to kopiowanie ([63a §15](63a-silniki-lokalne.md)) | watch `plan.hip` (#1932) |
| 20 | skyzh/tiny-llm | **przydatne** (metoda): „Performance Evidence Ledger” – 6 pytań przed przyjęciem zmiany ([63e §10.2](63e-metodologia-agenci.md)) | 6 pytań w `patch-manifest.json` (plan #13) |
| 21 | Harness: CUDA best practices | **nie dla nas**: podręcznikowe (bufory w `prepare()`, fuzje norm/RoPE, bez `.item()`), wszystko mamy ([63e §2.2](63e-metodologia-agenci.md)) | nic |
| 22 | Maya v1.1.39 + release'y | **przydatne**: #607 osobny mały wpis „wspólny początek” (system + narzędzia) = nowa rozmowa 19× szybciej; nasz `CACHE_SHARE_MIN` kopiuje cały wpis 2.3–14 GB ([63b §2](63b-colibri-maya-delta.md)) | port #607 do topki (plan #7); `agent_bench.py` (#406) jako benchmark (plan #6) |
| 23 | delta-inference-engine | **nie dla nas**: opakowanie DeepSeek na Windows; `REWIND_GAP` u nas łapią checkpointy ([63b §3](63b-colibri-maya-delta.md)) | Enigma Windows: ekran diagnostyki zasilania/HAGS/large pages (plan #24) |
| 24 | 100-days-of-inference | **nie dla nas**: poziom wstępny, dzień 7 ([63e §10.2](63e-metodologia-agenci.md)) | watch |
| 25 | rapidmlx (LSA w prefillu) | **nie dla nas**: w repo brak kodu LSA, jest tylko QSA block-sparse prefill (−31% TTFT przy 64K na Macu), twierdzenia niezweryfikowane ([63d §2](63d-atencja-spec-kwant.md)) | nic (rzadki prefill: 🚫) |
| 26 | Latent Sparse Attention | **reklama-zawyżone**: 72.4× to 10M tokenów; przy 512k TTFT 1.03× (H200) / 0.68× (B300), baseline na YaRN ×40 ([63d §1](63d-atencja-spec-kwant.md)) | 🚫 odrzucone |
| 27 | RDNA-FAST (nasza karta) | **przydatne**: większość trików mamy mocniej; nowe: MTP lean reserve (784 → 80 MiB), dynamiczny słownik draftu, f16 WMMA GEMM prefillu, chunked GDN, pułapki ROCm 10 ([63c §2](63c-amd-rocm-llamacpp.md)) | lean reserve + cap LDS (w toku, plan #5); słownik dynamiczny (plan #18); WMMA GEMM 🚫 |
| 28 | pentacoxian → Qwen-QSA | **przełom, ale nie dla nas**: 255K decode 114.7 vs 40.6 t/s **na RTX 4090**, nie na XTX; zmienia wyjście (PPL +2.44% przy 64k na Q4, KL długiego kontekstu „not tested”) ([63c §3](63c-amd-rocm-llamacpp.md)) | 🚫 port QSAPort zaparkowany |
| 29 | benchlab + HyperQwen | **przydatne**: rzetelny, sam się koryguje; turboderp: MTP-7 157 vs MTP-4 129 t/s na greedy kodzie (3090) ([63a §8](63a-silniki-lokalne.md)) | profil „kod/T=0” MTP n=6–7 (plan #15); punkt wspólny na 3090 (plan #25) |
| 30 | llama.cpp v0.9.0 | **przydatne**: tag = nightly b12110; 254 commity od pinu Enigmy; #30574 stan draftu w pliku slotu (akceptacja po restore 37 → 49%), #29948 fuzja MMQ +4.6…7.4% pp na CUDA ([63c §5](63c-amd-rocm-llamacpp.md)) | poprawki MTP w topce (w toku, plan #5); pin Enigmy → b12110 (plan #16) |
| 31 | Together Compiler / TKCC | **przydatne** (metoda): baza wiedzy ekspertów −25–31%, naiwny prompt > strategie (6.2× vs 4.9×), sufit = przepustowość pomiaru (252×); megakernel na AMD +0.22% ([63e §3](63e-metodologia-agenci.md)) | przełączanie flag w działającym serwerze (plan #20); wiki jako pamięć wyników, nie strategii |
| 32 | Baseten DeepSeek V4.1 Flash | **reklama-zawyżone**: artykuł nieczytelny, „1017” to wersja modelu; liczba SGLang GB300 przy symulowanej akceptacji 5.4 ([63e §4](63e-metodologia-agenci.md)) | CPU: czy jakiś koszt kroku skaluje się z `n_ctx` 204 800 zamiast z długością (wejście do plan #3) |
| 33 | Anthropic FlashProve | **nie dla nas**: narzut ~70–95×, tylko H100, model całkowitoliczbowy przy greedy ([63e §8](63e-metodologia-agenci.md)) | „rachunek modelu” w Enigmie: 32 tokeny greedy + top-5 logprobów (plan #12) |
| 34 | sf-tensor: PTX w Lean | **nie dla nas**: brak modelu AMDGPU ([63e §7](63e-metodologia-agenci.md)) | nic |
| 35 | 10 papierów GPU | **przydatne** (mapa): online softmax, FA1/2, split-KV, Marlin – mamy; Stream-K w MMQ RDNA3 wyłączony we wszystkich 243 konfiguracjach; LeanAttention nic nie wnosi ([63e §10.1](63e-metodologia-agenci.md)) | profil kroku przy 199k (plan #3) |
| 36 | vLLM v0.33.0 | **przydatne** (częściowo): TRITON_ATTN +18% na RDNA3 z 32-bitowego adresowania buforów; drafter DSpark dla LFM (664 MB); ROCM_OCTAVE 3-bit KV i FLy są stratne ([63c §6](63c-amd-rocm-llamacpp.md), [63d §6](63d-atencja-spec-kwant.md)) | buffer-resource loads w `kvq` (plan #22); LFM + DSpark (plan #10); Octave i FLy 🚫 |
| 37 | YASAKANI 1220 t/s | **reklama-zawyżone**: ~11–12 tokenów/krok na kopii; po normalizacji pasma i bajtów edycja 462 vs nasze 433.8 (parytet), thinking T=1 ~142 vs 114.8; brak kodu ([63a §9](63a-silniki-lokalne.md)) | watch `yasakani_dev`; wspólny zestaw zadań na XTX (plan #25) |
| 38 | Reward hacking w inferencji | **przydatne**: katalog wzorców (boczny strumień, pusty chunk SSE, cache po adresie, wykrywanie fazy); u nas G1 krytyczne i 8 dalszych luk ([63e §5–6](63e-metodologia-agenci.md)) | G1 w toku (EngineBenchFair), potem G2–G9 (plan #2) |
| 39 | LSA: wersja chińska (72.4×) | **reklama-zawyżone**: ta sama liczba z 1 warstwy przy 10M ([63d §1.3](63d-atencja-spec-kwant.md)) | nic |
| 40 | Soft-MTP (alphaxiv) | **nie dla nas**: +1.4–1.5% tylko dla modeli trenowanych od zera ([63d §5](63d-atencja-spec-kwant.md)) | nic |
| 41 | LLM Compressor 0.15 | **nie dla nas**: HIGGS, QAD, REAP zmieniają wagi ([63d §8](63d-atencja-spec-kwant.md)) | 🚫 (REAP dla klas 12 GB odrzucony) |
| 42 | Strata v0.2.10 (8 GB) | **reklama-zawyżone** (nagłówek): „128K na 8 GB” mierzono na dużej karcie ograniczonej do 8 GB; prawdziwy Arc 8 GB 12.7–14.8 t/s. Dobry wzór UX: drabina degradacji zamiast cięcia ctx ([63a §5](63a-silniki-lokalne.md)) | Enigma: drabina degradacji pamięci (plan #17) |
| 43 | MegaCapybara / NInfer / ignis / mkyt | **przydatne** (bez przełomu): MegaCapybara 540 t/s z +20% OC pamięci (stock 466); NInfer przeszedł na GLM; ignis top-k draftera 3145 → 44 µs; mkyt: pełne NVFP4 psuje równoległe tool-calle (BFCL 79 → 65.5%) ([63a §10–13](63a-silniki-lokalne.md)) | test równoległych tool-calli w bramce (plan #13); kafle GQA → plan #8 |
| 44 | Termika: cap GPU/CPU | **przydatne** (do zmierzenia): źródła (0xwhitemage, NullBurn, Blackfold) nie były badane w 63; użytkownik zatwierdził 2026-11-05 test z capem taktowania rdzenia GPU (pamięć bez zmian, bez undervoltu), wyniki jako „eco”, osobno od rekordów stock | test eco (plan #26; root, zgoda jest) |

## 3. Plan akcji (tylko bezstratne), ranking zysk / wysiłek

Duplikaty scalone: jedno przejście KV (63a E1 + 63c E7), n MTP per karta (63d E1 + 63e G8/E4), chude checkpointy (63b E2 + RTP #1574), planer pamięci Enigmy (63a E7 + 63a §16 + 63b E9), higiena `spec_sweep` (63e E5 + E8 + test tool-calli z 63a §13), diagnostyka Enigmy (63c E10 + 63e E9 + 63b E4/E6/E7).

| # | Akcja | Źródła | baseline → oczekiwane → przyrost | Wysiłek | Wymaga | Stan |
|---|---|---|---|---|---|---|
| 1 | **`--cache-ram 16384 → 40960`** w `run-llm.sh:109` (RAM 62 GB, model w VRAM) | 63b E1 | tura po przełączeniu wątku 75–120k: 85–200 s → ~4–8 s → **−90…−97%** `[SZACUNEK]`; bitowo | 1 linia + pomiar `free` w szczycie | **zgoda** (restart :8080), CPU | czeka |
| 2 | **Uczciwy bench Enigmy**: G1 te same tokeny dla obu ramion; dalej G2 ramię T=1, G3 próg szumu + potwierdzenie zwycięzcy, G4 deep 32k w decyzji, G5 zegar klienta, G6 rozgrzewka, G7 BACO keepawake | 63e §6.1, E2 | „przyrost %” liczony na różnych promptach → na tych samych; G7: 4.4 → 92 t/s po bezczynności przy `power/control=auto` | 1–2 dni TS | CPU + 1 przebieg **GPU** | **G1 w toku (EngineBenchFair)** |
| 3 | **Profil jednego kroku przy 199k** (rocprofv3, PM4 off): FA celu, FA draftu, maska KQ z CPU (F5), combine; potem maska na GPU / poprawka `kvq` | 63d E7, 63e §10.1, 63e §4 | 199k 74.5 → 93–104 → **+25…40%**, jeśli FA ≥ 2× nad podłogą pasma `[SZACUNEK, warunkowo]` | 30 min GPU + 0.5 d analizy | **GPU** | czeka |
| 4 | **MTP n=1…4 jako kandydaci** w optymalizatorze Enigmy (draft nie zmienia wyjścia) | 63d E1, 63e G8 | karty 8–12 GB: n=4 → najlepsze n → **+0…+15%** (4060 u closedcircuit 32 → 46 t/s); XTX 114.8 → 114.8 | 0.5 d | CPU + **GPU/$** (3060, 4060 Ti, XTX) | czeka |
| 5 | **Pakiet topki**: cap occupancy FA na 64 KB LDS (ROCm 10), MTP lean reserve, poprawki MTP z upstream (#30574, #31350, #31368) | 63c E4, E6, E8 | TTFT 32k −0…5%; VRAM −0.7 GB → `-ub 1024/2048` pp4096 1123 → 1157–1213 (+3…8%); akceptacja po restore 37 → 49% (upstream) | ~2 d | **GPU** (pomiar); ub zmienia kolejność sum → bramka md5/KLD | **w toku (TopkaQuick63)** |
| 6 | **Chude checkpointy w cache** (1. i 2 ostatnie wiadomości usera + n−4−ub, n−4; jak RTP #1574) + `agent_bench.py` Mai i `replay interf` z 2 wątkami ~75–120k | 63b E2, E0 | wpis 118k: 14.2 GB → ~3–4 GB; w 16 GB 1 → 3–4 długie wątki; save/restore ~3× szybciej `[SZACUNEK]`; md5 bez zmian | 1.5 d | CPU + **GPU** test | czeka |
| 7 | **Wpis „wspólny początek” (Maya #607)**: mały wpis KV 0..p + stan GDN + draft, `CACHE_SHARE_MIN` wybiera go zamiast kopii całego wpisu | 63b E3 | start sesji po wyrzuceniu: 4.4 s → 0.3–0.5 s; przy 100k+ ~5–7 s → 0.3–0.5 s → **−70…−95%** | 1–1.5 d | CPU + **GPU** test | czeka |
| 8 | **`kvq`: jeden odczyt K/V na weryfikację** (kafel na grupę N×G / 32 kolumny zamiast 2× po 16) | 63a E1, 63c E7, qwen-warp, mkyt | 94k 105.6 → 111–121; 199k 74.5 → 78–86 → **+5…15%** (63c: +2…4%, 63a: +8…15%) | 3–5 d | **GPU**; wariant 32 kolumn może zmienić md5 (kolejność redukcji) → bramka KLD | czeka |
| 9 | **Nadmiar KV 10.7 KiB/token**: znaleźć bufor (lookup/spec?) rosnący z ctx i przyciąć | 63a §16 | zapas VRAM przy 262k +~2.7 GiB `[SZACUNEK]`; 0 t/s | 0.5–1 d | **CPU** (czytanie `llama-context`), potem GPU | czeka |
| 10 | **LFM + drafter DSpark**: krok 1 krzywa t(K) `llama-bench -p 1..10` bez draftera; krok 2 drafter | 63d E2 | LFM ~296 → 281–385 → **−5…+30%** `[SZACUNEK]` | 0.5 d | **GPU**; krok 2: **zgoda** (pobranie 664 MB) | czeka |
| 11 | **Następny krok przed synchronizacją hosta** (token z GPU jako wejście grafu t+1) | 63e E1 | LFM ~296 → 308–314 (**+4…6%**); Qwen 114.8 → 116–117 (+1…2%) | średni–wysoki | **GPU**; bitowo z konstrukcji | czeka |
| 12 | **Diagnostyka bezstratna**: strażnik `splits` > 3 (FA na CPU), „rachunek modelu” (32 tok. greedy + top-5), `LLAMA_SERVER_PREFIX_LOG`, audyt `LLAMA_SERVER_SAFE_TOOLS` (nic nie przepisuje prefiksu), test przerwanego prefillu | 63c E10, 63e E9, 63b E4/E6/E7 | ochrona przed prefillem ×10–35 wolniejszym; diagnoza każdego chybienia cache | 0.5 d każda | **CPU** (+ krótki test GPU dla przerwania) | czeka |
| 13 | **Higiena `spec_sweep`**: 48 promptów dev/holdout, hash buildu i env w wierszu, minimum per prompt, `--gap 2,10`, test równoległych tool-calli, 6 pytań ledgera | 63e E5, E8, 63a §13 | 0% t/s; chroni przed fałszywymi wygranymi | 1 d | CPU + **GPU** (przebieg z przerwami) | czeka |
| 14 | **Przeszukiwanie flag** (TPE: DRAFT_N, LOOKUP_W/MMIN, p_min, ub, PM4_MIN_DISPATCH, typ KV draftu) z ABBA na holdoucie | 63e E4 | spec_sweep T=1 114.8 → 116–120.5 (**+1…5%**) | średni | **GPU** (po #13) | czeka |
| 15 | **Profil „kod/T=0”**: MTP n=6–7 z mniejszym słownikiem draftu, opt-in według klasy | 63a E2 | `mvs` 433.8 → 434–447 (0…+3%); kod/JSON T=0 +5…10%; czat 114.8 bez zmian (kill < −1%) | 1–2 d CPU + 20 min GPU | CPU, potem **GPU**; szerokość weryfikacji zmienia md5 → bramka | czeka |
| 16 | **Pin Enigmy b11856 → b12110 (v0.9.0)** | 63c E9 | CUDA pp Qwen 27B +5…7%, MoE pp +6…17%, Vulkan RDNA3 MTP n=8 do +13% | 1 d + e2e | **$** (3090, 5060 Ti) + **GPU** (Vulkan XTX) | czeka |
| 17 | **Planer pamięci Enigmy**: nachylenie 29.1 KiB/token + warstwa MTP, bufor wyceniany na ubatch, drabina degradacji (okno KV, bez MTP, głowica na host) zamiast cięcia ctx | 63a E7, §16, 63b E9 | UX na 8–16 GB; mniej OOM | 1–2 d | **CPU** | czeka |
| 18 | **Dynamiczny słownik draftu** (12k stałych + 12k top celu) | 63c E5, 63b §1.3 | 114.8 → 116–118 (**+1…3%**); 63b daje sufit +1–1.5% | sym. CPU 0.5 d, potem 2–3 d | CPU, potem **GPU** | czeka |
| 19 | **Trening głowicy MTP on-policy** (wagi na punktach odrzucenia, Decagon) | 63e E3 | czat 114.8 → 120.5–124 (+5…8%); proza 78.93 → 84.5–86 (+7…9%) `[SZACUNEK]` | wysoki | **$** (wynajem GPU) + GPU | czeka |
| 20 | **Szybszy pomiar fabryki**: flagi przełączane w działającym serwerze, poziom szybki (`klab`) → wolny (`spec_sweep`) | 63e E7 | 3–5× więcej ramion na godzinę | średni | CPU + GPU | czeka |
| 21 | **Fuzja GDN decode/weryfikacji** (conv + rekurencja + gated RMSNorm, stan w VGPR) | 63e E6 | 114.8 → 116–116.5 (+1…1.5%) | wysoki | **GPU**; bramka KLD | czeka |
| 22 | **Buffer-resource loads w `kvq`/FA MMA** | 63c E11 | atencja +0…3% (kill < +2% kernela) | 1–2 d | **GPU** | czeka |
| 23 | **Dokładna głowica Q8_0 w płaszczyznach dla LFM** (jeśli `output.weight` = Q8_0) | 63a §6 | −20% czasu głowicy u basalta; dla Q6_K kill | 10 min CPU + pilot | **CPU** | czeka |
| 24 | **Enigma Windows: diagnostyka** planu zasilania, HAGS, large pages | 63b E8 | 0…+12% przy MoE z offloadem na CPU | 0.5–1 d | CPU (test u użytkownika na Windows) | czeka |
| 25 | **Wspólne punkty odniesienia**: zestaw YASAKANI/NInfer (12 zadań + edycja + JSONL) na XTX; prompt benchlab na 3090 | 63a E4, §8 | wiedza: porównanie 1:1 | 0.5 d + 15 min GPU; 15 min 3090 | **GPU**, **$** | czeka |
| 26 | **Termika „eco”**: cap taktowania rdzenia GPU, pamięć bez zmian, bez undervoltu; t/s, W, °C vs stock | #44, decyzja 2026-11-05 | stock 114.8 / ~296 → ? (osobna kolumna „eco”, nie rekord) | 0.5 d | **GPU**, root (zgoda jest) | zatwierdzone |

Kolejność wykonania: #1 → #6 → #7 (jeden blok „cache agenta”, wspólny `agent_bench`), równolegle #2, #3, #4, #9, #12 (CPU albo krótkie GPU). Potem #8 według wyniku #3. #5 kończy TopkaQuick63.

## 4. Odrzucone: zmienia jakość (bez rankingu)

Reguła 2026-11-05. Te pozycje zmieniają wyjście modelu ponad różnice kolejności floatów. Wiedza zostaje w raportach; wracamy tylko na wyraźne polecenie użytkownika.

| Pomysł | Dlaczego odpada | Liczby (tylko informacyjnie) |
|---|---|---|
| QSA (Qwen-QSA-llama.cpp, wyuczone indeksery) | rzadka atencja: czyta 2048 z całego KV; PPL +2.44% przy 64k na Q4, KL długiego kontekstu nietestowane. **Port zaparkowany** | 255K decode 114.7 vs 40.6 t/s **na RTX 4090**, nie na XTX ([63c §3](63c-amd-rocm-llamacpp.md)) |
| LSA (Prefrontal) i test mapy offline | rzadka atencja; mapa destylowana pod YaRN ×40 | 512k TTFT 1.03× / 0.68× ([63d §1](63d-atencja-spec-kwant.md)) |
| Strata KVA (stan późnych warstw) | pomija obliczenia warstw dla promptu | ~−20% TTFT `[SZACUNEK]`, decode −11% u Straty |
| FLy (stratna weryfikacja) | przyjmuje odrzucone tokeny, rozkład celu niezachowany | +5.3…8.2% na Qwen 27B (vLLM) |
| KV 3-bit (ROCM_OCTAVE) | inny kwant KV | 216 B/slot, −1.1 GiB przy 262k |
| KV q4_0 z pierścieniem f16 (qwen-warp) | zmienia numerykę KV (choć w stronę wyższej precyzji) | tool-call 46 → 92–96% u nich |
| Mniejszy format wag (trellis 12.4 GB, YASAKANI/ignis) | zmiana kwantu wag | ~+25…35% `[SZACUNEK]` |
| REAP / HIGGS / QAD (LLM Compressor 0.15) | przycinanie ekspertów, inne kwanty | — |
| f16 WMMA GEMM w prefillu (RDNA-FAST) | aktywacje bez kwantyzacji q8_1: inne wyniki niż MMQ, nie tylko kolejność sum | pp −5…+10% (niepewne) |
| Flash-Next NVFP4 | inny model i kwant | ~30–50 t/s `[SZACUNEK]` |

**Wymaga osobnej decyzji (zmienia treść promptu, nie numerykę):** Enigma odsyłająca `reasoning_content` w historii ([63b E5](63b-colibri-maya-delta.md), ~0.3–1 s na turę) oraz stała kolejność narzędzi w proxy (Maya #625, [63b E6](63b-colibri-maya-delta.md)). Obie zmieniają to, co widzi model, więc nie wchodzą do planu bez zgody.

## 5. Szybkie wygrane widoczne dla użytkownika

- **`--cache-ram 16384 → 40960`** (plan #1): koniec tur agenta po 85–200 s przy przeplatanych wątkach. Wymaga zgody na restart serwera :8080.
- **Uczciwy bench Enigmy, G1** (plan #2): „przyrost %” w UI liczony na tym samym prompcie; w toku (EngineBenchFair).
- **MTP n per karta** (plan #4): pół dnia kodu; na słabszych kartach do +15%.

## 6. W toku

- **TopkaQuick63:** cap LDS w occupancy FA, MTP lean reserve, poprawki MTP z upstream (#30574, #31350, #31368) – plan #5.
- **EngineBenchFair:** G1 w benchmarku Enigmy – plan #2.
- **QSAPort:** zaparkowany (reguła bezstratności).

## 7. Jak myślą najlepsi (skrót listy z [63e §12](63e-metodologia-agenci.md))

**Pomiar.** Najpierw próg szumu z kilku powtórek baseline'u; zysk liczy się dopiero ponad nim i po potwierdzeniu. Oba ramiona dostają ten sam input bajt w bajt; kandydat nigdy nie renderuje własnego obciążenia. Mierz w reżimie użytkownika (temperatura, przerwy, długości, struktura tekstu); losowe dane kłamią przy top-k i MoE. Zegar poza mierzonym procesem; wyniki > 75% rooflinu i skoki o rzędy wielkości są podejrzane. Stroić na dev, raportować z holdoutu. Każdy wynik z hashem kodu i konfiguracji; nie powtarzać niezmienionego kodu, licząc na szum.

**Integracja.** Wygrana komponentu to hipoteza; złożenie zmian to nowy kandydat mierzony w całości. Zmiana statyczna (VGPR, occupancy) to hipoteza, dopóki ISA się nie zmieni (`klab isadiff`).

**Poszukiwanie.** Zanim powstanie nowy kernel: tani przegląd flag i strojenie bibliotek producenta. Szukaj martwej pracy: dopełnień, pracy rozmiarem pojemności zamiast długości, pustych copy/memset. Sterowanie zostaje na GPU, następny krok startuje przed swoim wejściem. Rejestry > LDS > pamięć globalna.

**Organizacja agentów.** Przepustowość pomiaru to sufit: hot-reload zamiast restartu, poziom szybki i wolny. Pamięć wyników tak, narzucona strategia nie; notatki w zwykłym Markdownie. Propozycja eksperymentu ma 4 części: wyjaśnienie, interwencja, przewidywanie, falsyfikacja. Plateau to sygnał do zmiany składu zespołu (np. audytor pomiaru), nie sufit problemu. Człowiek łapie oczywiste błędy i zatwierdza zmiany stratne; bezstratne i stratne zawsze osobno. Sędzia poza zasięgiem agenta, diff czyta niezależny weryfikator. Każda przyjęta zmiana odpowiada na 6 pytań: niezmiennik, hipoteza, gdzie wygrywa, gdzie przegrywa, fallback, pułapka benchmarku.

## 8. Źródła

- Raporty: [63a](63a-silniki-lokalne.md) (§3–§17), [63b](63b-colibri-maya-delta.md) (§0.1, §1–§6), [63c](63c-amd-rocm-llamacpp.md) (§2–§8), [63d](63d-atencja-spec-kwant.md) (§0–§9, E7), [63e](63e-metodologia-agenci.md) (§2–§12); rejestr [63-WATKI](63-WATKI.md); stan [63-STATUS](63-STATUS.md).
- Wersje i commity źródeł: sekcje „Źródła” w raportach; wiersze w `wiki/ZRODLA.md` (sekcja „Raport 63”).
- Nasze liczby: `wiki/REKORDY.md`, `product/WYNIKI-XTX-2026-10-19.md:82-86`, `qwen-opt/run-llm.sh:109`, `app/engine/src/server/optimize.ts:110` (stan 2026-11-05).
