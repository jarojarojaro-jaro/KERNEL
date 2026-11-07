# 66 — synteza: Strata 0.2.12 i Maya, 1Cat i TokenSpeed, Hyperkernel, Saber, anatomia serwowania i tqLLM, Flash-Next

Data: 2026-11-07. Synteza raportów [66a](66a-strata-maya.md), [66b](66b-1cat-tokenspeed.md), [66c](66c-hyperkernel-megakernele.md), [66d](66d-saber-engine-rdna.md), [66e](66e-anatomia-serwowania-tqllm.md) i [66f](66f-flash-next-dobor-kwantu-xtx.md). Praca tylko na CPU: bez GPU, bez pobierania wag, serwer :8080 nietknięty. Jedyny nowy pomiar to mikrobench CPU maski KQ (66e §3.3).

**Reguła z 2026-11-05: tylko optymalizacje bezstratne** (wiki `decyzje/2026-11-05-tylko-bezstratne`). Ranking obejmuje zmiany bitowo identyczne albo różniące się tylko kolejnością działań na floatach, sprawdzane bramką greedy md5 (c4708318 / 6f14e814 / 894e56e4) i KLD. Zmiany draftu (bez zmiany weryfikacji) są bezstratne co do rozkładu. Wszystko inne trafia do sekcji 4 i nie jest rankingowane. Numeracja planu („plan #N”) pochodzi z [63-SYNTEZA §3](63-SYNTEZA.md).

Punkty odniesienia (XTX, Qwen3.8-27B UD-Q4_K_XL; [63-SYNTEZA](63-SYNTEZA.md), wiki `REKORDY`):
- long_ctx (T=0, MTP4 + W16): 1.7k 136.5 / **94k 105.6 / 199k 74.5 t/s**; przyrost ~18 ms na krok między 1.7k a 199k, z czego ~5 ms to odczyt KV ([63d E7](63d-atencja-spec-kwant.md));
- spec_sweep T=1: 114.8 t/s w raportach 66; od q63 (2026-11-06) rekord **120.58 t/s**;
- proza E0 78.93 t/s, `mvs` 433.8 t/s, pp4096 1123 t/s;
- luka hosta przy krótkim kontekście: GPU stoi **410 µs/krok** ([37 §2](37-proza-100.md)).

`[SZACUNEK]` = arytmetyka z raportów, nie pomiar.

## 1. TL;DR

1. **Najwięcej obiecuje znany plan #8 (jeden odczyt KV na weryfikację), a pakiet 66 daje mu trzy niezależne wzorce.**
   - 1Cat Pack-GQA48: jeden kafel 48 wierszy, operator −20…21%, runda −8.6% przy 128K ([66b §3.2](66b-1cat-tokenspeed.md)).
   - Saber: fale dzielą wiersze Q, kafel KV wspólny, wariant bitowy z konstrukcji ([66d §3.2](66d-saber-engine-rdna.md)).
   - tqLLM T(x): wspólny „bulk” kluczy i ogon AR, bitowo równy z plain ([66e §3.5](66e-anatomia-serwowania-tqllm.md)).
   - Oczekiwane 199k 74.5 → 77–83 t/s. Bramką jest profil kroku przy 199k (plan #3), a górną granicę wyznacza nasz 24h: +3.0…6.6% przy 94k.
2. **Koszt maski KQ na hoście jest mniejszy, niż zakładała hipoteza F5.** Mikrobench CPU daje 0.25 ms na graf weryfikacji przy 199k, czyli ~0.5 ms na krok (~1.1%) ([66e §3.3](66e-anatomia-serwowania-tqllm.md)). Szacunek „2–6 ms na krok” w 66d G opiera się na starej F5 i jest nieaktualny. Rozstrzyga 20-minutowy ślad `LLAMA_HOSTGAP_TRACE` przy 94k i 199k.
3. **Nowy, tani i bitowy kandydat na prefill: Q6_K w MMQ na gfx1100 ładuje skale bajt po bajcie** (16× `ds_load_i8`, 0× `ds_load_b128`; 66a §3.4). pp4096 +1.5…5% `[SZACUNEK]`, 0.5–1 dnia.
4. **Megakernel: nie portujemy, bo nie ma czego.** Hyperkernel to tylko binaria B300. Pomiar x54 (z 2026-10-21, dotąd niewpisany) pokazał, że usunięcie 126 granic dispatchy poza łańcuchami MMVQ daje +0.24% (szum). Jedyny sensowny krok to tani PoC-A ([66c §7](66c-hyperkernel-megakernele.md)).
5. **Flash-Next na naszym boxie (66a §0, 66f):**
   - llama.cpp master ≥ b11330 ma `qwen4exp` + MTP (#29761); gałąź `danielhanchen` (#28243) zamknięto bez scalenia.
   - Strata ma dwie różne reguły RAM: rodzina ISTA trzyma wszystkich ekspertów w RAM przy „eksperci + ~10 GB”; zestawy Unsloth wymagają „eksperci + 16 GiB”, inaczej przechodzą w budżet RAM − 24 GB (40 GB na 64 GB).
   - Według porównania Unsloth przy równym rozmiarze UD-IQ3_XXS v3.1 (83.6 GB) ma KLD ~0.052 wobec ~0.065 dla GSQ IQ3_S (wykres producenta, stronniczy). To wybór zmieniający model, więc poza rankingiem.

## 2. Nakładki między raportami (scalone w rankingu)

| Temat | Gdzie | Scalone jako | Plan z 63 |
|---|---|---|---|
| **KV czytane raz na weryfikację** | 66b T1 (Pack-GQA: 30 kolumn w jednym kaflu 32), 66d A (blok 2 grup wierszy Q, wspólny kafel KV), 66e T8 (reguła T(x), bitexact z plain); wcześniej 63a E1, 63c E7, 24h | poz. 2 (wariant 66d A pierwszy, bo bitowy z konstrukcji) | **#8** |
| Dobór podziałów `kvq` dla q4_0 D=256 | 66b T2 (1 → 2 CTA/SM dało u 1Cat −21%), 66d §3.2 („argmin 64”) | poz. 3, tańsze preludium do #8 | #8 |
| **Koszt maski KQ na hoście** | 66e §3.3, T1, T3 (mikrobench 0.25 ms/graf przy 199k); 66d G (ws-h28: +6.6 ms/krok z uploadu wielkości pojemności) | poz. 1 (ślad) i poz. 9 (maska poza ścieżką krytyczną) | #3 (F5) |
| Profil kroku przy 199k | 66b T3 (atrybucja metodą 1Cat), 66c D (znaczniki per dispatch w taśmie PM4), 66e T1 | poz. 1 | #3 |
| Overlap kroku / rezydentna pętla MTP | 66b T7 (lekcja TokenSpeed: obcinanie po stop-tokenie na GPU), 66c C (grant z horyzontem 2 kroków), 66e T4 (sufit ~1.5% przy krótkim ctx) | poz. 12 | #11 |
| Megakernel / monokernel | 66b T8 (TokenSpeed), 66c A/B | poz. 15 | – (15a) |
| Checkpointy stanu GDN i odtwarzanie | 66b T4 (siatka co 8192 + junction), 66a A7 (łańcuch fallbacku, Maya #840), 66b T5 (dysk) | poz. 6 i 11 | #6 |
| Przyrostowa praca L1 (tokenizacja, parser) | 66a A3 (`TOK_CACHE` martwy przy `SAFE_SPECIAL`), 66e T2 (parser O(n²)) | poz. 7 i 8 | #12 (diagnostyka) |
| Strona draftu | 66d B (rerank głowicy), 66d C (drzewo), 66d D (lookup „zastąp”), 66a A2 (`p_min` per klasa), 66a A4 (DFlash2 na Macu) | poz. 5, 10, 13, 14, 19 | #4, #15, #18 |
| Planer pamięci Enigmy | 66a A6 (uczciwa wolna pamięć), 66e T9 (`MemAvailable` na pamięci zunifikowanej) | poz. 19 | #17 |
| Higiena pomiaru | 66d H (IC-cold + kontrola negatywna), 66e T7 (rejestr flag), 66c x54 (log nie pokazuje, czy fuzja zadziałała) | poz. 20 | #13 |

## 3. Ranking pomysłów bezstratnych (zysk / wysiłek)

Kolumna „Bramka” to pomiar, który rozstrzyga, czy robić dalej (albo próg kill).

| # | Pomysł | Źródła | Oczekiwany zysk | Wysiłek | Bramka (pomiar rozstrzygający / kill) | Plan z 63 | Wymaga |
|---|---|---|---|---|---|---|---|
| 1 | **Ślad kroku przy długim kontekście**: `LLAMA_HOSTGAP_TRACE=1` przy 1.7k / 94k / 199k (kod jest w topka-q63) + rocprofv3 kroku przy 199k (FA celu, FA draftu, combine, maska) | 66e T1, 66b T3, 66c D | 0% sam w sobie; decyduje o poz. 2, 3, 9 i 12 | ~20–30 min GPU + 0.5 d analizy | jeśli FA < 50% nachylenia 18 ms, poz. 2 spada; jeśli `graph→inputs` < 0.2 ms przy 199k, poz. 9 kill | **#3** | GPU |
| 2 | **`kvq`: KV raz na weryfikację.** Najpierw wariant Sabera (blok = 2 grupy wierszy Q × `nwarps`, dekwant V raz do LDS, podział jak dla `ntiles_x = 2`), potem Pack-GQA 32 kolumn albo T(x) | 66d A, 66b T1, 66e T8 | 199k 74.5 → 77–83 (**+3…11%**); 94k +1…5% `[SZACUNEK]`; nasz 24h: sufit +3.0…6.6% przy 94k, ≤ 2.3% przy 32k | 2–3 d (66d A); 3–5 d (Pack-GQA) | poz. 1; `test-backend-ops perf -o FLASH_ATTN_EXT` hs 256, nb 5, KV q4_0 94k/199k; kill: FA < −10% w rocprofv3; md5 (wariant 66d A z konstrukcji bitowy) | **#8** | GPU |
| 3 | **Przegląd podziałów `kvq` dla q4_0 D=256**: `blocks_per_sm` {1,2,3,4} × min. tokenów na podział {64,128,256}, przełącznik env | 66b T2 | FA przy 199k 0…−10% `[SZACUNEK]` (obecny dobór strojony na LFM2 D=64) | 0.5 d | ta sama komenda perf przy n_kv 32k/98k/196k; zwycięzca → `long_ctx_bench` 199k ABBA; zmiana granic podziału = kolejność sum → KLD | #8 (preludium) | GPU |
| 4 | **Q6_K MMQ na AMD WMMA**: skale raz jako `int` (jak ścieżka Turing), `x_df` przed pętlą `l`, `#pragma unroll` dla `k01`, tylko gfx11 | 66a A1 | pp4096 UD-Q4_K_XL +1.5…3%, Q4_K_M +2.5…5% `[SZACUNEK]`; Q6_K = 13.4% / 21.2% elementów | 0.5–1 d | rocprofv3 `llama-bench -p 4096`: kill, jeśli Q6_K < 5% czasu prefillu; `test-backend-ops -o MUL_MAT(_ID)`; ABBA kill < +1% pp4096; md5 | – (nowe; cel „T1: epilog Q6_K” z planu RSI 21h) | GPU |
| 5 | **Głowica draftu MTP: grube przejście + dokładny rerank top-K** (B1: IQ4_XS + rerank top-8 na wierszach Q6_K `output.weight`; B2: Q2_K + rerank) | 66d B | B1 spec_sweep **+1…3%** (odzysk −2–3% akceptacji z łatki 0032); B2 +1…4% `[SZACUNEK]` | 2 d | offline na logitach: czy top-8 grubej głowicy zawiera argmax Q6_K; potem spec_sweep T=1 + E0 + `mvs` ABBA; md5 bez zmian (cel nietknięty) | #18 (sąsiad: koszt głowicy draftu) | CPU, potem GPU |
| 6 | **Siatka checkpointów GDN** co ~8192 tokenów w długich wiadomościach + checkpoint w punkcie rozwidlenia (junction) + łańcuch fallbacku przy nieudanym restore (Maya #840) | 66b T4, 66a A7 | edycja ostatnich 10% promptu 60k: TTFT ~65 s → ~8–10 s `[SZACUNEK]`; ~150 MiB RAM na checkpoint `[INFERENCE]` | 1–1.5 d | replay: prompt 60k → zmieniony koniec → rodzeństwo; `prompt_n`, TTFT i md5 vs zimny start; projektować razem z #6 | **#6** | CPU + GPU test |
| 7 | **`TOK_CACHE` dla ścieżki `SAFE_SPECIAL`** (dziś martwy w produkcji), tryb `=2` porównuje z pełną tokenizacją | 66a A3 | kilkadziesiąt ms na turę agenta przy 90–262k (24i: 137 ms przy 91k bez PAR) | 0.5 d | `LLAMA_SERVER_AP_TIMING=1`, replay 2 wątków 75–120k na serwerze testowym; `=2` musi dać 0 rozbieżności | #7 / #12 (blok „cache agenta”) | CPU |
| 8 | **Parser czatu raz na krok MTP + przyrostowy O(n)** z wyrocznią (wzór tqLLM `update_reference`) | 66e T2 | CPU wątku HTTP −50…75% od razu (a); dekod 0…+1% przy długich wyjściach `[INFERENCE]` | (a) 0.5 d, (b) 2–3 d | 10 min GPU: `stream:true` vs `false`, 12k tokenów wyjścia, ms/krok na ostatnich 2k; test różnicowy tekstu i tool calli | – (nowe; 39c) | CPU + 10 min GPU |
| 9 | **Maska KQ poza ścieżką krytyczną**: budowa w czasie draftu albo na GPU, stały bufor staging zamiast `std::vector` | 66e T3, 66d G | 199k **+0.5…1.5%**, 94k ~+0.3%, krótki ctx 0 `[INFERENCE]` | 1–2 d | tylko jeśli poz. 1 pokaże `graph→inputs` ≥ 0.2 ms przy 199k; md5 | #3 (F5) | GPU |
| 10 | **Enigma: próg draftu per klasa**: `--spec-draft-p-min` {0, 0.5, 0.8} × n {1,2,4} dla MoE z `--n-cpu-moe` i kart ≤ 16 GB | 66a A2 | 0…+15% na MoE z offloadem `[INFERENCE z pomiarów Straty]`; XTX rezydentny ~0 | 0.5–1 d TS | emulacja na XTX: Qwen3.6-35B-A3B `--n-cpu-moe 20/30/40`, spec_sweep T=0/T=1, ABBA 2 rundy | **#4** | CPU + GPU |
| 11 | **Enigma: cache przeżywający restart** (`/slots?action=save` przy bezczynności i zamknięciu, CRC32C, stan draftu MTP #30574) | 66b T5 | pierwsza tura po restarcie przy rozmowie 50k: ~55 s → ~2–4 s `[SZACUNEK]` | 1–2 d | e2e: rozmowa 50k, restart, następna tura; TTFT, md5 i akceptacja MTP po odczycie | – (nowe; CRC32C z wątku #15 w 63) | CPU + GPU |
| 12 | **Overlap kroku / rezydentna pętla MTP** z grantem horyzontu i obcinaniem po stop-tokenie na GPU | 66b T7, 66c C, 66e T4 | Qwen **+1…1.5%** (sufit 410 µs z 27.3 ms), LFM +4…6%; więcej na słabych CPU (4070 Ti: luka 6.6%) | 5–10 d | po poz. 1; md5 + test „stop-token w środku zaakceptowanego okna, potem trafienie w cache” | **#11** | GPU |
| 13 | **Lookup „zastąp, gdy pewny”** (dopasowanie ≥ 3–6 i kontynuacja ≥ draftu zastępuje drafty MTP) | 66d D | `mvs` +0…5% `[SZACUNEK]`, czat 0 | 0.5 d offline + 0.5 d kod | najpierw offline na logach `LLAMA_SPEC_LOOKUP_LOG` trybu 1; kill przy czacie < −1%. **Uwaga:** synteza 15 odrzuciła „lookup nadpisujący MTP” (66a §3.1); wracamy tylko z nowymi danymi offline | #15 (profil kod/T=0) | CPU, potem GPU |
| 14 | **Drzewo weryfikacji MTP z GDN w formie WY** i maską przodków | 66d C | kod/T=0 +3…8%, czat T=1 0…+4% `[SZACUNEK]`; przy T>0 potrzebna rejekcja wielodraftowa | symulacja 1 d; całość 1–2 tyg. | symulacja CPU na logach MTP; warunek z 24s: dodatkowy wiersz weryfikacji ≤ 0.57 ms (dziś 0.85) | – (24s) | CPU, potem GPU |
| 15 | **PoC-A: hand-off w trwałej siatce** 96–192 WG, ≤ 1 atomik na WG na etap, wagi do VGPR przed czekaniem; jeśli przejdzie, PoC-B (warstwa GDN + FA jako trwały kernel) | 66c A/B, 66b T8 | sam PoC 0%; pełny megakernel +3…6% decode przy krótkim ctx, +2…4% przy 199k, po 40–70 osobodniach `[SZACUNEK]` | 1–1.5 d (A), 4–6 d (B) | kill A: hand-off > 0.3 µs albo < 30% zysku „bez granicy”; kill B: < 8% czasu warstwy albo md5 ≠ | – (15a) | GPU |
| 16 | Merge split-KV w `kvq` przez ostatni przybyły blok | 66d E | +0.2…0.5% (−17 launchy/krok) | 1 d | rocprofv3 combine przy 94k; ABBA; md5; Saber trzyma to wyłączone | #8 (sąsiad) | GPU |
| 17 | Split-K + redukcja ostatniego bloku w MMVQ dla 1024-wierszowych k/v | 66d F | +0.1…0.3% | 1 d | `klab` cold 1024×5120 vs R=1 (raport 49); E0 ABBA; KLD | – | GPU |
| 18 | Pomiar „tura dopisana przy długiej historii” (1Cat: 1.70 s przy 250K) | 66b T6 | wiedza; jeśli > 3 s przy 94k/199k → profil ścieżki „krótki kawałek po długim prefiksie” | 15 min GPU | fill 94k/199k, potem wiadomość 300 tokenów; TTFT z `timings` | #3 | GPU |
| 19 | Enigma (bez XTX): DFlash2 jako kandydat na Macu (66a A4); uczciwa wolna pamięć po starcie silnika (66a A6) i `MemAvailable` na pamięci zunifikowanej (66e T9); rezydua frontu L1 (66e T5); ramię `GGML_CUDA_DISABLE_GRAPHS=1` dla sm_120 (66e T6, najpewniej kill) | 66a, 66e | UX i 0…+14% tylko na Macu z MoE; reszta to diagnoza | 0.5 d każda | Mac / Strix / 5090 ($) albo przegląd kodu | #4, #17, #2 | CPU, $ |
| 20 | Higiena pomiaru (0 t/s): IC-cold w `klab` (rotacja < 96 MB + scrub 192 MB) i symbol kontroli negatywnej przy bramkach bitowych; rejestr flag topki (283 `getenv`); znaczniki czasu per dispatch w taśmie PM4; odporny parser tool-calli (`<toolcall>`, `<function=tools NAME>`) | 66d H, 66e T7, 66c D, 66a A5 | chroni przed fałszywą wygraną (Saber: +30% na gorąco = −11% na zimno) i cichą literówką w env | 0.5–1 d każda | powtórzyć 1 znany przypadek gorąco i na zimno; start serwera z błędną nazwą flagi → exit | #13 | CPU |

**Kolejność wykonania:** poz. 1 (jedna sesja GPU) → poz. 3 i 2 według profilu. Równolegle na CPU: poz. 4 (ISA i kod), 7, 8a, analiza offline do poz. 5, 13 i 14. Poz. 6 razem z planem #6. Poz. 12 i 15 dopiero po wyniku poz. 1.

**Zamknięte w tej syntezie:** 66c E (x54) wpisane do wiki: fuzje ATTN_PREP_MT + KVQ_FWHT_GATE dały prozę +0.24% (szum) i `mvs` 0.0%. Pozycje „mniej dispatchy poza łańcuchem MMVQ” z raportu 54 schodzą w kolejce.

## 4. Zaparkowane (stratne, bez rankingu)

| Pomysł | Źródło | Dlaczego odpada | Liczby (tylko informacyjnie) |
|---|---|---|---|
| Fuzowane eksperty F16 WMMA w prefillu (Strix Halo, gfx1151) | 66a §3.3 | iloczyny F16 zamiast int8/MMQ, „KL-gated” | prefill 4K ×1.77–2.12 |
| Strata `STRATA_HC_Q8`, `PF_FUSED_Q50`, route-tail-skip, „Faster” | 66a §6 | zmiana arytmetyki albo pomijanie ekspertów | dekod ~+9%, R9700 prompt +40–44% |
| Maya: GLM KV INT8, `DS4_INDEX_TC`, `DS4_PROMPT_F16`/`EXPERT_MMQ`, `DS4_CHUNK_GFX11=0` | 66a §6 | inny kwant KV albo „answers change” | VRAM 1.78 → 1.13 GB @128K; prompt +15–45% |
| NVFP4 W4A16 (1Cat, TokenSpeed) | 66b §3.7 | inny kwant wag | BFCL −13.5 pp przy pełnym NVFP4 (63a) |
| KV FP8 E4M3 i host KV FP8 (`qsa_host_kv`) | 66b §3.1 | inny kwant KV; zależność od rzadkiej selekcji | KL 0.0017–0.0021, akceptacja −2.3 pp |
| QSA / rzadka atencja (Flash-Next natywnie; dla 27B tylko przez doklejony indeksator) | 66b §3.1, 66e §6 | rzadka atencja | Flash-Next 250K −18% vs 1K |
| TokenSpeed: KV mxfp8, stan SSM bf16, BLASST skip-softmax, chunked weryfikacja GDN | 66b §3.8 | zmiana numeryki | — |
| Numeryka Hyperkernela i NVIDIA mega (FP8/FP4 tcgen05, KV FP8) | 66c §8 | wyniki nie bitowe | KL 0.0044 (NVIDIA mega) |
| Saber: MXFP4 W4A8, fold wykładnika d ≥ 9, KV fp8, partiale f16, głowica fp8, stan GDN f16, all-reduce `wht6`, FP8 WMMA w prefillu | 66d §6 | cała numeryka stratna | warstwa 58: 0.31% błędu normy |
| tqLLM: TurboQuant TQ3/TQ4/TQ3_4S, KV tq3/turbo/tcq, `--exact off`, ANE FFN, `TQFN_TAIL_SKIP`, prompt cache przy `--np > 1` | 66e §6 | inny kwant albo przybliżenia | KLD TQ_S 0.055, TQ_XS 0.079 |
| **Zmiana modelu na Flash-Next** (dowolny kwant) | 66a §0, 66f | inny model; decyzja użytkownika, wymaga zgody na pobranie 70–94 GB i zatrzymanie :8080 | Strata XTX 60–65 t/s (DDR5); u nas `[INFERENCE]` ~35–55 t/s |

## 5. Flash-Next: korekta 66f i decyzja kwantu (poza rankingiem)

- **llama.cpp:** master ≥ b11330 ma `qwen4exp` + MTP (#29761, `c061df198`, 2026-10-01). Gałąź `danielhanchen:qwen4exp/mtp` (#28243) zamknięto bez scalenia, HEAD `6fcaa16f`. Tablica PLE czytana leniwie z mmap; offload `--n-cpu-moe` + `--moe-cache-mib` (#29887). Livelock ładowania na HIP #29149 pozostaje ryzykiem.
- **Strata, reguły RAM** (66a §0.2; `setup.py:3710-3723`, `docs/MODELS.md:119-134`, `docs/UNSLOTH_Q4.md:26-32`):
  - rodzina ISTA (GSQ-RCO): wszyscy eksperci w RAM, gdy RAM ≥ eksperci + ~10 GB, czyli IQ3_S (50 GB ekspertów) „with little else open”;
  - zestawy Unsloth: wszyscy eksperci w RAM, gdy RAM ≥ eksperci (GiB) + 16 GiB, inaczej tryb budżetu: RAM − 24 GB (`--resident-budget-gib 40` na 64 GB), reszta z SSD.
  - **Obie liczby są prawdziwe, dotyczą różnych rodzin.** Błąd 66f polegał na zastosowaniu reguły ISTA do UD-IQ4_XS („w Stracie nie”). Naprawdę Strata uruchamia go w trybie budżetu z ~17 GiB ekspertów czytanych z SSD.
  - Nasz `MemTotal` to 62.72 GiB. UD-IQ3_XXS v3.1 (arena 50.3 GB = 46.85 GiB) potrzebuje 62.85 GiB, więc brakuje 0.13 GiB i setup wybierze budżet ~38.7 GiB (~8 GiB ekspertów z SSD). Większy budżet można wymusić ręcznie (`--resident-budget-gib`, setup zachowuje go z ostrzeżeniem).
- **Kwant (porównanie producenta Unsloth przy równym rozmiarze, stronnicze):**
  - przy 83.6 GB odzysk 12 benchmarków UD-IQ3_XXS 99.9% vs GSQ IQ3_S 99.0%;
  - zadania praktycznie remis (szerokie przedziały błędu);
  - KLD ~0.052 vs ~0.065 (odczyt z wykresu).
  - Kierunek zgadza się z naszym E1 na 27B (GSQ IQ3_S: KLD-PL 1.77 × UD-Q3_K_XL).
  - **Werdykt:** UD-IQ3_XXS v3.1 to najlepszy wybór przy tym rozmiarze, w Stracie (z SSD-tier ~8 GiB albo wymuszonym budżetem) lub w llama.cpp. GSQ IQ3_S jest domyślny w Stracie i jako jedyny ma pewność „wszyscy eksperci w RAM”.
  - Szczegóły: [66f](66f-flash-next-dobor-kwantu-xtx.md).

## 6. Źródła

- Raporty: [66a](66a-strata-maya.md) §0–6, [66b](66b-1cat-tokenspeed.md) §1–6, [66c](66c-hyperkernel-megakernele.md) §1–8, [66d](66d-saber-engine-rdna.md) §1–6, [66e](66e-anatomia-serwowania-tqllm.md) §1–7 (mikrobench `66e-skrypty/maskbench.cpp`), [66f](66f-flash-next-dobor-kwantu-xtx.md).
- Wcześniejsze: [63-SYNTEZA](63-SYNTEZA.md) (numeracja planu), [24h](24h-kv-jeden-przebieg.md) (sufit jednego odczytu KV), [24s](24s-proza-drzewa.md) (drzewa), [37](37-proza-100.md), [54](54-mniej-granic.md).
- Wersje i commity źródeł: wiersze w `wiki/ZRODLA.md`, sekcja „Raport 66”.
- Strata (klon `146df3c4`): `setup.py:452-509,3710-3738`, `docs/MODELS.md:119-145`, `docs/UNSLOTH_Q4.md:20-40,195-232`; `MemTotal` z `/proc/meminfo` (2026-11-07).
