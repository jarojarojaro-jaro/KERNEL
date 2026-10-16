---
typ: research
tags: [research, chmura, nvidia, sm-86]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/09-chmura-3090.md:1-233
status: aktualne
---
# Raport 09 (3090): RTX 3090 w chmurze

**RTX 3090 (sm_86, Vast, 2026-10-16): nasz silnik daje Qwen3.8-27B 39 → 78 t/s (×2.0 vs domyślny llama.cpp i Ollama, ×1.23 vs najlepsze flagi upstream) i LFM2.5 180 → 264 t/s (×1.46); greedy md5 różni się od upstreamu przez łatki 0001/0002 i 0013.**

- Sprzęt: limit mocy 300 W (domyślnie 350), PCIe gen3 x16, host i7-4790 z kwotą cgroup 7.68 CPU; koszt ≈ $0.90 (limit $1.90), instancja zniszczona.
- Qwen (spec_sweep 2 rundy ABBA × 18 żądań): A0 38.9, A1 (MTP upstream) 63.3, A2c (fork, flagi A1) 69.5, A2 (+słownik draftu, IQ4_XS) **78.0 t/s**, 38.4 ms/krok; A2-safe 74.5.
- LFM: A0 180.2, A1 176.0, A2 249.3, A2p (profil Ampere) **263.9 t/s**; zysk w serwerze głównie z samplera i hosta (llama-bench tylko +8.7% tg), upstreamowy sampler kosztuje tu ~1.4 ms/token.
- Profil Ampere (commit `3da7a02ec`): `GGML_CUDA_MMVQ_N1_ROWS=2` (+8.5% LFM, +7.2% Qwen tg128, bitowo) i `GGML_HIP_GATE_UP_Q8` off (+6.5% LFM); tg128 Qwen 40.1 → 43.0, LFM 256.8 → 284.5.
- md5: Qwen plain `eac36830` vs fork `4589b2ea`; przyczyna LFM wyłącznie 0001/0002 (build z `-DMMVQ_DISABLE_MULTI` = upstream `949a753b`), Qwen dodatkowo 0013. Bez multi-kolumny pp5 Qwena spada o 8% (144.2 → 132.4).
- nsys: kernele/token Qwen 1956 → 795, LFM 908 → 357; Qwen to w 91% MMVQ przy ~80% pasma.
- Długi kontekst: spadek przy 64k −30% (Qwen) i −41% (LFM) – kandydat na FA vec dla KV kwantyzowanego.
- Ollama 0.40.5 (domyślne): Qwen 39.0, LFM 180.5 t/s = A0.
Werdykt: szacunek raportu 08 trafił co do fuzji GPU (małe), ale nie docenił warstwy host/sampler/MTP i strojenia MMVQ pod architekturę.

## Powiązane
- [[research/_hub|research]]
- [[raport-09-chmura-5060ti]]
- [[raport-09-chmura-3060]]
- [[rtx-3090]]
- [[nvidia-wyniki-2026-10-16]]
- [[raport-08-platforma]]
