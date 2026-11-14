---
typ: repo
tags: [repo, amd, pm4, dflash]
aktualizacja: 2026-11-14
zrodlo: ~/KERNEL/qwen-opt/research/repos/30-hipfire.md:1-40; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:40; ~/KERNEL/product/research/23e-re-silniki.md:8-17
status: aktualne
---
# Kaden-Schutt/hipfire

**Silnik inferencji Rust + HIP tylko pod AMD (HEAD `1ff5182`, 2026-10-14, v0.4.2) z replayem tokenu jako bufor PM4; werdykt: średnia–wysoka.**

Własny format wag MQ4G256V2 (4.25 bpw, rotacja FWHT), warstwa „Redline” odtwarzająca nagrany token jako bufor PM4 przez kolejkę ROCr, toolchain ISA „PeaceMaker”. Ich pomiar na 7900 XTX: MoE 35B-A3B 219.6 → 251.8 t/s przy 603 kernelach/token; Qwen3.8-27B MTP 76.4 t/s (u nas 104 t/s), DFlash kod 307.9 t/s na jednym krótkim prompcie (τ≈13), prefill ~3000 t/s pp8192 (W4A4, stratny). Inspiracja L1 (replay tokenu, szacunek +10–30% LFM) i naszego PM4 replay w rundzie 4.

RE (23e, 2026-10-19): na XTX plain 27B 54.3 t/s (krok 19.67 ms) vs nasze 43.2 t/s (23.15 ms); różnica ~2.7 ms z bajtów (14.3 vs 16.83 GB/token, 4.25 bpw) i ~0.8 ms z fuzji – nie z ISA (ich GEMV 138 VALU vs nasze 61 na 32 wagi/lane, 76 VGPR, 16 fal); stan GDN w int8 ([[raport-23e-re-silniki]]).

- **Delta v0.4.4–v0.4.6 (2026-10-27…11-11, zwiad 2026-11-14):** na XTX int8 verify GEMV 2–5 wierszy (#987, decode +14…23%) i WMMA split-K verify attention (#989, przy 32k +24…27%), słownik draftu MTP 65 536 (#998, +7…9%). Wszystkie numeryczne (bramka KLD). 27B MTP code-1k 127,4 / prose-1k 131,1 t/s, czyli parytet z topką przy krótkim kontekście ([[zwiad-2026-11-14]]).

## Powiązane
- [[repo/_hub|repo]]
- [[lucebox]]
- [[cuda-rust]]
- [[pm4-replay]]
- [[repos-30-przeglad]]
