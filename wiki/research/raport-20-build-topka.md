---
typ: research
tags: [research, topka, lookup, pm4]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/20-build-topka.md:5-17,59,63-68,82-84
status: aktualne
---
# Raport 20: build „topka” (ogon lookupu + współdzielenie cache promptu)

**Topka = amd-opt @ `f61994f58` + ogon lookupu (`6c21a3e9f`) + `CACHE_SHARE_MIN` (`22e2b0f55`), PM4 wyłączone; greedy md5 = produkcja, code-edit `mvs` T=0 Qwen 166.1 → 396.9 t/s, Uncensored 414.8 t/s (2026-10-19).**

- Launcher `~/qwen-opt/run-topka.sh qwen|uncensored`: `LLAMA_SPEC_LOOKUP=3 W=16`, `LLAMA_SERVER_CACHE_SHARE_MIN=1024`, `GGML_HIP_PM4=0`, `DRAFT_N=4` (`20:10`).
- Poprawność: plain `c4708318`, MTP `6f14e814`; `mvs` T=0 4/4 md5 jak MTP-only; page faulty 31 → 31 (`20:12-14`).
- Czat T=1, 1 seed: Qwen 105.1, Uncensored 106.9 t/s – w szumie tekstu T=1 (`20:17`).
- Fałszywy alarm gpu-guard (zero-RPM firmware) – guard poprawiony (`20:59`).
- Szczegóły eksperymentu: [[2026-10-19-build-topka]]. Późniejszy stan topki (PM4 WA=2, GPU verify): [[raport-26-kolejka-gpu]], [[raport-wyniki-xtx-2026-10-19]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[2026-10-19-build-topka]]
- [[raport-16b-lookup-tail]]
- [[raport-26-kolejka-gpu]]
- [[raport-wyniki-xtx-2026-10-19]]
