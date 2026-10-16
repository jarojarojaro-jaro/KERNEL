---
typ: eksperyment
tags: [eksperymenty, fabryka, bramki]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/16h-fabryka-v1.md:38-50,253-262
status: aktualne
---
# 2026-10-16: backtest reguł fabryki na historii (X1 z 15f)

**Reguły fabryki v1 puszczone na prawdziwych danych (tylko CPU): R21 łapie 1/1 incydent (wiersz 15, 5.6 t/s) z 0 fałszywymi alarmami na 194 i 182 wierszach `spec_sweep.jsonl` (wcześniej 5/182 przez podciąg „lfm”); X1 przechodzi.**

| reguła | dane | wynik |
|---|---|---|
| R23 denylista | 70 łatek `amd-opt` | 0/70 odmów |
| R29 HIP poza guardem | `amd-opt`, 283 pliki | 5 trafień, wszystkie 0070 (prawdziwy błąd, `57e0bdfe4`) |
| R29 | `cuda-compat` | 0 |
| R28 PDL bez `pdl_sync` | `amd-opt` | 0053, 0057 (znane) + nowe: `flash_attn_kvq_combine_fwht` (`3a1279f95`) |
| R20 label ≠ binarka | `spec_sweep.jsonl` | 7 labeli z rozrzutem > 1%, np. `DRAFT_N=4 qwen mtp rocm` 28.94–41.74 ms/krok |
| R20 | `fusion/spec_sweep.jsonl` | `r1-base-qwen` 33.15–41.81 |
| R12 roofline w tekście | `15-road-to-65.md` | łapie 1075 i 1138 GB/s, „112% PEAKU” |

`rules test`: 0 rozbieżności na 36 regułach; `ledger verify`: łańcuch OK, 2 wiersze.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[fabryka-cli]]
- [[lekcja-label-to-nie-binarka]]
- [[lekcja-pdl-sm120]]
