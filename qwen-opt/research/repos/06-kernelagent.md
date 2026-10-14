# 06 — meta-pytorch/KernelAgent (KernelFalcon + pętla optymalizacji sterowana profilerem)

Źródło: https://github.com/meta-pytorch/KernelAgent, HEAD `e0647170` (2026-07-15). Klon płytki, nic nie było budowane ani uruchamiane. Ścieżki `plik:linia` są względem korzenia repo. Blogi: [KernelFalcon](https://pytorch.org/blog/kernelfalcon-autonomous-gpu-kernel-generation-via-deep-agents/) (generowanie, poprawność) i [KernelAgent](https://pytorch.org/blog/kernelagent-hardware-guided-gpu-kernel-optimization-via-multi-agent-orchestration/) (optymalizacja, 2026-03-06).

## 1. Co to jest

Wieloagentowy system w Pythonie. Zamienia program PyTorch na kernele **Triton**, weryfikuje je, a potem przyspiesza w pętli profil NCU → diagnoza LLM → przepisanie → test → pomiar. Licencja Apache-2.0, 592 gwiazdki, 96 forków, repo od 2025-07, ostatni push 2026-09-08 (GitHub API), czyli projekt aktywny. Sprzęt: tylko NVIDIA (H100 NVL we wszystkich configach, `examples/configs/*.yaml`, `gpu_name`) i Intel XPU. **Nie ma ROCm ani AMD** (README, tabela „Platform Support”; w kodzie brak `rocm`/`hip`/`rocprof`). Podkatalog `oink/` to osobny pakiet kerneli CuTeDSL dla Blackwell SM10x (RMSNorm/LayerNorm/Softmax/CE przy dużym M). Na decode przy M=1–16 nic z niego nie wynika.

Nie ma tu kerneli do przeniesienia. Wartość repo leży w **strukturze pętli agentowej**. Pomiar i bramki poprawności ma słabsze niż nasze (§5).

## 2. Kluczowe techniki

