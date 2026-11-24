---
typ: research
tags: [research, kolejka, colab, nvidia, cuda]
aktualizacja: 2026-11-24
zrodlo: podagent KqColab 2026-11-24, logi /tmp/kq/colab (Colab T4 i L4, 3,04 jednostki, maszyny wyłączone)
status: aktualne
---
# Kolejka testów NVIDIA na Google Colab (T4 / L4), 2026-11-24

**Siedem pozycji NVIDIA na Colabie za 3,04 jednostki: fork CUDA nie działa na Turingu (brak sm_75), regresja prefillu to stara baza forka, nie łatki, przerwy hosta to 12–14% kroku dekodu.**

Zlecenie: JARO 2026-11-24, kolejka `~/KERNEL/wiki/KOLEJKA-TESTOW.md` § Czeka, pozycje NVIDIA możliwe na Colab T4/L4 bez nowego kodu silnika.

## Wspólne warunki

- Model: `ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF` `Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf` (10 442 827 840 B), pobrany w VM z HF (bez tokena).
- Fork: wydanie `enigma-engines-cuda-2026-11-07`, `llama-kvqleana-bin-ubuntu-cuda-12.8-x64.tar.gz` (`version: 0.6.0-dev (build 11620, commit 007a6f813)`). W paczce jest **tylko `llama-server`** (bez `llama-bench`, `llama-perplexity`, `test-backend-ops`). Kod GPU: SASS + PTX tylko dla sm_86, sm_89, sm_120a (`cuobjdump --list-elf/--list-ptx`).
- Upstream: `llama-b12110-bin-ubuntu-cuda-12.8-x64.tar.gz` (commit `cd959bae9`; SASS sm_86/89/120a + PTX compute_50/61/70/75/80/90) i do K-023 dodatkowo `llama-b11620-bin-ubuntu-cuda-12.8-x64.tar.gz` (ta sama baza co fork). cudart z `cudart-llama-b12110-bin-ubuntu-cuda-12.8-x64.tar.gz`. Sumy: `colab/*/res/sha256*.txt`.
- KV wszędzie `-ctk q4_0 -ctv q4_0` (draft MTP `-ctkd q4_0 -ctvd q4_0`), `-fa on`. Zegary i limity mocy fabryczne, niczego nie zmieniano.
- Przepis forka z MTP (jak K-114/K-118): env `GGML_CUDA_KVQ=1 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SERVER_CACHE_SHARE_MIN=1024`, `--jinja --spec-type draft-mtp --spec-draft-n-max 2 -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs -ub 256`.
- Skrypty: `/tmp/kq/l4setup.sh` (setup obu VM), `/tmp/kq/t4run.sh` (K-069), `/tmp/kq/l4run.py` (pozostałe). Logi: `/tmp/kq/colab/t4/res/`, `/tmp/kq/colab/l4/res/` (każdy serwer: `logs/<ramię>.cmd` = dokładna komenda z env, `logs/<ramię>.log`; wyniki `k0xx.jsonl`; `smi*.csv` co 1 s).

Odczyt kart przed testami (`nvidia-smi --query-gpu=power.limit,power.default_limit,clocks.max.sm,clocks.max.mem,temperature.gpu`):

| karta | power.limit | power.default_limit | clocks.max.sm | clocks.max.mem | temp | VRAM | vCPU / RAM |
|---|---|---|---|---|---|---|---|
| Tesla T4 (sm_75) | 70 W | 70 W | 1590 MHz | 5001 MHz | 42 °C | 15 360 MiB | 2 / 12 GB |
| NVIDIA L4 (sm_89) | 72 W | 72 W | 2040 MHz | 6251 MHz | 37 °C | 23 034 MiB | 12 / 52 GB (AVX-512) |

Sterownik 580.82.07 na obu.

## K-069 · Turing sm_75: build forka i smoke test — **zrobione częściowo (smoke opublikowanych binarek); build forka pominięty**

