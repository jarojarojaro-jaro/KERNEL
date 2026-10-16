---
typ: rocm
tags: [rocm, amd-smi, telemetria]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/13-rocm-10.1.md:25,63-71,264-284; ~/KERNEL/qwen-opt/NOTES.md:116; amd-smi version (odczyt 2026-10-16)
status: aktualne
---
# AMD SMI (amd-smi)

**Narzędzie i biblioteka AMD do telemetrii i sterowania GPU (moc, zegary, perf-level); w ROCm zastąpiło rocm-smi, działa na Linuksie, natywnego Windows brak.**

U nas: `/usr/bin/amd-smi`, AMDSMI Tool 27.0.0, ROCm 10.0.0 (odczyt 2026-10-16). W 10.1: AMD SMI 27.1.0, ROCm SMI usunięty ze standardowego buildu TheRock.

Zastosowania w projekcie:
- odczyt mocy przy pomiarach: `amd-smi metric -p` (plan pomiaru limitu mocy w NOTES);
- przed profilowaniem liczników na gfx11: `amd-smi set -g 0 --perf-level STABLE_STD`, potem `AUTO` (wymaga sudo; raport 13 podejrzewa, że brak tego daje PMC = 0);
- poziomy perf-level w 10.0: `AUTO, LOW, HIGH, MANUAL, STABLE_STD, STABLE_PEAK, …, DETERMINISM`.

Dla produktu (raport 13 §7): biblioteka MIT, `libamd_smi.so.27.1.0` 5.3 MB. Na Linuksie inwentarz bez admina dalej z sysfs/DRM, a AMD SMI tylko jako opcjonalny `dlopen`. Natywnego, redystrybuowalnego AMD SMI dla Windows nie ma (TheRock: amdsmi „Unsupported”); jest eksperymentalny backend WSL. Na crates.io crate `amdsmi` jest cudzym wrapperem, nie AMD.

## Powiązane
- [[rocm/_hub|ROCm]]
- [[rocprof]]
- [[amdgpu-moc-i-termika]]
- raport-04-sprzet
- [[rocm-10-1]]
