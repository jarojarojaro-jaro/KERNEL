# 59: Recursive Flint (40B MoE, ~2.5B aktywnych) lokalnie (2026-10-21)

Model: `RecursiveSI/flint`, oficjalny kwant `RecursiveSI/flint-nvfp4-gguf` → `flint-nvfp4.gguf` (22 863 084 160 B,
QAT NVFP4). Obsługa w llama.cpp = upstream PR #30928 (otwarty, niezmergowany).

## XTX

**Stan: build gotowy (branch `flint`, port PR #30928 na topka + 4 poprawki), testy GPU przygotowane (`fl.jobs`),
jeszcze nieuruchomione — plik modelu się pobiera.**

### Nagłówek GGUF (odczytany z częściowego pobrania)
- 49 warstw (2 dense + 47 MoE), n_embd 2048, 256 ekspertów top-6 sigmoid (norm wag = true), 2 shared (n_ff_shexp 1024),
  n_ff_exp 512, GQA 32/4, head dim 128, sinks F32 [32] na warstwę, QK RMSNorm.
- `sliding_window_pattern` = `rope_pattern`: 35 warstw SWA 513 z RoPE, 14 warstw full-attention bez RoPE.
- Typy: wszystkie macierze NVFP4 + skale F32 `.scale` (per-tensor, per-ekspert dla `*_exps`), `ffn_gate_inp` BF16,
  `token_embd` BF16 (CPU), `output` NVFP4. `general.tensor_extra.prec_a4` = false dla wszystkich → `GGML_PREC_Q8`
  (aktywacje q8_1, na RDNA3 i tak jedyna ścieżka).
- EOG w metadanych: `<|end_of_text|>`, `<|user|>`, `<|observation|>`, `<|developer|>` (klucz `eog_token_ids` nie jest
  czytany przez llama.cpp).

### Port PR #30928
PR bazuje na nowszym upstream (269 commitów przed naszą bazą). Konflikty: `llama-graph.{h,cpp}` (upstream ma
`build_amax_src1_f16`, my nie), `llama-model.cpp` (rope type), `test-llama-archs.cpp`. Rozwiązanie:
- `build_amax_src1_f16` (skalowanie wejścia `ffn_down_exps` potęgą 2, by aktywacje q8_1 i ich sumy blokowe zmieściły
  się w F16) przeniesione z upstream i włączone **tylko dla Flint**. Mistral4 zostaje przy `GGML_PREC_F32`
  (bez zmian; uwaga: w naszym ggml-cuda `MUL_MAT_ID` z `GGML_PREC_F32` → op odrzucony → CPU).
- Brakujące w PR dla naszego drzewa: `ggml_build_forward_expand(gf, cur)` na końcu grafu (u nas framework tego nie
  robi; `test-llama-archs -a flint` padał na asercji `backend_res != nullptr`). Po poprawce: OK (NMSE 0, roundtrip OK).

### Opy na HIP (gfx1100)
- FA z sinks: vec/tile/mma obsługują sinks; **nasz kernel `kvq` (q4_0/q8_0 KV, decode/verify ≤16 tokenów) nie
  obsługiwał** → każdy model z sinks spadał na vec. Dodane: sink doliczany w pierwszym splicie (jak vec), także przy
  combine (zwykłym i FWHT). Bez sinks ścieżka identyczna. Testy: nowe przypadki Flint (D128, 4 głowice KV × GQA 8,
  q4_0, kv 512/1024/8192, nb 1/4/16) w `test-backend-ops` — do uruchomienia w kolejce (`fl-tbo`).
- Prefill z KV q4_0: tile/mma konwertują K/V do F16 w puli — ~2 KiB/token na warstwę full-attn ponad bufor compute
  (przy 262k ≈ 512 MiB). Dlatego pomiar max ctx robi pełny prefill, a nie sam load.
- SWA + warstwy bez RoPE: maska + pominięcie `rope_ext`; K-shift tylko gdy jakaś warstwa ma RoPE (z PR).
- MoE: fuzja topk-moe obsługuje sigmoid; NVFP4 `MUL_MAT_ID` przez MMQ (q8_1) i MMVQ; skale per-ekspert = `ggml_mul`.
- amax: ABS, POOL_1D (MAX), SCALE, LOG, CEIL, CLAMP, EXP, DIV, MUL — wszystkie na HIP. **Koszt**: ~10 małych
  kerneli na warstwę MoE (×47) w decode. POOL_1D (1 wątek/wiersz) zastąpiony warpem na wiersz tylko dla MAX z k0 =
  długość wiersza (patch z 3090: tg 129.8 → 146.7 t/s, greedy identyczne; commit `c586593cf`). Reszta łańcucha
  (7 launchy ×47) — kandydat do fuzji (~+7% na 3090). Wyłączenie amax zmienia greedy przy 8k → nie wyłączać.
- Żaden op nie powinien spadać na CPU ani abortować (`[INFERENCE]` z `supports_op`; potwierdzi `graph splits`
  w logu serwera i `fl-tbo`).

### Szablon czatu / narzędzia
- Szablon z GGUF: tagi GLM-4.7 (`<tool_call>name<arg_key>k</arg_key><arg_value>v</arg_value></tool_call>`,
  `<think>…</think>`), własne role `<|system|> <|developer|> <|user|> <|assistant|> <|observation|>`.
- **Luka 1 (naprawiona):** nasz lexer jinja nie znał `\x00` (`replace("\x00", "")` w szablonie) → szablon w ogóle się
  nie parsował. Dodane escape'y `\xHH` (test-jinja).
- Parsowanie: auto-parser (diff analyzer) sam wykrywa reasoning i format narzędzi; `test-chat` z szablonem Flint
  (treść, reasoning, tool call, tool call + reasoning, 2 równoległe) — PASS.
- **Luka 2 (naprawiona):** `<|developer|>` nie był EOG.
- **Luka 3 (otwarta):** llama.cpp mapuje rolę `developer` → `system` dla wszystkich szablonów poza GPT-OSS; Flint ma
  natywne `<|developer|>`. Wpływ: prompt z rolą developer dostaje `<|system|>`.
- **Luka 4 (cecha modelu):** szablon nie ma przełącznika myślenia — `EFFORT`/`--reasoning off` nie działa, model myśli
  zawsze (E0 `prose_bench` liczy t/s razem z reasoningiem).

### VRAM (rachunek, do potwierdzenia pomiarem)
Wagi na GPU ≈ 21.2 GiB (bez `token_embd` BF16 0.6 GB na CPU), KV q4_0 full-attn 14 × 1024 × 0.5625 B = 7.9 KiB/token
(200k: 1.5 GiB, 262k: 2.0 GiB), SWA ~25–60 MiB, compute zależny od ub. XTX: 24 534 MiB wolnego bez serwera.

### Profil i testy
- `run-llm.sh flint` / `run-topka.sh flint`: KV q4_0, spec none, lookup 3, `-b 2048 -ub 2048` (jak LFM), sampling z karty
  (T 1.0, top-p 0.95, top-k 20, min-p 0), `ROCM_DIR=~/qwen-opt/flint/inst`. ctx/ub domyślne = wynik pomiaru
  (`flint/ctx-max`, `flint/ub`; fallback 200 000 / 2048). `model-swap.py`: profil `flint`.
- `fl.jobs`: czekanie na plik → `test-backend-ops` (FA q4_0 z sinks, NVFP4 MUL_MAT/MUL_MAT_ID, POOL_1D) → sweep max ctx
  (262 144 → 200 000, ub 2048 i 512, pełny prefill, zapas ≥ 200 MB) → smoke PM4=0 (czat greedy, tool call 2 tury,
  igła ~150k na początku) → smoke PM4=1 → ABBA PM4 0/1: E0 decode + prefill/decode na głębokości 8k/64k/150k.
- Wyniki: do uzupełnienia po przebiegu kolejki.

## RTX 3090

Vast 56418874 (Słowacja, RTX 3090 24 GB, limit mocy 260 W (domyślny 390 W), PCIe 4.0 x16, driver 610.43), CUDA 12.8,
upstream + PR #30928 (`1b44e3077`), build `-DCMAKE_CUDA_ARCHITECTURES=86`, `-ngl 99 -fa on -ctk q4_0 -ctv q4_0 -np 1`.
Instancja 52 min, zniszczona (API: 0 naszych instancji). Pobranie modelu na instancji ~100 MB/s (3.5 min).
Dane: `~/qwen-opt/cloud/results/flint-3090-20261021/` (bench/*.jsonl, lb-summary.tsv, prof/*.nsys-rep, logs/, patche).

### Mieszczenie (KV q4_0, MiB z logu serwera; wolne = `nvidia-smi` po starcie, karta 24 576, dostępne 24 126)

| ctx | ub | wagi GPU | KV full (14 w.) | KV SWA | compute GPU | wolne | pełny prefill |
|---|---|---|---|---|---|---|---|
| 200 000 | 512 | 21 212 | 1 540 | 25 | 620 | ~400 `[SZACUNEK]` | (200k działa, por. 230k) |
| 200 000 | 1024 | 21 212 | 1 540 | 34 | 850 | 172 | nie testowany |
| 160 000 | 2048 | 21 212 | 1 230 | 54 | 1 077 | 232 | nie testowany (200k ub2048: OOM) |
| 230 000 | 512 | 21 212 | 1 770 | 25 | 708 | 94 | 225 000 tok OK (68 MiB wolne) |
| **235 000** | **512** | 21 212 | 1 807 | 25 | 722 | 42 | **232 000 tok OK** (16 MiB wolne) |
| 245 000 | 256 | 21 212 | 1 886 | 20 | 615 | 74 | nie testowany |
| **250 000** | **128** | 21 212 | 1 923 | 15 | 558 | 100 | **247 000 tok OK** (54 MiB), prefill 516 t/s |
| 262 144 | 512/256/128 | — | — | — | 801/657/? | — | OOM (compute buf / pierwsza partia) |

- Wagi: 21 212 MiB GPU + 586 MiB `token_embd` na CPU. KV q4_0 = 7.88 KiB/token (14 warstw full-attn), SWA 1 280 komórek.
- Compute buffer rośnie z ctx (~0.5 GiB przy 240k niezależnie od ub: widok K/V jednej warstwy w F16 dla prefillu FA)
  — dlatego mały ub kupuje tylko ~10–15k tokenów.
- Max: **235k przy ub 512** (pełne wypełnienie zweryfikowane), **250k przy ub 128** (wypełnione, ale prefill 2× wolniejszy).
  262 144 się nie mieści. Na pulpicie z innymi procesami na GPU zapas 16–54 MiB to za mało → praktycznie 200–220k.

### Szybkość (baseline = PR bez zmian, ub 512)

| test | prefill t/s | decode t/s |
|---|---|---|
| llama-bench pp512 / pp2048 / tg128 (d0) | 2 240 / 2 272 | 130.3 |
| llama-bench d8192 (p512, n64) | 2 141 | 108.8 |
| llama-bench d16384 / d32768 | — | 97.2 / 81.8 |
| llama-bench d65536 | 1 405 | 60.7 |
| serwer ctx 235k: prompt 9 tok / 8k / 64k / 150k | — / 2 082 / 1 703 / 1 283 | 124.7 / 107.0 / 60.4 / 36.0 |
| serwer prompt 225k (ctx 230k) / 232k (ctx 235k) | 1 054 / 1 039 | 24.9 / 25.6 |
| serwer ctx 200k **ub 1024**: 8k / 64k / 150k | **2 854 / 2 294 / 1 647** | 104.3 / 59.5 / 35.7 |

Prefill = średnia całego promptu (rośnie koszt atencji), decode = 128 tokenów greedy po prompcie.

### Profil decode (nsys, tg64 d0, CUDA graphs z `--cuda-graph-trace=node`): 7.41 ms GPU/token, 2 219 kerneli/token

| # | kernel (rola) | ms/token | % |
|---|---|---|---|
| 1 | `pool1d_nchw_kernel` — amax z PR (POOL_1D MAX, 1 wątek/wiersz, 21.5 µs ×47) | 1.01 | 13.6 |
| 2 | `mul_mat_vec_q<NVFP4>` MoE gate+up (fused, 6 ekspertów, 17.5 µs ×47, ~405 GB/s) | 0.82 | 11.1 |
| 3 | `mul_mat_vec_q<NVFP4>` MoE down (14.3 µs ×47, ~247 GB/s) | 0.67 | 9.1 |
| 4 | `quantize_q8_1` (wszystkie, ~436/token) | 0.55 | 7.5 |
| 5 | mmvq Q-proj 2048→4096 (8.7 µs ×49, ~540 GB/s) | 0.43 | 5.8 |
| 6 | mmvq shared expert gate/up (4.3 µs ×94) | 0.41 | 5.5 |
| 7 | mmvq K/V-proj 2048→512 (4.1 µs ×98, ~145 GB/s — latencja) | 0.40 | 5.4 |
| 8 | mmvq O-proj + dense down (7.7 µs ×51) | 0.39 | 5.3 |
| 9 | `flash_attn_ext_vec<q4_0>` + combine (sinks) | 0.36 | 4.8 |
| 10 | lm_head 150 144 × 2048 NVFP4 (222 µs, ~780 GB/s) | 0.22 | 3.0 |

Dalej: shared down 0.21, rms_norm 0.21, set_rows q4_0 0.20, FWHT (rotacja KV) 0.23, scale 0.16, router BF16 0.15,
topk_moe 0.14 ms. Całe 2.5B aktywnych w NVFP4 to ~1.3 GB/token → sufit pasma ~650 t/s; jesteśmy na ~20%: decode jest
ograniczony latencją ~2.2k małych kerneli (śr. 3.3 µs), nie pasmem.

**Przy głębokości** (tg d65536, nsys): `flash_attn_ext_vec` grid (1,5,32) = 1 głowa Q na blok → przy GQA 8 każdy
blok K/V q4_0 czytany 8×: ~489 µs na warstwę full-attn × 14 = **6.9 ms/token** (~42% z 16.5 ms). Dowód: KV f16 (ścieżka
MMA z pakowaniem GQA) przy d65536 = **97.6 t/s vs 60.7 q4_0** (q8_0 61.5 — typ kwantu bez znaczenia, liczy się
ponowny odczyt). Na Ampere kwantowany KV przy `ne1==1` zawsze idzie w VEC (fattn.cu, gałąź `cc < Ada`).
Prefill (pp2048): `mul_mat_q<NVFP4>` 75%, FA mma 4%, stream-k fixup 3%, pool1d 2%.

### A/B (llama-bench, r=3; greedy = 128 tok przez serwer, prompt krótki + 8k)

| zmiana | wynik | greedy |
|---|---|---|
| `-ub` 128 / 256 / **512** / 1024 / 2048 (pp2048) | 940 / 1 527 / 2 272 / 3 059 / **3 825** | inna kolejność sum (różni się) |
| CUDA graphs off (`GGML_CUDA_DISABLE_GRAPHS=1`) | tg 130.3 → 99.7 (−23%) | — |
| `GGML_CUDA_GRAPH_OPT=1` | tg 125.2 (−4%) | — |
| `GGML_CUDA_FORCE_MMQ` (build) | bez zmian (NVFP4 i tak idzie MMQ) | — |
| wątki `-t` 1 / 4 / 16 / 96 | 129.9 / 130.1 / 130.4 / 130.3 | — |
| KV q8_0 vs q4_0 (d0 / d65536) | tg 129.2 / 61.5 vs 130.3 / 60.7; pp −9% | — |
| FA off (KV f16) vs FA on (f16) | pp2048 1 946 vs 2 310, tg 126.7 vs 134.9 | — |
| `--swa-full` | nie testowany: SWA pełne = 35 w. × ctx → ~+4.6 GiB przy 200k, nie mieści się | — |
| spec `ngram-simple`: kopia pliku / edycja / opowiadanie | **225.4** / 115.5 / 121.3 vs 114.0 / 114.3 / 123.2 | różni się od ~256. znaku (weryfikacja partią) |
| spec `ngram-mod`: kopia / edycja / opowiadanie | 187.0 / 122.0 / 121.1 | j.w. |
| **patch pool1d warp-per-row** (`pool1d-rowmax.patch`) | **tg 129.8 → 146.7 (+13%)**, pp2048 +1.6%, d8k 118.3, d64k 63.7 | **identyczny** |
| amax wyłączony (`EXP_NO_AMAX`, tylko pomiar sufitu) | tg 157.7 (+21.5%) | **różni się przy 8k** → nie wyłączać |
| serwer ctx 200k ub 1024 + pool1d | 9 tok 138.8, 8k 114.6, 64k 62.7 t/s | — |

### Co zadziałało / zalecenia
- **Konfiguracja na 3090:** `-c 200000 -ub 1024 -b 2048 -ctk q4_0 -ctv q4_0 -fa on -np 1` (172 MiB zapasu, prefill +28–37%
  vs ub 512). Maksimum: 235k (ub 512) albo 250k (ub 128, wolny prefill). `ub 2048` tylko do ~160k.
- CUDA graphs muszą zostać włączone (+31%); wątki, FORCE_MMQ, GRAPH_OPT — bez zysku.
- `ngram-simple` ×2.0 na kopiowaniu tekstu, ~0 na edycji, −2% na swobodnym tekście.
- Szablon czatu z GGUF w tym buildzie wywala jinja (`\x`) — potrzebny merged #30929 (lub łatka z XTX).

### Pomysły do portu (HIP, nasz fork)
1. **pool1d whole-row** (gotowy patch, bit-exact): jeden warp na wiersz zamiast wątku; +13% decode na 3090. Na RDNA3
   ten sam problem (1 wątek sekwencyjnie przez 512 floatów, 47×/token).
2. **Fuzja łańcucha amax** ABS→POOL_1D→SCALE→LOG→SCALE→CEIL→CLAMP→SCALE→EXP (wzorzec w `ggml_cuda_can_fuse`, 1 kernel
   na wiersz) — zostało ~0.45 ms/token do sufitu 157.7 t/s (+7%); można też wliczyć dzielenie przez 2^e w kwantyzację q8_1.
3. **FA decode z kwantowanym KV i GQA** (największy zysk przy 64k+): VEC czyta K/V 8× (GQA 8). Nasz `fattn-kvq` (RDNA3)
   robi jeden przebieg na głowę K/V — z sinkami (commit 9c277853f w `~/wt/flint`) powinien dać na XTX skalę zysku jak f16
   na 3090 (60.7 → ~98 t/s przy 64k, przy 225k szacunkowo 25 → ~60 t/s `[INFERENCE]`). Odpowiednik na CUDA wymagałby
   wersji mma.sync m16n8k16 z dekwantyzacją do rejestrów.
4. MoE down mmvq NVFP4 ma tylko ~247 GB/s (krótki wymiar wewnętrzny 512 = 288 B/wiersz, 128 bloków × 6 ekspertów):
   więcej wierszy na warp / łączenie ekspertów w jednym bloku; K/V-proj (512 wierszy, 4 µs) — fuzja Q+K+V w jeden mmvq.

### Koszt
Oferta $0.4017/h (GPU $0.373 + dysk 90 GB) × 0.863 h = $0.35; pobieranie 24.6 GB × $2.6/TB = $0.06; wysyłka ~0.1 GB
< $0.001. **Razem ≈ $0.41** (limit $1.50). Trzy wcześniejsze próby wynajmu (oferty TH/CA/UT) odrzucone przez Vast
(`no_such_ask`, oferty zniknęły) — $0.