| # | Technika | Dowód | Liczby (czyje) |
|---|---|---|---|
| T1 | **Deterministyczna płaszczyzna sterowania.** Cykl życia workerów, timeouty i warunek sukcesu są w Pythonie, LLM tylko generuje kod | blog KernelFalcon („Deterministic control plane”); `Fuser/runner.py:120-177` (timeout, `killpg` SIGTERM→SIGKILL) | — |
| T2 | **Test pisany raz i zamrożony.** Kernel jest przepisywany co rundę, test nie | `triton_kernel_agent/worker.py:540-546` | — |
| T3 | **Statyczny zakaz „oszukiwania”.** Regexy blokują `torch.nn`, matmul/einsum, `torch.ops.aten`, introspekcję ramek i `globals()` w pliku kernela | `worker.py:38-121`, `:319-325`; anty-cheat w prompcie testu: `templates/test_generation.j2:59-64` | — |
| T4 | **Równoległe ziarna z „pierwszy poprawny wygrywa”.** N workerów z różną temperaturą, wspólny `mp.Event` zatrzymuje resztę | `manager.py:81`, `:193`; `agent.py:380`, `:402` (T=0.8+0.1·i) | 100% poprawności na 250 zadaniach KernelBench L1–L3 (blog KernelFalcon, ich pomiar) |
| T5 | **Izolacja kontekstów.** Każdy worker ma własny katalog i własną historię błędów, więc błąd jednego nie trafia do kontekstu innych | blog KernelFalcon; `worker.py:173` (`deque(maxlen=history_size)`) | — |
| T6 | **Dedup kandydatów.** SHA źródła między workerami oraz **znormalizowany odcisk PTX**: bez komentarzy i nagłówków, rejestry i etykiety przenumerowane | `Fuser/dedup.py:20-51`, `Fuser/worker.py:191-192`; `searching/ptx_fingerprint.py:78-171` | — |
| T7 | **Pętla: profil → diagnoza → recepta → przepisanie → test → pomiar** | `opt_worker_component/orchestrator/optimization_orchestrator.py:386-638` | 2.02× vs ich własne kernele „tylko poprawne”, 1.56× vs `torch.compile` (default, **bez CUDA graphs**), 65/100 L1, „89% roofline” (blog, H100, ich pomiar) |
| T8 | **Roofline z SOL z NCU.** `efficiency = max(compute_SOL, memory_SOL)`, klasy memory / compute / underutilized (<60% obu), stop przy ≥95% | `kernel_perf_agent/kernel_opt/roofline/ncu_roofline.py:47-56`, `:109-194` | — |
| T9 | **Diagnoza przez LLM.** 28 metryk NCU w sekcjach plus kod, wynik JSON {category, root_causes[evidence, fixes]} | `diagnose_prompt/judger_prompt.py:74-127`, `metric_schema.py:57-150` | — |
| T10 | **Pamięć prób i „reflexion”.** Rekord próby: diagnoza, poprawka, czas przed/po, SOL. LLM ocenia „expected vs actual”, „was_diagnosis_correct” i podaje listy `avoid_patterns`/`try_patterns`. Bloki „RECENT ATTEMPTS” i „AVOID/PRIORITIZE” trafiają do następnego promptu | `optimization_orchestrator.py:69-165`, `:964-1080`; `templates/reflexion_prompt.j2`; `templates/kernel_optimization.j2:83-98` | przykład z blogu: poprawka „wydłużyła czas o 37.4%”, wniosek: nie zwiększać naraz BLOCK_N, BLOCK_K i stages |
| T11 | **Beam search P×M×K×C.** P rodziców × M hipotez wąskiego gardła × K różnych LLM × C próbek; potem dedup po PTX, sort po czasie, top-N | `searching/strategy/beam_search.py:17-53`, `:132-160`, `:162-255` | config „concentrated”: 2×3×3×5 = 90 workerów/rundę (`examples/configs/beam_search_diverse_concentrated.yaml:7-14`). „W naszym smoke A/B P=1,C=10 > P=2,C=1” (`:23-26`, jeden smoke test) |
| T12 | **Śledzenie dwóch najlepszych kerneli** (najszybszy i najwyższy SOL) plus **cofnięcie przy dywergencji**. Następna runda startuje z nowego kernela, chyba że jest >50% wolniejszy | `optimization_orchestrator.py:1082-1175` | — |
| T13 | **Pomiar GPU szeregowany przez blokadę per GPU.** Generowanie przez LLM idzie równolegle | `opt_manager.py:207-223` | — |
| T14 | Pomiar: `triton.do_bench`, średnia, 25 warmup / 100 rep, w subprocesie. Opcjonalnie zdarzenia CUDA z czyszczeniem L2 buforem 256 MB (`do_bench` Tritona czyści L2 sam `[WNIOSEK]`) | `benchmarking/kernel_subprocess.py:156-176`; `benchmarking/timing.py:244-260`, `:311-322` | — |
| T15 | Oink: bramka poprawności **przed** pomiarem. Konkurent jest sprawdzany względem **tej samej** referencji („speedupy nie mogą wynikać z luźniejszej numeryki”). Roofline względem **zmierzonego** pasma, nie z karty katalogowej | `oink/benchmarks/README.md:52-61`; `oink/benchmarks/benchmark/bench_utils.py:100-104`, `benchmark_hbm_roofline_sm100.py:16-28` | GB300: zmierzony dach 7.14 TB/s (`oink/README.md`, ich pomiar) |
| T16 | RAG: drzewo 3 poziomów (wąskie gardło → technika → przykład kodu), embedding OpenAI. Treść: TMA, PID swizzle, kernel trwały | `prescribing/RAG_based_prescriber.py:15-60`; `kernel_opt/database/base.py`, `database/docs/*` | — |

