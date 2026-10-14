# 22 — Luce-Org/lucebox

Źródło: https://github.com/Luce-Org/lucebox (płytki klon HEAD `54132ca`, 2026-10-14), blog https://www.lucebox.com/blog/qwen38-r9700, PR #625 (opis przez API GitHub). Ścieżki niżej są względne do korzenia repo. Wszystkie liczby pochodzą z repo i bloga, czyli są **ich pomiarami** (głównie R9700 gfx1201, Strix Halo gfx1151, RTX 3090), chyba że oznaczono inaczej.

## 1. Co to jest

Lucebox to serwer inferencji w C++ (`server/`, OpenAI API) z własnym, mocno rozbudowanym forkiem ggml (`server/deps/llama.cpp`, vendored z `Luce-Org/lucebox-ggml@luce-dflash`, `VENDOR.md`). Do tego dochodzą eksperymenty w `optimizations/`: megakernel, PFlash, KVFlash, Spark i paged attention. Główny produkt to **spekulacja DFlash/DFlash2/DSpark** dla hybryd GDN (Qwen3.5/3.6/3.8), DeepSeek V4 (heterogenicznie R9700 + Strix Halo) oraz Gemma 4 i Laguna. Repo jest bardzo aktywne: ~2.9k gwiazdek, push z dnia analizy, 97 otwartych issues, licencja Apache-2.0. Sprzęt: przede wszystkim AMD RDNA4 R9700 i RDNA3.5 Strix Halo, do tego CUDA (3090/4090/5090). gfx1100 jest wspierany, ale nie strojony; są tylko stare pomiary z maja w `server/docs/HIP_PERF_PLAN.md`.

**Najważniejsze dla nas:** to ten sam model (Qwen3.8-27B) i ten sam drafter (z-lab DFlash2), którego mamy w `~/models/draft/`, na karcie AMD tej samej klasy.

## 2. Kluczowe techniki (z dowodami)

### A. DFlash2 szerzej niż wytrenowany blok (największy pojedynczy efekt)
- `--draft-block-size` dopuszcza do 2× horyzontu z metadanych checkpointu (`server/src/common/draft_block_size.h:5-18`, `server/src/qwen35/qwen35_backend.cpp:391-412`). DFlash2 trenowano na bloku 8, a przy bloku 16 akceptacja nadal rośnie. Za blokiem 16 czas kroku wpada w klif bez dalszego zysku (komentarz tamże).
- Ich wynik, R9700, Qwen3.8-27B UD-IQ4_XS, T=0, HumanEval-10, decode: blok 8 **133.9 → blok 16 208.1 t/s**, matematyka 109 → 133, plain AR 32.3 (blog, tabela „What the block width buys”). Wynik jest bajtowo identyczny z AR na tym pliku.
- Krok spekulacji na gfx1201 kosztuje **54–55 ms vs 28.6 ms plain** (ratio ~1.9; `qwen35_backend.cpp:2992-2993`). Z 6.4× nad AR wynika średnio **~12 tokenów/krok** na HumanEval przy bloku 16 `[WNIOSEK]`.
- Długi kontekst: od 8K zatwierdzonych tokenów szerokość *weryfikacji* jest cięta do 8, a drafter dalej proponuje 16 (`qwen35_backend.cpp:3144-3180`). Ich pomiar: 39.9K tokenów, verify 16 32.7 vs verify 8 45.5 t/s. Obserwacja nieoczywista: **draft 16 + verify 8 akceptuje lepiej niż draft 8** (0.414 vs 0.375 akceptacji na pozycję przy 27K, `:3150-3151`). Mask-tokeny dalszych pozycji pomagają niekauzalnemu blokowi.
- Selektor DFlash2: deterministyczna zachłanna ścieżka, w której każda pozycja jest warunkowana poprzednim wyborem przez iloczyn rank-256 (`server/src/common/dflash2_head.cpp:205-269`). Nasz llama.cpp robi to samo, argmax po kracie z poprzednikiem (`~/llama-master/common/speculative.cpp:1297-1319`), więc tu nie ma różnicy algorytmicznej.
- Nasz llama.cpp przycina `n_max` do `block_size-1` (`~/llama-master/common/speculative.cpp:1074-1081`), więc blok 16 jest dziś u nas niedostępny.
- Pod koniec bloga jest uczciwa prawda o prozie przy długim kontekście: 24–58 t/s, a przy 70K llama.cpp z tym samym drafterem jest szybszy (31.1 vs 23.7).

