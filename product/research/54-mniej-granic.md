# 54. Mniej granic dispatchy w kroku weryfikacji (Qwen3.8-27B, XTX)

Data: 2026-10-21. Agent LaunchCut. Gałąź `launch-cut` (worktree `~/wt/launch-cut`, commit a2800bf81 na topka cf927413b).
Stan: **kod gotowy, NIEZMIERZONY na GPU** (decyzja użytkownika: stop GPU na noc). Jobs na rano:
`~/qwen-opt/launchcut/lc-morning.jobs`.

## 1. Inwentarz (CPU, ślad `klab/traces/now1/off`, PM4=0, 1 krok = 946 dispatchy)

| region | dispatchy | skład |
|---|---|---|
| draft MTP ×4 | 109 | mmvq 32, rms_norm 20, rope_norm 8, fwht 8, set_rows 8, concat 7, quantize 4, FA+combine 8, gate 4, argmax 4, get_rows 4 |
| verify (n=5, 64 warstwy) | 824 | mmvq 340, rms_norm 129, unary_gated (silu 64 + sigmoid 16) 80, gdn_conv_ab 48, GDN 48, norm_silu_gate 48, rope_norm 32, fwht 32, set_rows 32, FA 16, combine 16 |
| MTP update (n=5) | ~13 | norm, concat, quantize, mmvq, rope, set_rows, … |

Warstwa attention (16 verify + 4 draft + 1 MTP = **21/krok**) ma 9 małych launchy wokół 3 mmvq i FA:
`rope_norm_fwht(Q)`, `fwht64(V)`, `rope_norm_fwht(K)`, `set_rows K`, `set_rows V`, FA, `combine`, `fwht64(out)`,
`sigmoid·mul (+q8_1)`. Istniejące fuzje topki (`GGML_HIP_ATTN_PREP`, `GGML_HIP_KVQ_FWHT`) celują w LFM (głowa 64,
q8_0, 1 token, Hadamard = głowa) i dla Qwena (głowa 256, Hadamard V = 64, q4_0, 5 tokenów) się nie dopasowują.

Łańcuchy bez bariery globalnej (koszt granicy z raportu 37: 2.3–4 µs w taśmie PM4):

| fuzja | granic mniej / krok | szac. ms/krok | stan |
|---|---|---|---|
| **A. ATTN_PREP_MT**: q/k norm+rope+FWHT, FWHT64 V, set_rows K+V (5→1) | 4×21 = **84** | 0.19–0.34 | zaimplementowana |
| **B. KVQ_FWHT_GATE**: combine + FWHT64 + sigmoid gate + q8_1 (3→1) | 2×21 = **42** | 0.10–0.17 | zaimplementowana |
| C. prolog MTP: argmax→get_rows→norm, norm, concat, quantize (1 blok) | ~18 | 0.04–0.07 | nie robione |
| D. gdn_conv_ab w GDN (hipfire `dflash_gdn_pre`) | 48 | 0.11–0.19 | nie robione (lag/replay stanu conv) |
| E. silu·mul w mmvq gate/up (wzorzec ticketów, już jest w `mmvq_conv`) | 68 | 0.16–0.27 | nie robione (koliduje z pracami MMVQ) |
| F. sąsiednie mmvq różnych typów w 1 launchu (qkv+z, gate+up) | ~60 | ≤0.2 | nie robione (VGPR = max obu) |

A+B: **−126 dispatchy/krok (13 %) → szac. −0.29…−0.5 ms/krok** (+ krótsze ścieżki: 5 małych kerneli A ≈ 21 µs
pracy w PM4=0 zamienione na 1 launch 160 bloków). [INFERENCE — niezmierzone]

## 2. Implementacja (oba przełączniki domyślnie OFF, `=1` włącza)

- `GGML_HIP_ATTN_PREP_MT` — `rope.cu: attn_prep_mt_f32<ff, N=256, NV=64, block_q4_0|q8_0>`, siatka
  (q_heads + k_heads + v_heads, n_tokens). Blok q/k = ten sam `rms_norm_mul_rope_f32_rows<256,…,256>` co produkcja
  (pętla kanałów raz, dla tokenu blockIdx.y), k dalej `quantize_f32_q4_0_block` jak `k_set_rows_quant` do wiersza
  `idx[t]`; blok v: warpy 0–3 `fwht_row_warp<64>` jak `fwht_cuda<64>`, bariera, SET_ROWS. Matcher = istniejący
  `ggml_cuda_try_attn_prep` (V/K mmvq liczone przed grupą q do scratch, jak w LFM) + `ggml_cuda_attn_prep_mt_supported`
  + warunek K na offsecie 0. Ścieżka LFM nietknięta (ten sam kernel/warunki).