Studium z blogu (matvec 2048×1 048 576 BF16, H100): 9.52 → 6.80 → 6.20 → 4.03 → **1.95 ms**, `torch.compile` 2.09 ms, „direct prompt” 8 rund sekwencyjnie 3.20 ms. Ostateczny kernel to podręcznikowy „jeden wiersz na program, skalarny akumulator”.

## 3. Przeniesienie na AMD/HIP/RDNA3

| Technika | Da się? | Jak u nas | Co się nie przenosi |
|---|---|---|---|
| T1 sterowanie w kodzie, timeouty, `killpg` | tak | Mamy częściowo: `spec_sweep.sh` dobija SIGKILL po 15 s (`NOTES.md:160`), `ab.sh` używa `flock /tmp/gpu.lock` + `/tmp/quiet.lock` | — |
| T2 zamrożony test | tak | Agent edytuje tylko pliki kernela (`ggml/src/ggml-cuda/*.cu`). Bramka (test-backend-ops + `lh.sh` hash logitów + greedy md5) jest niezmienna i spoza zakresu edycji agenta | U nich test pisze LLM. U nas referencją jest backend CPU ggml i hash logitów, co jest dużo mocniejsze |
| T3 zakazy „oszukiwania” | tak, w innej formie | Odpowiednikiem „fallbacku do PyTorch” jest u nas **cichy powrót do starej ścieżki** (przełącznik `GGML_HIP_*` nie zadziałał, warunek dispatchu nie złapał kształtu). Sprawdzenie: oczekiwane nazwy kerneli i liczba kerneli/token w śladzie rocprofv3 (pomysł 1) | Regexy po źródle nie mają sensu dla C++ w ggml |
| T4/T5 ziarna, pierwszy poprawny wygrywa, izolacja | tak, przy generowaniu nowych kerneli (np. instancja q8_0 kernela kvq) | Osobny worktree i katalog build na agenta (już: `~/wt/lfm2`), jedna kolejka GPU | Przy optymalizacji pierwszy poprawny ≠ najszybszy. Kompilacja HIP ggml trwa minuty, nie sekundy jak JIT Tritona |
| T6 odcisk PTX | **tak** | Znormalizowany **ISA gfx1100** (`llvm-objdump -d --mcpu=gfx1100` na code object z buildu) per symbol kernela. Do tego metadane AMDGPU (`llvm-readelf --notes`: `.vgpr_count`, `.sgpr_count`, `.group_segment_fixed_size`, `.private_segment_fixed_size` = spill/scratch) | Normalizacja jest „best-effort”: fałszywe różnice tylko obniżają dedup i nie scalają różnych kerneli (`ptx_fingerprint.py:22-27`) |
| T8/T9 SOL z NCU i diagnoza LLM | częściowo | **Liczniki PMC rocprofv3 zwracają u nas 0** (`NOTES.md:256`), więc SOL trzeba liczyć z bajtów/czasu (mamy `kernel_bw.py`, `tok.py`) względem **zmierzonego** dachu (T15), a nie 960 GB/s z karty. Zamiast metryk stalli: statyczny profil z ISA (VGPR → fale/SIMD, scratch, liczba `s_waitcnt`, `buffer_load`/`global_load`, `v_dot4`/`v_wmma`) | Metryki NCU (scoreboard stalls, sector hit rate) nie mają u nas działającego odpowiednika. Diagnoza LLM bez ablacji to zgadywanie (§5) |
| T10 pamięć prób i reflexion | **tak** | Nasze „Wyniki negatywne” w NOTES to ręczna, prozatorska wersja tego samego. Do zrobienia: maszynowy ledger, prognoza przed pomiarem, automatyczny blok w briefie agenta (pomysł 4) | — |
| T11 beam P×M×K×C | tak, z ograniczeniami | Dobre dla stołów strojenia (RPB, NI, waves_per_eu per (typ, n)) i dla trudnych kerneli (FA q8_0, kafle MMQ prefillu) | 1 GPU i drogi build: budżet to kilka do kilkunastu kandydatów na rundę, nie 90 |
| T12 dwa najlepsze, cofnięcie przy dywergencji | tak | Drugą osią u nas powinna być **liczba kerneli/token** (LFM jest launch-bound), a nie SOL | — |
| T13 blokada GPU | już mamy | `flock /tmp/gpu.lock` | — |
| T14 pomiar `do_bench` mean | **nie kopiować** | Nasze przeplatane A/B (`ab.sh`), ms/krok z serwera i rocprofv3 w modelu są lepsze | — |
| T16 treść RAG | nie | TMA, klastry i swizzle Hoppera nie mają odpowiednika na RDNA3. Strukturę (wąskie gardło → technika → przykład) można wypełnić naszymi łatkami 0001–0054 | — |

