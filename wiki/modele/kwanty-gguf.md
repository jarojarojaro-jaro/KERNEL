---
typ: model
tags: [modele, kwanty, kv]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/SPEC-QWEN27B.md:21; stat -c %s ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf (17559178144 B = 16.35 GiB, 2026-10-16); ~/KERNEL/sources/qwen3.8-27b.md:15-24; ~/KERNEL/qwen-opt/NOTES.md:283-286,330,354,363; ~/KERNEL/qwen-opt/research/lfm-kv-q4-vs-q8.md; ~/KERNEL/reports/Optymalizacja kerneli na AMD.md:86; ~/qwen-opt/cloud/PLAN-TESTOW.md:89-91; ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:59-61,219-251
status: aktualne
---
# Kwanty wag i KV, których używamy

**Wagi trzymamy w kwantach K/I GGUF ładowanych w całości do VRAM; KV cache to q4_0 dla Qwena i q8_0 dla LFM (decyzja użytkownika); zmiana kwantu = inny model, więc to nie jest „optymalizacja bezstratna”.**

Wagi:
- Qwen3.8-27B UD-Q4_K_XL (unsloth): 16.35 GiB (17 559 178 144 B; SPEC podaje 16.34 przez obcięcie), mieszanka Q5_K / IQ4_XS / Q4_K / Q6_K; Uncensored Q4_K_M 15.66 GiB; rozmiary OrcaRouter: Q4_K_M 16.8–17.1 GB, Q6_K 20.9–22.9 GB, Q8_0 29 GB (nie mieści się w 24 GB).
- LFM2.5 Q5_K_M 15.86 GiB (na 16 GB kartach Q4_K_M, bo Q5 = 15.86 GiB się nie mieści).
- Na mniejszych kartach w chmurze: Qwen UD-Q3_K_XL (12.2 GiB, 16 GB), UD-IQ3_XXS (10.2 GiB, 12 GB); eksperymenty niskobitowe: Saluki IQ2-mix, Bonsai Q2_0/PTQ1_0.
- Głowica draftu MTP przekwantyzowana przy ładowaniu do IQ4_XS (łatka 0032): draft 4.82 → 3.62 ms/krok, +0.4 GB VRAM.

KV cache:
- Qwen: q4_0 (`kvq` czyta go wprost); KV draftu też q4_0 (94k: 97.5 → 100.6 t/s).
- LFM: q8_0 z decyzji użytkownika; koszt vs q4_0 (tg128): głębokość 0 +2.6%, 98k +30.1% przed łatką 0055; KLD vs f16: q8_0 0.044, q4_0 0.128.
- Raport AMD: na Radeonie najpewniejsze Q4_0, Q4_K i Q8_0; dla KV q4_0 „vastly superior” do q4_1/q5_x/iq4_nl.

Niezależne KLD dla Qwen3.8-27B (raport 15e, protokół agentionai [A]: wiki ctx 2048, 60 chunków, ref BF16; wiki / held-out): UD-Q4_K_XL 0.0122 / 0.0117; UD-Q3_K_XL 0.0337 / 0.0421; AP-Q3_K_XL 0.0352 / 0.0339; UD-IQ3_S 0.0470 / 0.0617; GSQ-RCO IQ3_S 0.0665 / 0.0594. AP-Q3_K_XL to te same bajty co nasz UD-Q3_K_XL (13.15 GB) przy KLD held-out −19.5%. KLD z różnych protokołów nie są porównywalne ([[lekcja-kld-protokoly]]).

## Powiązane
- [[modele/_hub|Modele]]
- [[fattn-kvq]]
- [[qwen3-8-27b]]
- [[lfm2-5-24b-a2b]]
- [[2026-10-14-lfm-kv-q8]]
- [[raport-15e-kwantyzacja-nowa]]
- [[swift-1-5]]