- `GGML_HIP_KVQ_FWHT_GATE` — `fattn-kvq.cu: flash_attn_kvq_combine_fwht_gate<D, NH=64>`: wiersz jak
  `flash_attn_combine_results` (zapis wyjścia FA), warpy w < D/64 `fwht_row_warp<64>` do wyjścia FWHT, potem każdy lane
  `sigmoid(gate)·fwht` (to samo wyrażenie co `unary_gated_op_kernel<op_sigmoid>`) + `quantize_q8_1_group` w tej samej
  kolejności lane'ów. Matcher `ggml_cuda_try_fa_fwht_gate` (FA → FWHT64 → para SIGMOID+MUL przez `ggml_cuda_can_fuse`,
  kształty, brak nakładania wyjść i bramki), q8_1 dla o-proj przez `ggml_cuda_q8_1_producer_target`.
- Bitowość: każda wartość liczona tym samym kodem/wyrażeniem co zastępowane kernele (te same funkcje device, ta sama
  kolejność redukcji); dowód = md5 on==off (poniżej, rano). Test: `test-backend-ops -o ATTN_PREP`, nowy
  `test_attn_prep_qwen` (n_tokens 1/5, kv 512/2048, q4_0, Hadamard 256/64, bramka sigmoid).
- Build: `rbuild --local ~/wt/launch-cut ggml-hip test-backend-ops` — **kompiluje się** (rc=0, lib nowszy od źródeł).
  `llama-server` budowany w tle przez noc (`nohup rbuild --local ~/wt/launch-cut llama-server`, log `/tmp/lc_build3.log`).

## 3. Zmierzone

Nic na GPU (blokada kolejki: ~13 runnerów, potem stop GPU). Inwentarz §1 — CPU ze śladu.

## 4. Rano — dokładne kroki

1. Jeśli `~/wt/launch-cut/build-hip/bin/llama-server` nie istnieje: `~/qwen-opt/tools/rbuild --local ~/wt/launch-cut`
   (całość; CPU, bez GPU). Sprawdzić kompilację (`tail /tmp/lc_build2.log`).
2. `~/qwen-opt/queue/run-jobs.sh ~/qwen-opt/launchcut/lc-morning.jobs` (jeden plik):
   `lc-tbo` (PM4=0, test-backend-ops ATTN_PREP off i on) → `lc-smoke` (PM4=0, greedy oba on) → `lc-gate`
   (`p100_md5.sh lc54`, PM4 produkcyjne, 4 ramiona: off / MT / GATE / oba, LFM=1) → ABBA `x54-A1,B1,B2,A2` prose+mvs
   seeds 1,2 (A = off, B = oba).
3. Oczekiwane: md5 Qwen c4708318 / 6f14e814 i LFM 894e56e4 we wszystkich ramionach; E0 +1…+1.5 % t/s
   (−0.3…−0.5 ms z ~31 ms/krok). Ślad kontrolny (opcjonalnie `klab trace` z XENV): ~820 dispatchy/krok zamiast 946,
   brak `fwht_cuda`, `set_rows`, `flash_attn_combine_results`, `unary_gated_op<sigmoid>` w warstwach attention.
4. Reguła adopcji: md5 PASS we wszystkich ramionach + ABBA B > A poza rozrzutem A1/A2 → do IntegTopka3 jako
   default-on (zmiana domyślnej wartości w obu matcherach). Pierwszy fault/reset → gałąź stop.
5. Pending: zrzut tensorów on/off (bitowy dowód na poziomie tensora poza md5) — do zrobienia małym harnessem
   ggml (graf `test_attn_prep_qwen`, zapis `out`, `k_cache`, `v_cache`, `cmp`).

## Do bazy wiedzy

| folder | tytuł | treść |
|---|---|---|
| wyniki | Inwentarz dispatchy kroku Qwen MTP | 946/krok: draft 109, verify 824 (mmvq 340, rms_norm 129, unary_gated 80, GDN 3×48, attention 9 małych × 16), MTP update ~13. Warstwa attention: 9 małych launchy, 21 wystąpień/krok (raport 54 §1) |
| metody | Fuzje bez bariery globalnej dla Qwena | ATTN_PREP_MT (5→1, −84/krok) i KVQ_FWHT_GATE (3→1, −42/krok): ten sam kod per element co zastępowane kernele, przełączniki `GGML_HIP_ATTN_PREP_MT`, `GGML_HIP_KVQ_FWHT_GATE` (default off), gałąź `launch-cut` (raport 54 §2) |
| wyniki-negatywne | Fuzje LFM nie łapią Qwena | `GGML_HIP_ATTN_PREP` (głowa 64, q8_0, 1 token) i `GGML_HIP_KVQ_FWHT` (Hadamard = głowa ≤128) nie pasują do Qwena (głowa 256, Hadamard V 64, q4_0, n=5) — stąd osobne fuzje (raport 54 §1) |
| metody | Kolejne kandydaci na cięcie granic | prolog MTP 1-blokowy (~18), conv w GDN (48), silu·mul w mmvq gate/up przez tickety (68), sąsiednie mmvq różnych typów (~60) (raport 54 §1) |
