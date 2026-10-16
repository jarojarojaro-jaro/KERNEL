---
typ: repo
tags: [repo, llama-cpp, galezie, rocm]
aktualizacja: 2026-10-16
zrodlo: git -C ~/llama-master log --oneline e60eff95f..amd-opt (70); ~/KERNEL/wiki/latki/seria-amd-opt.md:5-30
status: aktualne
---
# Gałąź amd-opt (produkcja ROCm)

**Gałąź produkcyjna dla RX 7900 XTX: 70 commitów (łatki 0001–0070) liniowo na upstream `e60eff95f` z 2026-10-09, HEAD `f61994f58` (2026-10-15, epilog MMQ).**

Zainstalowana w `~/llama-opt` i używana przez `run-llm.sh`. Ostatni commit to łatka 0070 (runda 6: epilog skal Q4_K/Q5_K w MMQ w operacjach f32 parowalnych w VOPD, bitowo te same sumy, wyłącznik `GGML_HIP_MMQ_EPI=0`). Gałęzie rund 5–6 (`opt-samp`, `opt-gdn6`, `opt-mmq6`, `opt-qwen5`, `tools6`) wychodzą z wcześniejszego HEAD `c36fd2c87`. Na NVIDIA ta gałąź nie kompilowała się (łatki 0057, 0070) – stąd `cuda-compat`. Serię łatek eksportuje `~/KERNEL/qwen-opt/patches/llama.cpp-amd-opt/`.

## Powiązane
- [[repo/_hub|repo]]
- [[llama-cpp-fork]]
- [[amd-opt-v070]]
- [[cuda-compat-galaz]]
- [[seria-amd-opt]]
