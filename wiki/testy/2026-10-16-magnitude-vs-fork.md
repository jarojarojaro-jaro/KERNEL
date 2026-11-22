---
typ: test
tags: [testy, konkurencja, nvidia, spekulacja]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/16d-magnitude-vs-nasz.md:5-117,140-157; ~/qwen-opt/cloud/results/magnitude-vs-3090-20261016/x/xbench.jsonl; ~/qwen-opt/cloud/results/magnitude-vs-5060ti-20261016/x/xbench.jsonl; ~/KERNEL/product/research/16d-magnitude-vs-nasz.md:1-176
status: aktualne
model: qwen3-8-27b
karta: rtx-3090
wyniki:
  - qwen3-8-27b | rtx-3090 | 65.7 t/s | sweep T=1 fork; cuda-3090-opt (Magnitude 65.7, upstream 49.2) | 2026-10-16
  - qwen3-8-27b | rtx-3090 | 105.2 t/s | code-edit fork; (Magnitude 156.1) | 2026-10-16
  - qwen3-8-27b | rtx-3090 | 888 t/s | prefill 64k fork; (Magnitude 744) | 2026-10-16
  - lfm2-5-24b-a2b | rtx-3090 | 291.6 t/s | sweep fork; (Magnitude 209.0) | 2026-10-16
  - lfm2-5-24b-a2b | rtx-5060-ti | 205.1 t/s | sweep 32k fork; (Magnitude 157.8) | 2026-10-16
  - qwen3-8-27b | rtx-5060-ti | 58.0 t/s | sweep fork; Q3_K_XL (upstream 43.5) | 2026-10-16
---
# 2026-10-16: X1 – Magnitude vs nasz fork vs upstream (3090, 5060 Ti)

**Kill X1 nie zadziałał: bez draftera (LFM) nasz fork bije Magnitude o +40% (3090) i +30% (5060 Ti), na Qwenie przy nowym pisaniu jest remis 65.7 = 65.7 t/s, a na kopii i edycji kodu wygrywa Magnitude drafterem DFlash2 (156.1 vs 105.2 t/s).**

Warunki: Magnitude `954d677d` (cli 0.2.9), fork `cuda-3090-opt` / `cuda-v070-5060ti`, upstream v0.7.0; te same GGUF; ABBA na świeżych serwerach (Magnitude Qwen 3090: 1 runda); rozrzut rund ≤ 2.4%; koszt ≈ $1.5.

| karta / model | klasa | Magnitude | fork | upstream |
|---|---|---|---|---|
| 3090 Qwen3.8-27B | sweep T=1 | 65.7 | 65.7 | 49.2 |
| 〃 | copy 64k | 80.2 | 69.3 | 58.6 |
| 〃 | code-edit | 156.1 | 105.2 | 78.7 |
| 〃 | prefill 64k / TTFT 2k | 744 t/s / 2.04 s | 888 / 1.68 s | 887 / 1.64 s |
| 3090 LFM2.5-24B | sweep / code-edit | 209.0 / 216.9 | 291.6 / 280.4 | 216.6 / 212.7 |
| 5060 Ti LFM (32k) | sweep / code-edit | 157.8 / 161.6 | 205.1 / 199.9 | 153.4 / 150.4 |
| 5060 Ti Qwen 27B Q3_K_XL | sweep | nie ładuje się | 58.0 | 43.5 |

Fork + DFlash2 na 3090: sweep 49.0, copy 94.0, code 121.1 t/s (DFlash2 u nas 64.0 vs 47.6 ms/krok u Magnitude). VRAM Qwen: 22.2 vs 19.6 GB.

**Qwen3.5-9B na 5060 Ti** (1 runda, bez upstreamu): sweep 68.2 vs 121.0 t/s; pl-proza 1.00 vs 1.71 tok/krok; copy 64k 175.8 vs 128.1; code-edit 376.7 vs 239.0; prefill 64k 2053 vs 2343 t/s (31.1 vs 27.3 s).

## Ze scalonej notatki: Raport 16d: Magnitude vs nasz fork vs upstream (X1 z 15c) + KLD Nemotrona

Head-to-head na 3090 i 5060 Ti: przewaga naszych kerneli na NVIDIA bez draftera +30–40% i w prefillu +18–35%, a słabością są głębokie drafty – Magnitude wygrywa kopią/edycją kodu dzięki DFlash2 (7.3–7.8 tok/krok vs sufit 5 MTP n=4).

- Wyniki: [[2026-10-16-magnitude-vs-fork]]. Luki Magnitude: [[magnitude]]. Mechanizmy: [[raport-16i-magnitude]].
- Harness Magnitude (prose-repeat 64k) liczy dekod 121.3 t/s, choć ich `timings` dają 80 `[INFERENCE: część pracy liczona jako TTFT]`; fork 71.5, upstream 58.5.
- Jakość: KLD Magnitude niemierzalne (brak logitów w API); proxy – prefiks/ratio kopii identyczne dla wszystkich silników.
- Wniosek dla planu: kandydaci – tańsza weryfikacja 16 tokenów, adaptacyjna głębokość, spec-copy/n-gram; raporty publiczne zawsze rozdzielają kopię i nowe pisanie.
- KLD Nemotrona `TOPK_MOE_NP2`: PASS ([[2026-10-16-nemotron-3090]]).

## Powiązane
- [[magnitude]]
- [[ekosystem/magnitude]]
- [[2026-10-16-magnitude-rozklad-wygranej]]
- [[testy/2026-10-16-magnitude-vs-fork]]
- [[lekcja-drafter-gleboki-vs-mtp]]
