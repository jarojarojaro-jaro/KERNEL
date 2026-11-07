# 67c: Pełny backlog testów NVIDIA (z całej bazy wiedzy), 2026-11-07

Autor: NvBacklog67 (Opus). Bez GPU i bez pobierania. Źródła przejrzane systematycznie:
- wiki: `nvidia/*`, `karty/rtx-*`, `kernele/*`, `metody/*`, `lekcje/*`, `decyzje/*`, eksperymenty NVIDIA, `repo/*` (silniki CUDA), REKORDY;
- research 15d, 16c, 24e, 27, 29, 56, 56-orca, 57a–g, 60b, 60c, 63-*, 65, 66-*, 67b;
- łatki `qwen-opt/patches/*`, `cloud/CUDA-AUDIT.md`, `PLAN-TESTOW.md`, `fork-switches.tsv`;
- planer Enigmy: `app/engine/src/server/optimize.ts`, `engine.ts`, `catalog/memory.ts`, `catalog/index.ts`, `data/engines.json`.

Powód: na AMD (XTX) przetestowaliśmy ~70 łatek z leave-one-out. Na NVIDIA było kilka kampanii (09, 16c, 24e, 27, 29, 56, 67), ale w każdej po kilka ramion. Ten plik to **jedna kolejka** dla kampanii `NvVast67b` i następnych wynajmów.

## 0. Legenda i ramiona bazowe

**Oznaczenia**
- ★N: pozycja w TOP-15 do uruchomienia teraz. ★0 wymaga buildu.
- ⚑: wynik koryguje domyślne ustawienie Enigmy (plik:wiersz w kolumnie źródła).
- Bezstratność:
  - **B**: bezstratne (ten sam model; md5 równe albo zmienia się tylko kolejność sumowania przy KLD na poziomie szumu);
  - **B/KLD**: bezstratne pod warunkiem bramki KLD;
  - **LOSSY-parked**: zaparkowane zgodnie z decyzją „tylko bezstratne” z 2026-11-05 (`decyzje/2026-11-05-tylko-bezstratne.md:12-13`).
- Klasy kart: T = Turing sm_75 (2080 Ti), A = Ampere sm_86 (3060/3070/3080/3090), Ad = Ada sm_89 (4060 Ti/4070/4090), B = Blackwell sm_120 (5060 Ti/5070/5080/5090).

**Ramiona bazowe** (w schemacie `fork_arms` z `runs/nv67/inst/nv67.py:432-440`: `label`, `engine`, `env`, `extra`, `ub`, `ctx`, `what`)
- **U** = upstream b12110 (`engine: "new"`) z flagami Enigmy: `-ngl 999 -fa on -ctk/-ctv q4_0 -np 1` (`engine.ts:489-490`), plus MTP `--spec-type draft-mtp --spec-draft-n-max N --spec-draft-n-ubatch 64` (`optimize.ts:116`). Model, ctx i ub według karty z 67b §4.
- **U0** = U bez MTP.
- **P** = pin Enigmy b11856. To **dzisiejszy silnik Enigmy na NVIDIA** (`data/engines.json:80-107`).
- **F** = `cuda-topka2` `2a261101b` (`engine: "topka2"`, tarball w `runs/nv67/pkg/`):
  - env: `LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_GPU_VERIFY=1 LLAMA_SERVER_REASONING_CONTROL=0`;
  - flagi: `--spec-type draft-mtp --spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab {nv}/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs`;
  - wzór: `cards-run/3090f.json` (ramię F131k).
- **L** = `b12110lean` (`runs/nv67/lean/`, łatka `patches/nv67-lean-reserve/0001`).
- **PR** = prism (`runs/nv67/pkg/llama-prism-*`).

**Koszt jednego ramienia** (zmierzony w logu kampanii 67, `results/nv67-4090-20261107/run.log`):
- greedy + sweep 3×400 + prefill: ok. 2–3 min na 4090/5090 i ~3 min na 3090 (P0 3:04, N3u 2:03);
- na 3060/4060 Ti/5060 Ti szacuję ~4 min `[SZACUNEK]`;
- fill 262k: 3.5–4 min na 4090, na kartach 16 GB ~6–8 min `[SZACUNEK]`.

Kolumna „min/kartę” to suma ramion danej pozycji.

**Ważne fakty techniczne** (sprawdzone w kodzie):
- `GGML_CUDA_FORCE_MMQ` i `GGML_CUDA_FORCE_CUBLAS` to **opcje kompilacji**, a nie zmienne środowiskowe (b12110 `ggml/CMakeLists.txt:202-203`). Wymagają osobnego buildu upstream.
- Zmienne runtime w b12110: `GGML_CUDA_DISABLE_GRAPHS`, `GGML_CUDA_GRAPH_OPT`, `GGML_CUDA_GRAPH_CHUNK_SIZE`, `GGML_CUDA_PDL`, `GGML_CUDA_MMQ_PREC`, `GGML_CUDA_CUBLAS_COMPUTE_TYPE` (`git grep getenv b12110 -- ggml/src/ggml-cuda`).
- topka2 dokłada do tego: `GGML_CUDA_MMVQ_N1_ROWS`, `GGML_CUDA_MMVQ_L2PF`, `GGML_CUDA_DISABLE_FUSION`, `GGML_HIP_*` (działają też na CUDA), `LLAMA_*` (sampler, spec, verify).
- kvq **nie ma w topka2**. Gałąź `~/wt/nv-4060ti-kvq` @ `007a6f813` to „topka2 + kvq, domyślnie off, `GGML_CUDA_KVQ=1` włącza”. Ma też przełączniki `GGML_CUDA_KVQ_BPSM` i `GGML_CUDA_KVQ_N1_D256_Q4`.

## 1. TOP-15: kampania musi uruchomić teraz

Wysłane do `NvVast67b` o 17:40 UTC. Odpowiedź: #9 i #12 są już na kartach (4060til/3060s, 3060g/2080tig); #1, #3 i #8 miały dołączyć jako krótkie łańcuchy. **Chwilę później (ok. 17:45 UTC) użytkownik zatrzymał wszystkie testy GPU w chmurze** (polecenie Main: collect, zniszczenie instancji). TOP-15 jest więc kolejką na **pierwszy wynajem po wznowieniu**. Co z #9/#12 zdążyło się zmierzyć, opisze raport 67 (NvVast67b).