Karta: Colab **Tesla T4** (sm_75), sesja `kqt4`. Build forka dla sm_75 niemożliwy bez nowej pracy: źródła forka (`~/wt/nv-4060ti-kvq`, ścieżka zapisana w binarce) są tylko na jaroserverai, którego nie wolno dotykać; w `~/KERNEL` są wyłącznie łatki AMD (`llama.cpp-amd-opt`), nie gałąź `cuda-topka2`+kvq. Zamiast tego sprawdziłem, co dostanie użytkownik Enigmy z kartą Turing.

1. Fork z wydania (`kvqleana`, kod GPU tylko sm_86/89/120a):
   `LD_LIBRARY_PATH=$FB:/usr/lib64-nvidia GGML_CUDA_KVQ=1 llama-server -m m.gguf -c 4096 -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -ub 256 -np 1`
   → model ładuje się do VRAM (47 s), potem **abort (rc 134)**: `CUDA error: no kernel image is available for execution on the device` w `ggml_cuda_h2d_batch_flush` (`ggml-cuda.cu:2609`).
2. Upstream b12110 z wydania (PTX compute_75, JIT przy pierwszym uruchomieniu):
   `llama-completion -m m.gguf -c 4096 -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -p "The capital of France is" -n 48 --temp 0 -no-cnv` → „The capital of France is Paris.” (poprawnie); pierwszy prompt 20,9 s przez JIT PTX, load 91,9 s.
   `llama-bench -m m.gguf -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -p 512 -n 128 -r 3` → **pp512 302,3 ± 0,5 t/s, tg128 9,14 ± 0,21 t/s** (T4 pod obciążeniem 70–71 W z 70 W, SM 1125–1245 MHz, 57–61 °C).
- Werdykt: **opublikowany silnik CUDA Enigmy nie działa na Turingu (2080 Ti/T4) — twardy crash, nie fallback.** Upstream działa przez PTX. Dla klasy 11 GB w Enigmie trzeba albo dodać `75` (lub `75-virtual`) do `CMAKE_CUDA_ARCHITECTURES` przy buildzie wydania, albo planer musi dla sm < 86 wybierać upstream. Build i `test-backend-ops` forka na sm_75 zostają do zrobienia tam, gdzie są źródła.
- Logi: `colab/t4/res/k069.log`, `logs/k069-fork-server.log`, `logs/k069-up-completion.log`, `k069-up-bench.jsonl`, `smi-k069.csv`, `fork-archs.txt`/`up-archs.txt` (cuobjdump).

## K-023 · Regresja prefillu forka vs upstream na sm_89 + LOO przełączników — **zrobione (bez bisekcji commitów)**

Karta: Colab **L4** (sm_89, 72 W), sesja `kql4`. Bisekcja commitów wymaga budowania forka ze źródeł (jaroserverai) → pominięta; zrobione porównanie z upstreamem na tej samej bazie (b11620) i z b12110 oraz leave-one-out wszystkich przełączników runtime forka (po jednym `=0` na start serwera).

Komenda ramienia (serwer, bez spekulacji): `[env] llama-server -m m.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 8192 -ub 512 -b 2048 -np 1`; fork z `GGML_CUDA_KVQ=1` + jeden przełącznik `=0`. Prompt: tokeny wikitext-2 train (różne przesunięcia, `cache_prompt:false`), rozgrzewka + 3 powtórzenia, mediana `timings.prompt_per_second`. Kolejność: F-a, U12110-a, U11620-a, F-KVQ0, 17 × LOO, U11620-b, U12110-b, F-b.

| ramię | pp512 a / b (mediana) | pp4096 a / b |
|---|---|---|
| fork kvqleana (F) | 668,8 / 654,0 | 727,5 / 710,8 |
| upstream b12110 | 696,7 / 690,9 | 750,5 / 741,8 |
| upstream b11620 (baza forka) | 639,0 / 642,2 | 693,0 / 697,7 |
| F `GGML_CUDA_KVQ=0` | 654,7 | 709,5 |
| F LOO (17 przełączników) | 650,8 … 656,6 | 705,4 … 713,0 |

`llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -p 512,4096 -n 0 -r 3`: b12110 806,3 / 798,8 t/s; b11620 742,1 / 740,7 t/s (fork nie ma `llama-bench`).

