---
typ: latka
tags: [latki, pending, nie-scalone]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/patches/pending/opt-gdn6/, ~/KERNEL/qwen-opt/patches/pending/opt-qwen5/ (listing 2026-10-16); ~/KERNEL/qwen-opt/research/qwen-round5.md:80-85; ~/KERNEL/qwen-opt/research/round6/gdn-bitwise.md:176-184
status: aktualne
---
# Łatki oczekujące (poza amd-opt)

**W `qwen-opt/patches/pending/` leżą łatki z gałęzi, które nie weszły do `amd-opt`: GDN fast (`opt-gdn6`) i runda 5 Qwena (`opt-qwen5`).**

`pending/opt-gdn6/` (2 pliki):
- 0001 osobny bitowo identyczny kernel GDN fast z DPP;
- 0002 stan czytany/pisany w kawałkach 16 B przez LDS.
Zmierzone 2026-10-15: bitowe, zysk w szumie (+0.15% tg128) → nie scalone.

`pending/opt-qwen5/` (7 plików):
- 0001 DFlash/DFlash2: bloki do dwukrotnej szerokości treningowej (`LLAMA_DFLASH_WIDE`); szeroki blok n=15 wolniejszy niż n=6;
- 0002 GDN DPP (pierwsza próba, niebitowa) i 0006 jej revert;
- 0003 haki ablacji MMQ (tylko build `-DGGML_MMQ_ABLATION`);
- 0004 `--spec-draft-vocab` także dla draftera DFlash (niezmierzone);
- 0005 podwójny bufor y w MMQ (−2.6% pp4096) i 0007 jego revert.

Do zmierzenia z rundy 5 zostały: tryb „draft 16, verify k” (`LLAMA_DFLASH_BLOCK`) i mniejszy słownik głowicy DFlash (STATUS-NEXT).

## Powiązane
- [[latki/_hub|Łatki]]
- [[gdn-fast]]
- [[qwen-runda-5]]
- [[drafter-dflash]]
- [[seria-amd-opt]]
