---
typ: eksperyment
tags: [eksperymenty, mtp, trening]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/mtp-train/RESULTS.md:1-44,68-127
status: aktualne
---
# 2026-10-12: trening głowicy MTP — faza 1 (wykonalność)

**Sprawdziliśmy, czy samodestylacja głowicy MTP ma sens: dane, ekstraktor i lustro PyTorch działają, a pomiar akceptacji wskazuje +5–11% tok/krok; rekomendacja GO dla pilota 2 M tokenów.**

Cel: Qwen3.8-27B-UD-Q4_K_XL z głowicą `blk.64`, ustawienia jak w `run-llm.sh qwen mtp rocm`; fork `amd-opt` @ c90db29c6.

Ustalenia:
- PyTorch 2.14.1+rocm7.14 na gfx1100: matmul 4096² bf16 71 TFLOP/s, fp16 74 TFLOP/s.
- Dane: 57 promptów (27 PL, 30 EN), 69 207 tokenów odpowiedzi, generowanie 107–127 t/s (`-np 4` + MTP).
- Ekstraktor `mtp_extract.cpp`: 2.3 ms/token przejście celu + 3.7 ms na łańcuch draftu; cała próbka 7.4 min.
- Lustro PyTorch vs llama.cpp: zgodność top-1 98.4%, łańcuch draftu d1–d4 99.6 / 99.0 / 98.2 / 97.3%.
- Akceptacja głowicy: 3.04 tok/krok (wyrocznia 3.93); brak luki PL, jest luka głębokości.
- Trening (zmierzony): rekurencyjny K=4, T=2048, bf16 — 2.3 k tokenów/s, szczyt 12.1 GiB; pilot 2 M × 3 epoki ≈ 45–60 min.

Plan pilota: ~1.7 k promptów → 2 M tokenów (40% PL, 35% EN, 25% kod/tech), łącznie ≈ 8–9 h (głównie generowanie 5.3 h). Gałąź `mtp-train` (2026-10-16) dodała narzędzie `llama-mtp-extract`; w repo KERNEL nie ma jeszcze wyników pilota (stan 2026-10-16).

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[glowica-mtp]]
- raport-10-post-training
- [[2026-10-10-sweep-mtp-dflash]]
- [[mtp-draft-graf]]
