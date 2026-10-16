---
typ: rocm
tags: [rocm, vulkan, backend]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:6-16,172-191; ~/KERNEL/reports/Optymalizacja kerneli na AMD.md:75; ~/KERNEL/hardware/rx-7900-xtx.md:32-34
status: aktualne
---
# ROCm czy Vulkan na RX 7900 XTX

**Na początku Vulkan (RADV) dekodował szybciej, a ROCm szybciej przetwarzał prompt; 2026-10-12 ROCm został stałym backendem i od tej pory optymalizujemy tylko pod HIP.**

Pierwsze porównanie (Qwen3.8-27B, ctx 204800, KV q4_0, mieszanka 3 EN + 3 PL, serve_bench T=0):
- ROCm (nasze kernele + cache q8_1 + słownik draftu 64k), MTP n=4: 85.5 t/s;
- Vulkan RADV, MTP n=4 / n=5: 88.1 / 91.8 t/s;
- prefill pp4096: ROCm 1044 vs Vulkan 850 t/s; przy 16k kontekstu 890 vs 622.

Cały czas odpowiedzi (2026-10-12, prompt + 1000 tokenów, ROCm / Vulkan): 1.7k 15.0 / 13.3 s, 6.6k 20.3 / 21.2 s, 29.5k 50.2 / 62.4 s, 94k 165 / 260 s. Vulkan wygrywał tylko przy krótkich promptach (~11%).

Decyzja (NOTES, 2026-10-12): ROCm stałym backendem domyślnym; Vulkan zostaje opcją (`run-llm.sh … vulkan`). Potem fuzje i PM4 zlikwidowały przewagę Vulkana w dekodowaniu (dziś Qwen 109 t/s na ROCm).

Kontekst zewnętrzny: issue llama.cpp #20934 (03/2026) — na 7900 XTX ROCm generuje 15–25% wolniej niż Vulkan; scoreboard Llama 2 7B Q4_0: Vulkan tg128 190.9, ROCm 170.1. Główna przyczyna u nas: narzut grafu HIP na granicę kernela.

## Powiązane
- [[rocm/_hub|ROCm]]
- [[hip-graph-narzut]]
- [[vulkan-mmvq]]
- [[2026-10-12-rocm-domyslny]]
- [[2026-10-12-rocm-vs-vulkan]]