### B. Adaptacyjna polityka „AR burst”
- Mierzą na żywo EMA akceptacji i stosunek kosztu kroku spec/plain. Poniżej `0.8·(ratio−1)` przechodzą na 40 kroków plain decode, potem robią jedną próbę spec (`qwen35_backend.cpp:2983-3015`). Na prozie z każdym drafterem są poniżej progu opłacalności (PR #625, „Known limitations”).

### C. Kernele HIP w ich ggml
- **GDN grouped-cols**: 4 kolumny na 16-lane podgrupę, stan 4×8 floatów w rejestrach, redukcje w podgrupie 16 (`ggml/src/ggml-cuda/gated_delta_net.cu:364-623`). Tryb drzewa przeładowuje stan rodzica z bufora pośredniego (`:458-493`). Ich wynik: weryfikacja DDTree 61–196 → ~37 µs/warstwę (PR #625). U nas jest to samo w `gdn_cols_per_warp=4` (`~/llama-master/.../gated_delta_net.cu:4-60`), więc nic nowego.
- **Kafelkowany GDN do prefillu** (port z pwilkin/strix-halo): 16 tokenów q/k/v ładowanych kooperacyjnie do LDS, 8 kolumn na warp, stan w rejestrach przez cały kafel, redukcja DPP `row_xmask` + `permlanex16` (`gated_delta_net.cu:625-807`). Na gfx1151 przy ubatch 24576 dał **2.37× prefillu** według ich komentarza (`:626-627`). Włączony tylko dla RDNA3.5 i qwen4exp (`:843-859`).
- **MMQ, dwa kształty kafla w jednym binarium**: mmq.cuh jest ponownie dołączany w `namespace lucebox_mmq_big`, co daje równolegle 64×64/4 warpy (verify) i 128×128/8 (prefill). Na gfx1201 mały kafel wygrywa do N=64, przy 128 jest remis, przy 512 duży wygrywa o 16–18% (`ggml/src/ggml-cuda/mmq_big.h:1-15`, `mmq.cu:45-76`). Dla verify (N≤32) +12–23%.
- **Paged attention decode** (`ggml/src/ggml-cuda/paged-attn.cu`):
  - Q jest kwantyzowane do q8_1 **raz na krok**, a nie w każdym (warp, partycja) (`:203-228`).
  - Jeden warp liczy `n_batch_heads` głów Q tej samej głowy KV, więc K/V q8_0/q4_0 są czytane raz dla wielu głów (`:230-282`).
  - Wariant WMMA dla prefillu dał 20.6–22.4 vs 6.4–6.8 TFLOPS dla V_DOT2 (RDNA4, `server/docs/PAGED_ATTN_WMMA_HANDOFF.md`, sekcja Performance).
- **Rotacja K (FWHT)** jest domyślnie wyłączona dla KV f16/q8_0 („precision-neutral”) i włączona tylko dla węższych typów (`server/src/common/kv_rotation.h:12-24`). Uwaga: to deklaracja w komentarzu, nie znalazłem pomiaru KLD. U nas llama.cpp obraca każdy skwantyzowany typ, też q8_0 (`~/llama-master/src/llama-kv-cache.cpp:321-336`). Wyłącza to `LLAMA_ATTN_ROT_DISABLE`.
- **Batch-invariant MMVQ** (`ggml-cuda.cu:172-185`, `mmvq.cu:3133-3160`): weryfikacja liczona dokładnie jak decode 1-kolumnowy, żeby wynik był bitowo identyczny z AR. Głównie dla DeepSeek V4 i Q8_0 na RDNA4.
- **MoE**:
  - grouped MMID: tokeny grupowane po ekspercie przy weryfikacji. Na HIP domyślnie wyłączone (`mmvq.cu:562-580`).
  - F16 WMMA GEMM dla ekspertów przy prefillu: kafel wag dekodowany raz do LDS (`mix-wmma-moe.cu:1-20`).
  - eksperymentalna trwała kolejka kafli ekspertów `GGML_CUDA_MMQ_MOE_PERSISTENT` (`server/docs/ENVIRONMENT.md:80`).
  - `moe_fused_kernel` (`moe-fused.cu:66-269`) to skalarna, jednoblokowa fuzja gate/up/down. Wydajnościowo bez wartości.

### D. Megakernel (CUDA, Qwen3.5-0.8B BF16)
- Cały forward w jednym trwałym kernelu: 82 bloki × 512 wątków, czyli 1 blok na SM (`optimizations/megakernel/kernel.cu:68-73`).
- Bariera atomowa `AtomicGridSync` (`:140-164`), ~5 barier na warstwę (`:474-614`, `:644-783`).
- Matvec „warp na wiersz” z aktywacjami w shared memory i ładowaniami 128-bit `L1::no_allocate` (`:186-201`, `:310+`).
- **RMSNorm liczony redundantnie przez każdy blok**, co usuwa barierę między normą a matvec (`:217-259`).
- Wynik na 3090: decode 413 vs 267 t/s llama.cpp (**1.55×**), prefill 1.9× (`README.md:51`). Przy 220 W zostaje 95% prędkości (`RESULTS.md`, DVFS).
- Sami piszą, że zysk maleje z rozmiarem modelu i że to tylko BF16, bez kwantyzacji (`README.md`, „Scope and limitations”).

### E. Notatki o gfx1100 (`server/docs/HIP_PERF_PLAN.md`, maj 2026, Qwen3.6, stary ggml)
- Kafel MMQ 48/64/4 na RDNA3_0: +1.93% (`:387-416`).
- MMF przy ncols ≤ 16 na RDNA3_0: −2.78% (`:505-520`).
- Rozszerzenie starego MMVQ na 16/23 kolumny: −42% (`:153-246`).
- ggml HIP graphs: −0.73% (`:418-438`).
- Drafter F16 przez Tensile spadał na tile klasy FP32, Q8_0 GGUF dał +8.7% (`:440-557`).
- Referencja: **hipfire** (Rust, kernele per-arch, przechwytywanie hipGraph per forward) daje 132 t/s DFlash na 7900 XTX wobec 76 t/s lucebox (`:559-591`). Repo: https://github.com/Kaden-Schutt/hipfire.

### F. Pozostałe, stratne albo nie dla nas
- PFlash: spekulatywny prefill, mały model wybiera tokeny do prefillu, 10× TTFT przy 128K (`optimizations/pflash/README.md`).
- KVFlash: pula KV 4K z paging do RAM, decode płaski w kontekście, needle 14/16 (`optimizations/kvflash/README.md`).
- Spark: offload ekspertów z kalibrowanym gorącym zbiorem.
- SpecLA: HLD-drzewa i opóźniony commit GDN, +4–7% na gfx1151 (`server/docs/SPECLA.md`, ostatnia sekcja). Opóźniony commit to to samo co nasze S4.
- ROCmFP4: kodbook 4-bit + skala UE4M3, 4.25 bpw (`ggml/rocmfp4/README.md`).

## 3. Przeniesienie na AMD/HIP/RDNA3

| Technika | Na gfx1100? | Jak / dlaczego nie |
|---|---|---|
| DFlash2 blok 16, verify ≤ 16 | **Tak**, to tylko logika hosta | Mamy WMMA iu8 dla 9–16 kolumn (K4, ~0.43 ms/kolumnę) i historię conv bez snapshotów (T1). U nas weryfikacja 16 vs 5 kolumn to ~35 vs ~26 ms, czyli ratio spec/plain jest wyraźnie lepsze niż ich 1.9. Blok 16 powinien u nas dać relatywnie więcej `[WNIOSEK]`. |
| Draft 16, verify 8 przy długim kontekście | Tak | fattn-kvq obsługuje ≤8 tokenów, więc verify 8 trafia w szybki kernel FA. |
| AR burst | Tak | U nas MTP ma ratio ~1.1–1.2, więc próg opłacalności jest niski i zysk mały. Ma sens tylko dla DFlash na prozie. |
| Kafelkowany GDN prefill | Tak, kod jest już pod RDNA3 | DPP `row_xmask`/`permlanex16` jest wspólne dla RDNA3 i 3.5. Brama `IS_RDNA3_5` jest arbitralna. Trzeba połączyć z naszym l2_qk i lag (wersja chain bez lag dotyczy tylko prefillu). |
| Megakernel / persistent | Tak, z zastrzeżeniem | `grid.sync` → bariera atomowa: zmierzyliśmy 0.54–0.58 µs przy 96 blokach. `ld.global.L1::no_allocate` → buffer load z GLC/DLC/SLC. Warp-per-row → wave32. Ryzyko: 96×512 wątków to 16 wave/CU, czyli mniej niż MMVQ ma w locie. Pasmo matvec musi zostać ≥650 GB/s. |
| Paged decode n_batch_heads | Tak | Warp32 robi int8 dp4a (`v_dot4`) z q8_1 Q dla 4 głów Q, a K/V q8_0 czyta raz. Ich kod jest pod D=256, u LFM D=64. |
| Dwa kształty MMQ w binarium | Tak | Ten sam trik namespace. U nas mmq_y/nwarps są stałymi kompilacji na arch. |
| Batch-invariant MMVQ | Tak, ale nie potrzebujemy | Weryfikujemy przez dokładne dopasowanie, a greedy md5 już jest identyczne. |
| Megakernel NVFP4, ROCmFP4, FP8 | Nie / bez sensu | RDNA3 nie ma FP4/FP8. ROCmFP4 ma 4.25 bpw jak IQ4_XS i nie ma dowodu szybkości na gfx1100. |
| PFlash/KVFlash/Spark/heterogeniczne | Nie dla nas | Stratne albo pod offload i wiele GPU. |

## 4. Pomysły dla nas

1. **DFlash2 z blokiem 16 (Qwen3.8, kod i matematyka)**
   - Co zmienić: w `common/speculative.cpp` (~1074–1081) dopuścić `n_max` do `2·block_size−1`. Drafter dostaje wtedy `[id_last, mask×15]`. Sprawdzić, czy graf draftu (pozycje, maska SWA, lm_head dla 15 pozycji) nie zakłada `block_size`.
   - Weryfikacja 16 tokenów idzie przez nasz kernel K4.
   - Zysk `[SZACUNEK]`:
     - krok ≈ 35 ms verify(16) + ~5 ms draft;
     - na kodzie T=0 przy 7–12 tokenach/krok to 175–300 t/s wobec dzisiejszych ~110–130;
     - na czacie/prozie T=1 DFlash przegrywa z MTP (nasze NOTES: 71.9 vs 81.1; brak losowania ścieżki).
   - Koszt: 0.5–1 dnia.
   - Ryzyko:
     - VRAM: drafter 1.14 GB obok MTP przy ctx 204800 może się nie zmieścić;
     - akceptacja po polsku jest słaba.
   - Pomiar: `spec_sweep` na en-code/pl-kod/en-tech, T=0 i T=1, n_max 6/7/11/15. Logować tok/krok i ms/krok. Greedy md5 przy T=0 musi być równe AR.

2. **Rozdzielić szerokość draftu od weryfikacji w DFlash**
   - Co zmienić: draft zawsze 15 masek, weryfikacja tylko pierwszych k (k=6–8, przy >8K kontekstu k≤8 pod fattn-kvq). Lucebox widzi +10% akceptacji na pozycję przy tej samej szerokości verify (0.414 vs 0.375).
   - Zysk `[SZACUNEK]`: +5–10% t/s DFlash przy tym samym koszcie verify.
   - Koszt: kilka godzin, łącznie z pkt 1. Ryzyko niskie.

3. **Wybór drafter per żądanie (outside the box)**
   - MTP dla czatu/prozy, DFlash2-16 dla kodu. Prosty klasyfikator promptu (bloki ``` / słowa kluczowe) albo przełączenie po N krokach na podstawie EMA akceptacji, jak AR burst w lucebox (`qwen35_backend.cpp:2983-3015`).
   - Zysk: kod +50% bez straty na prozie `[SZACUNEK]`.
   - Koszt: 2–3 dni.
   - Ryzyko: VRAM (dwa draftery), złożoność serwera.

4. **LFM2.5: `LLAMA_ATTN_ROT_DISABLE=1` przy KV q8_0**
   - W profilu LFM jest 20 wywołań `fwht` na token (`lfm-decode-round2.md`, tabela §2) plus 20 granic po ~2.5 µs. Lucebox domyślnie nie obraca q8_0 (`kv_rotation.h:12-24`).
   - Zysk `[SZACUNEK]`: −50…−70 µs/token, około −1.5% ms/token.
   - Koszt: zero kodu. Zmienia numerykę, więc trzeba zmierzyć KLD (`llama-perplexity --kl-divergence`) przy q8_0 z rotacją i bez.

5. **LFM2.5: trwały kernel warstwy MoE w stylu megakernela**
   - To dokładnie ścieżka oznaczona u nas „not attempted” (`lfm-decode-round2.md:40-41`).
   - Projekt:
     - 96 bloków (1/CU), wszystkie fazy warstwy shortconv+MoE jako pętle grid-stride (in_proj+conv → out_proj+res → norma+router+top-k → gate+up → down+reduce+res);
     - norma liczona **redundantnie w każdym bloku** z 8 KB wejścia (L2), co usuwa barierę;
     - bariera atomowa między fazami.
   - Zysk `[SZACUNEK]`: 8 granic × 2.53 µs → ~6 barier × 0.6 µs, czyli ~16 µs/warstwę × 30 warstw ≈ 0.5 ms z 4.1 (−12%), o ile matvec w formie grid-stride utrzyma ≥650 GB/s.
   - Koszt: 2–3 tygodnie.
   - Ryzyko:
     - obłożenie (16 wave/CU), przez co MMVQ może stracić 10–20% pasma i zjeść zysk;
     - bitowa zgodność wymaga tej samej kolejności redukcji.
   - Najpierw tani prototyp: jedna faza out_proj (2048×2048 Q5_K) jako grid-stride z 96 blokami, porównana w GB/s z MMVQ. Jeśli wyjdzie ≥90% pasma MMVQ, iść dalej.

6. **LFM2.5: FA decode dla q8_0 z wieloma głowami Q na warp**
   - Wzór: `paged_attn_decode` z `n_batch_heads` (`paged-attn.cu:230-282`) oraz Q→q8_1 raz na krok (`:203-228`). To „bitowa alternatywa” z naszego `lfm-decode-round2.md` §4, z gotowym projektem: każda głowa liczona tą samą arytmetyką co vec, K/V czytane raz zamiast 4×.
   - Zysk `[SZACUNEK]`: przy 98k ok. −0.5 ms/token (+10%), przy głębokości 0 ~0.
   - Koszt: 3–5 dni. Pomiar: llama-bench tg128 d0/32k/98k, hash logitów.

7. **Qwen3.8 prefill: kafelkowany GDN**
   - Najpierw zmierzyć udział `gated_delta_net` w pp4096 (rocprofv3).
   - Jeśli jest >8%, przenieść `gated_delta_net_tiled_cuda` (`gated_delta_net.cu:660-807`) z naszym l2_qk na ścieżkę prefillu z bramą RDNA3. Ich 2.37× zmierzono na gfx1151 przy bardzo dużym ubatch. My mamy ubatch 512, więc zysk na kernelu raczej 1.2–1.5× `[SZACUNEK]`.
   - Koszt: 2–3 dni.

8. **Porównać AL naszego DFlash z lucebox**
   - Ten sam drafter, 10 promptów HumanEval, T=0, n=7.
   - Lucebox przy bloku 8 ma 4.1× nad AR, a llama.cpp na RDNA4 tylko 1.8×. Jeśli nasze tok/krok będzie wyraźnie niższe niż ich ~4–5 (blok 8), szukać przyczyny: nieaktualne cechy targetu po cofnięciu (blog: „keeps the drafter's features exactly current across rollbacks”) albo pozycje i maska.
   - Koszt: 1–2 godziny.

## 5. Krytyka

- „208 t/s” i „3.8× llama.cpp” to HumanEval, T=0, sam decode, bajtowo przewidywalny kod. E2E daje 156. Na prozie przy długim kontekście jest 24–58 t/s, a przy 70K przegrywają z llama.cpp (sami to piszą). Porównanie z llama.cpp dotyczy jego słabej implementacji DFlash na RDNA4 (1.8× nad AR), a nie dobrze strojonego rywala.
- `HIP_PERF_PLAN.md` jest nieaktualny wobec naszego stanu:
  - teza „WMMA bije amortyzację pasma” wynika z naiwnego MMVQ z pętlą po kolumnach; nasze wielokolumnowe MMVQ 2–8 i WMMA 9–16 temu przeczą;
  - „pivot na Vulkan” też nie dotyczy nas, bo nasz ROCm już wyprzedził Vulkan;
  - „MMVQ 1.1% dekodowania” odnosi się do ich ścieżki DDTree.
- Kernelowo nie są przed nami:
  - plain AR na R9700 to 32.3 t/s × 13.3 GiB ≈ 460 GB/s, czyli ~72% z 640 GB/s;
  - ich verify MMQ ~457 GB/s przy szerokościach 4–16 (PR #625);
  - nasze MMVQ 1–5 kolumn ma ~700–740 GB/s z 960, a krok weryfikacji jest relatywnie tańszy (ratio ~1.15 vs ich 1.9).
- `moe_fused_kernel` (jeden blok, skalarny) i `fattn-chunked.cu` (SGEMM cuBLAS) to kod wydajnościowo słaby.
- Megakernel to 0.8B BF16, tylko CUDA i bez kwantyzacji. Sami zastrzegają, że zysk maleje z rozmiarem.
- SpecLA: zysk +4–7% jest pomieszany ze zmianą top-k (przyznają to). Wymaga wytrenowanego drafter EAGLE, którego nie ma.
- ROCmFP4/FP2/FP3 i masa kodu DeepSeek V4/Strix to szum dla nas. Vendored ggml jest bardzo daleko od upstream i trudny do cherry-picku.
- Rotacja q8_0 „precision-neutral” to deklaracja w komentarzu bez pomiaru w repo, więc trzeba to zmierzyć samemu.

## 6. Werdykt

**Średnia.** Kernelowo jesteśmy dalej niż lucebox na RDNA. Repo daje jednak twardy, bezpośrednio przenośny wynik algorytmiczny na naszym modelu i drafterze: DFlash2 z blokiem 16 (oraz draft 16 + verify 8). Dla kodu może to być największy pojedynczy zysk t/s w zasięgu dnia pracy. Jest też gotowy wzorzec trwałego kernela i wielogłowicowego FA q8_0 dla LFM.