- Średnio z a/b: **F vs b12110: pp512 −4,7%, pp4096 −3,6%** (zgodne z −3,5…−3,9% z kolejki). **F vs b11620 (ta sama baza): +3,2% / +3,4%.** Regresja nie pochodzi z łatek forka, tylko z tego, że fork stoi na b11620, a upstream między b11620 a b12110 przyspieszył prefill o ~8% (llama-bench +8,6% / +7,8%).
- LOO: żaden z 17 przełączników (`GGML_HIP_MMVQ_PAIR, NORM_FAST, ARGMAX_FAST, NORM_GATE, GDN_CONV_AB, CONV_MUL, ATTN_PREP, INPUT_BATCH, GDN_AB, GDN_L2, INPROJ_CONV, CONV_ROWS4, MMQ_EPI, Q8_PRODUCER, KVQ_FWHT, LLAMA_ASYNC_INPUTS, LLAMA_KV_MASK_FAST`) ani `GGML_CUDA_KVQ=0` nie zmienia prefillu poza ±0,5% względem F-b. Dryf F-a → F-b −2,2% (L4 trzyma limit 72 W, karta się nagrzewa) jest większy niż każdy efekt przełącznika.
- Werdykt: **odzysk prefillu na NVIDIA = rebase forka na nowszy upstream (≥ b12110), nie wyłączanie przełączników.** Kandydaci 0013/0045/0043 z kolejki nie są widoczni jako przełączniki runtime; bisekcja ma sens dopiero po rebase.
- Logi: `colab/l4/res/k023.jsonl`, `logs/k023-*.cmd|.log`, `logs/k023-llama-bench-*.jsonl`, `sha256-b11620.txt`.

## K-065 · Zimny start `--no-mmap` i nieprzetestowane flagi upstream — **zrobione (A12, A4, A8, A16); A10 pominięte**

Karta: Colab **L4**. W b12110 i w forku nie ma już `--no-mmap`; jest `-lm/--load-mode` (upstream: `auto, none, mmap, mlock, mmap+mlock, dio`; w forku testowałem tylko `auto` i `none`).

**A12 zimny start.** W VM `drop_caches` jest tylko do odczytu, więc przed każdym startem usuwałem strony modelu przez `posix_fadvise(POSIX_FADV_DONTNEED)`. Nie dało się potwierdzić, że to działa: nie ma `fincore`, a `dd` 3,4 GB po wyrzuceniu dał 3,3 GB/s wobec 4,9 GB/s na ciepło, czyli dysk VM jest bardzo szybki. Ramię `dio` z definicji czyta z dysku z pominięciem cache. Komenda: `llama-server … -c 8192 -ub 256 -np 1 --jinja -lm <tryb>`, potem 2 × to samo żądanie czatu (38 tok. promptu, 128 tok.).

| ramię | start do /health (s), rep 1 / 2 | 1. żądanie: prompt ms / tg t/s | 2. żądanie: tg t/s |
|---|---|---|---|
| up `-lm auto` (mmap) | 8,0 / 8,0 | 446 / 19,2 ; 451 / 18,6 | 18,3 ; 17,8 |
| up `-lm none` (= dawne `--no-mmap`) | 6,0 / 5,0 | 448 / 17,8 ; 460 / 18,3 | 18,0 ; 18,4 |
| up `-lm dio` | 4,5 / 4,5 | 457 / 18,2 ; 453 / 18,2 | 17,7 ; 18,4 |
| fork `-lm auto` | 8,5 / 8,5 | 448 / 18,0 ; 448 / 17,6 | 17,8 ; 17,6 |
| fork `-lm none` | 5,5 / 5,5 | 449 / 17,5 ; 446 / 17,7 | 17,6 ; 17,6 |

- Na Colab (szybki dysk, `dio` czyta 10,4 GB w ~4,5 s) **nie ma zjawiska „pierwszy prompt 0,39–1,07 t/s”**: pierwsze żądanie = drugie (±3%). `-lm none` skraca start o 2–3 s względem mmap, `dio` o 3,5 s, bez wpływu na t/s. Objaw z 3090 (Orca) wynikał prawdopodobnie z wolnego dysku hosta Vast i stron mmap ściąganych leniwie [INFERENCE]; tu nie do odtworzenia. Rekomendacja dla Enigmy: `-lm none` (albo `dio` na upstreamie) zamiast domyślnego mmap — szybszy start, zero kosztu.

