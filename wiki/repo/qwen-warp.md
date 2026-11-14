---
typ: repo
tags: [repo, dlugi-kontekst, rtx-3090, kv]
aktualizacja: 2026-11-09
zrodlo: ~/KERNEL/product/research/63a-silniki-lokalne.md:24-26,389-407,471-487; https://github.com/tuan3w/qwen-warp (`146a654`, 2026-11-05; `689901c` v0.8.0, 2026-11-07); ~/KERNEL/product/research/69b-tensorfold-qwen-warp.md:7-8,15-38,73-77; qwen-opt/cloud/nv69q/summary.txt (pomiar 2026-11-09)
status: aktualne
---
# qwen-warp (tuan3w): 262k na jednej RTX 3090

**Graf CUDA z fuzjami W4A16 (Swift-1.5 INT4), MTP k ≤ 3 + ogon prompt-lookup; decode 124 / 115 / 102 / 94 t/s przy 32k / 100k / 190k / 262k (2026-11-05).**

- Po przeskalowaniu pasma (×1.026) ~105 / 96 t/s wobec naszych 74.5 przy 199k: najmocniejszy dowód zapasu przy ≥ 100k.
- Lekcja z ich portu: atencja w weryfikacji była 15–20% wolniejsza przy 190k, bo dekwantyzowała ten sam kafel KV raz na kafel zapytań; naprawa = raz na grupę. To nasz otwarty punkt w [[fattn-kvq]] (dwa przejścia po KV przy 30 kolumnach).
- KV 4-bit z rotacją WHT i dokładnym pierścieniem fp16 (4 sinki + 256 ostatnich): tool-call 46 → 92–96%. Zmienia numerykę KV, więc u nas odrzucone ([[2026-11-05-tylko-bezstratne]]).
- Akcja bezstratna: jedno przejście KV na weryfikację, oczekiwane +5…15% przy 94–199k `[SZACUNEK]`.

## Delta v0.6.0 → v0.8.0 (`689901c`, 2026-11-07, raport 69b)
- **DFlash2 w silniku** (`incoai/Qwen3.8-27B-DFlash2`, W4A16, 1.15–1.4 GiB): cały cykl w jednym grafie CUDA, 21.0 ms (verify T=8 + accept 18.6 ms, drafter 2.50 ms), 4.48 tok/cykl wobec 2.98 dla MTP k=3. Serwer, KV bf16, 3090 350 W, zachłannie: kod 183.9 → 276.7 t/s (×1.51), czat ×1.34, 12 zadań ×1.07, proza ×0.96; **tury agenta z kopiowaniem −31%** (230 vs 334 t/s) – zgodne z [[lekcja-benchmark-kopia]]. KV draftera 20 KiB/token bez pierścienia: maks. ~125k, 262k na 24 GB się nie mieści.
- **Multiuser:** GEMV W4 z dwoma kaflami n8 (16 wierszy na przejście po wagach), 5 slotów: 154 / 278 / 425 / 441 t/s przy 1/2/4/8 klientach.
- Długi kontekst (94–133 t/s przy 32k–262k) bez zmian. Zasilanie: tylko limit 350 W, nic do przeniesienia.
- Dla Enigmy 3090: najmocniejszy publiczny punkt odniesienia.

## Pomiar na wynajętym 3090 (2026-11-09, [[2026-11-09-qwen-warp-vs-fork-3090]])
- Ta sama karta (350 W), te same 6 promptów, ten sam klient streamingowy, oba silniki przy 262 144. T=0 / T=1: 16k 114.0 / 121.0 wobec forka 76.8 / 66.7; 64k ×1.58 / ×1.59; 128k ×1.60 / ×1.65; 262k 68.3 / 68.6 wobec 51.1 / 45.1 (×1.34 / ×1.52). Kill (< ×1.15) nie zachodzi, temat portu zostaje.
- Około ×1.24 to lżejsze wagi (W4 g128 wobec UD-Q4_K_XL) `[SZACUNEK]`. Reszta to dokładne próbkowanie spekulacyjne przy T=1 (fork traci tam 7–13%, warp nie), GEMV W4 na rdzeniach tensorowych i cykl w jednym grafie.
- Deklaracje vendora na naszych promptach: „155 czat” to 117–128, a „94 przy 262k” to 68 t/s. Oba silniki mieszczą 262 144 na 24 GB.

## Powiązane
- [[repo/_hub|repo]]
- [[fattn-kvq]]
- [[qwen-qsa-llama-cpp]]
- [[raport-63-synteza]]
- [[final-recipes-nvidia]]
