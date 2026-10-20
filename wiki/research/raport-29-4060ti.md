---
typ: research
tags: [research, nvidia, rtx-4060-ti, wyniki]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/29-4060ti.md:7-21,87-89,104-108,113-116
status: aktualne
---
# Raport 29: RTX 4060 Ti 16 GB – przed/po (Qwen Q3_K_XL, LFM QAD-Q4_0)

**Na 4060 Ti (100 W, PCIe gen3 x8) topka `cuda-topka2` daje Qwen czat T=1 35.4 t/s (×1.90 vs gołe upstream, ×1.16 vs upstream z MTP), code-edit 170.9 t/s i LFM 149.4 t/s (×1.31); bramka GPU verify 22/22 md5 przeszła na sm_89 (2026-10-20).**

- Zysk T nad U1 to krótszy krok (81.6 vs 97.7 ms), nie więcej tokenów na krok (2.88 vs 2.99) (`29:9-11`).
- Pomiar na GPU serwera buildów Vast (~$0.37), harness nv-final z raportu 27, ABBA na świeżych serwerach (`29:3-5,113`).
- `rbuild` na współdzielonym hoście: `make -l $(nproc)` przy load ~32 innych kontenerów dławi build do 1 zadania – build bezpośredni sm_89 trwał 17 min (`29:104-105`).
- GPU verify przyspiesza krok o ~4% (orientacyjnie) (`29:88`).
- Karta: [[rtx-4060-ti]]; rekordy w [[REKORDY]] (nie w produkcji).

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[rtx-4060-ti]]
- [[raport-27-3090-final]]
- [[REKORDY]]
