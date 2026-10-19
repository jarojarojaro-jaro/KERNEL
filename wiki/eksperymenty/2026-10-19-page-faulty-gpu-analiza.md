---
typ: eksperyment
tags: [eksperymenty, pm4, awarie, rdna3]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:6-61,104-130,184-193; journalctl -k -b -2/-1/0; ~/qwen-opt/coupled/logs*/; ~/KERNEL/product/research/17-gpu-page-fault.md:216-247
status: do-sprawdzenia
---
# 2026-10-16/19: page faulty GPU i 10 resetów XTX (analiza bez GPU)

**10 resetów w 3 bootach: 2 z jawnych eksperymentów (`pdl` R0 16.10 15:30:52, `GGML_HIP_PM4_UB` 18.10 19:56:24), 8 to ta sama awaria produkcyjnej ścieżki replayu PM4 w `llama-server` Qwen MTP – SQC(data) @0, `STATUS 0x00801431`, `sq_intr type 2` (MEMVIOL) `priv 0`, po ~110–130 ms „MES failed to response msg=3” i mode1 reset.**

| # | czas (UTC) | proces | kontekst |
|---|---|---|---|
| R1 | 16.10 15:30:52 | `pdl` | X1 wariant R0, zawieszony IB (eksperyment) |
| R2 | 16.10 15:35:06 | `llama-server` (lookup) | równolegle `validate.sh` bez blokady GPU |
| R3, R4, R6 | 18.10 19:47, 19:56, 20:14 | `llama-server` (coupled) | tryby 0 / 2 / 1, request 36, 33, 50 |
| R5 | 18.10 19:56:24 | `llama-bench` | `PM4_UB` bez synchronizacji (eksperyment) |
| R7–R10 | 22:42, 22:57, 23:25, 19.10 00:16 | `llama-server` (coupled) | tryby 0 / 0 / 1 / 0, request 74, 53, 77, 158 |

- Fault przychodzi 0.57–3.20 s po starcie requestu, a „tape of 823 dispatches did not complete within 10 s” dopiero ~10 s później – timeout jest skutkiem ([[lekcja-timeout-tasmy-to-skutek]]).
- E-X4: 7 resetów na 2338 requestów (~1/330), 0 w 901 slotach przed zapełnieniem `--cache-ram` 16 GiB, 7 w 1410 później (~1/200).
- Hipotezy: **H1 (~60%)** wywłaszczenie kolejki KFD w środku IB gubi rejestry SH → `USER_DATA` = 0 → wskaźnik kernargów 0 (w bootach widać `restore_userptr_worker` 64×, `svm_range_restore_work` kończące się 156 ms po R9); H2 (~20%) uszkodzenie kernargów w VRAM; H3 (~10%) uszkodzenie IB w RAM; H4 (~10%) inne. Wszystko `[INFERENCE]`.
- Korekty: R9 to tryb 1 i nie wynikał z kolizji blokad ([[lekcja-nie-odtwarzac-lockow]]); alarmy „serwer na 8080” były fałszywe ([[lekcja-pgrep-f-lapie-powloki]]).
- Produkcja zagrożona: `~/llama-opt` ma PM4 domyślnie i te same flagi; reset zabija serwer użytkownika i zeruje krzywą wentylatora. Plan testu i decyzja: [[raport-17-gpu-page-fault]], [[otwarte-decyzje-techniczne]].

Ciąg dalszy (§9): [[2026-10-19-pm4-priv-analiza]] – kandydat H1′ (PRIV=0 + ewikcja SVM).

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[pm4-replay]]
- [[dekodowanie-page-fault-amdgpu]]
- [[lekcja-pm4-zamienia-fault-w-reset]]
- [[2026-10-18-sprzezone-probkowanie-mtp]]
