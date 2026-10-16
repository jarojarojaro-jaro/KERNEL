---
typ: nvidia
tags: [nvidia, nvfp4, kwantyzacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/hardware/rx-7900-xtx.md:38,42; ~/KERNEL/product/research/01-konkurencja.md:330; ~/KERNEL/qwen-opt/patches/llama.cpp-amd-opt/0004-*.patch:144, 0012-*.patch:120, 0024-*.patch:179; ~/KERNEL/qwen-opt/research/v2/roadmap.md:246; ~/KERNEL/qwen-opt/research/v2/rr-engines-drafters.md:355; ~/KERNEL/qwen-opt/research/repos/22-lucebox.md:76
status: aktualne
---
# NVFP4 (4-bitowy format NVIDIA)

**NVFP4 to 4-bitowy format liczb NVIDIA, sprzętowo liczony od Blackwella (np. RTX 5060 Ti); RX 7900 XTX nie ma FP4/FP8, a my go nie używamy, bo zmienia model.**

Gdzie się pojawia:
- **Sprzęt:** 5060 Ti (sm_120) ma tensor core'y 5. generacji z FP8 i FP4 (NVFP4/MXFP4); gfx1100 nie ma FP8/FP4 w WMMA.
- **Upstream llama.cpp:** ścieżki NVFP4 w MMVQ (fuzja skali tylko dla NVFP4); NVIDIA wnosi przyspieszenia, w tym NVFP4 MMQ (raport 01). Nasze łatki 0012/0024 zostawiają warunki NVFP4 bez zmian, a 0004 (słownik draftu) wprost nie obsługuje skalowanych głowic NVFP4.
- **Silniki konkurencji:** TensorFold i Strata mają ścieżki NVFP4 (np. Strata: eksperci NVFP4 w decode bitowo identyczni, 1.14–2.5×; TensorFold czyta checkpointy NVFP4).
- **Drafty:** repaki głowic MTP/DFlash w NVFP4 (np. DSpark NVFP4) w naszym przeglądzie: bez zysku albo inny sprzęt.

Decyzja techniczna (roadmap v2): zmiana kwantu trunku dla prędkości (IQ4_XS, NVFP4) zmienia model wyjściowy, więc jest poza ograniczeniem „bezstratnie”. Lucebox: megakernel NVFP4 dla RDNA3 „bez sensu” (brak FP4).

## Powiązane
- [[nvidia/_hub|NVIDIA]]
- [[sm-86-89-120]]
- [[kwanty-gguf]]
- [[rtx-5060-ti]]
- tensorfold