**A4 `--spec-draft-n-ubatch 64` i A8 `GGML_CUDA_GRAPH_CHUNK_SIZE`** (upstream b12110, MTP n3): `llama-server … -c 32768 -ub 256 -np 1 --jinja --spec-type draft-mtp --spec-draft-n-max 3 [--spec-draft-n-ubatch 64]`, 6 promptów czatu × 256 tok., T=0, zbiorcze t/s:

| ramię | t/s (a / b) | VRAM MiB |
|---|---|---|
| ubd domyślne (= ub 256) | 30,95 / 31,39 | 11 354 |
| `--spec-draft-n-ubatch 64` | 31,18 / 31,50 | 11 306 |
| ubd64 + `GRAPH_CHUNK_SIZE` domyślne | 31,34 | 11 306 |
| … =1 / =2 / =4 / =8 | 30,83 / 31,09 / 31,19 / 31,35 | 11 306 |

- A4: ubd64 = +0,5% (szum), −48 MiB VRAM → **bez kosztu szybkości, zostaje.** A8: domyślne ≥ każda wartość (chunk 1: −1,6%) → **nie ruszać.**

**A16 `--spec-default` (n-gram upstream)**: `llama-server … -c 16384 -ub 256 -np 1 --jinja [--spec-default | --spec-type draft-mtp --spec-draft-n-max 3]`. Prompt kopiujący: przepisz `json/encoder.py` z jedną zmianą nazwy (1024 tok. wyjścia, T=0) + 6 promptów czatu.

| ramię | kopia t/s (a / b) | draft acc | czat t/s (a / b) | md5 kopii |
|---|---|---|---|---|
| plain | 17,60 / 18,15 | – | 18,56 / 18,60 | `4bd8820e…` |
| `--spec-default` | **133,07 / 134,38** | 935/1027 | 18,46 / 18,71 | identyczne |
| MTP n3 | 44,95 | 767/767 | 31,24 | identyczne |

- **`--spec-default` na kopiowaniu ×7,4 względem plain i ×3 względem MTP; na czacie 0% (ani zysku, ani straty).** Wyjście bitowo identyczne (bezstratne). Kandydat dla Enigmy: n-gram + MTP razem (fork już ma lookup W16; na upstreamie warto zmierzyć kombinację).
- **A10 `-fa off` pominięte:** wymaga KV f16 (bez FA nie ma kwantyzowanego V), a reguła zlecenia to KV q4_0…q6.
- Logi: `colab/l4/res/k065.jsonl` (pełne wiersze per prompt), `logs/k065-*.cmd|.log`.

## K-062 · Dekoder FA CUDA `__launch_bounds__(…,2)` — **pominięte**

To nie jest flaga budowania ani przełącznik runtime: wymaga zmiany atrybutu kernela w źródle (`fattn-*.cuh`), czyli nowego kodu silnika (i źródeł forka z jaroserverai). W binarkach nie ma żadnego env do occupancy dekodera FA (`GGML_CUDA_KVQ_BPSM` dotyczy kvq-mma, nie dekodera vec; to pozycja B13, nie K-062).

## K-061 · `-np 4` z MTP: `failed to create context` — **zrobione (odtworzone, zapisany błąd)**

Karta: Colab **L4** (23 GB). Komenda (fork, przepis MTP n2): `[FORK_ENV] llama-server -m m.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c <ctx> -np <np> -ub 256 --spec-draft-n-max 2 --jinja --spec-type draft-mtp -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab … --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs`, potem jedno żądanie czatu.

