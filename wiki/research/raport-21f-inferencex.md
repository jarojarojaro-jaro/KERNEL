---
typ: research
tags: [research, benchmarki, agenci]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21f-inferencex.md:1-317; ~/KERNEL/product/research/21f-agentx-stats-out.txt
status: aktualne
---
# Raport 21f: InferenceX / AgentX (SemiAnalysis) i „megakernel” Kimi K3 w vLLM

**AgentX mierzy serwer przy kształcie ruchu agenta (393 sesje Claude Code) na syntetycznej treści z wymuszoną długością akceptacji – dla nas cenny jest kształt ruchu, nie wyniki; standardem zostaje nasz zestaw (`spec_sweep`, `copy`, `mvs`, `long_ctx_bench`) + własny „PodX” z prawdziwą treścią sesji omp.**

- Wada dla nas: syntetyczna treść i wymuszona AL wyłączają z pomiaru akceptację MTP i ogon lookupu (×2.4 na `mvs`); c=1 przez 1 h to na XTX ~1 sesja; „throughput per GPU” to w ~99% tokeny wejścia z cache (Kimi K3 c=1: 1554 tok/s/GPU, 10.1 wyjścia).
- Analiza śladów: [[ksztalt-ruchu-agentowego]], [[lekcja-agent-prefill-nie-decode]]. Harness: [[agentx-harness]]. Qwen na InferenceX: [[qwen38-27b-inferencex]]. Kimi K3: [[vllm-kimi-k3-specialized-decode]].
- Adaptacja (bez GPU teraz): test systemowy oficjalnym harnessem przy c=1 bez spekulacji; PodX = replay o kształcie AgentX z prawdziwą treścią omp (`capture_proxy.py`/`replay.py` z 16f).
- Link arXiv 2605.08513 podany przez użytkownika dotyczy innego tematu: [[single-neuron-safety-2605-08513]]; publicznej pracy o InferenceX nie ma (metodologia na stronie `/agentx/methodology`, w kodzie i SPEED-Bench arXiv 2604.09557).

## Powiązane
- [[research/_hub|research]]
- [[2026-10-19-workload-omp]]
- [[raport-18-nastepna-fala]]
- [[zestaw-copy-mvs]]
