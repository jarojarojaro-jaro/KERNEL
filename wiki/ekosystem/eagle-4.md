---
typ: ekosystem
tags: [ekosystem, spekulacja, drafter]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/52-eagle4.md:1-30; ~/KERNEL/product/research/52-eagle4.md:14-30
status: aktualne
---
# EAGLE-4 (eagle-hq/EAGLE-4)

**Paper + harness + drafter Qwen3.8-27B-EAGLE4 (`7b7b5a5`, 2026-10-20); dla nas przydatny Efficient LM Head (low-rank wyszukiwanie kandydatów), drafter licencyjnie tylko do ewaluacji.**

- Drafter: EAGLE-3.1, cechy z warstw 3/31/59, 0.435 mld param., 6.18 GB BF16.
- 961.6 t/s z niepublicznego PR – niesprawdzalne.

## Ze scalonej notatki: Raport 52: EAGLE-4 – co bierzemy

Najcenniejszy jest EAGLE Efficient LM Head na naszej głowicy MTP (low-rank r=128 po 248k + dokładne 128 wierszy): szacunek proza PL +3…6% `[INFERENCE]`; drafter EAGLE-4 licencyjnie do ewaluacji, 961.6 t/s niesprawdzalne.

- Taśma draftu −0.5 ms/krok; znika OOV 64k (14% pęknięć PL).

## Powiązane
- [[ekosystem/eagle-4]]
- [[raport-53-draft-shortlist]]
- [[glowica-mtp]]
