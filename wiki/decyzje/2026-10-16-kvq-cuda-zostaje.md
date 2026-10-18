---
typ: decyzja
tags: [decyzje, kv, cuda, kld]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16c-kvq-cuda.md:12,126-145,164-168; decyzja Main 2026-10-16 (komunikat do WikiIngest); ~/KERNEL/product/research/16c-kvq-cuda.md:191-221,245-252; ~/qwen-opt/cloud/results/kvq-cuda-20261016/kld-c5/
status: aktualne
---
# 2026-10-16: kvq na CUDA zostaje włączone, KLD Qwena do powtórki

**Rodzic (Main) zdecydował (2026-10-16; 2026-10-18 zawężone wyjątkiem n=1, niżej): `kvq` na CUDA zostaje domyślnie włączone także dla Qwena przy ub 1, mimo FAIL bramki KLD +2.53σ; przy następnym wynajmie 3090 powtarzamy KLD Qwena z `--chunks 4`.**

Dane (wikitext-2, referencja f16 KV): Qwen q4_0 ub1 vec 0.002527 ± 0.000081 → kvq 0.002899 ± 0.000123 (+2.53σ; same top −0.68σ, 99.9% ×1.005), Qwen ub5 −1.95σ, LFM ub1 −2.00σ, LFM ub5 −0.56σ (PASS), kanarek KV q4_0 +22.2σ (FAIL oczekiwany).

Uzasadnienie: kontrola szumu – to samo jądro z innym podziałem KV daje dla Qwena 0.002755 (+1.91σ vs vec), a dla LFM oblewa bramkę mimo identycznej arytmetyki ([[lekcja-kld-szum-kolejnosci]]). Odrzucony wariant ostrożny: wyłączenie kvq przy `Q->ne[1] == 1` dla D256 q4_0 (traci +36.8% tg@64k).

Warunek: jeśli powtórka `--chunks 4` znów da > 2σ, wraca decyzja o wyjątku dla ub1.

**Wynik powtórki (2026-10-18):** `--chunks 5` (bliżej niż planowane 4) – średnia i top-p przechodzą, ogon 99.9% FAIL (×2.04 vs szum ×1.41), więc zgodnie z warunkiem wszedł wąski wyjątek `678473a27`: przy decode 1 tokenu D256 q4_0 domyślnie vec (tg@64k Qwena +35.5% → +0.4%), weryfikacja MTP i LFM zostają na kvq. KLD wariantu z wyjątkiem niezmierzone (instancja zniszczona przed restartem) `[INFERENCE: przy -ub 1 identyczne z vec]`.

## Powiązane
- [[decyzje/_hub|Decyzje]]
- [[2026-10-14-lfm-kv-q8]]
- [[2026-10-16-kvq-cuda]]
- [[bramka-kld-kanarki]]