## 4. Pomysły dla nas

Uwaga o zakresie: przeplatane A/B, kontrola A/A, bramka bitowa, „mikrobench nie wybiera konfiguracji” i ponowne testy przy zmianie reżimu są już w `research/strata/README.md:240-266` i `research/tensorfold/README.md:100-139`. Nie powtarzam ich. Poniżej jest tylko to, co dokłada KernelAgent: **automatyzacja pętli agentowej**.

### 1. `gate.sh`: niezmienny kontrakt agenta z kontrolą cichego fallbacku i „higieny GPU”
- **Co.** Jeden skrypt poza zakresem edycji agenta (T2, T3). Kroki:
  - (a) `git diff --name-only` mieści się w białej liście plików zadania;
  - (b) test-backend-ops dla dotkniętych opów, `lh.sh` (hash logitów 64 kroków, d0 i d3000) oraz greedy md5 LFM i Qwen plain/MTP;
  - (c) **anty-fallback**: profil `tok.py` musi zawierać oczekiwane nazwy kerneli (np. `norm_router_topk_f32`, `mul_mat_vec_q_conv`, `mul_mat_vec_q_moe_down_reduce`) i dokładną liczbę kerneli/token (LFM 416, weryfikacja Qwen ~815–830). Gdy liczba rośnie, zmiana po cichu wyłączyła fuzję;
  - (d) **higiena GPU** przed pomiarem: zero obcych procesów KFD, VRAM równy stanowi bazowemu. Dwa incydenty są już w NOTES: serwer DFlash dzielący VRAM (`NOTES.md:160`) i serwer agenta K4 na porcie 8097 (`NOTES.md:300`).
- **Zysk.** Brak bezpośredniego zysku t/s. Bramka chroni przed fałszywymi A/B i fallbackami, które dziś łapie dopiero człowiek. `[SZACUNEK]` oszczędza 1 zmarnowaną rundę pomiarów na ~10 eksperymentów.
- **Koszt.** 0.5–1 dnia, bo składniki już istnieją (`lh.sh`, `greedy.sh`, `tok.py`).
- **Ryzyko.** Niskie. Liczba kerneli/token zależy od kształtów (n kolumn), więc trzeba zapisać oczekiwania per (model, tryb).
- **Pomiar.** Podłożone błędy w stylu TensorFold: build z `GGML_HIP_NORM_ROUTER=0` oraz drugi `llama-server` trzymający VRAM. Bramka musi oba odrzucić.

### 2. Odcisk ISA i statyczny profil zamiast liczników PMC
- **Co.** Dla każdego wariantu (makro, env, zmiana kodu):
  - wyciągnąć code object gfx1100;
  - dla każdego symbolu kernela zrobić `llvm-objdump`, znormalizować (adresy, komentarze, numery etykiet) i policzyć hash (T6);
  - dodać metadane: VGPR/SGPR, LDS, scratch, a z VGPR obliczyć fale/SIMD;
  - zrobić histogram instrukcji: `buffer_load*`, `global_load*`, `s_waitcnt`, `v_dot4*`, `v_wmma*`, `ds_*`, `scratch_*`.
