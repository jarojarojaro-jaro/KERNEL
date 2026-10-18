---
typ: metoda
tags: [metody, poprawnosc, kld]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/qwen-opt/tools/kld-canary.md:1-62; ~/KERNEL/qwen-opt/tools/README.md:35-51; ~/KERNEL/qwen-opt/NOTES.md:363; ~/KERNEL/product/research/16c-kvq-cuda.md:209-210,249-252
status: aktualne
---
# Bramka KLD z kanarkami

**Zmianę numeryki przepuszczamy tylko, gdy KLD względem referencji f16-KV mieści się w 2σ bazy, a celowo zepsute warianty („kanarki”) bramka musi odrzucić.**

Pomiar: `llama-perplexity --kl-divergence` na LFM2.5-24B-A2B Q5_K_M, wikitext-2, `-c 16384 -ub 1 --chunks 3` (ub 1 = kernele dekodowania, 24573 tokenów), referencja `~/wt/lfm3-prof/ref.kld` (f16 KV, 6.3 GB).

Reguły (`kld_gate.py compare`, k=2):
- **PASS**: ΔKLD ≤ 2σ, Δsame-top ≥ −2σ, KLD99.9 ≤ 1.25× bazy;
- **IDENTICAL**: wszystkie liczby równe;
- **ERROR**: inna referencja albo niepełny log.

Sprawdzone na prawdziwych logach (baza: q8_0 vec):

| kandydat | ΔKLD | verdykt |
|---|---|---|
| q8_0 kvq (łatka 0055) | +0.000025 (+0.01σ) | PASS |
| q8_0 vec, 2. przebieg | 0 | IDENTICAL |
| q4_0 kvq | +0.084188 (+26.8σ) | FAIL |

Ograniczenie: próg 2σ to ok. 0.005 KLD, więc błąd mniejszy od tego przejdzie. Kanarki (`kld_canary.sh`: KV q4_0, 3 z 4 ekspertów, wagi warstwy ×1.10, requant Q3_K_M…) mają zmierzyć tę granicę; na GPU jeszcze nieuruchomione (~2 h) wg tools/README.

Uwaga 16c §9 (2026-10-18): 99.9% KLD na 40 960 tokenach to ~41 tokenów – na Qwenie z KV q4_0 jeden fragment (chunk 3, KLD tokenu ~20) decyduje o werdykcie, a sama zmiana kolejności sumowania przesuwa tę statystykę o ×0.69–×1.41; przy kandydatach blisko progu zawsze kontrola „to samo jądro, inny podział” ([[lekcja-kld-szum-kolejnosci]]).

## Powiązane
- [[metody/_hub|Metody]]
- [[zgodnosc-bitowa-md5]]
- kld-canary-sh
- [[fattn-kvq]]: 0055 to jedyna zmiana numeryki w rundach LFM
- [[lfm2-5-24b-a2b]]