| ★ | pozycja (wiersz w §2) | ⚑ | dlaczego teraz |
|---|---|---|---|
| 0 | kvq (B1). **Build** `nv-4060ti-kvq` | – | największy zmierzony zysk na NVIDIA: +25–37% decode @64k. sm_89 bez e2e |
| 1 | typ KV q4_0 / q8_0 / f16 @64k (A1) | ⚑ | planer wybiera f16 > q8_0 > q4_0, a KB mówi, że q8_0 na CUDA jest wolniejsze od q4_0 |
| 2 | topka2 F vs U na każdej klasie (B2) | ⚑ | Enigma nie ma silnika CUDA; F zmierzony tylko na 3090/4060 Ti/3060/3080 |
| 3 | MTP n = 1…4 per klasa (A2) | ⚑ | `MTP_N_MAX_DEFAULT = 3` dla wszystkich kart |
| 4 | `LLAMA_GPU_VERIFY` 0/1 (B3) | – | sm_120 niezmierzone, bez ABBA |
| 5 | `GGML_CUDA_MMVQ_N1_ROWS` na sm_89 (B4) | – | KB: „Ada do ustalenia” |
| 6 | `GGML_CUDA_DISABLE_GRAPHS=1` (A5) | – | tqLLM +20% bez grafów na 5090; u nas niezmierzone na sm_120 |
| 7 | `GGML_CUDA_GRAPH_OPT=1` (A6) | – | upstream env; jedyny wynik −1%, platforma nieznana |
| 8 | ub 256 / 512 / 1024 (A3) | ⚑ | `UB_STEPS` nie ma 256, a przepisy 67b go używają |
| 9 | lean vs b12110 przy max ctx (D3) | – | +0.7 GiB → więcej kontekstu na 12/16 GB |
| 10 | lookup W8 / W16 / off (B5) | – | W8 vs W16 nigdy na NVIDIA |
| 11 | `-np 2` agregat (A13) | – | fork +27–29%; upstream niezmierzony; Enigma `-np 1` |
| 12 | prism vs b12110 na Bonsai Q2_0 (D4) | – | 3060: prism 44.9 vs nasze 35.5 (inny kwant) |
| 13 | `GGML_CUDA_PDL=0` na sm_120 (A7) | – | upstream PDL #22522: +5–13% tg na Blackwell; własnego pomiaru brak |
| 14 | power-limit perf/W (E1) | – | tylko karty wynajęte i tylko gdy kontener pozwala |
| 15 | `-t` z kwoty cgroup + `--no-mmap` zimny start (A11, A12) | ⚑ | llama.cpp bierze `nproc` (32 wątki przy kwocie 7.7) |

## 2. Tabela rankingowa (wszystkie pozycje)

Kolumna „#” to ranga w całym backlogu (1 = najpierw; 1–17 to TOP-15 z §1, ★15 ma dwa wiersze). Wiersze są pogrupowane A–E.

