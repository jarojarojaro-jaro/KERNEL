---
typ: repo
tags: [repo, modele, agenci]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21h-rsi.md:264-293; https://huggingface.co/IntelligenceLab/RSR-27B (HF API 2026-10-19); https://arxiv.org/abs/2610.02826
status: do-sprawdzenia
---
# RSR-27B (IntelligenceLab): Qwen3.8-27B po RSR + RL

**Wydany model `IntelligenceLab/RSR-27B` (Apache-2.0, `qwen3_5`, 64 warstwy, 27.78 mld parametrów BF16) to Qwen3.8-27B dostrojony na przepisanych trajektoriach RSR + „dodatkowe RL”; tensory `mtp.*` (15) i `model.visual.*` są skopiowane z bazy (`model-missing-from-origin-*.safetensors`), więc głowica MTP nie pasuje do zmienionego pnia (2026-10-19).**

- Nasz silnik: ta sama architektura → konwersja GGUF i kwant jak dla Qwena `[INFERENCE]`; md5 to nowe bazy; PM4/kvq bez zmian; lookup tail do ponownego pomiaru.
- MTP: oczekiwany spadek akceptacji; naprawa pipeline'em z raportu 11 (dopasowanie `blk.64.*`, koszt tam $2.14) ([[glowica-mtp]]).
- W pracy RSR samo SFT dało TB 2 pass@3 57.0 → 74.2%. To nie jest Terminal-RSI-27B (niewydany: „Code soon / Model soon”, repo 404).
- Produktowo: osobny wybór w katalogu („Qwen-agent”), nie przyspieszenie; agent po RL robi więcej tur (RPR-1 50 → 84.8, RPR-2 83.8 → 116.8), czyli 5.3–7.9 min dekodowania na zadanie przy 103.7 t/s.

## Powiązane
- [[repo/_hub|repo]]
- [[qwen3-8-27b]]
- [[raport-21h-rsi]]
- [[2026-10-19-plan-e1-rsr27b]]
