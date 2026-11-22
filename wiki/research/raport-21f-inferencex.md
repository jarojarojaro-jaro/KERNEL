---
typ: research
tags: [research, benchmarki, agenci]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/21f-inferencex.md:1-317; ~/KERNEL/product/research/21f-agentx-stats-out.txt; ~/KERNEL/product/research/21f-inferencex.md:24; InferenceX run 35359530151, PR #3260; ~/KERNEL/wiki/REKORDY.md
status: aktualne
---
# Raport 21f: InferenceX / AgentX (SemiAnalysis) i „megakernel” Kimi K3 w vLLM

**AgentX mierzy serwer przy kształcie ruchu agenta (393 sesje Claude Code) na syntetycznej treści z wymuszoną długością akceptacji – dla nas cenny jest kształt ruchu, nie wyniki; standardem zostaje nasz zestaw (`spec_sweep`, `copy`, `mvs`, `long_ctx_bench`) + własny „PodX” z prawdziwą treścią sesji omp.**

- Wada dla nas: syntetyczna treść i wymuszona AL wyłączają z pomiaru akceptację MTP i ogon lookupu (×2.4 na `mvs`); c=1 przez 1 h to na XTX ~1 sesja; „throughput per GPU” to w ~99% tokeny wejścia z cache (Kimi K3 c=1: 1554 tok/s/GPU, 10.1 wyjścia).
- Analiza śladów: [[ksztalt-ruchu-agentowego]], [[lekcja-agent-prefill-nie-decode]]. Harness: [[agentx-harness]]. Qwen na InferenceX: [[research/raport-21f-inferencex]]. Kimi K3: [[vllm-kimi-k3-specialized-decode]].
- Adaptacja (bez GPU teraz): test systemowy oficjalnym harnessem przy c=1 bez spekulacji; PodX = replay o kształcie AgentX z prawdziwą treścią omp (`capture_proxy.py`/`replay.py` z 16f).
- Link arXiv 2605.08513 podany przez użytkownika dotyczy innego tematu: [[single-neuron-safety-2605-08513]]; publicznej pracy o InferenceX nie ma (metodologia na stronie `/agentx/methodology`, w kodzie i SPEED-Bench arXiv 2604.09557).

## Ze scalonej notatki: Qwen3.8-27B na InferenceX (wpis eksperymentalny)

Na InferenceX Qwen3.8-27B ma eksperymentalny wpis: bf16, 1×H100, vLLM + drafter DSpark k=7, fixed-sequence 1k/1k na losowych tokenach; przy c=1 mediana 86.1 tok/s, p90 67.4, AL ≈ 2.0 (run 35359530151, PR #3260 niescalony, 2026-10-19).

Nasz XTX (UD-Q4_K_XL + MTP4) daje 109.0 t/s na `spec_sweep` ([[REKORDY]]), czyli ~1.27× przy 3.2× mniejszej liczbie bajtów na token – porównanie orientacyjne (inne kwanty, prompty, T; losowe tokeny obniżają akceptację draftu).

## Powiązane
- [[research/_hub|research]]
- [[2026-10-19-workload-omp]]
- [[raport-18-nastepna-fala]]
- [[zestaw-copy-mvs]]
