---
typ: lekcja
tags: [lekcje, chmura, cpu, watki]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/09-chmura-5060ti.md:16,19; ~/KERNEL/product/research/09-chmura-3090.md:18; ~/KERNEL/product/research/11-mtp-pl-pilot.md:171-174
status: aktualne
---
# Kontener widzi wszystkie rdzenie hosta, a ma limit cgroup

**W kontenerach Vast i RunPod `nproc` pokazuje wszystkie wątki hosta (64 albo 96), a limit cgroup to ok. 7.7 CPU; llama.cpp bez `-t` bierze za dużo wątków i dławi się na kwocie.**

- RTX 5060 Ti (Vast): `nproc` = 64, limit CFS 7.68 CPU; llama.cpp bez `-t` bierze 32 wątki → wszystkie konfiguracje A1+ z `-t 8`.
- RTX 3090 (Vast): 8 vCPU, kwota cgroup 7.68.
- RunPod A40 (pilot MTP): `llama-server` domyślnie bierze `nproc` = 96 wątków przy limicie 7.65 CPU → trzeba `-t 6 -tb 6`; build CUDA trwał tam 30 min.
Reguła: na wynajętej maszynie odczytać kwotę cgroup (`/sys/fs/cgroup/cpu.max`) i ustawić `-t`/`-tb` według niej, nie według `nproc`. To samo dotyczy produktu w kontenerach i WSL.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-fit-mtp-16gb]]
- [[lekcja-obciazenie-cpu]]
- [[lekcja-slaby-cpu-3090]]
- [[skrypty-chmury]]