| ctx | np | wynik | VRAM po starcie |
|---|---|---|---|
| 32 768 | 4 (MTP) | start OK, odpowiedź OK | 20 776 MiB |
| 32 768 | 2 (MTP) | OK | 15 914 MiB |
| 32 768 | 4 (bez MTP) | OK | 10 828 MiB |
| 32 768 | 4 (MTP, upstream b12110) | OK | 12 538 MiB |
| 65 536 | 1 / 4 (MTP) | OK / OK | 12 144 / 21 442 MiB |
| 131 072 | 1 (MTP) | OK | 13 656 MiB |
| 131 072 | 4 (MTP) | /health OK, **pierwsze żądanie: abort** `cudaMalloc failed: out of memory` (170,25 MiB), `CUDA error: out of memory` | 22 432 MiB |
| 204 800 | 1 (MTP) | OK | 15 358 MiB |
| 204 800 | 4 (MTP) | **nie startuje (rc 1):** `allocating 9576.00 MiB on device 0: cudaMalloc failed: out of memory` → `llama_init_from_model: failed to initialize the context: failed to allocate buffer for rs cache` → `common_init_: failed to create context` | – |

- Błąd z kolejki odtworzony: to **OOM bufora stanu rekurencyjnego (rs cache) przy MTP**, a nie usterka logiki slotów. Przy np 4 bufor rs ma 9576 MiB [INFERENCE: niezależnie od ctx, bo przyrost VRAM na slot jest podobny przy 32k i 65k]. W forku każdy dodatkowy slot z MTP kosztuje ~2,4–3,1 GB VRAM (32k: np 4 − np 2 = +4,9 GB, czyli 2,4 GB/slot; 65k: np 4 − np 1 = +9,3 GB, czyli 3,1 GB/slot). Upstream b12110 z MTP przy np 4 i 32k zajmuje tylko 12,5 GB, ale ramienia np 1 dla upstreamu nie mierzyłem. 9576 MiB = 64 × 149,6 MiB (stan GDN jednej sekwencji z 67b), czyli ~16 komórek rs na slot [INFERENCE: rezerwa na szerokość weryfikacji lookup W16; do potwierdzenia w kodzie]. Na 24 GB `-np 4` z MTP mieści się do ~64k ctx. Przy 131k start przechodzi, a serwer pada przy pierwszym żądaniu, co jest gorsze, bo /health zgłasza gotowość.
- `common_fit_params: failed to fit params … abort` przy np 4 to tylko ostrzeżenie (`-ngl 999` ustawione ręcznie), nie przyczyna.
- Naprawy ani pomiaru `K_BY_B` nie robiłem (poza zakresem: kod).
- Logi: `colab/l4/res/k061.jsonl`, `logs/k061-*.log`, `logs/k061b-*.log` (+ `.cmd`).

## K-068 · CUDA `kvq`: wariant z wyjątkiem n=1 D256 q4_0 i serwer MTP@64k — **zrobione częściowo (bez KLD z `llama-perplexity`)**

Karta: Colab **L4**. KLD z `llama-perplexity --kl-divergence` niemożliwe: paczka forka ma tylko `llama-server`, a upstreamowy `llama-perplexity` nie ma ścieżki kvq (inne ABI i brak kernela). Zamiast tego: dekod przy głębokości 63 000 tokenów (wikitext-2 train, `cache_prompt`), 256 tokenów T=0, md5 wyjścia, `n_probs 10` jako przybliżenie rozkładu. Ramiona plain: `LLAMA_SPEC_LOOKUP=0`, bez spekulacji; ramiona MTP: pełny przepis forka n2. `-c 65536 -ub 256 -np 1`, KV q4_0. Domyślnie w wydaniu działa wyjątek (n=1 D256 q4_0 idzie ścieżką vec); `GGML_CUDA_KVQ_N1_D256_Q4=1` wyłącza wyjątek.

| ramię | prefill 63k t/s | dekod t/s (1. / 2. żądanie) | md5 wyjścia | drafty acc/n |
|---|---|---|---|---|
| plain `GGML_CUDA_KVQ=0` (stock FA) | 442,3 | 12,57 / 12,57 | `ab005968…` | – |
| plain `KVQ=1` (domyślnie, z wyjątkiem) | 442,2 | 12,54 / 12,59 | `16e5ffd2…` | – |
| plain `KVQ=1 N1_D256_Q4=0` | 441,9 | 12,60 / 12,31 | `16e5ffd2…` (= domyślne) | – |
| plain `KVQ=1 N1_D256_Q4=1` (bez wyjątku) | 442,0 | **16,64 / 16,36** | `8384a666…` (inne) | – |
| MTP n2 `KVQ=1` (domyślnie) | 426,9 | 38,08 / 38,61 | `cbc7404a…` | 179/312 |
| MTP n2 `KVQ=1 N1_D256_Q4=0` | 427,0 | 38,30 / 38,89 | `cbc7404a…` | 179/312 |
| MTP n2 `KVQ=1 N1_D256_Q4=1` | 426,5 | 38,96 / 39,29 | `cbc7404a…` (identyczne) | 178/314 |

