---
typ: research
tags: [research, metody, latki]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:5-47
status: aktualne
---
# Raport 07: nasze metody i uogólnienie

**70 łatek: 45 bitowo identycznych, 6 te same tokeny, 3 tylko drafty, 3 poprawki, 7 zmienia numerykę (4 przeszły KLD); proces jest powtarzalny, ~60 h zegarowych w 6.4 dnia.**

- Klasy: MODEL 22, AMD-RDNA3 18, GEN-CUDA/HIP 12, GEN-host 10, VK-RDNA 5, narzędzia 3.
- Zysk: Qwen krok 41.7 → 27.74 ms (~48% MODEL, ~30% RDNA3, ~22% ogólne); LFM 5.07 → 3.40 ms/token.
- Transfer: LFM na łatkach Qwena 169.3 → 198.3 t/s (+17%) bez pracy pod LFM; kampania LFM (~11 h) 198 → 295 t/s (+49%).
- Konfiguracja: upstream Vulkan Qwen 38.8 t/s bez spekulacji, 85.6 t/s z MTP n=4 (×2.2); łatki dokładają +27–60%.
- Pętla: profil rocprofv3 → ranking → hipoteza z budżetem µs → łatka z wyłącznikiem → test-backend-ops + bramka → przeplatane A/B → wpis z wynikami negatywnymi.
- Koszt GPU: 6.8 h samych `spec_sweep` (182 konfiguracje), łącznie ok. 20–35 GPU-h.
- Luka: KLD Qwena nigdy nie zmierzone (0011 zmienia tekst greedy).
Raport zawiera też 17 trybów porażek (zob. lekcje).

## Powiązane
- [[research/_hub|research]]
- [[raport-08-platforma]]
- [[raport-02-autotuning]]
- [[klasyfikacja-latek]]
- [[playbook-optymalizacji]]
- [[lekcja-kolejnosc-akumulacji-fa]]
