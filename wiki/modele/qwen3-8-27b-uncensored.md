---
typ: model
tags: [modele, qwen, uncensored]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/sources/qwen3.8-27b.md:34-40; ~/KERNEL/qwen-opt/STATUS-NEXT.md:11; ~/KERNEL/qwen-opt/run-llm.sh:8; ~/KERNEL/qwen-opt/README.md:52; ~/KERNEL/qwen-opt/research/v2/rr-engines-drafters.md:180; ls ~/models (2026-10-16); ~/KERNEL/product/research/21e-kv-miedzy-modelami.md:96-104
status: aktualne
---
# Qwen3.8-27B-Uncensored (OrcaRouter)

**Abliterowana wersja Qwen3.8-27B od OrcaRouter: usunięty „kierunek odmowy”, architektura bez zmian; u nas najszybszy wariant Qwena (115.5 t/s).**

- Repo `orcarouter/Qwen3.8-27B-Uncensored-GGUF` (Apache 2.0; repo HF bramkowane, ten sam plik jest w rejestrze Ollama `orcarouter/qwen3.8-27b-uncensored:q4_K_M`).
- Plik: `~/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf` (15.66 GiB) + `mmproj-…-f16.gguf` (0.87 GiB); `VISION=1` w `run-llm.sh` dokłada mmproj.
- Głowica MTP w tym pliku jest w Q4_K (UD ma Q6_K/Q8_0) — fakt z parsowania GGUF (rr-engines-drafters).
- Wyniki (2026-10-15, spec_sweep 6×3, T=1, MTP, KV q4_0): **115.5 t/s**, 26.68 ms/krok, pp4096 1109, tg128 bez spekulacji 44.0.
- Te same kształty tensorów i kernele co bazowy model; abliteracja zwykle lekko pogarsza jakość, OrcaRouter nie podaje miar (KL, benchmarki).

Analiza wag (21e, 2026-10-19): to Qwen3.8-27B z jedną globalną ablacją kierunku we wszystkich writerach (s ≈ 1), F32 i `output.weight` bajtowo identyczne – [[uncensored-ablacja-kierunku]].

## Powiązane
- [[modele/_hub|Modele]]
- [[qwen3-8-27b]]
- orcarouter
- [[stan-2026-10-15]]
- [[kwanty-gguf]]