Przybliżenie rozkładu (`k068kl.py`, top-10 logprobów, pozycje do pierwszej różnicy tokenu, odniesienie = domyślne KVQ=1): `N1_D256_Q4=1` daje te same tokeny przez 100/255 pozycji, średnie KL(top-10) 4,3e-4, max 2,8e-3, max |Δp| 0,035; dla porównania stock (KVQ=0) vs kvq różni się już na 2. tokenie (bliski remis, p 0,29), KL(top-10) na 1. pozycji 1,1e-3. `N1_D256_Q4=0` jest bitowo równe domyślnemu (wyjątek jest domyślny).

- **Wyjątek kosztuje 25% dekodu plain przy 63k na L4 (12,6 vs 16,6 t/s, +32,7% bez wyjątku), ale przy MTP tylko ~2% (38,3 → 39,0), a wyjście MTP jest bitowo identyczne** we wszystkich trzech ramionach (cel weryfikuje 3 wiersze, więc n=1 D256 dotyka tylko kroków draftu).
- Bez wyjątku numeryka plain się zmienia (inne md5), więc wariant nie jest bitowo bezstratny względem domyślnego; przybliżenie pokazuje odchylenie tego samego rzędu co kvq vs stock. **Do decyzji potrzebny prawdziwy KLD** (`llama-perplexity --kl-divergence --chunks ≥ 5` z buildu forka z narzędziami). Dla przepisu Enigmy (zawsze MTP) zysk jest mały (+2%), a wyjście identyczne → nie ma pilności.
- Logi: `colab/l4/res/k068.jsonl`, `k068-*.probs.json`, `logs/k068-*.cmd|.log`; skrypt `/tmp/kq/k068kl.py`.

## K-027 · Profil kroku przy długim kontekście (1,7k / 94k / 199k) — **zrobione (nsys; bez `LLAMA_HOSTGAP_TRACE`)**

Karta: Colab **L4** (24 GB mieści 199k z IQ3_XXS: 15,7 GB). `LLAMA_HOSTGAP_TRACE` nie istnieje w forku CUDA (to łatka topka-q63/ROCm; lista env w `fork-envs.txt`), więc przerwy hosta liczone z nsys jako czas bez żadnego kernela/memcpy na GPU.
Komenda: `nsys launch --session-new=k027 --trace=cuda,nvtx,osrt --cuda-graph-trace=node` + `[FORK_ENV] llama-server … -c 204800 -ub 256 -np 1` + przepis MTP n2 (lookup W16). Dla każdego N: prefill `tokens[:N]` z `n_predict 1`, potem `nsys start` → to samo żądanie z `n_predict 128` T=0 (cache, ponowna ewaluacja 4 tokenów) → `nsys stop`; analiza `nsys export sqlite` (suma przedziałów kerneli+memcpy). Kroki celu = 128 − zaakceptowane drafty.

| kontekst | prefill t/s | dekod t/s (bez nsys) | kroków | ms/krok | GPU zajęte ms/krok | **przerwa hosta ms/krok** | FA (kvq_mma + vec + combine) ms/krok | MMVQ ms/krok |
|---|---|---|---|---|---|---|---|---|
| 1 700 | 515 | 37,50 (37,43) | 50 | 73,9 | 63,3 | 10,7 (14,4%) | 0,9 (1,5% GPU) | 54,0 |
| 94 000 | 354 | 29,98 (30,16) | 51 | 93,2 | 82,1 | 11,1 (11,9%) | 14,8 (18,0%) | 57,6 |
| 199 000 | 171 (614 s) | 25,03 (25,35) | 46 | 126,7 | 109,5 | 17,2 (13,6%) | 34,7 (31,6%) | 53,7 |

