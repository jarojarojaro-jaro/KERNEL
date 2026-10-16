---
typ: model
tags: [modele, qwen, gdn]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/sources/qwen3.8-27b.md:5-24; ~/KERNEL/qwen-opt/SPEC-QWEN27B.md:17-27; ~/KERNEL/qwen-opt/STATUS-NEXT.md:8-13; ~/KERNEL/qwen-opt/NOTES.md:6-13,331; ls ~/models (2026-10-16); ~/KERNEL/product/research/06-produkt-ux-prawo-biznes.md:50
status: aktualne
---
# Qwen3.8-27B (główny model)

**Gęsty hybrydowy model 27B (48 warstw Gated DeltaNet + 16 pełnej uwagi) z wbudowaną głowicą MTP; na RX 7900 XTX przyspieszony z 59.2 do 109 t/s.**

Architektura (`qwen35` w llama.cpp): 64 warstwy w układzie 3:1, hidden 5120, słownik 248 320, kontekst natywny 262 144, head dim atencji 256 (raport 13), 27.32 B parametrów. DeltaNet trzyma stały stan rekurencyjny, więc KV cache to ok. 1/4 klasycznego 27B. Głowica MTP `blk.64` (nextn) zostaje w GGUF. Wizja przez osobny `mmproj`.

Plik: `~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf` (unsloth), 16.35 GiB, mieszane kwanty (Q5_K 7.9 GB, IQ4_XS 3.1, Q4_K 3.1, Q6_K 2.9, reszta 0.7).

Nasze ustawienia (`run-llm.sh qwen`): ROCm, ctx 204800, KV q4_0, MTP n=4, słownik draftu 64k, draft IQ4_XS, KV draftu q4_0, `EFFORT=low`.

Wyniki na XTX:
- start 2026-10-09 (stary build, MTP n=3): 59.2 t/s (serve_bench, mieszanka EN/PL, T=0);
- 2026-10-15 (`amd-opt`, spec_sweep 6×3, T=1): **109.0 t/s**, 27.74 ms/krok, pp4096 1115, tg128 bez spekulacji 43.2;
- długi kontekst (2026-10-14, T=0, przed PM4): 1.7k 130.2 / 29.5k 105.2 / 94k 100.6 t/s.

Licencja: Apache 2.0.

## Powiązane
- [[modele/_hub|Modele]]
- [[qwen3-8-27b-uncensored]]
- [[glowica-mtp]]
- [[gdn-replay]]
- [[stan-2026-10-15]]
