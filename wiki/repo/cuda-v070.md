---
typ: repo
tags: [repo, llama-cpp, galezie, cuda]
aktualizacja: 2026-10-16
zrodlo: git -C ~/llama-master log --format=%h\ %s 8c942e5a9..cuda-v070, 7a538d96f..cuda-3090-opt, 7a538d96f..cuda-v070-5060ti; git -C ~/llama-master branch -v
status: aktualne
---
# Gałęzie cuda-v070, cuda-3090-opt, cuda-v070-5060ti, 3060-opt

**Nasze łatki na v0.7.0 z poprawkami dla NVIDIA: `cuda-v070` @ `7a538d96f` = `amd-opt-v070` + 4 commity cuda-compat; z niej wychodzą gałęzie kampanii chmurowej na RTX 3090, 5060 Ti i 3060.**

- `cuda-v070` (74 commity nad v0.7.0): `b479c67dd` epilog MMQ tylko pod `GGML_USE_HIP`, `398ded98d` jawna lista dla nvcc, `5dae6224f` PDL w 0053/0057, `7a538d96f` bariera warpu przy tickecie 0056.
- `3060-opt` @ `7a538d96f`: to samo co `cuda-v070` (RTX 3060, Saluki + Bonsai).
- `cuda-3090-opt` @ `da4748c4f`: + `GGML_CUDA_MMVQ_N1_ROWS=2|4` (domyślnie wyłączone) + wyłączniki `GGML_HIP_GDN_L2`/`GGML_HIP_GDN_AB` do bisekcji md5 względem upstreamu.
- `cuda-v070-5060ti` @ `2600ad94a`: jak wyżej + `GGML_HIP_Q8_PRODUCER` (producenci q8_1: norm/GLU/unary*mul).
Wszystkie z 2026-10-15/16.

## Powiązane
- [[repo/_hub|repo]]
- [[cuda-compat-galaz]]
- [[amd-opt-v070]]
- [[nvidia-wyniki-2026-10-16]]
- [[2026-10-16-kampania-nvidia]]
