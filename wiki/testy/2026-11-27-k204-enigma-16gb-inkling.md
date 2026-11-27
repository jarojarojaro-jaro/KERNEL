---
typ: test
tags: [testy, nvidia, vast, 5060ti, 4060ti, inkling, enigma, k204, kontekst]
aktualizacja: 2026-11-28
zrodlo: ~/dev/KERNEL/qwen-opt/cloud/nvq3/results/qwenbench-nvq3-{5060tie-11272300,5060tie2-11272344,4060tie-11272317}/
status: aktualne
---
# 2026-11-27 K-204: Enigma 16 GB z Inklingiem IQ3_S bez cenzury i pełnym kontekstem (5060 Ti, 4060 Ti)

**Inkling 2 Mini GSQ-RCO IQ3_S + LoRA bez cenzury + DSpark n2, ub 128: 5060 Ti 32,5 → 66,5 t/s (+104%) przy 262 144 kontekstu (było 200 704, +31%), 4060 Ti 23,9 → 48,6 t/s (+103%) przy 283 648 (było 217 088, +31%); igły 5/5 przy 95% głębokości, odmowy 0/5. Koszt 0,41 $.**

Warunki: upstream llama.cpp b12811 CUDA 12.8, `-fa on -ctk q4_0 -ctv q4_0 -np 1 --jinja -ngl 99 -ngld 99 -fit off`; wall = mediana 4 promptów (kod, tech, pl, json) × 300 tok., T=0 / T=0,7; baseline = obecny przepis Enigmy 16 GB (Qwen3.8-27B GSQ IQ3_XXS-mtp, bez MTP, ub 256, `-c 200704`) na tym samym hoście i tym samym skrypcie. 5060 Ti: host Ryzen 5 7600, 180/180 W (druga sesja na Ryzen 9 9900X: 74,5 / 69,6 t/s). 4060 Ti: Threadripper 2950X, 150/165 W.

```
llama-server -m Inkling-2-Mini-GSQ-RCO-IQ3_S.gguf --lora Inkling-2-Mini-Uncensored-LoRA.gguf \
  -md dspark-Inkling-2-Mini-Q8_0.gguf -ngl 99 -ngld 99 -fit off -fa on -ctk q4_0 -ctv q4_0 \
  -c <262144 (5060 Ti) | 283648 (4060 Ti)> -ub 128 -b 128 -np 1 --jinja \
  --spec-type draft-dspark --spec-draft-n-max 2 --spec-draft-p-min 0
```

| | RTX 5060 Ti | RTX 4060 Ti 16 GB |
|---|---|---|
| wall T=0 / 0,7 | 32,50 / 32,41 → **66,45 / 61,97 (+104% / +91%)** | 23,94 / 23,95 → **48,58 / 48,99 (+103% / +105%)** |
| kontekst | 200 704 → **262 144** | 217 088 → **283 648** |
| 95% głębokości + 700 tok. odpowiedzi | PASS, prompt 248 452, igły 5/5 | PASS, prompt 269 503, igły 5/5 |
| odmowy z LoRA | 0/5 | 0/5 |
| szczyt VRAM | 15 698 / 16 311 MiB | 15 955 / 16 380 MiB |
| dekod przy 64k / 128k / maks. | 32,7 / 30,1 / 20,6 | 23,2 / 23,4 / 14,9 |
| prefill 32k przy ub 512 / 256 / 128 | 973 / 837 / 632 t/s | 771 / 662 / 497 t/s |
| prefill maks. | 248k w 925 s (268 t/s) | 269k w 1159 s (232 t/s) |

Największy `-c`, który startuje (5060 Ti / 4060 Ti): DSpark ub 512 216 064 / 222 208; ub 256 240 640 / 263 168; **ub 128 262 144 / 283 648**; bez DSpark ub 128 404 480 / 411 648, ub 64 416 768 / 423 936 (bez DSpark nie sprawdzone w głębi: 337k z 381k promptu bez błędu, potem stop budżetu).

## Wnioski
- ub 128 daje najwięcej kontekstu; prefill −35% wobec ub 512, dekod bez zmian. `-b 2048` zamiast 128 bez różnicy.
- DSpark: długość 2 najlepsza (64,2 / 48,8 t/s), 3: 58,4 / 47,8, 4: 52,9 / 46,1, bez draftera 51,4 / 37,8. `p_min` ≥ 0,1 wyłącza drafter całkowicie.
- KV draftera q4 zużywa więcej VRAM niż domyślne (18,7 vs 17,3 MiB na 1k tok.) i przy 270k ładuje się, a pada na pierwszym zapytaniu: nie ustawiać `-ctkd/-ctvd`.
- Wątki (`-t` 2–8) bez wpływu (±0,3%).
- **LoRA w czasie działania kosztuje 17–33% dekodu** (bez niej 79,6 / 83,2 na 5060 Ti, 72,2 na 4060 Ti) → K-207.
- Procesor hosta waży więcej niż flagi: EPYC 7502 (K-201) 28,4 t/s, Ryzen 7600 66,5, 9900X 74,5. Bramka wykorzystania GPU w llama-bench (≥ 85%) odsiewa złe hosty.
- vast-reaper zniszczył działającą instancję po jednym odczycie „offline” (strata 40 min pracy); stop budżetu zadziałał przy szacunku 0,457 $ przy faktycznych 0,40 $. `nvq3/state/STOP` ustawiony.

## Na później
- Przepis do strony Enigmy 16 GB tylko decyzją JARO (zmienia model).
- Reaper: dwa kolejne odczyty „offline” przed zniszczeniem.

## Test u nas
K-207 (tania ablacja zamiast LoRA w llama.cpp). Wynik produkcyjny: [[final-recipes-nvidia]] (kandydat).
