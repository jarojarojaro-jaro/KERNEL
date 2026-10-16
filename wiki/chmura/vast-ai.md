---
typ: chmura
tags: [chmura, vast, nvidia]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:12-22,66,99-128,185-189,202-204; ~/qwen-opt/cloud/PLAN-TESTOW.md:5,11,20-23,36-49,95-104
status: aktualne
---
# Vast.ai (główne źródło kart NVIDIA)

**Marketplace hostów z kartami NVIDIA od GTX 10xx do RTX 50xx; tu wynajmujemy karty do kampanii (3060, 5060 Ti, 3090), bo zakup jest dużo droższy; AMD na Vast nie ma.**

- Oferta (raport 05, 2026-10): ~80 modeli GPU, 0 ofert AMD (filtr `gpu_arch=amd` istnieje); Docker domyślnie albo KVM VM (`vms_enabled=true`); on-demand, interruptible (licytacja), reserved (do −50%); publiczny feed cen JSON.
- Mediany $/h: RTX 3060 ~0.08, 3090 0.228 (162 oferty), 4090 0.507 (318), 5060 Ti 0.165 (163), 5070 0.294, 5090 0.734 (445).
- Profilowanie: w kontenerze brak liczników profilera i blokady zegarów (`ncu` prawie zawsze `ERR_NVGPUCTRPERM` [INFERENCE raportu]); VM Vast deklaruje pełne liczniki → benchmarki w kontenerach, profilowanie w VM.
- Narzędzia u nas: `vastai` CLI 1.8.3 w `cloud/.venv`; `vastai search offers` działa bez klucza; brak max-duration dla on-demand, stąd nasze dwa timery zniszczenia.
- Pierwsza runda (plan 2026-10-15): budżet ≤ $8, plan ~$2.5 na 3060 ($0.097/h z dyskiem), 5060 Ti ($0.188), 3090 ($0.232).
- Zasada pomiaru: porównania A/B tylko na tym samym hoście w tej samej sesji; „typowe t/s” dopiero jako mediana z ≥ 3 hostów.

## Powiązane
- [[chmura/_hub|Chmura]]
- [[harness-chmurowy]]
- [[runpod]]
- [[rtx-3090]]
- raport-05-chmura
