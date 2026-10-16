---
typ: repo
tags: [repo, amd, pm4, dflash]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/30-hipfire.md:1-40; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:40
status: aktualne
---
# Kaden-Schutt/hipfire

**Silnik inferencji Rust + HIP tylko pod AMD (HEAD `1ff5182`, 2026-10-14, v0.4.2) z replayem tokenu jako bufor PM4; werdykt: średnia–wysoka.**

Własny format wag MQ4G256V2 (4.25 bpw, rotacja FWHT), warstwa „Redline” odtwarzająca nagrany token jako bufor PM4 przez kolejkę ROCr, toolchain ISA „PeaceMaker”. Ich pomiar na 7900 XTX: MoE 35B-A3B 219.6 → 251.8 t/s przy 603 kernelach/token; Qwen3.8-27B MTP 76.4 t/s (u nas 104 t/s), DFlash kod 307.9 t/s na jednym krótkim prompcie (τ≈13), prefill ~3000 t/s pp8192 (W4A4, stratny). Inspiracja L1 (replay tokenu, szacunek +10–30% LFM) i naszego PM4 replay w rundzie 4.

## Powiązane
- [[repo/_hub|repo]]
- [[lucebox]]
- [[cuda-rust]]
- [[pm4-replay]]
- [[repos-30-przeglad]]
