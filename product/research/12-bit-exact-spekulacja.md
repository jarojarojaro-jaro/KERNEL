# 12. Bitowo identyczna spekulacja (MTP == plain greedy)

Data: 2026-10-16. Gałąź `batch-invariant` w `~/wt/batchinv` (od `amd-opt-v070` @ 8c942e5a9), niezacommitowane zmiany opisane niżej.
Narzędzia offline: `~/wt/bx-isa/` (ISA, emulatory, wyniki). Bez użycia GPU.

## 1. Cel i wniosek

Dziś na 7900 XTX: Qwen3.8-27B plain greedy md5 `c4708318`, MTP (n_max 4) `6f14e814`. Przyczyną jest numeryka weryfikacji. Ta sama pozycja tokenu liczona jest innym kernelem przy N=1 (plain) i przy N=2..6 (weryfikacja). Dodatkowo jeden przełącznik po stronie hosta zależy od trybu.

Projekt: tryb `LLAMA_SPEC_BITEXACT=1` (ggml przyjmuje też `GGML_HIP_BITEXACT=1`). Ścieżka N=1 dostaje arytmetykę kolumny kerneli wielokolumnowych (opcja b). Weryfikacja (N≥2) pozostaje bez zmian, więc **koszt dla MTP jest praktycznie zerowy**. Koszt płaci tylko dekodowanie N=1, czyli plain i rzadkie kroki bez draftu.

Dla MMVQ i GDN równoważność udowodniono offline (symboliczny emulator ISA gfx1100). FA i reszta opierają się na analizie kodu. Wymagany jest test na GPU (sekcja 7).

## 2. Stan wiedzy

- Thinking Machines, „Defeating Nondeterminism in LLM Inference” (He i in., 10.09.2025): https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference
  - Źródłem niedeterminizmu nie jest „GPU + atomiki”, tylko brak niezmienniczości względem rozmiaru batcha.
  - Recepta: RMSNorm/matmul/attention o stałej kolejności redukcji, bez split-K zależnego od batcha, oraz attention ze **stałym rozmiarem splitu** (nie stałą liczbą splitów).
  - Kod: https://github.com/thinking-machines-lab/batch_invariant_ops
- vLLM, `VLLM_BATCH_INVARIANT=1` (beta): https://docs.vllm.ai/en/latest/features/batch_invariance/
- SGLang, deterministic inference (LMSYS, 22.09.2025): https://www.lmsys.org/blog/2025-09-22-sglang-deterministic, dokumentacja: https://docs.sglang.io/docs/advanced_features/deterministic_inference
- Prace: arXiv 2506.09501 (źródła numerycznego niedeterminizmu); LLM-42, deterministyczna inferencja przez „verified speculation”: https://arxiv.org/html/2601.17768
- llama.cpp:
  - #23335 (MTP zmienia wynik greedy na Qwen3.6 Q4_K_M; ggerganov: „This is expected – we use different kernels for different batch sizes”; na Q8_0 zgodne): https://github.com/ggml-org/llama.cpp/issues/23335
  - #25618 (Vulkan: lista źródeł podobna do naszej, m.in. FA split_k zależny od N oraz MMVQ niezmienniczy względem N; obejście przez wyłączenie MMVQ, które kosztuje szybkość): https://github.com/ggml-org/llama.cpp/issues/25618

