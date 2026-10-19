---
typ: model
tags: [modele, lfm, kld, determinizm]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16f-xtx-szybkie.md:75-86,176-179; ~/wt/quickwins/qw/{e1-kld.txt,e1-kld2.txt,e1-kld3.txt}
status: do-sprawdzenia
---
# LFM2.5: logity zależą od podziału promptu na ubatche

**Dowolne dwa rozmiary ubatcha (128–2048) dają dla LFM2.5-24B-A2B KLD 0.055–0.068 i 88–89% tego samego top-1, przy KV q8_0 i f16, a upstream `e60eff95f` daje bit w bit te same liczby co fork; A/A (ub 512 vs 512) to KLD 0 (2026-10-18).**

PPL 14.09–14.30 ± 0.45 dla wszystkich ub (korpus: notatki wiki, `-c 2048 --chunks 12`), więc to nie zmiana jakości, tylko czułość numeryczna. Przyczyna niepotwierdzona `[INFERENCE: remisy w routingu top-k MoE wzmacniane przez 40 warstw]`.

Konsekwencje: zmiana `-ub`, granic batcha albo checkpointów zmienia greedy LFM – np. `LLAMA_LFM2_MSG_SPANS=1` daje md5 `407b8411` zamiast `894e56e4`. Krótkie prompty (< 512 tokenów, `greedy.sh`) nie są dotknięte. Porównania md5 LFM robić tylko przy tym samym podziale batcha.

## Powiązane
- [[modele/_hub|Modele]]
- [[lfm2-5-24b-a2b]]
- [[lekcja-spekulacja-zmienia-numeryke]]
- [[2026-10-18-lfm-ubatch-2048]]