- **Użycie.**
  - (a) Wariant z identycznym ISA we wszystkich instancjach (typ, n) jest no-opem: oznaczyć go i nie mierzyć.
  - (b) Automatyczny dowód „n=1 bez zmian (ISA identyczne)” (`NOTES.md:244`), dziś sprawdzany ręcznie.
  - (c) Diff profilu wklejany agentowi zamiast metryk NCU. Dwa nasze wyniki negatywne mają przyczynę, którą widać w ISA bez GPU: fuzja gate+up z podwójnymi rejestrami i niższym obłożeniem (`NOTES.md:100`) oraz offsety 32-bit bez `waves_per_eu`, gdzie kompilator czekał na każdy load (`NOTES.md:249`).
  - Uogólnia to punkt Straty „sprawdzić ISA, czy szybka ścieżka się skompilowała” (`strata/README.md:265`).
- **Zysk.** `[SZACUNEK]` 20–40% mniej przebiegów GPU w sweepach typu K1, bo wiele (typ, n) dzieli ISA lub nie zmienia się wcale. Diagnoza „dlaczego wolniej” zajmuje minuty zamiast rundy A/B.
- **Koszt.** ~1 dzień (Python + `llvm-objdump`/`llvm-readelf` z `/opt/rocm/core-10.0/llvm`).
- **Ryzyko.** Niskie. Fałszywe różnice w normalizacji obniżają tylko dedup.
- **Pomiar.** Odtworzyć sweep z `mmvq-bench/results/*` (NI, RPB, NW) i policzyć, ile wariantów miało identyczne ISA.

### 3. „SOL-lite” dla gfx1100: ranking odzyskiwalnych µs dla agenta
- **Co.** Zamiennik roofline z NCU (T8). Dla każdej klasy kernela ze śladu rocprofv3 (`tok.py`, `kernel_bw.py`):
  - **dach zmierzony raz** zamiast 960 GB/s z karty: zimny odczyt i kopia >96 MB, bufor większy niż Infinity Cache (T15);
  - klasa kernela: memory (≥80% dachu), launch/latency (czas < ~4 µs albo siatka < 96 WG), underutilized (reszta);
  - **odzyskiwalne µs**: dla memory `czas − bajty/dach`, dla launch ~2.53 µs na granicę (`lfm-decode-round2.md:23-41`).
- Tabela posortowana po odzyskiwalnych µs × liczba wywołań trafia na początek każdego briefu agenta. Liczy się deterministycznie, nie przez LLM jak `judger_prompt.py:74-127`.
- **Zysk.** Brak bezpośredniego zysku. Celowanie: np. klasy MMVQ out_proj/attn LFM ~560 GB/s vs gate+up 711 GB/s (`lfm-decode-round2.md:110`) dostają liczbę µs do odzyskania zamiast „wydaje się wolne”.
- **Koszt.** 0.5 dnia.
- **Ryzyko.** Dach zależy od zegara przy 285 W, więc mierzyć w tym samym reżimie mocy.
- **Pomiar.** Suma odzyskiwalnych µs vs realny zysk kolejnych łatek, czyli kalibracja.

### 4. Ledger prób z prognozą przed pomiarem i „wyzwalaczem ponownego testu”
- **Co.** `experiments.jsonl` zamiast prozy (T10). Jeden rekord: `{id, model, plik/kernel, mechanizm, klasa wąskiego gardła + dowód, prognoza_ms (zapisana PRZED pomiarem), wynik_ms + liczba par + rozrzut A/A, bitowo?, Δkernele/token, ΔVGPR/fale (z pomysłu 2), werdykt, cause_tags, enables_tags}`.
- Skrypt generuje do briefu agenta blok „OSTATNIE PRÓBY / UNIKAĆ / PONOWNIE TESTOWAĆ”, jak `kernel_optimization.j2:83-98`, ale z prawdziwych pomiarów, nie z autorefleksji LLM.
- **Element nowy względem KA.** Gdy nowa łatka ma `enables_tags` = przyczyna starego negatywu, ledger wypisuje te negatywy do ponownego testu.
- **Kandydaci dziś.**
  - Fuzja gate+up(+SwiGLU) w wielokolumnowym MMVQ (`NOTES.md:100`, przyczyna: rejestry/obłożenie). Powstała **przed** K1 (`waves_per_eu` per (typ, n), offsety w SGPR, `NOTES.md:242-244`). `GGML_HIP_MMVQ_PAIR` łączy gate i up w jednej siatce, ale `unary_gated` (swiglu, 2.7 µs) dalej jest osobnym kernelem (`NOTES.md:267-268`).
  - NI=8 / RPB=8 (`NOTES.md:103`), też sprzed K1.