**Nowość u nas:** nie wyłączamy szybkich kerneli (jak #25618). Zamiast tego **N=1 przechodzi na arytmetykę już strojonych kerneli wielokolumnowych**, a równoważność dowodzimy symbolicznie na ISA.

## 3. Mapa operacji (N=1 vs N=2..6), drzewo bazowe 8c942e5a9

| Op | N=1 | N=2..6 | Różnica arytmetyki | Naprawa w trybie bitexact |
|---|---|---|---|---|
| MUL_MAT Q4_K/Q5_K | `mul_mat_vec_q<…,1>`, `vec_dot_q4_K_q8_1` (vecdotq.cuh:918-965, impl 508-530), vdr 2, 1 fala, 2 wiersze/blok (mmvq.cu:1362-1383, 2302-2313) | ścieżka multi (mmvq.cu:1494-1497, 1723-1731, `mmvq_dot` 681-694), vdr 4 | inny podział K na linie; człon min z `ds.y` (suma fp16 aktywacji, mmvq.cu:120-123) zamiast dokładnej sumy int q8 (vecdotq.cuh:521-524); inne zaokrąglenia | n1_multi |
| Q6_K | nwarps 2 (mmvq.cu:1301-1302), vdr 1, LDS + shfl | multi, nwarps 1, vdr 4, przy n=5 pipeline | inny podział, inna redukcja, inna kolejność iloczynów | n1_multi |
| IQ4_XS / IQ4_NL / IQ3_S | `d*(sumi*(ls-32))` (vecdotq.cuh:1357-1380) | `x.d*u.d*sumi` (mmvq.cu:747-755) | inne zaokrąglenia | n1_multi |
| Q8_0 (attn_k/v, ssm_out) | nwarps 8 (mmvq.cu:1299-1300) | nwarps 1 | podział K i redukcja przez LDS | n1_multi (nwarps 1) |
| Q3_K | nwarps 1, ten sam vec_dot | to samo | brak (udowodnione) | – |
| MMVQ 7-8 kol. (Q6_K) / 9-16 kol. | – | WMMA iu8 (mmvq.cu:2550-2553, 3726-3743) | sumy kafli WMMA | WMMA wyłączone; ≤8 kolumn dp4a; >8 → MMQ (nie bitexact) |
| SwiGLU FFN | gate+up+silu w 1 kernelu MMVQ (ggml-cuda.cu:1890-1919, 5403-5470) + q8 (GATE_UP_Q8) | para MMVQ + `unary_gated_op_kernel` (unary.cu:306-330) | ta sama formuła, ale **instancja z bramką inaczej kontraktuje FMA w iloczynach skalarnych** (emulator: 555 mul/578 fma vs 475/658) | fuzja gate/GLU wyłączona przy N=1 |
| bias/residual w MMVQ | `has_fusion` z akumulatorami bramki | `bias_only` | dla IQ4_XS inna kontrakcja (mul+fma vs łańcuch fma) | n1_multi używa kernela `bias_only` |
| Flash attention (q4_0, D=256, GQA 6) | kvq, 1 kafel (fattn.cu:634-637) | kvq, `ntiles=ceil(6N/16)` | liczba splitów KV = `2·nsm/(ntiles·4)` (fattn-kvq.cu:615-636), więc inne granice splitów, max per fala, zaokrąglenia P do fp16 i scalanie. Dla nsm=96 dotyczy kontekstów >3072 (N 3-5) i >2048 (N=6). Dodatkowo `n_kv=pad(p+1,256)` vs `pad(p0+N,256)` (llama-kv-cache.cpp:1337-1350), a 1 split zapisuje VKQ/sum bezpośrednio (fattn-kvq.cu:568-575), inaczej niż combine | stały rozmiar splitu (domyślnie 512 wierszy), zawsze ≥2 splity |
| Q/K norm+IMROPE+FWHT, set_rows q4_0, FWHT V, bramka sigmoid | blok na (głowę, token) | to samo | brak (AttnScout) | – |
| GDN | `GATED_DELTA_NET` K=1 (delta-net-base.cpp:629-645) | `GATED_DELTA_NET_LAG` + replay (gated_delta_net.cu:97-162, 164-291) | inne instancje i pętla replay | **udowodnione bitowo równe**, bez zmian |
| alpha/beta (A4, Q8_0) | `gdn_conv_ab<Q8_0,1>` | `<…,N>` (mmvq.cu:3016-3108) | ten sam kod per token, stałe nwarps 4 | dowód emulatorem nieukończony (sekcja 6) |
| SSM_CONV (plain vs LAG) | 1 wiersz stanu | gather 3 kroków | to samo Σ_j w kolejności j (ssm-conv.cuh:99-110) | – |
| rms_norm(+mul,+q8), norma bramkowana, l2 | blok na wiersz, rozmiar od ncols | to samo | brak | – |
| quantize_q8_1 / producenci A6 | `quantize_q8_1_group` | to samo | brak (MMQ ma inną formułę, ale przy N≤8 nieużywany) | – |
| argmax / sampling | CPU greedy, pierwsze maksimum (llama-sampler.cpp:1053-1059) | to samo per wiersz | brak | – |
| Host: podział promptu | `split_equal(…, tail 0)` | `tail = n_max+1 = 5` (llama-memory-hybrid.cpp:85-91) | dla len%512∈1..4 inne N w ubatchu brzegowym | tail ≥ 8 w obu trybach |
| Host: crop wyjścia | GET_ROWS przed residual w warstwie 63 (qwen35.cpp:180-183) | po output_norm (qwen35.cpp:214-219) | per wiersz równe przy niezmienniczym MMVQ (dodawanie fp32 i q8 identyczne) | – |

## 4. Projekt `LLAMA_SPEC_BITEXACT=1` i porównanie opcji

- **(a) Wielokolumnowe MMVQ odtwarza kolejność N=1.**
  - Trzeba porzucić sztuczkę `ds.y`, vdr 4 i jedną falę, a dla Q6_K/Q8_0 dojdzie redukcja przez LDS z 2/8 fal.
  - Szacunek [INFERENCE]: MMVQ weryfikacji wzrośnie z 22.1 do ~25-27 ms, czyli krok MTP +10% i ~-10% t/s. Odrzucone.
- **(b) N=1 używa arytmetyki wielokolumnowej. Wybrane.**
  - Nowy parametr szablonu `n1_multi`: `mmvq_arith_ncols()` podaje do vdr/nwarps/use_multi wartość 2, a wiersze na blok i siatka pozostają z N=1.
  - Kernele wielokolumnowe są **bajt w bajt nietknięte**: `isadiff_bx.py` pokazuje 862/862 kerneli identycznych po rename.
  - Plain decode zmienia się raz; plain i MTP stają się równe.
- **(c) Attention.**
  - Stały rozmiar splitu KV `GGML_HIP_BITEXACT_FA_UNITS` (domyślnie 4 jednostki = 512 wierszy), co najmniej 2 splity, więc zawsze ten sam combine.
  - Dodatkowe zamaskowane wiersze i puste splity dają dokładne +0.

Zmiany w kodzie (diff w worktree):

1. `ggml/src/ggml-cuda/common.cuh`: `ggml_cuda_bitexact()`.
2. `mmvq.cu`:
   - `n1_multi`, `mmvq_arith_ncols`, `mmvq_n1_multi_type`;
   - dispatch N=1 (gałąź bitexact); jednokolumnowy bias przez kernel `bias_only`;
   - WMMA wyłączone; ponad 8 kolumn → MMQ.
3. `fattn-kvq.cu`: stały split.
4. `ggml-cuda.cu`: brak fuzji gate/GLU przy bitexact.
5. `src/llama-memory-hybrid.cpp`: tail `max(n_rs_seq+1, 8)` (`LLAMA_SPEC_BITEXACT_TAIL`).
6. `common/speculative.cpp` (niezależnie od trybu): `pending_h` zerowane dla pozycji 0. Patrz sekcja 8.

Ograniczenia:
- Wspierane tylko RDNA3 (gfx1100).
- n_max ≤ 7 (weryfikacja ≤ 8 tokenów).
- Pozostałe tablice nwarps dla N≥2 nie są stałe względem N, więc na innych architekturach tryb nie działa.

## 5. Koszt (szacunki do potwierdzenia na GPU)

- **Weryfikacja MTP (N=2..5):**
  - MMVQ: 0 (te same kernele).
  - FA, krótki kontekst: przy ~1k tokenach 2 splity × 512 zamiast 8 × 128, ~+1-3 µs na warstwę × 16 [INFERENCE], czyli <0.2%.
  - FA, 32k: N=5 ma 64 splity zamiast 24, combine to ~+5 MB/warstwę, ~0.1-0.2 ms na weryfikację (~0.5%).
  - FA, 98k: ~0.4 ms (~1.5%). Można to zmniejszyć przez `GGML_HIP_BITEXACT_FA_UNITS=8`.
- **N=1 (plain i draft MTP):**
  - kernele n1_multi zamiast strojonych N1: ±?, wymaga pomiaru;
  - brak fuzji GLU: +2 kernele na warstwę × 64. Przy granicy 0.5-2.75 µs to ~0.06-0.35 ms/token (~0.3-1.3% plain).
- **n_max 6-7:** Q6_K traci WMMA dla 7-8 kolumn.
- **Przewidywanie:** MTP t/s w granicach szumu, plain −0..2%. Jeśli n1_multi okaże się neutralne albo szybsze, warto je włączyć domyślnie. Wtedy plain z definicji równa się MTP bez żadnego przełącznika.

## 6. Status prototypu (offline, CPU)

- **Kompilacja:** pełny build HIP gfx1100 (`build-hip`: llama-server, llama-bench, test-backend-ops, llama-cli) z wszystkimi zmianami: rc=0 (`/tmp/batchinv-build2.log`).
- **`isadiff_bx.py`:** 862/862 bazowych kerneli MMVQ bajtowo identycznych (domyślny tryb nie zmienia numeryki ani kodu kerneli).
- **`mmvqemu.py`** (rozszerzony emulator gdnemu: buffer loads, dp4a, DPP, permlanex16, tablice stałych, rejestry 16-bit).
  - Każde słowo wyniku jednokolumnowego n1_multi to **ten sam węzeł DAG IEEE** co kolumna kernela n-kolumnowego, dla n=2..8 i typów Q4_K, Q5_K, Q6_K (z pipeline n=5), IQ4_XS, IQ4_NL, IQ3_S, Q8_0 oraz Q3_K (domyślny).
  - To samo dla epilogu bias/residual, po poprawce `bias_only`.
  - Kontrola: domyślny kernel N=1 różni się (Q4_K 2/2, Q5_K 2/2, IQ4_XS 1/1 słów).
  - Fuzja SwiGLU N=1 różni się od ścieżki multi (0/4, 0/20), stąd jej wyłączenie.
  - Wyniki w `~/wt/bx-isa/mmvqemu_result.txt`.
- **`gdnseq.py`:**
  - Sekwencja plain (GDN K=1, token po tokenie) i sekwencja LAG (weryfikacje 3, 5 i 1 token z replay zaakceptowanych wierszy) dają identyczne DAG dla wszystkich 36 wyjść attention oraz stanów po replay.
  - Kontrola negatywna (inny kernel l2) wykrywa różnice.
- **Niezweryfikowane offline:**
  - per-kolumnowa niezależność WMMA w FA [INFERENCE];
  - alpha/beta `gdn_conv_ab<n>` (`gdnab.py` nie dokończony: emulator się wysypuje, KeyError przy n=1);
  - kernel combine FA;
  - zgodność producentów q8 vs `quantize_q8_1` (deklarowana w NOTES jako bitowa).

## 7. Plan testów GPU

```bash
cd ~/wt/batchinv && flock -s /tmp/quiet.lock nice -n 10 cmake --build build-hip -j6 --target llama-server llama-bench test-backend-ops
B=~/wt/batchinv/build-hip/bin
# 1. poprawność względem CPU, oba tryby
$B/test-backend-ops -o MUL_MAT; $B/test-backend-ops -o FLASH_ATTN_EXT; $B/test-backend-ops -o GATED_DELTA_NET
LLAMA_SPEC_BITEXACT=1 $B/test-backend-ops -o MUL_MAT; LLAMA_SPEC_BITEXACT=1 $B/test-backend-ops -o FLASH_ATTN_EXT
# 2. domyślny tryb = baza (md5 jak build ~/wt/rebase070/build-hip na tym samym drzewie)
~/KERNEL/qwen-opt/greedy_check.sh $B $B /tmp/bx_def
# 3. cel: plain == MTP
LLAMA_SPEC_BITEXACT=1 ~/KERNEL/qwen-opt/greedy_check.sh $B $B /tmp/bx_on   # md5 plain == md5 mtp (dflash też)
#    + n_max 2..7, długie prompty (long_ctx_bench, T=0: 6.6k/29.5k/94k), prompt o długości 512k+1..+7
# 4. determinizm serwera: det_probe.py na serwerze MTP (z pending_h fix) i plain, oba tryby
# 5. szybkość, przeplatane ABBA vs ~/llama-opt:
$B/llama-bench -m ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf -fa 1 -ctk q4_0 -ctv q4_0 -n 128 -p 0 -r 5            # N=1, env 0/1
$B/llama-bench ... -p 5 -n 0 -ub 5 -d 0,32768,98304 -r 10                                                    # forward N=5 (FA), env 0/1
~/KERNEL/qwen-opt/spec_sweep.py qwen mtp (6 promptów x 3 seedy)   # env 0/1, oczekiwane MTP t/s bez zmian
```

Kryterium przyjęcia: w trybie bitexact md5 plain == md5 MTP (nowa wspólna wartość, różna od `c4708318`), dla n_max 1..7 i kontekstów do 94k. MTP t/s ≥ 99% bazy.

## 8. Osobne źródło: rozjazd kolejnych requestów na tym samym serwerze

Najmocniejszy kandydat dotyczy tylko MTP. `pending_h` (common/speculative.cpp:1665, 1781) jest zerowane tylko w konstruktorze. Pierwszy token nowego requestu (pozycja 0) dostaje więc ukryty stan z końca poprzedniego requestu (:1896-1898), a pierwszy request po starcie dostaje h=0. W efekcie różnią się drafty, szerokości weryfikacji N i, przy niezmienniczości złamanej względem N, również tekst. `det_probe` uruchamiano na `run-llm.sh qwen` (domyślnie MTP), co jest spójne z tym, że upstream zachowuje się tak samo [INFERENCE].

Poprawka w worktree: zerowanie dla `pos==0`. Przy bitexact tekst nie zależy od draftów nawet bez niej.

GPU: uruchomić `det_probe` na serwerze plain. Jeśli wynik jest identyczny, przyczyna jest potwierdzona.
