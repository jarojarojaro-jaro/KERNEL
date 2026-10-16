---
typ: nvidia
tags: [nvidia, nvfp4, kwantyzacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/hardware/rx-7900-xtx.md:38,42; ~/KERNEL/product/research/01-konkurencja.md:330; ~/KERNEL/qwen-opt/patches/llama.cpp-amd-opt/0004-*.patch:144, 0012-*.patch:120, 0024-*.patch:179; ~/KERNEL/qwen-opt/research/v2/roadmap.md:246; ~/KERNEL/qwen-opt/research/v2/rr-engines-drafters.md:355; ~/KERNEL/qwen-opt/research/repos/22-lucebox.md:76; ~/KERNEL/product/research/09-chmura-5060ti.md:168-188,258-290; ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:41-51,89,186-200,320-332; ~/llama-master/ggml/src/ggml-quants.c:384-417
status: aktualne
---
# NVFP4 (4-bitowy format NVIDIA)

**NVFP4 to 4-bitowy format liczb NVIDIA, sprzętowo liczony od Blackwella (np. RTX 5060 Ti); RX 7900 XTX nie ma FP4/FP8, a my go nie używamy, bo zmienia model.**

Gdzie się pojawia:
- **Sprzęt:** 5060 Ti (sm_120) ma tensor core'y 5. generacji z FP8 i FP4 (NVFP4/MXFP4); gfx1100 nie ma FP8/FP4 w WMMA.
- **Upstream llama.cpp:** ścieżki NVFP4 w MMVQ (fuzja skali tylko dla NVFP4); NVIDIA wnosi przyspieszenia, w tym NVFP4 MMQ (raport 01). Nasze łatki 0012/0024 zostawiają warunki NVFP4 bez zmian, a 0004 (słownik draftu) wprost nie obsługuje skalowanych głowic NVFP4.
- **Silniki konkurencji:** TensorFold i Strata mają ścieżki NVFP4 (np. Strata: eksperci NVFP4 w decode bitowo identyczni, 1.14–2.5×; TensorFold czyta checkpointy NVFP4).
- **Drafty:** repaki głowic MTP/DFlash w NVFP4 (np. DSpark NVFP4) w naszym przeglądzie: bez zysku albo inny sprzęt.

**Pomiar na RTX 5060 Ti (2026-10-16, raport 09):**
- llama.cpp v0.7.0 na sm_120 używa natywnych FP4 tensor core tylko w prefillu (MMQ, ścieżka W4A4); dekod 1 tokenu idzie przez MMVQ (dp4a), więc liczy się tylko liczba bajtów wag.
- Prefill: NVFP4 +65–69% (Qwen, pp512/pp4096 1730 / 1747 t/s) i +71–81% (LFM, 7270 / 7663 t/s) względem K-quantów; decode bez zysku (Qwen NVFP4 14.86 GB jest większy od UD-Q3_K_XL i wolniejszy).
- Jakość (KLD vs Q8_0): Qwen NVFP4-MTP-VERY-LOW 0.0865 vs UD-Q3_K_XL 0.0265; LFM NVFP4 (WhiskyAKM) 1.1826, PPL ×1.857 – praktycznie zepsuty. Nie do produktu.
- Oficjalne checkpointy NVFP4 pod vLLM (`nvidia/Qwen3.8-27B-NVFP4` 21.9 GB) nie mieszczą się w 16 GB; `nvidia/` nie publikuje wariantu LFM2.5.
- Na NVFP4 i Q4_0 nasz fork daje md5 identyczne z upstreamem (niebitowa łatka dotyczy tylko ścieżki K-quantów).

**Raport 15e (2026-10-16):** kwantyzator NVFP4 w ggml nie ma skali globalnej ani imatrix (99.8–100% subnormalnych skal); szczegóły w [[2026-10-16-nvfp4-skala-globalna-sim]]. CSF+QAD NVIDIA dotyczy tylko Flash-Next 96 GiB.

Decyzja techniczna (roadmap v2): zmiana kwantu trunku dla prędkości (IQ4_XS, NVFP4) zmienia model wyjściowy, więc jest poza ograniczeniem „bezstratnie”. Lucebox: megakernel NVFP4 dla RDNA3 „bez sensu” (brak FP4).

## Powiązane
- [[nvidia/_hub|NVIDIA]]
- [[sm-86-89-120]]
- [[kwanty-gguf]]
- [[rtx-5060-ti]]
- [[tensorfold]]
- [[raport-09-chmura-5060ti]]
- [[raport-15e-kwantyzacja-nowa]]
- [[2026-10-16-nvfp4-skala-globalna-sim]]