- **Zysk.**
  - Gate+up+SwiGLU w weryfikacji Qwen: 64 warstwy FFN × (2.7 µs + ~2.53 µs granicy) ≈ **0.33 ms/krok, ok. 1.1% z 28.9 ms**, o ile MMVQ nie straci pasma `[SZACUNEK]`.
  - Kalibracja prognoz (prognoza vs wynik) mówi, którym szacunkom w raportach ufać.
- **Koszt.** Ledger ~0.5 dnia plus przepisanie istniejących negatywów. Eksperyment gate+up+SwiGLU 1–2 dni.
- **Ryzyko.** Gate+up+SwiGLU: wysokie, bo poprzednio było −14% (DFlash 111 → 96).
- **Pomiar.** rocprofv3 MMVQ w weryfikacji (dziś 22.1 ms, `NOTES.md:254`) plus ms/krok w `spec_sweep`; bitowo.

### 5. Kopalnia łańcuchów fuzji (odpowiednik Fuser/subgraph extractor)
- **Co.** Ze śladu rocprofv3 jednego tokenu/kroku (sekwencja kerneli, czasy, przerwy) i listy węzłów grafu ggml policzyć częste n-gramy (2–6) kolejnych kerneli. Dla każdego: liczba wystąpień/token, suma czasów i przerw. Szacunek zysku z fuzji: `(k−1) × 2.53 µs + przerwy − ~1 µs` za ogon „ostatni blok” (koszty z `lfm-decode-round2.md:23-41`). Fuser robi to przez LLM na grafie PyTorch, my możemy deterministycznie.
- **Zysk.** Sama kopalnia nie przyspiesza, ale porządkuje kolejkę. Znane pozycje z `lfm-decode-round2.md:103-112` dają razem `[SZACUNEK]` **~0.35–0.4 ms/token dla LFM (4.10 → ~3.7 ms, ok. +10% t/s)**:
  - down+reduce liczący attn_norm następnej warstwy (−40 uruchomień, ~0.12 ms);
  - gate+up piszące q8_1 (−38, ~0.1 ms);
  - atencja z 11 do ~6 uruchomień/warstwę (−50, ~0.13 ms);
  - jedna kopia wejść grafu zamiast 12 (~0.03 ms).
- Kopalnia powinna potwierdzić tę kolejność i znaleźć pozycje, których lista nie ma.
- **Koszt.** Kopalnia 0.5 dnia. Każda fuzja 0.5–2 dni.
- **Ryzyko.** Niskie dla narzędzia. Fuzje jak w łatkach 0049–0054.
- **Pomiar.** Kernele/token, `ab.sh` 3 rundy, `lh.sh`.

### 6. Równoległe generowanie kandydatów, szeregowy pomiar, dwa etapy
- **Co.** Dla stołów strojenia i trudnych kerneli: instancja q8_0 kernela `fattn-kvq` (`lfm-decode-round2.md:95-101`, −1.1 ms/token przy 98k, `[SZACUNEK]` z tamtego raportu) i kafle MMQ prefillu (~50 z ~123 TFLOPS).
  - Uruchomić C niezależnych agentów (T11) na różnych hipotezach.
  - Każdy kompiluje tylko swój TU (`mmvq.cu`, `fattn-*.cu`) we własnym katalogu build.
  - Kandydaci przechodzą najpierw pomysł 2 (dedup ISA, spill = odrzucenie bez GPU), potem pomiar.
  - Pomiar ma dwa etapy: zimny mikrobench jako sito, potem rocprofv3 w modelu dla top-2. Mikrobench myli się dla Q6_K i GLC/DLC (`NOTES.md:247-248`).
  - Budżet skupić na liderze (P=1, duże C), zgodnie z jedyną obserwacją KA (`beam_search_diverse_concentrated.yaml:23-26`, jeden smoke).
