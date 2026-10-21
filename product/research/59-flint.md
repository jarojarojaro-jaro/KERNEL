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
  kerneli na warstwę MoE (×47) w decode; kandydat do fuzji w kwantyzację q8_1 (do zmierzenia).
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
