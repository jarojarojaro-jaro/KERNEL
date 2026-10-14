# Przegląd 30 repozytoriów o kernelach GPU + aktualizacja TensorFold: co bierzemy dla 7900 XTX

Data: 2026-10-14. Każde repo przeanalizował osobny agent (tylko czytanie kodu i dokumentów, bez GPU), według `_BRIEF.md`. Pełne raporty: `NN-nazwa.md` w tym katalogu, TensorFold: `../tensorfold/update-v1.0.11.md`. Liczby z repozytoriów to **ich** pomiary (nie powtarzaliśmy ich), a wszystkie zyski dla nas to **szacunki** do sprawdzenia przeplatanym A/B.

Punkt odniesienia: Qwen3.8-27B 104 t/s (krok 28.9 ms, MTP), LFM2.5-24B-A2B ~240 t/s (4.1 ms/token, KV q8_0, 416 kerneli/token, ~2.5 µs na granicę kernela w grafie HIP).

## 1. Werdykty

| # | Repo | Werdykt | Co z niego mamy |
|---|---|---|---|
| 01 | NVIDIA/open-gpu-kernel-modules | średnia | Hipoteza na losowe spowolnienie gate+up w LFM: układ fizyczny VRAM i rozmiar stron TLB inny w każdym procesie; tanie testy (wyrównanie bufora wag do 2 MB, `HSA_MAX_VA_ALIGN`) |
| 02 | a-hamdi/GPU | niska | Kurs z błędnymi benchmarkami; tylko odnośnik do artykułu o GEMM FP32 na 7900 XTX (dual-issue, padding LDS) |
| 03 | deepseek-ai/DeepGEMM | średnia | Harmonogram „Mega MoE” (cała warstwa MoE w jednym trwałym kernelu bez zakleszczeń); pomysł potoku ładowania kafli w MMQ |
| 04 | ScalingIntelligence/KernelBench | średnia (proces) | Lepsza bramka poprawności: diff listy kerneli przy A/B, zatruwanie buforów NaN, hash logitów w trybie wsadowym, A/A i kolejność ABBA |
| 05 | perplexityai/pplx-kernels | niska | Potwierdza nasze tickety/bariery; pomysł rozgrzewania Infinity Cache w przerwach między kernelami |
| 06 | meta-pytorch/KernelAgent | średnia (proces) | Zamrożona bramka testów, odcisk ISA wariantu, miner łańcuchów fuzji z trace'ów |
| 07 | flashinfer-ai/flashinfer | średnia | Wzorce: KV ładowany raz na grupę GQA, monomoe, combine w ostatnim bloku, maska przyczynowa liczona w kernelu |
| 08 | Liu-xiandong/How_to_optimize_in_GPU | niska | Wzór podwójnego bufora LDS dla MMQ (to samo co 03 i 12) |
| 09 | gpu-mode/reference-kernels | niska | Ranking 2026 to nie źródło technik (zwycięzcy oszukiwali albo łatali zależności); pomysły: int8 WMMA dla KQ, `-mcumode`, koszt granicy na poziomie pakietów HSA |
| 10 | tile-ai/tilelang | niska | RDNA3 tylko f16 WMMA, bez iu8; nie generuje lepszych kerneli niż nasze |
| 11 | vllm-project/vllm-xpu-kernels | niska | Fuzja q/k-norm + RoPE + zapis KV; stan GDN w fp16 (zmienia numerykę) |
| 12 | openai/blocksparse | niska | Gotowy wzorzec pętli z prefetchem kafla dla MMQ |
| 13 | NVIDIA/cutile-python | niska–średnia | Odpowiednik PDL na AMD: wcześniejszy start następnego kernela (`hipExtAnyOrderLaunch` + flaga) |
| 14 | Dogacel/auto-gpu-kernel | średnia | Fork ludoo: zbiorcze (coalesced) ładowanie stanu GDN, u nich 20.6 → 11.3 µs, bitowo |
| 15 | openxla/tokamax | niska | conv1d w kernelu GDN (−48 kerneli/krok Qwena); testy „5 tokenów naraz = 5 pojedynczych” |
| 16 | uccl-project/mKernel | niska | Wzorce synchronizacji w trwałych kernelach (liczniki gotowości, epoki, ładowanie wag przed czekaniem) |
| 17 | NVIDIA/TileGym | niska | GDN: dwie redukcje równolegle zamiast po kolei (bitowo); audyt „siatka w pełnych falach” |
| 18 | tensara/tensara | niska | Telemetria `gpu_metrics` co 5 ms; wejścia grafu przez zero-copy |
| 19 | vukrosic/gpu-kernel-engineer-from-scratch | brak | Niedokończony kurs dla początkujących |
| 20 | getkeops/keops | niska | Combine atencji w ostatnim bloku; zmierzyć kopię logitów do hosta |
| 21 | TongmingLAIC/AKO4ALL | średnia (proces) | Test „leave-one-out” całego stosu 54 łatek; archiwum per rodzina kerneli |
| 22 | Luce-Org/lucebox | średnia | **DFlash2 z blokiem 16** (u nich kod 134 → 208 t/s, bajtowo jak AR); `LLAMA_ATTN_ROT_DISABLE` przy KV q8_0 |
| 23 | ekondis/mixbench | średnia | Plan pomiaru sufitu pasma dla rozmiaru pojedynczego wywołania: rozstrzyga, czy dalsza praca nad pasmem MMVQ ma sens |
| 24 | FalkonML/falkon | brak | Out-of-core nie pomaga (PCIe 20–40× za wolne na wagi per token) |
| 25 | alibaba/atrex-kernel-agent | średnia (narzędzia) | Thread trace rocprofv3 (ATT) zamiast martwych liczników PMC; sufit pasma per rozmiar; sondy czasu w kernelach |
| 26 | KernelTuner/kernel_tuner | średnia | Jako silnik przeszukiwania tablic per kształt (z naszym buildem i pomiarem, nie ich HIP) |
| 27 | flashinfer-bench-starter-kit | średnia (proces) | Katalog prawdziwych workloadów z naszych trace'ów; analiza offline unii ekspertów dla spekulacji w LFM |
| 28 | gpu-mode/pygpubench | średnia | **Bit DLC na RDNA3 = „nie alokuj w MALL”**: 1-kolumnowe MMVQ (cały dekod LFM) czyta bez niego |
| 29 | NVIDIA/cuda-rust | brak | Liczba odniesienia: granica kernela w grafie CUDA ~0.81 µs (RTX 5090) vs nasze ~2.5 µs |
| 30 | Kaden-Schutt/hipfire (dodane, polecone przez 22) | średnia–wysoka | **Replay tokenu jako jeden bufor poleceń PM4** zmierzony na 7900 XTX: MoE 35B-A3B 219.6 → 251.8 t/s przy 603 kernelach/token |
| TF | ashhart/TensorFold v1.0.8 → v1.0.11 | średnia (LFM) | LFM2.5 na Metal z n-gramem; „wszystkie loady przed sumami” w małych kernelach; przepis na atencję decode przy długim kontekście (#746); bramka KL przepuściła 2 celowe błędy |

## 2. Co warto zrobić u nas (posortowane wg spodziewanego zysku / kosztu)

### LFM2.5 (ograniczony kosztem uruchomień)
| # | Eksperyment | Źródła | Zysk [szacunek] | Koszt / ryzyko | Pierwszy krok |
|---|---|---|---|---|---|
| L1 | **Replay całego tokenu jako jeden bufor poleceń** (PM4/AQL przez kolejkę ROCr, argumenty kerneli w VRAM) zamiast grafu HIP | 30, 09, 29 | **+10–30% LFM**, +3–8% Qwen | 2–4 tyg.; ryzyko zawieszeń GPU (u nich wariant bezpośrednio do sterownika miał timeouty na XTX) | 1–2 dni: mikrobench kosztu granicy kernela tą drogą vs nasze 2.53 µs; idziemy dalej tylko przy ≤1 µs |
| L2 | **Atencja decode dla KV q8_0** czytająca KV raz na grupę GQA | 07, 10, 15, 30, TF #746, 09 | +12–19% przy 98k (hipfire: 300 → 153 µs/warstwę przy 32k) | w toku (agent rundy 3) | — |
| L3 | **DLC (bez alokacji w MALL) dla wag 1-kolumnowego MMVQ** | 28 | 0–3%, bitowo | 0.5–1 dnia | A/B `spec_sweep lfm none` (nie llama-bench: losowe tokeny = inny routing) |
| L4 | **Trwały kernel warstwy MoE** (norm+router+top-k → gate+up → down+residual), harmonogram w stylu DeepGEMM Mega MoE, wagi ładowane przed czekaniem na licznik | 03, 07, 16, 22, 05 | −0.2…−0.4 ms/token (+5–10%) | 2–3 tyg., wysokie | mikrobench: matvec Q5_K w stałej siatce traci ≤5% pasma? |
| L5 | **Wczesny start następnego kernela** (`hipExtAnyOrderLaunch`, czekanie na flagę po załadowaniu wag) | 13, 05 | −0.2…−0.45 ms/token | średni; sprawdzić, czy przechwytywanie grafu zachowuje flagę | test pary A→B w `launch_cost.hip` |
| L6 | Małe fuzje: combine FA w ostatnim bloku, q/k-norm+RoPE+zapis KV, jedno wgranie wejść grafu / zero-copy | 07, 11, 20, 18, TF | razem ~2–4% | małe, bitowo | po kolei, każda osobno |
| L7 | „Wszystkie loady przed sumami” w małych kernelach | TF #771/#833 | +1–2.5% | małe, bitowo | rms_norm, top-k, router |
| L8 | `LLAMA_ATTN_ROT_DISABLE=1` przy KV q8_0 | 22 | ~1.5% | zero kodu; zmienia numerykę → KLD | KLD vs f16 KV |
| L9 | Diagnoza losowego spowolnienia gate+up (24.3 vs 27.2 µs) | 01, 18, 25 | ~0.11 ms/token, gdy trafia | tani | log wyrównania bufora, liczniki eviction KFD, `gpu_metrics` co 5 ms |
| L10 | Spekulacja dla LFM (n-gram) | TF, 27 | nieznany | — | najpierw offline: ile różnych ekspertów czyta okno k tokenów na prawdziwym tekście (przy losowym routingu ×1.54/×2.05/×2.98 bajtów dla k=2/3/5) |
| L11 | Prefill LFM z `-ub` 1024–4096 | TF #720 | +5–15% prefillu | 15 min, ryzyko VRAM | pomiar |

### Qwen3.8-27B
| # | Eksperyment | Źródła | Zysk [szacunek] | Koszt / ryzyko | Pierwszy krok |
|---|---|---|---|---|---|
| Q1 | **DFlash2 z blokiem 16** (drafter trenowany na 8; dziś blokuje to przycięcie `n_max` w `common/speculative.cpp:1074-1081`), nasza weryfikacja 9–16 kolumn już jest na WMMA | 22, 30 | **kod: 175–300 t/s zamiast ~110–130**; czat/proza nadal lepszy MTP | 0.5–1 dnia; tylko jako opcja dla kodu | zdjąć przycięcie, spec_sweep na promptach kodu |
| Q2 | **Prefill MMQ: potok ładowania kafli** (prefetch następnego kafla do VGPR, mniej barier; dziś 4 bariery i 0 nakładania) + tańszy epilog (magiczna konwersja int→float, skale w rejestrach) | 03, 08, 12, 30 | +3–12% prefillu, bitowo | średni | P0: ablacja (promocja vs ładowanie), żeby wiedzieć, co ogranicza |
| Q3 | GDN: zbiorcze ładowanie stanu (16-bajtowe zamiast pojedynczych floatów), dwie redukcje naraz, conv1d w kernelu GDN | 14, 17, 15 | razem ~1.5–2.5% | średni, bitowo | sonda dostępu do stanu |
| Q4 | Maska przyczynowa liczona w kernelu FA zamiast budowania i wysyłania z CPU | 07, 15, 20 | do −0.6 ms/krok przy 94k | mały, bitowo | rocprof: czas budowy/uploadu maski |
| Q5 | Zmierzyć kopię logitów do hosta przy weryfikacji (~5 MB/krok) | 20 | 0.5–1.2%, jeśli ≥0.2 ms | mały | `rocprofv3 --memory-copy-trace` |
| Q6 | Build z `-mcumode` | 09 | ? (bitowo) | 1 przebudowa | A/B |
| Q7 | Stan GDN w fp16 (obliczenia fp32) | 11, 07 | −0.15…−0.3 ms/krok | zmienia numerykę | najpierw offline na CPU na prawdziwych danych (27 P5) |

### Metodologia i narzędzia (bez zysku t/s, ale chronią przed błędami i oszczędzają czas)
1. **Sufit pasma dla rozmiaru pojedynczego wywołania** (zimna pamięć, 2–50 MB, te same loady co MMVQ): jeśli idealny czytnik też ma ~720 GB/s, kończymy pracę nad pasmem MMVQ i idziemy w liczbę kerneli (23, 25).
2. **Thread trace rocprofv3 (ATT) na gfx1100**: wgląd w stalle instrukcji, skoro liczniki PMC zwracają 0 (25, 02).
3. **Bramka poprawności**: diff listy kerneli w trace przy każdym A/B (czy nowy kernel w ogóle się uruchomił), hash logitów dla 2–16 tokenów i głębokości do 98k, zatruwanie buforów NaN, test A/A, kolejność ABBA (04, 06).
4. **Test czułości bramki KLD celowo zepsutymi wariantami**: w TensorFold bramka KL przepuściła 2 celowe błędy, które złapał test z referencją FP64 per kernel (TF, 18).
5. **Leave-one-out całego stosu 54 łatek** (wszystko wł., wszystko wył., każda wył. po kolei): znajdzie łatki, które już nic nie dają (np. 0049 po 0053) (21).
6. **Tablice strojenia per kształt** z Kernel Tunerem jako silnikiem wyszukiwania (nasz build i pomiar, top-3 weryfikowane w modelu) (26).
7. Czyszczenie cache odczytem bufora > L2 + MALL (6 + 96 MB) w mikrobenchach (28).

## 3. Odrzucone (z powodem)
- Generowanie kerneli przez TileLang / cuTile / Triton: brak iu8 WMMA na RDNA3, brak formatów GGUF, inne bity (10, 13, 17).
- Chunked GDN (WY) dla prefillu: −39% na gfx1100 (Strata #888), tylko dokładne rozwiązanie jest bezpieczne przy L2-norm kluczach (17).
- Out-of-core / offload do RAM: PCIe za wolne (24).
- Sampling bez sortowania na GPU: nie bitowo z naszym samplerem; `-bs` już nic nie dał (07).
- Split-K pod spinlockiem: niedeterministyczny (12).
- Ranking gpu-mode 2026 jako źródło technik: zwycięskie rozwiązania obchodziły testy (09).

## 4. Rekomendowana kolejność
1. **L2** (w toku), potem **L3** i **L9** (tanie, bitowe).
2. **Q1** (DFlash2 blok 16, pół dnia, duży potencjał na kodzie).
3. Pomiar sufitu pasma (metodologia 1) i mikrobench **L1** (koszt granicy przez bufor PM4): te dwa pomiary decydują, czy kolejne tygodnie idą w pasmo MMVQ, w trwałe kernele (L4) czy w replay (L1).
4. **Q2** (prefill MMQ) po ablacji P0.
5. Drobne fuzje L6/L7, Q3/Q4 jako kolejne rundy agentów.