- **Zysk.** Szybsza eksploracja. Zysk t/s pochodzi z samych kerneli, oszacowanych w źródłach.
- **Koszt.** 1–2 dni infrastruktury.
- **Ryzyko.**
  - Kompilacja na 8C/16T konkuruje z pomiarem. Pomiar musi brać `/tmp/quiet.lock`, co `ab.sh` już robi.
  - **Klątwa zwycięzcy**: wybór minimum z N zaszumionych średnich zawyża zysk o ~√(2 ln N)·σ (N=20 → ~1.9σ, N=90 → ~2.5σ, obliczenie własne). Dlatego top-k mierzyć ponownie w świeżych procesach. Ważne też z powodu losowego „slow mode” gate+up (24.3 vs 27.2 µs, `lfm-decode-round2.md:78-81`).
- **Pomiar.** Odsetek kandydatów odrzuconych przed GPU. Zysk zwycięzcy w etapie 1 vs w etapie 2, czyli wielkość klątwy zwycięzcy.

### 7. Outside the box: diagnoza przez automatyczne ablacje zamiast LLM czytającego liczniki
- **Co.** Krok „Diagnose” KA to LLM interpretujący metryki (T9). U nas liczników nie ma, a LLM bez nich zgaduje. Zamiast tego każdy kernel w pętli dostaje szablonowe warianty-ablacje przełączane makrem:
  - same loady bez matematyki;
  - skale jako stałe;
  - bez zapisu;
  - pusty kernel (sama granica).
- Agent widzi czasy ablacji, a nie hipotezy. TensorFold pokazał to ręcznie (`tensorfold/README.md:121-126`). Nowe jest wpięcie ablacji w pętlę jako krok obowiązkowy przed każdą zmianą MMVQ (~700 GB/s z 960).
- **Zysk.** `[SZACUNEK]` rozstrzyga, czy dziura 700 → ~850 GB/s w MMVQ n=1/n=5 to problem loadów (warto walczyć) czy dekwantyzacji i latencji (inny kierunek). Zysk pośredni.
- **Koszt.** 1 dzień na makra w `mmvq.cu`.
- **Ryzyko.** Kompilator może wyrzucić „martwe” loady, więc wynik trzeba sprawdzić w ISA (pomysł 2).
- **Pomiar.** `mmvq-bench` zimno plus rocprofv3.

### 8. (mały) Druga oś „najlepszego”: kernele/token
- **Co.** KA trzyma osobno najszybszy kernel i kernel o najlepszym SOL, a eksplorację kontynuuje z nowego wariantu, chyba że jest >50% wolniejszy (T12).
- **Odpowiednik u nas.** Wariant fuzji z mniejszą liczbą kerneli przy **równym** ms (w szumie) zachować jako bazę następnych fuzji, zamiast go odrzucać. Przykład: Hadamard+quantize, „szum” (`NOTES.md:351`). Pojedyncza fuzja nie daje zysku, ale kolejne mogą się złożyć. Blog KA mówi to samo: „A nie działa, B nie działa, A+B tak”.
- **Koszt.** Zero, zmiana reguły decyzji.
- **Ryzyko.** Narastanie złożoności kodu bez zysku. Limit: maksymalnie 2 kroki bez zysku.

## 5. Krytyka

- **Pomiar jest słaby.**
  - Pojedynczy proces, `do_bench(return_mode="mean")` (`kernel_subprocess.py:166-171`).
  - Bez przeplatania i bez A/A.
  - Akceptacja przy ścisłym `new_time < best_runtime_time` (`optimization_orchestrator.py:1116`).
  - Beam sortuje do 90 kandydatów po surowej średniej (`beam_search.py:220`), więc systematycznie wybiera szum (klątwa zwycięzcy, pomysł 6).
  - Nasz `ab.sh` i ms/krok z serwera są lepsze. Nie kopiować.
