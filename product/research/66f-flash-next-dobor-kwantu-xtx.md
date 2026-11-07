# 66f: Qwen3.8-Flash-Next na naszym boxie: dobór kwantu i silnika (2026-11-06)

**TL;DR (aktualizacja 2026-11-07: korekta z [66a §0](66a-strata-maya.md), sekcje GSQ-RCO i Unsloth v3.1 vs GSQ-RCO)**
- Na XTX 24 GB + 62 GB DDR4 (Ryzen 7 5700X, `MemTotal` 62.72 GiB) i 119 GB wolnego dysku **najlepszym kwantem przy tym rozmiarze jest Unsloth Dynamic v3.1 UD-IQ3_XXS (83.6 GB, 54.8 GB bez tabeli n-gramów)**, w Stracie albo w llama.cpp. Według porównania Unsloth przy równym rozmiarze ma KLD ~0.052 wobec ~0.065 dla GSQ IQ3_S, a w zadaniach jest z nim praktycznie na remis (wykres producenta, stronniczy).
- **ISTA-DASLab GSQ-RCO IQ3_S** (54.8 GB + 28.8 GB tabeli n-gramów na SSD) to domyślny kwant Straty i jedyny pakiet tej wielkości z pewnym „wszyscy eksperci w RAM” u nas. Społeczność zmierzyła na XTX 62.3 t/s (DDR5, 96 GB RAM).
- **Korekta:** Strata ma dwie reguły RAM. Rodzina ISTA trzyma wszystkich ekspertów w RAM przy „eksperci + ~10 GB”. Zestawy Unsloth potrzebują „eksperci + 16 GiB”, inaczej przechodzą w budżet RAM − 24 GB (~40 GB) i resztę czytają z SSD. Wcześniejsze „UD-IQ4_XS w Stracie nie” było błędne: działa w trybie budżetu, z ~17 GiB ekspertów z SSD.
- **Korekta:** MTP dla `qwen4exp` jest w llama.cpp master od b11330 (#29761). Gałąź `danielhanchen:qwen4exp/mtp` (#28243) zamknięto bez scalenia, więc bierzemy master.
- Najwyższy mieszczący się kwant to UD-IQ4_XS (93.7 GB). Daje tylko ~25% niższy KLD niż UD-IQ3_XXS (wykres), nie ma danych z zadań, a w Stracie część ekspertów idzie z SSD.
- UD-Q4_K_XL (111.3 GB) się nie mieści: bez tabeli n-gramów zostaje 82.5 GB, a RAM i VRAM to ~86 GB łącznie, przed KV i systemem.
- Dzisiejsze 27B daje 95–217 t/s. Flash-Next będzie wyraźnie wolniejszy (`[INFERENCE]` ~35–55 t/s), ale lepszy w benchmarkach agentowych.

## Model (karta HF unsloth/Qwen3.8-Flash-Next-GGUF, README)
- **Parametry:** 125B MoE, 6B aktywnych, do tego 51B embeddingu n-gramowego (warstwa 2) i 4B MTP.
- **Warstwy:** 48 = 12 × (3 × GDN → MoE, 1 × QSA → MoE).
- **QSA:** 24 głowice Q i 2 głowice KV, head 256.
- **Eksperci:** 512, aktywnych 10 routowanych + 1 współdzielony, wymiar pośredni 640.
- **Kontekst:** 262 144 natywnie, do 1M z rozszerzeniem.
- **Benchmarki z karty, Flash-Next vs Qwen3.8-27B:**
  - DeepSWE 1.1: 58.7 vs 42.2;
  - SWE-bench Pro: 62.5 vs 61.7;
  - JobBench: 55.7 vs 33.4;
  - Toolathlon: 73.5 vs 67.1;
  - GPQA-D: 91.7 vs 89.2;
  - HLE: 35.9 vs 30.8.
- **Licencja:** Qwen Community 1.0. Do produktu „AI Work Assistant” potrzebna osobna licencja (wiki `ludzie-firmy/qwen-alibaba`).

## Rozmiary (API HF tree, 2026-11-06; GB dziesiętne)
Tabela n-gramów to w każdym kwancie osobny shard: IQ4_NL, 28.8 GB. Przy losowym dostępie wystarczy ją zostawić na SSD (mmap), czyta się kilka wierszy na token.

| Kwant Unsloth v3.1 | Razem | Bez tabeli n-gramów | top-1 / mean KLD (tabela z poradnika Unsloth, uwaga niżej) | Mieści się u nas? |
|---|---:|---:|---|---|
| UD-Q2_K_XL | 79.5 | 50.7 | 82.7 / 0.225 | tak |
| UD-IQ3_XXS | 83.6 | 54.8 | 85.4 / 0.165 | tak; w Stracie budżet ~38.7 GiB, ~8 GiB ekspertów z SSD (brakuje 0.13 GiB do „wszyscy w RAM”) |
| UD-Q3_K_XL | 89.4 | 60.6 | 88.3 / 0.107 | tak (llama.cpp); w Stracie budżet, ~13 GiB ekspertów z SSD |
| **UD-IQ4_XS** | 93.7 | 64.9 | **89.6 / 0.084** | tak w llama.cpp (~13 GB na GPU + ~52 GB w RAM); w Stracie budżet, ~17 GiB ekspertów z SSD |
| UD-Q4_K_XL | 111.3 | 82.5 | 92.3 / 0.047 | **nie** |

Uwaga do kolumny KLD: tabela z poradnika podaje dla UD-IQ3_XXS rozmiar „82.0 GB” i KLD 0.165, czyli inne rozmiary niż pliki v3.1. To najpewniej stary V3 albo inny protokół `[INFERENCE]`. Nie mieszać z liczbami v3.1 z porównania z GSQ-RCO niżej (wiki `lekcja-kld-protokoly`).

Strata w trybie budżetu (`setup.py:3710-3723`): wszyscy eksperci w RAM tylko wtedy, gdy `MemTotal` (GiB) ≥ eksperci (GiB) + 16. U nas 62.72 GiB. Budżet = RAM − 24 GB. Większy budżet można wymusić ręcznie (`--resident-budget-gib N`, setup zachowuje go z ostrzeżeniem).

Tabele n-gramów do podmiany (`engram/`):
- BF16 102.4 GB;
- Q8_0 54.4 GB;
- Q5_1 38.4 GB, RMSE 0.038;
- IQ4_NL 28.8 GB, RMSE 0.076.

IQ4_XS z tabelą Q5_1 zajmuje 103.3 GB i mieści się na dysku (119 GB wolne).

Shared MTP Q8_0: 2.8 GB. Unsloth podaje dla MTP przy 4 bitach 97–115 GB łącznej pamięci.

## GSQ-RCO (ISTA-DASLab)

Karta Flash-Next: https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF (README, 2026-11-06), 6.89M pobrań. GSQ-RCO to domyślny dostawca Straty (`docs/MODELS.md`).

- **Co to jest:**
  - GSQ (arXiv 2604.18556) to skalarna PTQ z Gumbel-Softmax, która uczy się przypisań do siatki i skal;
  - RCO (arXiv 2605.00649) to riemannowskie wyszukiwanie jednego typu kwantu na tensor pod dokładny budżet rozmiaru;
  - razem dają standardowy GGUF; przeszukano 352 tensory;
  - `ffn_down_exps` ma 640 wierszy, więc K/I-quanty z blokiem 256 odpadają i zostają tylko Q2_0 albo IQ4_NL. IQ3_XXS podnosi 18 z 48 warstw do IQ4_NL.
- **Pliki** (GB; do każdego wariantu ten sam shard n-gramów 28.8 GB IQ4_NL):

| Wariant | bpw | Shard 1 | Razem | Eksperci w RAM (Strata) |
|---|---:|---:|---:|---:|
| Q2_0 | 2.40 | 37.6 | 66.4 | 34 |
| IQ2_XS | 2.50 | 39.2 | 68.0 | 35.5 |
| IQ3_XXS | 3.00 | 47.0 | 75.8 | 43 |
| IQ3_S | 3.50 | 54.8 | 83.6 | 50 |

- **Średnia z zadań** (AIME25 / GPQA-D / LCBv6; BF16 93.12): IQ3_S 93.26, IQ3_XXS 92.57, IQ2_XS 89.16, Q2_0 89.07. Benchmarki są małe (AIME ma 30 pytań), więc to parytet, nie poprawa względem BF16.
- **Prędkość w llama.cpp** (karta): Q2_0 prompt 367 / decode 93.8 t/s, IQ2_XS 108 / 70.3. Formaty IQ z tablicą kosztują czas, a decode IQ2_XS waha się 49–94 t/s.
- **Flagi:** `-lm mmap --lazy-mode on` zostawia tabelę n-gramów na dysku.
- **Reguła Straty:** RAM ≥ eksperci + ~10 GB, więc przy 64 GB mieści się każdy wariant, a IQ3_S „with little else open” (`docs/MODELS.md:119-134`).
- **Karta 27B** (`ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF`): IQ3_S 11.8 GB ogłoszony jako „task-lossless” (AIME 100, LCB 85.71 = BF16); są warianty `-mtp`.
- **Nasze niezależne pomiary przeczą „bezstratności” przy 3.5 bpw:**
  - E1 (2026-10-18): KLD-PL GSQ IQ3_S = 1.77 × UD-Q3_K_XL, akceptacja MTP −3% (wiki `eksperymenty/2026-10-18-e1-kwanty-27b-kld`);
  - 15e: KLD 0.0665 vs UD-IQ3_S 0.0470 (wiki `kwanty-gguf`, `lekcja-kld-protokoly`, R57a);
  - GSQ wygrywa tylko przy ≤ 3 bpw.

## Unsloth v3.1 vs GSQ-RCO przy równym rozmiarze (porównanie Unsloth)

Źródło: https://unsloth.ai/docs/basics/dynamic-3.0-ggufs/dynamic-3.1-ggufs.md oraz wykresy „final key 4.png” i „fully final.png” z CDN gitbooka, odczyt 2026-11-06. **To wykresy producenta, a Unsloth konkuruje z GSQ, więc liczby są stronnicze.**

Pary rozmiarów: UD-IQ1_S 66.4 GB ↔ Q2_0; UD-IQ1_M 68.0 ↔ IQ2_XS; UD-IQ2_XS 75.8 ↔ IQ3_XXS; **UD-IQ3_XXS 83.6 ↔ IQ3_S**.

Średni odzysk z 12 benchmarków (BF16 = 100%):

| Unsloth v3.1 | Odzysk | GSQ-RCO | Odzysk |
|---|---:|---|---:|
| UD-IQ1_S | 97.9 | Q2_0 | 90.5 |
| UD-IQ1_M | 97.4 | IQ2_XS | 89.5 |
| UD-IQ2_XS | 99.4 | IQ3_XXS | 96.8 |
| UD-IQ3_XXS | 99.9 | IQ3_S | 99.0 |

Przy 83.6 GB, UD-IQ3_XXS vs GSQ IQ3_S (w nawiasie BF16):
- DeepSWE 55.1 vs 54.9 (55.8);
- Terminal Bench 2.1: 70.8 vs 67.1 (68.3);
- LCB v6: 90.5 vs 90.0 (90.4);
- GPQA-D: 91.8 vs 92.0 (92.6);
- Aider: 87.1 vs 85.3 (89.3).

Przedziały błędu są szerokie (Terminal Bench ±~8 pkt), więc w zadaniach to praktycznie remis.

KLD (średnia z 7 osi, odczyt z wykresu, przybliżony):

| Kwant | Rozmiar | KLD |
|---|---:|---:|
| GSQ IQ3_S | 83.6 GB | ~0.065 |
| UD-IQ3_XXS | 83.6 GB | ~0.052 |
| UD-Q3_K_XL | ~90 GB | ~0.044 |
| UD-IQ4_XS | ~94 GB | ~0.038 |

- Dla Q3_K_XL i wyżej nie opublikowano benchmarków zadań; wykresy kończą się na 85 GB.
- Kierunek zgadza się z naszym E1 na 27B (KLD GSQ IQ3_S gorszy niż UD). Wspólnego protokołu KLD (nasz korpus, ta sama referencja BF16) dla Flash-Next nie mamy, więc **rzetelne porównanie jakości to pytanie otwarte**.
- **Mieszczenie:** UD-IQ3_XXS shard 1+2 = 49.9 + 4.9 = 54.8 GB wag bez n-gramów, tyle samo co GSQ IQ3_S. W llama.cpp mieści się identycznie. W Stracie nie jest to jednak ta sama reguła: Unsloth potrzebuje eksperci (46.85 GiB) + 16 GiB = 62.85 GiB, a mamy 62.72 GiB. Setup wybierze więc budżet ~38.7 GiB i ~8 GiB ekspertów z SSD, chyba że budżet wymusimy ręcznie.

**Werdykt (2026-11-07):**
- UD-IQ3_XXS v3.1 (83.6 GB) to najlepszy wybór przy tym rozmiarze, w Stracie albo w llama.cpp.
- GSQ IQ3_S zostaje bezpieczną alternatywą w Stracie: jest domyślny i ma wszystkich ekspertów w RAM.
- UD-IQ4_XS: tylko ~25% niższy KLD (wykres), bez danych z zadań, w Stracie z ~17 GiB ekspertów z SSD.

## Silniki na gfx1100
- **Strata:**
  - ISTA: wszyscy eksperci w RAM i liczeni na CPU; Unsloth przy 64 GB: budżet RAM, reszta z SSD; gorący cache ekspertów i KV siedzą w VRAM, tabela n-gramów na SSD;
  - MTP jest wbudowane, jest paczka Linux rx7900 (własny ROCm 7.10); Auto wybiera DFlash2 ze standardowym packiem, na gfx1100 niezmierzony (66a §0.1);
  - pomiary społeczności na XTX: IQ3_S 62.3 t/s, MTP spec 3, greedy, 7900X + 96 GB DDR5; prefill przy 128K 926 → 1687 t/s z tabelą hipBLASLt (R57b §4);
  - nasz DDR4 dual-channel ma ~połowę pasma DDR5, więc `[INFERENCE]` spodziewamy się ~40–55 t/s (66a: ~35–55 t/s);
  - zastrzeżenie: opiekunowie nie uruchamiali paczek RX 7000 na karcie (`docs/AMD_HIP.md:114-118`), także wydania 0.2.12.
- **llama.cpp upstream:**
  - ma arch `qwen4exp` (QSA: `GGML_OP_LIGHTNING_INDEXER`, `TOP_K_MASK`) i `--moe-cache-mib` (PR #29887);
  - **MTP jest w master od #29761 (b11330, `c061df198`, 2026-10-01)**, `--spec-type draft-mtp`. Gałąź `danielhanchen:qwen4exp/mtp` (#28243) zamknięto bez scalenia (HEAD `6fcaa16f`), konkurencyjny #27836 wciąż otwarty;
  - tabela PLE czytana leniwie z mmap (`TENSOR_READ_LAZY`);
  - otwarte problemy:
    - #29149: livelock ładowania na HIP, jest łatka z buforem pośrednim 64 MiB; ta sama ścieżka mmap → upload na urządzenie co nasze `init_user_pages` w dmesg `[INFERENCE]`;
    - #30032: OOM indeksera QSA przy wizji;
    - #30768: śmieci na Vulkan RADV z transfer queue;
  - społeczność (#29149): RX 9060 XT 16 GB + 64 GB DDR4: 8 t/s, przy długim kontekście 3 t/s (ROCm); 5700X + 16 GB VRAM + DDR4: 14.8 t/s;
  - na V100 Strata vs llama.cpp z `--moe-cache-mib`: ~2.4× (#3082).
- **Topka (nasz fork):** brak `qwen4exp` (baza d5839abfb), więc odpada bez rebase.

## KV przy pełnym kontekście
- Pełna uwaga to tylko 12 warstw QSA × 2 głowice KV × 256, co daje 24.6 KB/token f16, a indekser dokłada ~3 KB/token.
- 262 144 tokenów to ok. **7.2 GB f16**, do tego mały stan GDN. Pełny kontekst bez kwantyzacji KV jest więc wykonalny `[INFERENCE: z karty modelu]`.

## Plan testu (po decyzji użytkownika)
1. Pobranie robi użytkownik, ~84 GB, nie my przez łącze domowe:
   - **UD-IQ3_XXS v3.1** (83.6 GB): ten sam GGUF w obu silnikach, zgodnie z A/B z 66a §0.4;
   - alternatywa: GSQ-RCO IQ3_S z repo ISTA-DASLab (Strata, wszyscy eksperci w RAM).
2. Czat 27B zatrzymać przez `run-llm.sh` (jeden SIGTERM).
3. Uruchomić Stratę z paczki rx7900.
4. Test w tych samych warunkach co nasz czat: spec_sweep T=1 seedy 1,2,3, prompt prefill 12K, fill 255K, VRAM i RAM w szczycie, waty i temperatury przy eco 2200.
5. Wynik zapisać jako baseline (27B uncensored) → Flash-Next → %, plus jakościowo DeepSWE wg karty.
6. Powrót: `run-llm.sh uncensored`.

## Źródła
- https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF (README, API tree 2026-11-06)
- https://unsloth.ai/docs/models/qwen3.8-next (Dynamic v3.1, tabela KLD, engram, MTP)
- https://unsloth.ai/docs/basics/dynamic-3.0-ggufs/dynamic-3.1-ggufs.md + wykresy „final key 4.png”, „fully final.png” (CDN gitbook, 2026-11-06; porównanie z GSQ-RCO, stronnicze)
- https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF (README, 2026-11-06); `ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF`
- Strata klon `146df3c4`: `setup.py:452-509,3710-3738`, `docs/UNSLOTH_Q4.md:20-40`; `MemTotal` z `/proc/meminfo` (2026-11-07)
- https://github.com/ggml-org/llama.cpp/pull/29761, /pull/28243, /pull/27836 (66a §0.3)
- https://github.com/Niko1221/Strata `docs/MODELS.md` (main, 2026-11-06)
- https://github.com/ggml-org/llama.cpp/issues/29149, /issues/30768, /issues/30032, /pull/28699
- R57b (`57b-strata-qwen38-flash.md` §4), R21n, wiki `repo/strata`, `repo/llama-moe-cache-mib`, `repo/tqllm`
