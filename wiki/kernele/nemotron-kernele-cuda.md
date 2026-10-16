---
typ: kernel
tags: [kernele, cuda, moe, iq2]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/14-nemotron-3090.md:104-150,201; git -C ~/llama-master log -1 e46d34e0e
status: aktualne
---
# Łatki CUDA dla Nemotron 3.5 Bolt: TOPK_MOE_NP2, MMVQ_N1_IQ2, IQ2_LUT

**Trzy przełączniki z gałęzi `nemotron-3090`: fuzja topk-moe dla nietypowych liczb ekspertów (−280 kerneli/token, zmienia bity), IQ2_XXS w ścieżce 2 wierszy na blok (bitowo neutralna) i LUT siatki IQ2 w pamięci współdzielonej (wynik negatywny).**

| przełącznik | domyślnie | co robi | efekt |
|---|---|---|---|
| `GGML_CUDA_TOPK_MOE_NP2` | on | fuzja topk-moe dla 240/304/368/432/496 ekspertów: ceil(n/32) slotów na lane, ogon maskowany do −INF; zastępuje 9 kerneli na warstwę MoE | −280 kerneli/token, rozpiętość −0.99 ms/token; **zmienia bity** (`=0` przywraca md5 forka) |
| `GGML_CUDA_MMVQ_N1_IQ2` | on | IQ2_XXS dołącza do 2 wierszy na blok na sm_80–87 | bitowo neutralna |
| `GGML_CUDA_IQ2_LUT` | opt-in | kopia `iq2xxs_grid` w shared memory | tg128 96.7 → 94.4 (−2.4%) – **wynik negatywny** |

Łącznie (llama-bench ABBA ×2): tg128 91.1 → 96.7 (+6.1%), pp6 263 → 269. Rekomendacja: `TOPK_MOE_NP2` i `N1_IQ2` do manifestu z predykatem „nemotron_h_moe / IQ2_XXS”, przed produktem KLD dla `TOPK_MOE_NP2`. Kandydaci niezrobieni: szybsze MMVQ IQ2_XXS (wciąż 320–400 GB/s), FA vec dla KV q8_0 przy GQA 16:1, replay zamiast snapshotów stanu Mamby, szybszy `topk_moe_cuda` (8.4 µs/wywołanie).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[mmvq-n1-wiersze]]
- [[fuzje-lfm-moe]]
- [[nemotron-3-5-bolt-74b-a9b]]
- [[latki-na-nvidia]]
- [[nemotron-3090]]