- **Poprawność jest luźna.**
  - Test pisze LLM, tolerancje dobiera LLM: domyślnie 1e-3, dla BF16 1e-2/2e-2, „przy dużej akumulacji 1e-1” (`test_generation.j2:93-98`).
  - Referencja liczona celowo w BF16, nie FP32 (`:31-36`).
  - Prompt optymalizacji mówi „atol=1e-4” (`kernel_optimization.j2:115`), a realna bramka to ten wygenerowany test, więc jest niespójność.
  - Blog przyznaje: „we trust the LLM-generated test harness itself — we don't statically analyze it for cheating”.
  - Regexy zakazów łatwo obejść, np. `torch.addmm`, `torch.tensordot`, `torch.linalg.*` nie pasują do `worker.py:80-95` `[WNIOSEK]`.
  - „100% poprawności” znaczy więc „przechodzi test napisany przez agenta”. Nasza bramka (bitowy hash logitów) jest o rząd ostrzejsza.
- **Martwy kod i błędy.**
  - `sol_improvement_threshold` jest zapisywany, ale nigdzie nieużywany (`optimization_orchestrator.py:225`, `:277`).
  - Warunek zbieżności w `should_stop` jest nieosiągalny: wywołanie następuje tylko przy `at_roofline` (`optimization_orchestrator.py:626-633`), a wtedy funkcja zwraca stop już w warunku 1 (`ncu_roofline.py:209-214`).
  - W bazie GPU H100 NVL ma `peak_fp16_tflops: 1671.0  # Without sparsity` (`gpu_specs_database.py:138`), a to liczba **ze** sparsity. LLM dostaje zawyżony dach obliczeniowy ×2.
- **Twierdzenia z blogu.**
  - 2.02× jest względem ich własnych, słabych kerneli „tylko poprawnych”.
  - 1.56× jest względem `torch.compile` w trybie default **bez CUDA graphs**, nie max-autotune.
  - Matvec: 1.95 vs 2.09 ms `torch.compile` to tylko +7%. 4.29 GB / 1.95 ms ≈ 2.2 TB/s ≈ **56% z 3.9 TB/s** H100 NVL (obliczenie własne), a nagłówek mówi „89% roofline”. SOL = max(compute, memory) z `gpu__compute_memory_throughput`, które jest maksimum po jednostkach pamięci, nie DRAM, więc może zawyżać.
  - Porównanie z „direct prompt” (1 łańcuch × 8 rund) vs KA (4 workery × 8 rund) ma **4× większy budżet** po stronie KA. Brak ablacji profilera i reflexion przy równym budżecie, więc wkład „hardware-guided” nie jest wyodrębniony.
- **Nieistotne dla nas.**
  - Cała generacja jest w Tritonie (my piszemy HIP C++ w ggml).
  - NCU tylko pod NVIDIA.
  - Treść RAG (TMA, Hopper).
  - Oink (Blackwell, duże M).
  - AutoRouter/Fuser dla KernelBench (`Fuser/auto_agent.py`).
  - Kernele wynikowe (matvec „jeden wiersz na program”) są daleko za naszym MMVQ (~700–750 GB/s z 960, tj. 73–78%).

## 6. Werdykt

**Średnia** (tylko jako proces). Kerneli do przeniesienia brak, a pomiar i bramki są słabsze od naszych. Warto przejąć cztery elementy struktury pętli agentowej: zamrożoną bramkę z kontrolą cichego fallbacku, dedup kandydatów po znormalizowanym ISA ze statycznym profilem zastępującym liczniki PMC, maszynowy ledger prób z prognozą i wyzwalaczem ponownych testów oraz równoległe generowanie przy szeregowym, dwuetapowym pomiarze.