| # | ★ | ⚑ | pozycja | źródło KB (plik:wiersz) | oczekiwany zysk + dlaczego | klasy | ramię (flagi/env/build) vs baseline | min/kartę | fork / upstream | B / LOSSY |
|---|---|---|---|---|---|---|---|---|---|---|
| | | | **A. Flagi runtime na upstream** | | | | | | | |
| 2 || ★1 | ⚑ | **A1. Typ KV dla CUDA: q4_0 vs q8_0 vs f16 przy głębokości** | `nvidia/fa-kv-kwantyzowane-cuda.md:20-23`; `56-orca-3090.md:79`; `16c-kvq-cuda.md:69`; Enigma `catalog/index.ts:167-169` | 3090 @14.7k MTP4: f16 86.5, q4_0 75.4, **q8_0 65.7 (−13% vs q4_0)**: upstream q8_0 idzie ścieżką vec. Na sm_120 vec q4_0 18.9× wolniejszy w opie (3738.9→198.3 µs). Planer daje f16, gdy zostaje ≥ 2 GiB, inaczej q8_0, gdy się mieści, inaczej q4_0 | wszystkie; najpierw B (5060 Ti/5080/5090), A (3090/3060) | U MTP n3 ubd64, `ctx 65536`, `what [sweep, fill]`, extra `-ctk q8_0 -ctv q8_0` i `-ctk f16 -ctv f16` (ostatnia flaga wygrywa `[INFERENCE]`); baseline U q4_0 w tym samym ctx | 3 × (3 + 5) ≈ 25 | upstream | B w ramach decyzji KV (q4_0 standard Qwen, q8_0 LFM); f16 = jakość ≥ |
| 4 || ★3 | ⚑ | **A2. MTP n per klasa: 1/2/3/4** | `63d:25-27,399-404`; `REKORDY.md:132-133`; Enigma `memory.ts:45`, `optimize.ts:84,106` | 4090 262k ub256 (kampania 67): n1 67.0, n2 76.8, **n3 79.1**. 3080: najlepsze n=2, 3060: n=3. 4060 (closedcircuit): n1 46 vs n3 32. RS rośnie 149.6 MiB × (n+1) (67b:37). Enigma testuje tylko n=3 | wszystkie; najważniejsze 8–16 GB | U `--spec-type draft-mtp --spec-draft-n-max N --spec-draft-n-ubatch 64`, N = 1…4; baseline N=3. Kampania ma `spec_n [1,2,3]`, więc **dopisać N4u**, gdzie się mieści | 4 × 3 ≈ 12 | upstream | B (greedy identyczny) |
| 9 || ★8 | ⚑ | **A3. ub 256 / 512 / 1024 (LFM: 2048)** | Enigma `optimize.ts:22` (`UB_STEPS 512/1024/2048`), `catalog/index.ts:161-164`; `67b:18-24`; `15d:112`; `65:40-43` | ub decyduje o ctx (compute ∝ ctx × 2·ub) i o pp. 67b daje ub256 na 12/16 GB, ale optymalizator nie umie 256. LFM `-b 2048 -ub 2048`: pp4096 +56% na 5060 Ti (4217→6587); 3090 niezmierzone | wszystkie | U z `ub` 256 / 512 / 1024 przy ctx klasy, `what [sweep, prefill]`; baseline ub z 67b | 3 × 3 ≈ 10 | upstream | B |
| 31 || | | A4. `--spec-draft-n-ubatch 64` vs domyślne (= ub): szybkość | `67b:36`; `memory.ts:46-48` | pamięć zmierzona (648 → 40 MiB). Szybkość „ta sama” tylko z założenia | wszystkie | U MTP n3 z `--spec-draft-n-ubatch 64` i bez; ctx mieszczący oba | 6 | upstream | B |
| 7 || ★6 | | **A5. `GGML_CUDA_DISABLE_GRAPHS=1`** | `66-SYNTEZA.md:70`; `66e:141-143,190`; `nvidia/latki-na-nvidia.md:24` | tqLLM: +20% bez grafów na 5090, −3% na 3090. U nas grafy: +1.8…4.3% (3060/5060 Ti), −6.9% po wyłączeniu na 3090 LFM. sm_120 bez grafów niezmierzone | B (+ kontrola A) | env `GGML_CUDA_DISABLE_GRAPHS=1` na U0 i U MTP; baseline bez env | 6 | upstream | B |
| 8 || ★7 | | **A6. `GGML_CUDA_GRAPH_OPT=1`** | b12110 env (git grep); `wiki … wyniki-negatywne.md:14` (−1%, platforma nieznana) | optymalizacja grafu / współbieżne strumienie w upstream; wynik −1% nie jest przypisany do karty | wszystkie | env `GGML_CUDA_GRAPH_OPT=1` na U MTP; baseline bez env | 6 | upstream | B (sprawdzić md5) |
| 14 || ★13 | | **A7. `GGML_CUDA_PDL=0` vs domyślne (sm_120)** | `CUDA-AUDIT.md:275`; `repo/megakernele-prior-art.md:14`; `66c:146` | upstream PDL (#22522): +5–13% tg na Blackwell; własny pomiar nigdy. Na sm_86/89 PDL jest no-op | B | env `GGML_CUDA_PDL=0` na U0 i U MTP; baseline domyślny | 6 | upstream | B |
| 43 || | | A8. `GGML_CUDA_GRAPH_CHUNK_SIZE` (sweep) | b12110 env (git grep); brak wpisu w KB | nieznany `[INFERENCE]` | wszystkie | env 1/2/4/8 vs domyślne | 12 | upstream | B |
| 41 || | | A9. MMQ vs cuBLAS dla prefill (`GGML_CUDA_FORCE_MMQ` / `FORCE_CUBLAS`) | b12110 `ggml/CMakeLists.txt:202-203`; `15d:114`; `56-orca-3090.md:90` | pp: vLLM 1595 vs llama.cpp 1289 t/s przy 16k na 3090. Wybór MMQ/cuBLAS zależy od arch. i kwantu | A, Ad, B | **wymaga 2 buildów upstream** z `-DGGML_CUDA_FORCE_MMQ=ON` / `-DGGML_CUDA_FORCE_CUBLAS=ON`; `llama-bench -p 512,4096` vs U | 15 + build | upstream build | B/KLD (inna ścieżka GEMM) |
| 42 || | | A10. `-fa off` (tylko KV f16) | Enigma `engine.ts:412,489` (zawsze `-fa on`) | spodziewany brak zysku `[INFERENCE]`; kontrola na sm_120 i 3060 | B, A | U0 `-fa off -ctk f16 -ctv f16` vs `-fa on` f16 | 6 | upstream | B |
| 16 || ★15 | ⚑ | **A11. `-t` z kwoty cgroup / rdzeni fizycznych** | `lekcje/lekcja-limit-cpu-kontenera.md:12-19`; Enigma `engine.ts:414,495` (`-t` tylko dla CPU) | 5060 Ti host: 32 wątki przy kwocie 7.68 CPU. Sampler i host MTP na CPU; host gap 1.9–2.1 ms/krok (66e:85-91) | wszystkie (hosty z kwotą i desktopy z SMT) | U MTP `-t <kwota>` i `-t <rdzenie fiz.>` vs bez `-t` | 9 | upstream | B |
| 17 || ★15 | | **A12. `--no-mmap` zimny start** | `56-orca-3090.md:112-116` | pierwszy prompt po restarcie 0.39–1.07 t/s vs 856–1000 na ciepło (cache stron) | wszystkie | `--no-mmap` vs domyślne: czas ładowania + TTFT pierwszego żądania (po `drop_caches` tam, gdzie wolno) | 8 | upstream | B |
| 12 || ★11 | | **A13. `-np 2`, dwa równoległe żądania** | `56-orca-3090.md:100-107,161,202`; Enigma `engine.ts:490` | fork 3090: suma +27…29% (82.1 vs 64.4). `-np 4` z MTP się nie uruchamia | 24/32 GB | U MTP n2 `-np 2` + 2 współbieżne żądania vs `-np 1` (nv67 nie ma harnessu równoległego → osobny skrypt) | 10 | upstream | B |
| 32 || | | A14. MTP `p_min` × n dla MoE z `--n-cpu-moe` | `66-SYNTEZA.md:61`; `66a:374,389` | 0…+15% przy offloadzie (Strata −4…+9%). Blok `moe` ma dziś `grid` tylko z p=0 | 8–16 GB | Qwen3.6-35B-A3B, `--spec-draft-p-min {0, 0.5, 0.8}` × n {1, 2, 4}; baseline n2 p0 | 20 | upstream | B (rozkład) |
| 33 || | | A15. `--n-cpu-moe` per klasa (+ `--moe-cache-mib`, jeśli jest w b12110) | `67b:31,182`; `66e:145-147` | MoE 262k na każdej klasie; LRU w upstream (#29887) daje 4090 Flash-Next 25.0 → 40.7 | 8–16 GB | blok `moe` `ncmoe_try` (w toku); dodatkowo `--moe-cache-mib N` vs sam ncm | 15 | upstream | B |
| 34 || | | A16. Upstream n-gram (`--spec-default`) na NVIDIA | Enigma `optimize.ts:86-98,117` | kandydat Enigmy nigdy niezmierzony na CUDA; zysk na kodzie/kopiowaniu | wszystkie | U0 `--spec-default` vs U0 i vs U MTP, na prompcie kopiującym | 9 | upstream | B |
| – || | | A17. `-fit on` z MTP: tylko strażnik regresji | `lekcje/lekcja-fit-mtp-16gb.md:10-13` | ZDECYDOWANE: 7.7 vs 31.8 t/s na 16 GB; Enigma daje `-ngl 999` | – | nie testować; pilnować, by nie wróciło | 0 | – | – |
| – || | | A18. `-ctkd/-ctvd q4_0` na stock upstream | `67b:36` | ZDECYDOWANE: stock dokłada kopię f16 (+0.9–1.5 GiB); używać tylko z L (D3) | – | – | 0 | – | – |
| | | | **B. Łatki forka vs upstream per klasa** | | | | | | | |
| 1 || ★0 | | **B1. kvq-mma (FA czyta q4_0/q8_0 bez konwersji do f16, cała grupa GQA w jednym przebiegu)** | `15d:9,107,187-219`; `16c-kvq-cuda.md:9-15,19,27`; `eksperymenty/2026-10-16-kvq-cuda.md:10-26`; `decyzje/2026-10-16-kvq-cuda-zostaje.md:10,18`; `56-orca-3090.md:141-161,220` | 3090 tg @64k: Qwen +36.8%, LFM +30.4%, MTP @59k +27.6%. 5060 Ti: +24.6 / +30.0%. Orca 3090 262k: +20.7%. 4060 Ti @29.5k: 39.3 → 50.2 (+28%). Oszczędza 0.27–0.84 GB VRAM | A, Ad, B (T nie: brak cp.async) | **build** `~/wt/nv-4060ti-kvq` `007a6f813` (topka2 + kvq) dla 86;89;120. F + `GGML_CUDA_KVQ=1` vs F (`=0`), `ctx 65536`, `what [sweep, fill]` + `llama-bench -fa 1 -d 0,8192,32768,65536 -n 64 -r 3` ABBA | 40–60 + build 15 | fork | B/KLD: zdany; wyjątek n=1 D256 q4_0 domyślnie na vec |
| 3 || ★2 | ⚑ | **B2. topka2 (F) vs upstream U na każdej klasie** | `REKORDY.md:110,115,118,132-135`; `27-3090-final.md:12,24`; `29-4060ti.md:18,88-100`; Enigma `data/engines.json:80-107` (NVIDIA = upstream b11856, brak silnika CUDA Enigmy) | 3090 czat T=1: 93.3 vs U1 75.3 (+24%), mvs 348.9 (×3.19). 4060 Ti 35.4 vs 30.6, 3060 38.2 vs 24.0. Niezmierzone: 5060 Ti (harness nv-final), 5080, 5090, 4090, 4070 | wszystkie poza T | F (jak `3090f` F131k) vs U z najlepszym n, ta sama karta/model/ctx; ctx F ≤ 131072 na 24 GB (`27:211-212`) | 2 × 3 ≈ 8 | fork | B (md5 = fork; vs upstream KLD na szumie) |
| 5 || ★4 | | **B3. `LLAMA_GPU_VERIFY` 0/1** | `27-3090-final.md:43-46`; `29-4060ti.md:18,88` | mvs +6…+9% (3090), ~+4% (4060 Ti): logity nie idą przez PCIe. sm_120 nigdy; pomiary pojedyncze, bez ABBA | Ad, B (+ A ABBA) | F z `LLAMA_GPU_VERIFY=0` vs F (`=1`), ABBA | 12 | fork | B (md5 22/22) |
| 6 || ★5 | | **B4. `GGML_CUDA_MMVQ_N1_ROWS` per arch.** | `kernele/mmvq-n1-wiersze.md:21-32`; `nvidia/sm-86-89-120.md:22`; `karty/rtx-3090.md:16` | sm_86: +7–8.5% tg128 (Qwen 40.1→43.0, LFM 256.8→284.5); z MTP 0 / −7%. sm_120: −1.7…−2.7%. **sm_89 do ustalenia**, 3060 nie testowane | Ad (4060 Ti/4070/4090), A 3060, B potwierdzić | F + env `=1` / `=2` / `=4` vs F domyślne (2 na sm_80–87, 1 poza nimi); U0-podobny F bez spec (`LLAMA_SPEC_LOOKUP=0`, bez MTP) + F MTP | 12 | fork | B (bitowo) |
| 11 || ★10 | | **B5. Ogon lookup W8 / W16 / off** | `eksperymenty/2026-10-18-lookup-ogon.md:12-21`; `24e-nvidia-runda.md:9,22,33`; `56-orca-3090.md` (W32 −1.1%) | mvs ×2.55, kopia 64k ×3.0 (3090). W8 vs W16 na NVIDIA nigdy; weryfikacja W16 droższa na wąskiej szynie (4060 Ti 288 GB/s) `[INFERENCE]` | wszystkie | F z `LLAMA_SPEC_LOOKUP_W=8` / `16` / `LLAMA_SPEC_LOOKUP=0`, **prompt kopiujący/kod** (sweep czatu tego nie pokaże) | 12 | fork | B (md5 T=0 11/11; W16 poza `BITEXACT`) |
| 20 || | | B6. MTP n dla F: 2/3/4/5 | `karty/rtx-5060-ti.md:15`; `eksperymenty/2026-10-19-build-topka.md:12,23` | 5060 Ti: n=3 ≥ n=4; F ma sztywne 4 z XTX | wszystkie, najpierw B i 12 GB | F z `--spec-draft-n-max 2/3/5` vs 4 | 12 | fork | B |
| 25 || | | B7. Rozmiar słownika draftu 32k / 64k / 96k | `eksperymenty/2026-10-19-tokeny-spoza-slownika-draftu.md:14` | 16k −5%, 32k +7%, 64k +7.5%, 96k +6% (karta nieopisana); optimum może zależeć od szyny `[INFERENCE]` | wszystkie | F z `--spec-draft-vocab-n 32768 / 98304` vs 65536 | 9 | fork | B |
| 24 || | | B8. `GGML_HIP_GATE_UP_Q8` i `GGML_HIP_Q8_IDS` na sm_89 | `kernele/fuzje-lfm-moe.md:24-25`; `nvidia/latki-na-nvidia.md:21` | GATE_UP off: +6.5% LFM / +2.2% Qwen (3090), +5.34 / +2.38% (5060 Ti). Q8_IDS off: +4.99% LFM (5060 Ti), a na 3090 +4.6% solo i −1.6% razem z ROWS=2 | Ad (+ 3060) | F LFM z `=0` vs `=1` | 12 | fork | B |
| 40 || | | B9. Leave-one-out pozostałych przełączników forka na NVIDIA | `fork-switches.tsv`; `PLAN-TESTOW.md:16`; `CUDA-AUDIT.md:110-157`; `kernele/{argmax-dpp,rmsnorm-dpp,para-mmvq,attn-prep-fwht,gdn-fuzje-k2,fuzje-weryfikacji}.md` | na XTX każda +0.3…4.8%; „na NVIDIA nigdy nieuruchomione”. 0025 `__launch_bounds__(1024,1)` może spillować; 0057 ryzyko aliasingu | Ad, B (najpierw), A | F z `=0` po kolei: `GGML_HIP_MMVQ_PAIR`, `NORM_FAST`, `ARGMAX_FAST`, `NORM_GATE`, `GDN_CONV_AB`, `CONV_MUL`, `MOE_DOWN_REDUCE`, `NORM_ROUTER`, `ATTN_PREP`, `INPUT_BATCH`, `LLAMA_ASYNC_INPUTS`, `LLAMA_MTP_CHAIN_SCHED`, `LLAMA_KV_MASK_FAST`, `LLAMA_SPEC_LAZY_SAVE`, `LLAMA_SAMPLER_FAST_*`; md5 | ~8 × 18 ≈ 140 | fork | B |
| 35 || | | B10. `LLAMA_SERVER_CACHE_SHARE_MIN=1024` osobno | `eksperymenty/2026-10-19-build-topka.md:10-12` | zysk tylko w pakiecie; TTFT agenta | wszystkie | F bez env vs F; wielotur. sesja agenta | 10 | fork | B |
| 21 || | | B11. Regresja prefill topka na sm_89 (−3.5…−3.9%) i 3060 (tg −2.4%, pp −3%): bisect | `karty/rtx-4060-ti.md:15`; `29-4060ti.md:16,108`; `27-3090-final.md:36,186,218`; `15d:244-248` | TTFT 512 +30% vs U1; kandydaci: 0013 (prolog GDN), 0045, 0043 | Ad, A 3060 | `llama-bench -p 512,4096` U vs F + leave-one-out przełączników (B9) + `nsys` per kernel | 30 | fork | B |
| 29 || | | B12. Wariant kvq: wyjątek n=1 D256 q4_0 i akumulacja P·V w f32 | `16c-kvq-cuda.md:207,216-219`; `kernele/fattn-kvq.md:30` | z wyjątkiem tg @64k 27.40 vs 39.14 (−30%); f32 P·V może oddać ~+35% bez ogona KLD | A, Ad, B | `GGML_CUDA_KVQ_N1_D256_Q4=1` (nowa numeryka) vs domyślne + KLD `--chunks ≥ 10` | 60 + KLD | fork (nowy wariant) | B/KLD |
| 28 || | | B13. kvq `GGML_CUDA_KVQ_BPSM` 1/2/3/4/6 na sm_89/120 i kvq q4_0 na sm_120 | `16c:26,69,150-161`; `66b:107,217` | na 3090 domyślne ≤3% od optimum; D256 strojone pod D64 (LFM). 1Cat 1→2 CTA/SM: −18…22% opu | Ad, B | po B1: `GGML_CUDA_KVQ_BPSM=N` perf FA @32k/98k/196k | 20 | fork | B/KLD |
| 23 || | | B14. Lean reserve w linii topka2 (port q63 0002) | `65-vram-rezerwa-mtp-kontekst.md:7-13,55`; `eksperymenty/2026-11-06-ctx-262k-fit.md:10-21`; `karty/rtx-3090.md:24` | XTX: −1041 MiB, ctx 204800 → 262144 przy 0% t/s. F na 3090 OOM od ~55.6k przy 204800 | A 24 GB, 16 GB | build topka2 + `topka-q63/0002`; F `-c 262144` vs F `-c 131072`, fill | 30 + build | fork | B (md5 równe na XTX) |
| 44 || | | B15. Poprawki rollback MTP (#30141 #31350 #31368 #30574) | `patches/topka-q63/0003` (10-21) | akceptacja MTP po przywróceniu slotu 37 → 49% | wszystkie | F z 0003 vs bez; sesja z `/slots` restore | 15 + build | fork | B |
| 45 || | | B16. `-np 4` z MTP nie startuje | `56-orca-3090.md:202` | wielu użytkowników | 24/32 GB | naprawa + `-np 4` | 15 | fork (fix) | B |
| 46 || | | B17. Build `-DMMVQ_DISABLE_MULTI` (md5 = upstream): koszt | `nvidia/latki-na-nvidia.md:12,20`; `lekcje/lekcja-md5-wzgledem-upstreamu.md:12-15` | bez 0001/0002 Qwen pp5 −8%; daje parytet md5 z upstream | A, Ad, B | build F z flagą vs F | 10 + build | fork | B (bitowo = upstream) |
| 47 || | | B18. GDN chunked MMA zintegrowany z grafem topki | `56-orca-3090.md:168-195` | prefill +10.5…11.3% (pp2048 1515 → 1708); dziś NaN / PPL 130k | A (+ Ad, B) | `GGML_CUDA_GDN_MMA=1` vs 0 + PPL | 45 | fork `orca-gdn2` | B (PPL identyczne wymagane) |
| 48 || | | B19. Zwinięcie haka promptu MTP do grafu celu (L4) | `15d:110` | TTFT −5…7% przy 2k | wszystkie | build + TTFT 512/2k | 30 | fork (nowe) | B (bitowo) |
| 49 || | | B20. Przełączniki Nemotrona (`TOPK_MOE_NP2`, `MMVQ_N1_IQ2`) na sm_89 | `kernele/nemotron-kernele-cuda.md:14-18`; `eksperymenty/2026-10-16-nemotron-3090.md:22-26` | razem +6.1% (3090); `IQ2_LUT` −2.4% | Ad | tylko jeśli Nemotron w katalogu | 10 | fork `nemotron-3090` | B/KLD (NP2 zdany) |
| 50 || | | B21. Sesje na dysku (L3) i cache przeżywający restart | `15d:14,109`; `repo/lucebox.md:18`; `66-SYNTEZA.md:62` | 45k sesja: 48–56 s → 1–4 s po restarcie | wszystkie | `--slot-save-path` + auto-restore vs `--cache-ram` | 30 | fork lub upstream #28092 | B |
| 51 || | | B22. Siatka checkpointów GDN co 8192 + junction | `66-SYNTEZA.md:57`; `66b:202` | edycja końca 60k promptu: TTFT ~65 → 8–10 s | wszystkie | replay 60k → zmieniony koniec | 20 | łatka do pinu | B |
| | | | **C. Nowe pomysły kernelowe z 60b/63/66, przenośne na CUDA** | | | | | | | |
| 22 || | | C1. Profil kroku przy długim kontekście na NVIDIA (bramka dla C2–C6) | `66-SYNTEZA.md:52`; `66b:218`; `63-SYNTEZA.md:82`; `63d:448-450` | 0% sam w sobie; decyduje, czy FA/maska/host warte pracy (na XTX odczyt KV ~5 ms z +18 ms/krok) | A 3090 / Ad 4090 | `nsys` + `LLAMA_HOSTGAP_TRACE` (topka-q63) przy 1.7k / 94k / 199k | 25 | fork (trace) | – |
| 27 || | | C2. KV raz na weryfikację (Pack-GQA; wariant Saber 2 grupy wierszy) | `66-SYNTEZA.md:53`; `66b:109,129,216`; `kernele/kv-raz-na-weryfikacje.md:12-20`; `repo/1cat-vllm.md:12`; `63a:475` | 199k: 74.5 → 77–83 (+3…11%); MTP-4 = 30 kolumn = 2 kafle, więc KV czytane 2×. 1Cat (V100): op −20…21%, runda −8.6% @128k | A, Ad, B | nowy wariant kvq vs kvq; `test-backend-ops perf -o FLASH_ATTN_EXT` hs256 nb5 q4_0 98k/196k, potem long_ctx ABBA; kill < +3% @94k | 40 | fork (nowe, na B1) | B (Saber bitowo) / B/KLD |
| 36 || | | C3. GQA packing w VEC FA dla małego n (port #29846) | `nvidia/fa-kv-kwantyzowane-cuda.md:11-16` | #29846 3090 pp1024 @d32768: ub2 ×1.21, ub4 ×1.18, ub8 ×1.10 (upstream odrzucił) | A, Ad, B | port vs upstream vec; `-ub 2/4/8` @d32768 | 60 | fork | B (kolejność sumy) |
| 37 || | | C4. Dekoder FA z `__launch_bounds__(…,2)` (dual-CTA) | `66b:97-98` | 1Cat V100: 128k 40.82 → 48.54 t/s, rejestry 188 → 168, bitowo identyczne; dekoder był latency-bound (23% DRAM) | A, Ad, B | wariant kernela vs obecny, perf FA + long_ctx | 30 | fork / upstream | B (bitowo) |
| 38 || | | C5. L2 `evict_first` dla strumienia wag w MMVQ/MMQ | `60b-apple-engines-bonsai.md:31,174,264,289,312,326-329` | +0.5–2% `[INFERENCE]`; GB10 ×1.0331. Wagi (~11 MB/launch) przestają wypychać KV, aktywacje i stan z L2. 3090 ma tylko 6 MB L2, więc większy sens na Ad/B (32–96 MB) | A, Ad, B (sm_80+) | nowy przełącznik `GGML_CUDA_WEIGHT_EVICT_FIRST=1` (`createpolicy.fractional.L2::evict_first` + `ld.global.L2::cache_hint`) vs 0; md5 równe, ABBA ≥ +0.5% | 30 + 0.5 dnia | fork (nowe) | B |
| 39 || | | C6. L2 persisting window dla danych czytanych co token | `nvidia/l2-persist.md:10-12` | `[SZACUNEK]` 5060 Ti +1.1%, 4090 +2%, 5090 +1.7%, 3090 0; Qwen ~0.36% (blok MTP ~1% na 5090) | Ad, B | `GGML_CUDA_L2_PERSIST=<MB>` vs 0; kill < +0.7% LFM d0 albo regresja d32k > 0.5% | 45 | fork (nowe) | B |
| 52 || | | C7. Wyzwalacz PDL + prefetch L2 przed `pdl_sync` w gęstym MMVQ | `kernele/pdl-mmvq-trigger.md:10-16` | `[SZACUNEK]` 5060 Ti +1.1–4.6% LFM, +0.7–2.6% Qwen | B | po A7: `GGML_CUDA_MMVQ_PREWAIT=0/1/2`; kill < +1.5% LFM tg128 | 20 | fork (nowe) | B |
| 53 || | | C8. Prefetch L2 w MMVQ dla ncols ≥ 2 | `kernele/mmvq-prefetch-l2.md:10-12`; `24e:12` (`MMVQ_L2PF=1` −0.4…−0.8%, inna ścieżka) | upstream włącza tylko na DGX Spark: Q4_K +2.89%, Q6_K +6.19% przy 5 kolumnach | A, Ad, B | przełącznik dla `ncols_dst ≥ 2`; `test-backend-ops -o MUL_MAT` ne11 = 1…8, potem spec_sweep | 10 | fork (nowe) | B |
| 54 || | | C9. Sito głowy draftu (połowa K → top-128 → dokładnie) / coarse + rerank | `60b:29,288,318-325`; `66-SYNTEZA.md:56` | +0.5–1.5% (głowa IQ4_XS 64k × 5120 ≈ 178 MB/token draftu); rerank +1…3% spec_sweep | wszystkie | najpierw profil matvec głowy (≥ 0.5 ms/krok), potem wariant; bramka tok/krok −0.5% | 20 + 1–2 dni | fork | B (cel bez zmian) |
| 55 || | | C10. Taśma delta GDN (replay bez k·S) | `60b:30,290,330-333`; `kernele/gdn-replay.md:27` | +0.3–0.8% (GDN ≈ 0.7 ms/krok); GB10 ×1.02 | A, Ad, B | rozszerzenie `GATED_DELTA_NET_LAG`; md5, GDN ≥ −20% | 20 + 2–3 dni | fork | B (bitowo) |
| 56 || | | C11. Maska KQ poza ścieżką krytyczną | `66-SYNTEZA.md:60`; `66e:171,187` | 199k +0.5…1.5%; upstream nie ma `LLAMA_KV_MASK_FAST`, więc zysk tam większy `[INFERENCE]` | A, Ad, B | maska w trakcie draftu / na GPU vs obecna; kill gdy graph→inputs < 0.2 ms | 30 | fork / upstream | B |
| 57 || | | C12. Nakładanie kroków / rezydentna pętla MTP z obcięciem na stop-tokenie na GPU | `66-SYNTEZA.md:63`; `66e:173,188`; `66b:191,219`; `repo/tokenspeed.md:13` | Qwen +1…1.5%, LFM +4…6%; więcej na słabym CPU | wszystkie | overlap vs serial; md5 + test stop-tokenu w oknie | 30 + 5–10 dni | fork | B |
| 58 || | | C13. Profil „kod/T=0”: MTP n = 6–7 + słownik 32k; usunięcie przycięcia `n_max` (lucebox Q1) | `63-SYNTEZA.md:94`; `63a:476`; `repo/lucebox.md:12` | exl3 3090: MTP-7 157 vs MTP-4 129 (+22%); lucebox `[SZ]` 175–300 t/s na kodzie | A, Ad, B | F n7 vocab 32k vs n4 64k; mvs T=0 + spec_sweep T=1 (kill < −1%) | 20 | fork | B (zmienia md5 przez szerokość weryfikacji → bramka) |
| 59 || | | C14. Koszt szerokości weryfikacji > 8 kolumn (MMQ) + swap-AB GEMV na `mma.m16n8k16` | `metody/koszt-szerokosci-weryfikacji.md:22`; `lekcje/lekcja-sufit-bloku.md:10`; `kernele/mmvq-multikolumnowe.md:20` | Magnitude wygrywa kod 157 vs 105.7 tylko przez 8 vs 5 tokenów na przejście wag; swap-AB daje M = 1…16 bitowo jak M=1 | A, Ad, B | `llama-bench` ms/krok W5/W8/W16; nowa ścieżka MMVQ | 10 + dni | fork | B |
| 60 || | | C15. Więcej loadów w locie w GEMV batch-1 (prawo Little'a) | `lekcje/lekcja-littles-law-gemv.md:10-12` | potrzeba 10–16 loadów 16 B/warp; cp.async już ~92% pasma na 5060 Ti, więc zysk głównie A/Ad | A, Ad | prefetch rejestrowy w MMVQ vs obecny | 10 | fork | B |
| 61 || | | C16. Pipeline kafli MMQ (DeepGEMM) / głębokie MMQ IQ4_XS | `repo/deepgemm.md:12`; `15d:114`; `56-orca-3090.md:90,203` | pp `[SZ]` +3–12%; do vLLM brakuje ~+20%; occupancy 2 dało −11.5% | A, Ad, B | `llama-bench -p 512,4096` | 30 + 10 dni | fork | B (zachować kolejność) |
| 62 || | | C17. Shared expert w launchu ekspertów routowanych; ewikcja „MRU-other” | `66e:54,145-147`; `66a:74` | MoE 3090 207.8 → 220.1 (+5.9%), wynik identyczny; tqLLM hit 0.5 → 77% przy 128k | A, Ad, B (MoE) | fused vs osobno; `--moe-cache-mib` LRU vs MRU-other | 30 | fork / łatka upstream | B |
| 63 || | | C18. Reguła AGR2 (kandydat lookup zgodny z MTP), słownik draftu ∪ tokeny kontekstu, SuffixDecoding | `eksperymenty/2026-10-19-sufit-pointera-lookup.md:10-24`; `…tokeny-spoza-slownika-draftu.md:10-14`; `repo/suffixdecoding.md:12` | sym. CPU: agent +3.7%; słownik +0.8…1.7%; suffix `[SZ]` +5–15% na agentach | wszystkie (host) | AGR2 vs F W16; dynamiczny słownik vs 64k; bramka spec_sweep PL ABBA ≥ +1% | 30 | fork | B |
| 64 || | | C19. Odcięcie draftu po iloczynie akceptacji / próg τ per pozycja | `57f:34,75,85`; `60c:147-149,238,261` | 0…+5% przy T>0 (Maya +6.5%); tqLLM 3090 +1.5% / +3% po 32k | wszystkie | `LLAMA_DRAFT_CUMP` / τ 0.8–0.9 vs n4 | 15 | fork | B przy greedy |
| 65 || | | C20. Fuzje: klej GDN + granica warstwy weryfikacji (ADD + RMSNorm + q8 ≤ 16 wierszy) | `60b:168-169,308-311` | GB10: ×1.0103 / ×1.0143 decode | A, Ad, B | przełącznik per fuzja, md5 | 20 | fork | B |
| 66 || | | C21. Scalanie split-KV w ostatnim bloku; split-K MMVQ dla 1024 wierszy | `66-SYNTEZA.md:67-68`; `repo/flashinfer.md:12` | +0.2…0.5% i +0.1…0.3% | A, Ad, B | profil combine @94k; ABBA; md5/KLD | 20 | fork | B/KLD |
| 67 || | | C22. Audyt „sufitu wzorca” i kafelkowy układ wag | `60b:32,181-185,291,334-337` | 0–10% `[INFERENCE]` (GB10 ciągły strumień 230–236 vs 200–210 GB/s) | A (+ Ad, B) | mikrobench ffn 5120×17408; kill < 5% | 60 | fork | B (permutacja) |
| 68 || | | C23. Parser czatu raz na krok MTP (O(n)) | `66-SYNTEZA.md:59`; `66e:172` | CPU wątku HTTP −50…75%; decode 0…+1% | wszystkie | `stream:true` vs `false`, 12k tokenów | 10 | łatka upstream | B |
| 69 || | | C24. Megakernel / koszt granicy grafu CUDA (X5) | `nvidia/sm-86-89-120.md:24`; `66c:146`; `repo/megakernele-prior-art.md:12,19` | LFM 3090 na 54% pasma; literatura 0.29–0.46 ms/token; lucebox 1.55× na 0.8B, 2 zawieszenia w 12.5 h | A, Ad | pomiar X5; **wymaga zgody użytkownika** | 60 | fork R&D | B |
| 70 || | | C25. Drzewo weryfikacji MTP z GDN w postaci WY; TqCache (KV w RAM hosta) | `66-SYNTEZA.md:65`; `63a:372`; `66e:153,178` | kod +3…8%, ale mkyt 5090 netto ~0; TqCache 5060 Ti 224k 42 t/s zamiast odmowy | B, A; 12–16 GB | najpierw symulacja CPU | – | fork | B |
| 71 || | | C26. Bit-check każdej fuzji na wagach przy starcie, z fallbackiem | `60b:306` | odporność na nieznane GPU sm_75–120 | wszystkie | proces, nie A/B | – | fork / Enigma | – |
| | | | **D. Warianty silnika** | | | | | | | |
| 18 || | ⚑ | **D1. Pin Enigmy b11856 vs b12110** | Enigma `data/engines.json:80-107`; `63-SYNTEZA.md:58,95`; `ZRODLA.md:254` | prefill Qwen 27B +5…7%, MoE +6…17% (#29948). Kampania 67 (4090): decode 47.22 vs 47.37, pp 2699 vs 2627 @262k ub256 (**b12110 −2.7%**), 3031 vs 3038 @160k ub512 | wszystkie | P0/N0 i P4/N3 są w kampanii; dodać `llama-bench -p 512,4096` P vs N | 10 | upstream | B/KLD (fuzje MMQ) |
| 10 || ★9 | | **D3. Lean (`b12110lean`) vs b12110 przy max ctx** | `67b:20,24,36`; `65:7-13`; `patches/nv67-lean-reserve/0001` | −0.7 GiB → 16 GB: 200–217k → 225–245k z MTP; 12 GB: 135k → 151k | 12 GB (3060/4070), 16 GB (4060 Ti/5060 Ti/5080) | L `-ctkd q4_0 -ctvd q4_0 --spec-draft-n-ubatch 64` n2 przy 225–245k / 151k (ctx_probe + fill) vs U przy ctx stock (jak `4060til.json`) | 15 | port upstream (do PR) | B |
| 13 || ★12 | | **D4. Prism vs b12110 vs F na Bonsai** | `repo/prism-llama-cpp.md:10`; `67b:25,120`; `ZRODLA.md:331` | 3060: prism PTQ1_0 44.75–44.9 vs nasz Q2_0 35.1–35.5; upstream Q2_0 33.15 | A 3060, T 2080 Ti, Ad 4070 | PR na oficjalnym Q2_0 i PTQ1_0 vs U0 Q2_0 (już na `3060g`/`2080tig`) | 10 | prism fork | B (repack bezstratny: PPL 8.6154 vs 8.6171) |
| – || ★0 | | D5. topka2 + kvq (= B1) jako kandydat na silnik CUDA Enigmy | jw. | jw. | A, Ad, B | jw. | jw. | fork | B/KLD |
| 26 || | | D6. Turing sm_75: build forka i smoke test | `nvidia/cuda-stos.md:13-15`; `16c:189`; `CUDA-AUDIT.md:41` | brak jakichkolwiek danych sm_75; 2080 Ti jest w katalogu 67b (11 GB, Bonsai) | T | build topka2 z `-DCMAKE_CUDA_ARCHITECTURES=75`, `test-backend-ops`, F vs U0 (kvq: nie) | 45 + build | fork | B |
| 72 || | | D7. Konkurenci na 3090 (wiedza): tqLLM 1.2.3, Strata, vLLM GSQ Marlin, exl3, benchlab | `60c:243,262`; `57b:106-109,151-154`; `57a:154,160`; `repo/exllamav3.md:13-14`; `63-SYNTEZA.md:104` | 0 t/s dla nas; punkt odniesienia (exl3 3090 146, HyperQwen 180, llama.cpp 97 na benchlab) | A | ich bench vs F; wymagają 64–128 GB RAM i ~55 GB pobrań | 60–120 | zewnętrzne | – |
| | | | **E. Moc i termika (tylko wynajęte karty, zawsze zapisywane; nigdy karta użytkownika)** | | | | | | | |
| 15 || ★14 | | **E1. Sweep limitu mocy → perf/W** | analogia XTX: `eksperymenty/2026-11-06-eco-sweep-sclk.md:14-17` (2200 MHz: −1.9% pisania, −10.5% W, J/token −8.8%); `05-chmura-gpu-do-testow.md:196`; `06-produkt-ux-prawo-biznes.md:167` | decode jest ograniczony pamięcią, więc spodziewam się zbliżonego spadku W przy małej stracie t/s `[INFERENCE]`. Dane dla „Cichego trybu” i rekomendacji per karta | A (3060 170 W, 3090 350 W), Ad (4060 Ti 165 W, 4090 450 W), B (5060 Ti 180 W, 5090 575 W) | na ramieniu wygrywającym: `nvidia-smi -pl` 100 / 85 / 70 / 55% TDP; zapis `power.draw`, zegary SM/mem, temp., `clocks_throttle_reasons`, t/s decode i pp, J/token; przywrócić limit. W kontenerze bez uprawnień pominąć (oferty `vms_enabled`) | 4 × 3 ≈ 15 | upstream (dowolny silnik) | B |
| 19 || | | E2. Odcisk mocy hosta przy każdym wyniku | `lekcje/lekcja-limit-mocy-hosta.md:10-12`; `lekcje/lekcja-vast-transfer-kosztuje.md:17`; `09-chmura-3090.md:16` | 3060 120 W vs 170 W: Saluki 17.2 vs 23.0 t/s; 3090 300 W „SW Power Cap”. Bez tego wyniki między hostami są nieporównywalne | wszystkie | `nvidia-smi -q -d POWER,CLOCK,PERFORMANCE` przed i po każdym ramieniu (do `hw/`) | 1 | – | – |
| 30 || | | E3. Soak termiczny przy fill 262k | `06-produkt-ux-prawo-biznes.md:167`; blok `stab` w nv67 | throttling po kilku minutach na kartach z gorszym chłodzeniem (5060 Ti, 4060 Ti) `[INFERENCE]` | wszystkie | `stab` z `soak_s ≥ 600` + log temp./zegarów co 1 s | 12 | – | B |
| | | | **LOSSY-parked** (nie testować na produkt; decyzja 2026-11-05) | | | | | | | |
| P1 | | | NVFP4 (trunk W4A4, QAD-NVFP4, FP4 MMA, disaggregated prefill) | `nvidia/nvfp4.md:19-21,32`; `57d:29,63`; `57a:158`; `63a:377,488-491` | pp +65–81% na sm_120, decode 0; KLD 0.0865 vs 0.0265; BFCL 79 → 65.5% | B | – | – | – | LOSSY-parked |
| P2 | | | QSA, KV 3-bit, ring f16 + sinks, `q4_b16`, FLy, KV FP8 | `repo/qwen-qsa-llama-cpp.md:10,15`; `63-SYNTEZA.md:115-118`; `57d:62,163,170-207`; `66-SYNTEZA.md:84-88` | QSA 4090 255k 114.7 vs 40.6 t/s; q4_b16 KL attn −22…25% (sym.) | Ad, B | – | – | – | LOSSY-parked |
| P3 | | | PFlash v2 (kompresja promptu), int8 IMMA prefill, chunked GDN (błąd 3e-8), `LLAMA_ATTN_ROT_DISABLE=1` przy q8_0, alokacja per tensor qa1–qa3, GSQ 3-bit w vLLM | `15d:10-12,122,232-235`; `repo/tqllm.md:16,27`; `60b:187-195`; `repo/lucebox.md:12`; `57g:19-25,58-60,76-79` | TTFT ×2.5–3.5; pp 2258 vs 1378; +1…3% pp; ~1.5%; +4–8.5% (z bajtów) | A, Ad, B | – | – | – | LOSSY-parked |

Pozycji z rangą: 72 (w tym C26 to proces, a D7 pomiar wiedzy); 2 zdecydowane (A17, A18), D5 = B1, 3 wiersze LOSSY-parked. Wiersze są pogrupowane A–E, a ranga to globalna kolejność wykonania (1–17 = TOP-15).

## 3. Korekty domyślnych Enigmy (⚑), które wynikną z testów

1. **Silnik CUDA** (`data/engines.json:80-107`): NVIDIA dostaje upstream b11856, a kandydat „enigma” jest odrzucany jako `no_enigma_engine` (`engine.ts:76-78`). Do ustalenia (B2, B1, D1):
   - pin → b12110;
   - topka2 albo topka2 + kvq jako silnik Enigmy na sm_86/89/120.
2. **Typ KV** (`catalog/index.ts:167-169`): kolejność f16 > q8_0 > q4_0 jest kalibrowana na XTX. Na CUDA bez kvq q8_0 jest wolniejsze od q4_0, a na sm_120 q4_0 bez kvq to pułapka. A1 rozstrzyga regułę per arch.
3. **MTP n** (`memory.ts:45`, `optimize.ts:84,106`): jedno n=3 dla wszystkich kart. A2 + B6 → n per klasa (i per silnik: F używa 4).
4. **ub** (`optimize.ts:22`): brak 256, a przepisy 67b na 12/16 GB używają 256. A3.
5. **Wątki** (`engine.ts:414`): na GPU brak `-t`, a llama.cpp bierze `nproc`, nie kwotę cgroup. A11.
6. **Margines pamięci** (`memory.ts:19-21,67`; `catalog/index.ts:22,26-30`):
   - `overheadMiB` zaniża 4090 o 135 MiB i 5080 o 107 MiB;
   - `VRAM_RESERVE` 1.8% zawyża o ~250 MiB na 8–16 GB.
   
   Do sprawdzenia testem fill w kampanii 67 (już w blokach `fill`), nie osobnym ramieniem.
7. **Reguła `decide()`** (`optimize.ts:12-15,267-268`): dopuszcza −15% prefill przy decode ≥ +20%, na podstawie jednego pomiaru 3090. A3, A2 i D1 dadzą dane z innych klas.

## 4. Luki w pokryciu

- **sm_75 (Turing):** zero pomiarów forka. Buildy celowały tylko w 86;89;120, a kvq wymaga cc ≥ 8.0. Zostaje D6.
- **sm_89 (Ada):** niezmierzone kvq e2e, `MMVQ_N1_ROWS`, `GATE_UP_Q8` / `Q8_IDS`, GPU verify ABBA i bisect regresji prefill.
- **sm_120:** F z harnessem nv-final (był tylko stary bench.sh), PDL, grafy off, kvq q4_0.
- **Wieloużytkownikowo:** `-np 2/4` na upstream nigdy.

## Powiązane
- Wiki: `wiki/nvidia/backlog-testow-nvidia.md`
- Poprzednie raporty: [67b](67b-wybor-modeli-nvidia.md), [16c](16c-kvq-cuda.md), [27](27-3090-final.md), [29](29-4060ti.md), [56-orca](56-orca-3090.md), [63-SYNTEZA](63-SYNTEZA.md), [66-SYNTEZA](66-SYNTEZA.md), [60b](60b-apple-engines-bonsai.md)
