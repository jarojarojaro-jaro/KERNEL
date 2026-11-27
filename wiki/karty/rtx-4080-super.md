---
typ: karta
tags: [karty, nvidia, wynajem]
aktualizacja: 2026-11-22
zrodlo: wiki/testy/2026-11-19-k118-nvidia-pelna-moc.md:10-24,51-54; wiki/KOLEJKA-TESTOW.md (K-131)
status: aktualne
karta: rtx-4080-super
gdzie: Vast (wynajem, K-118)
stan: jednorazowy test fork CUDA na pełnej mocy
---
# NVIDIA RTX 4080 SUPER (wynajem, Vast)

**Karta z jednego wynajmu na Vast (K-118, 2026-11-19): nasz fork CUDA z MTP n4 T=0 daje 107,3 t/s Qwen3.8-27B przy pełnej mocy, a dekod plain wykorzystuje 78% pasma (3090: 58%).**

Warunki (K-118): moc pod obciążeniem 278 z 280 W, pamięć 11 251 MHz, fork CUDA Enigmy (`kvqleana`).

- dekod plain 55,7 t/s (78% pasma); MTP n2 T=0 / T=1 105,5 / 92,3; n4 T=0 / T=1 107,3 / 91,2 t/s;
- prefill ~3,2k / ~11k: 1554 / 1862 t/s; przy 95,6k 1338 t/s;
- długi kontekst (K-116a, 95,6k): dekod plain → MTP n2 35,4 → 73,7 t/s (+108%), VRAM 14,2 GB.

K-131: MMVQ celu wykorzystuje 58% pasma na 3090 i 78% na 4080 SUPER, więc strumieniowanie wag przez `cp.async` celuje w 3090.

<!-- TABELE:START -->
## Wyniki z notatek (2)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-28); pełna tabela: [[najlepsze-wyniki]].

| model | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP n4 T=0 | **107,3 t/s** | GSQ IQ3_XXS-mtp, kvqlean, 278 W | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
| Qwen3.8-27B [[qwen3-8-27b]] | prefill ~11k | **1862 t/s** | kvqlean | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
<!-- TABELE:END -->

## Powiązane
- [[2026-11-19-k118-nvidia-pelna-moc]]
- [[rtx-3090]]
- [[KOLEJKA-TESTOW]]
