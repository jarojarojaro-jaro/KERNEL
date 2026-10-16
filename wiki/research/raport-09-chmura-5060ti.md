---
typ: research
tags: [research, chmura, nvidia, sm-120, nvfp4]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/09-chmura-5060ti.md:1-290
status: aktualne
---
# Raport 09 (5060 Ti): RTX 5060 Ti 16 GB w chmurze

**RTX 5060 Ti (Blackwell sm_120, Vast, 2026-10-16): Qwen3.8-27B UD-Q3_K_XL 28 → 51.7 t/s (×1.84; ×1.38 vs flagi upstream), LFM2.5 Q4_K_M 148 → 208 t/s (×1.41); NVFP4 przyspiesza tylko prefill, a jakość dostępnych GGUF NVFP4 jest słaba.**

- Sprzęt: 180 W, PCIe gen4 ×8, GDDR7 448 GB/s, host EPYC 7502 z limitem cgroup 7.68 CPU; koszt ≈ $1.05 (5.24 h), instancja zniszczona.
- test-backend-ops 19251/19253: 2 FAIL tolerancji w `GATED_DELTA_NET_PROLOGUE` (ERR 5.05e-4 i 9.44e-4 przy progu 5.0e-4).
- Qwen ms/krok 68.36 (A1) → 48.58 (A2): build-only, przełączniki i słownik draftu + głowica IQ4_XS; tok/krok prawie bez zmian (2.55 vs 2.48). MTP n=3 (52.81) ≥ n=4.
- LFM: +31% w serwerze, +2% w llama-bench – źródło to sampler (`LLAMA_SAMPLER_FAST_TOPK=0`: 207.7 → 165.5 t/s); profil NVIDIA (`GATE_UP_Q8=0`, `Q8_IDS=0`) +5.8% w serwerze, bitowo.
- `GGML_CUDA_MMVQ_N1_ROWS=2` na sm_120 szkodzi (LFM −2.7%, Qwen −1.7%), na sm_86 pomaga → predykat per arch.
- Pułapka: upstream A1 z `-fit on` i MTP na 16 GB dawał 7.7 t/s; `-fit off -ngl 99 -t 8` 31.8 t/s na jednym prompcie.
- Formaty: NVFP4 pp +65–69% (Qwen) i +71–81% (LFM), ale decode bez zysku; KLD Qwen NVFP4-VERY-LOW 0.0865 vs UD-Q3_K_XL 0.0265, LFM NVFP4 (WhiskyAKM) 1.1826 – zepsuty. Najlepszy dla LFM na 16 GB: oficjalny **QAD-Q4_0** (KLD 0.2029, serwer 226.8 t/s, md5 = upstream).
- Prefill LFM: `-b 2048 -ub 2048` +56% (flaga, nie łatka). Q5_K_M z offloadem `--n-cpu-moe 6`: tg128 120.9 t/s – nie opłaca się.
- nsys: LFM 908 → 435 kerneli/token; Qwen na ~85% z 448 GB/s.
Werdykt: teza raportu 08 częściowo obalona – kernelowo +1–5%, ale end-to-end +31% (LFM) i +37% (Qwen MTP) nad A1 dzięki warstwie hosta.

## Powiązane
- [[research/_hub|research]]
- [[raport-09-chmura-3090]]
- [[raport-09-chmura-3060]]
- [[rtx-5060-ti]]
- [[nvfp4]]
- [[lekcja-fit-mtp-16gb]]