Przy 199k dodatkowo `mul_mat_q` 10,1 ms/krok (przy 1,7k/94k 1,5 ms) i `mul_mat_q_stream_k_fixup` — do wyjaśnienia (inna szerokość batcha weryfikacji przy tej głębokości [INFERENCE]). Narzut nsys ≤ 1,3% t/s. L4 przez cały czas na limicie 72 W (śr. SM pod obciążeniem 1116 MHz z 2040, do 83 °C), więc wartości bezwzględne są niższe niż na 3090/4090; proporcje są tym, czego szuka bramka.

- **Bramka dla K-062/K-063/maski:** od ~94k atencja (FA) to 18%, a przy 199k 32% czasu GPU kroku (z czego dekoder vec 10,4 ms/krok, kvq-mma 24,2 ms/krok) → dekoder FA (K-062) i KV raz na weryfikację (C2) mają realny sufit tylko przy długim kontekście: przy 199k skrócenie FA o 20% = ~−7 ms/krok (~+5,5% t/s) [INFERENCE]. Przerwa hosta 11–17 ms/krok (12–14%) jest stała i rośnie przy 199k o ~6 ms → maska/host (K-031, C11) warte ataku. MMVQ (wagi) ~54–58 ms/krok niezależnie od kontekstu.
- Logi i raporty: `colab/l4/res/k027.jsonl` (wiersze i top-15 kerneli), `k027-{1700,94000,199000}.nsys-rep`, `*_cuda_gpu_kern_sum.csv`, `*_cuda_api_sum.csv`, `logs/k027-*.log`. (Pliki `.sqlite` zostały w VM — odtworzalne `nsys export` z `.nsys-rep`.)

## Budżet i sesje

| sesja | karta | czas | stan |
|---|---|---|---|
| `kqt4` | Tesla T4 | 15:42–15:53 (≈ 12 min) | **wyłączona** (`colab stop`, 15:53:44) |
| `kql4` | NVIDIA L4 | 15:43–17:11 (≈ 88 min) | **wyłączona** (`colab stop`, 17:11:25) |

Saldo: 200,00 → **196,96 jednostek (zużyte 3,04 z limitu 25)**; `colab sessions`: brak aktywnych. Dwie pierwsze próby L4 (15:33, 15:37) skończyły się `Service Unavailable` bez przydziału.

## Podsumowanie

| pozycja | status | najważniejsze |
|---|---|---|
| K-069 | smoke zrobiony; build forka pominięty (źródła tylko na jaroserverai) | wydany fork na sm_75: `no kernel image` → abort; upstream b12110 (PTX) T4: pp512 302, tg128 9,14 t/s |
| K-068 | dekod/md5 zrobione; KLD pominięte (brak `llama-perplexity` w paczce forka) | bez wyjątku plain @63k +32,7% (12,6 → 16,6), MTP +2% z bitowo tym samym wyjściem |
| K-065 | zrobione (A12, A4, A8, A16); A10 pominięte (wymaga KV f16) | cold start bez zjawiska na Colab, `-lm none` −2…3 s startu; ubd64 0% / −48 MiB; chunk domyślny najlepszy; `--spec-default` kopia ×7,4, czat 0% |
| K-027 | zrobione (nsys) | FA 1,5% → 18% → 32% czasu GPU kroku; host 11–17 ms/krok (12–14%) |
| K-023 | zrobione bez bisekcji commitów (brak źródeł) | fork vs b12110 −4,7% / −3,6%, vs b11620 +3,2% / +3,4%; 17 przełączników LOO w ±0,5% → regresja = stary upstream, lekarstwo rebase |
| K-061 | odtworzone | np 4 + MTP: rs cache 9576 MiB → `failed to create context` przy 204 800; przy 131 072 OOM na 1. żądaniu; ~2,4 GB/slot |
| K-062 | pominięte | `__launch_bounds__` to zmiana kodu, nie flaga buildu |

## Powiązane
- [[KOLEJKA-TESTOW]]
- [[przeglad-kolejki-2026-11-24]]
