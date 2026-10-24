---
typ: repo
tags: [repo, apple, mlx, spekulacja, mtp]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60b-apple-engines-bonsai.md:3.1-3.2; https://github.com/jundot/omlx/releases/tag/v0.7.2; ~/qwen-opt/research/omlx (c4bb311e) omlx/patches/mlx_lm_mtp/batch_policy.py, commit 8a9b1972
status: aktualne
---
# oMLX (jundot/omlx)

**Serwer MLX na Maca z „Lightning MTP” (natywne MTP głębokości k z adaptacyjną głębokością z pomiaru), DFlash, Splash dla GGUF i klastrem Maców; dla Qwen3.8-27B na XTX bez nowej techniki (raport 60b).**

- Lightning MTP (commit `8a9b1972`, 2026-07-08): łańcuch draft/verify, jedna synchronizacja hosta na cykl, akceptacja zachowująca rozkład, kernele qmm pod kształt weryfikacji z MTPLX. M3 Ultra greedy: Qwen3.6-27B 42.8 → 55.1 tok/s.
- `BatchPolicy`: głębokość z mierzonego czasu całego wywołania vs zwykły dekod; MTP „parkowane”, gdy 4× z rzędu < 0.9 tokenów/ms dekodu.
- Cofanie GDN: snapshot `(conv, ssm)` między prefiksem a draftem + przeliczenie prefiksu.
- 0.7.2 (2026-10-21): MTP przy PP/TP między Macami (GLM-5.3 TP 13.7 → 27.7 tok/s), CED DeepSeek V4.1 (Causal Encoder-Decoder: pół dekodera w prefillu liczy tylko ogon okna), Splash 1.4.0 z Qwen3.8-Flash-Next GGUF + DFlash2, poprawka cache dla Claude Code (#4712).
- Apache-2.0; w compwatch (B).

## Powiązane
- [[repo/_hub|repo]]
- [[locals]]
- [[bonsai-fast-contest]]
- [[raport-24q-adaptacyjna-spekulacja]]
- [[raport-60b-apple-bonsai]]
