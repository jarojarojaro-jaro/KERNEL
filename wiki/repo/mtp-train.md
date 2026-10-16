---
typ: repo
tags: [repo, galezie, mtp, trening]
aktualizacja: 2026-10-16
zrodlo: git -C ~/llama-master log --format=%h\ %ad\ %s 7a538d96f..mtp-train; ~/KERNEL/product/research/10-post-training.md:29-34; ~/KERNEL/product/research/11-mtp-pl-pilot.md:3-9,17
status: aktualne
---
# Gałąź mtp-train (llama-mtp-extract)

**Gałąź `mtp-train` @ `532fd1057` (2026-10-16) = `cuda-v070` + 1 commit: narzędzie `llama-mtp-extract` do danych treningowych głowicy MTP.**

Commit: „tools: llama-mtp-extract – target h_nextn / top-k teacher logits / greedy MTP draft chains for MTP head training and offline acceptance”. Służy planowi z raportu 10: self-distillation głowicy MTP Qwen3.8-27B na naszym trunku Q4 (zmienia się tylko `blk.64.*`), szacunek +10–17% tok/krok na czacie PL. Pilot (RunPod A40, 2026-10-16) użył tego narzędzia do ekstrakcji danych; wynik negatywny: ±0.2% tok/krok offline, głowica fabryczna jest już blisko optimum.

## Powiązane
- [[repo/_hub|repo]]
- [[galezie-rund]]
- [[speculators-specforge]]
- [[glowica-mtp]]
- [[raport-10-post-training]]
- [[raport-11-mtp-pl-pilot]]
