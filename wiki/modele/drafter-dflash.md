---
typ: model
tags: [modele, dflash, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/drafters.md:9-11,28-29,44-57; ~/KERNEL/qwen-opt/NOTES.md:45-50,148-160; ~/KERNEL/qwen-opt/research/qwen-round5.md:26-28; ~/KERNEL/qwen-opt/SPEC-QWEN27B.md:24,74-75; ls ~/models/draft (2026-10-16)
status: aktualne
---
# Drafter DFlash2 dla Qwen3.8-27B

**Osobny mały model draftujący (z-lab / incoai, 5 warstw) — świetny na angielski kod przy T=0, ale na szerszym zestawie i po polsku nie bije głowicy MTP, więc domyślnie używamy MTP.**

- Plik: `~/models/draft/Qwen3.8-27B-DFlash2-Q4_K_M.gguf` (1.06 GiB); architektura: 5 warstw, hidden 5120, SWA 2048, selektor top-16, blok 8 (7 draftów), tapy z warstw 5/19/33/47/61 celu.
- Publikowane AL (H200, T=1, thinking xhigh): MT-Bench MTP 3.74 / DFlash2 4.10; GSM8K 5.02 / 5.46.
- U nas:
  - 2026-10-09: upstream DFlash2 n=7 97.7 t/s, nasze kernele n=6 111–112 t/s, z cache q8_1 115.7 (prompty EN); po polsku 65 t/s (MTP 78) — drafter słabo zna polski;
  - 2026-10-10 (zestaw PL/EN, 285 W): przy T=0 mediana DFlash n=6 90.6 vs MTP n=5 86.3; przy T=1 71.9 vs 81.1 (DFlash nie ma rejection sampling); „120 t/s” to był jeden prompt;
  - 2026-10-15 (runda 5): szeroki blok n=15 wolniejszy niż n=6 (EN kod 89.7 vs 104.8 t/s) przy tych samych zaakceptowanych tokenach.
- Pomysł z drafters.md: probabilistyczny wybór ścieżki + rejection w llama.cpp (~40 linii) — szacunek +20–24% na EN czat T=1, niezrobione.
- `run-llm.sh qwen dflash` uruchamia wariant DFlash.

## Powiązane
- [[modele/_hub|Modele]]
- [[glowica-mtp]]
- [[latki-oczekujace]]
- [[qwen-runda-5]]
- hipfire
