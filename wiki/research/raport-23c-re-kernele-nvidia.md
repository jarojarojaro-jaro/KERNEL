---
typ: research
tags: [research, reverse-engineering, nvidia]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/23c-re-kernele-nvidia.md:1-51; ~/qwen-opt/re/nv/{csv,sass,calib}/
status: aktualne
---
# Raport 23c: kernele NVIDIA (cuBLASLt, FlashInfer, Marlin, exllamav3) vs nasz ggml-cuda

**Vendorzy nie mają „magicznej” instrukcji dekodu, której nam brakuje; w gorącym MMVQ (SASS sm_120a/sm_86) są trzy różnice: PDL tylko po stronie czekania (`ACQBULK` bez `PREEXIT`), 0 cache hintów na strumieniu wag (cuBLASLt gemvx ~89 `LDG.E.EF` na kernel, exllamav3 też `LDG.E.EF`) i wagi ładowane 32-bitowo (Q4_K ~55 `LDG.E` na kernel, 0 `LDG.E.128`) (raport 23c, CPU, 2026-10-19).**

| # | zmiana | karty | szacunek | kill |
|---|---|---|---|---|
| 1 | trigger PDL na starcie MMVQ + prefetch L2 przed `pdl_sync` ([[pdl-mmvq-trigger]]) | 5060 Ti, 5090 | LFM +1–4.5% / +3–11% | < +1% tg na 5060 Ti przy md5 bez zmian |
| 2 | `ld.global.L1::evict_first` na wagach, `evict_last` na wektorze q8_1 | wszystkie | 0–2% `[INFERENCE]` | < +0.5% albo regres na 3090 |
| 3 | prefetch L2 w pętli MMVQ dla 2–8 kolumn ([[mmvq-prefetch-l2]]) | 3090, 5060 Ti | 0…+3% weryfikacji | < +1% przy 4–5 kolumnach |

Do dekodu nie brać cp.async/LDGSTS, `.L2::256B`, LDSM ani split-K/stream-K (mamy je w MMQ i FA-mma; w GEMV batch 1 opłaca się to tylko w Marlinie). Mapowanie PTX → SASS ustalone na kernelach kalibracyjnych: `L1::evict_first` → `LDG.E.EF`, `evict_last` → `.EL`, `L1::no_allocate` → `.NA`, `prefetch.global.L2` → `CCTL.E.PF2`, `griddepcontrol.launch_dependents` → `PREEXIT`, `griddepcontrol.wait` → `ACQBULK`, `cp.async.bulk.prefetch.L2` → `UBLKPF.L2` (tylko sm_120a). Narzędzie: `~/KERNEL/tools/re/sass_mix.py` (miks instrukcji + `cuobjdump -res-usage`). Analiza zgodna z zasadami [[re-vendorow-zasady]] (z bibliotek NVIDIA tylko metadane i miks instrukcji z naszych narzędzi).

## Powiązane
- [[research/_hub|research]]
- [[raport-21b-gpu-perf-zasoby]]
- [[raport-23b-re-kernele-amd]]
- [[sm-86-89-120]]
