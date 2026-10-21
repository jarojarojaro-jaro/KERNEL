---
typ: nvidia
tags: [nvidia, flash-attention, kv, cuda]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15d-prefill-dlugi-kontekst.md:8-9,39-41,59-60,255; ~/wt/3090-opt/ggml/src/ggml-cuda/fattn.cu:655-670; ~/wt/3090-opt/ggml/src/ggml-cuda/fattn-vec.cuh:108-111; ~/KERNEL/product/research/16c-kvq-cuda.md:11,57-75,190-198
status: aktualne
---
# Flash attention na KV q4_0/q8_0 w upstream CUDA

**Upstream CUDA dla skwantyzowanego KV wybiera kernel VEC tylko przy n=1 (Ampere) albo n ≤ 2 (Ada+), a w pozostałych przypadkach MMA_F16 z buforem f16 całego K/V; vec czyta KV osobno dla każdej głowy Q w grupie GQA.**

- Wybór kernela (`fattn.cu:655-670`): `cc >= ADA_LOVELACE` → VEC przy `Q->ne[1] <= 2`, inaczej VEC tylko przy `== 1`; reszta → `BEST_FATTN_KERNEL_MMA_F16`, które wymaga konwersji K/V do f16 (`fattn-common.cuh:1041-1090`).
- Vec: offset K/V liczony z `head / gqa_ratio`, jeden blok na głowę Q (`fattn-vec.cuh:108-111`) – przy GQA 6 (Qwen) KV czytane 6×.
- Bufor f16 dla Qwena: 268 MB przy 64k i 839 MB przy 204800 tokenów (różnica VRAM −0.27…−0.84 GB po porcie kvq).
- Upstream odrzucił #29827 i #29846 (maintainer: „Don't make new PRs for this. I'm not going to review them.”). #29846 zmierzył dla qwen35 27B na 3090 pp1024@d32768: ub2 ×1.21, ub4 ×1.18, ub8 ×1.10, ub512 ×1.02.
- Metal #30645 robi pakowanie GQA dla 1–4 tokenów: 1.11–1.80× przy 4 głowach KV / 6 Q (kształt Qwen3.8-27B).
- Otwarte issues #29371 i #29826: bufor konwersji f16 zjada 8.7–13.3% oszczędności VRAM z kwantyzacji KV przy 131k.
- **Luka zamknięta w forku (2026-10-16, raport 16c):** kvq-mma na Ampere+; 5060 Ti sm_120 Qwen q8_0 tg@64k +24.6%, LFM +30.0%, jądro ~92% pasma 448 GB/s. Zobacz [[2026-10-16-kvq-cuda]].

## OrcaCyber-Nano-1.0 na 3090, 2026-10-21 (pomiar q4_0 vs f16)
Przy KV q4_0 decode na głębokości 14.7k: **75.4 t/s**, f16: **86.5 t/s** (+15%), q8_0: 65.7 (−13% vs q4_0).
Prefill identyczny dla wszystkich typów (~920 t/s) — czyli na CUDA q4_0 KV kosztuje ~13% decode, a q8_0 wypada
gorzej niż q4_0 (ścieżka vec). Przy 262 144 tokenach tylko q4_0 się mieści (f16 = 16 GiB KV).
`kvq-mma` (`01d6c6955`, Ampere+) **nie było w linii `topka`** — przeniesione na `orca-kvq`; pomiar w
[[raport-56-orca-3090]].

## Powiązane
- [[nvidia/_hub|NVIDIA]]
- [[cuda-stos]]
- [[sm-86-89-120]]
- [[fattn-kvq]]
- [[raport-15d-prefill-dlugi-kontekst]]
