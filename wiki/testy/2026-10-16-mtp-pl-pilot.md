---
typ: test
tags: [testy, mtp, trening, wynik-negatywny]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/11-mtp-pl-pilot.md:3-9,66-93,104-132,164-171; ~/KERNEL/product/research/11-mtp-pl-pilot.md:1-189
status: aktualne
---
# 2026-10-16: pilot douczania głowicy MTP (wynik negatywny)

**Douczanie wbudowanej głowicy MTP Qwen3.8-27B na naszym Q4 (RunPod A40, 3.50 h, $2.14) nie dało zysku: offline najlepszy przebieg +0.2%, online n=4 PL-proza +2.3% i pozostałe klasy 0 do −1.7%.**

- Pipeline: `llama-mtp-extract` (gałąź `mtp-train`) → lustro PyTorch grafu MTP (parytet: tok/krok 3.268 llama.cpp vs 3.266 lustro) → trening FastMTP (K=5, 0.9·TV + 0.1·CE) → zapis do GGUF bez dotykania pnia.
- Dane: 0.39 M tokenów on-policy (odpowiedzi naszego Q4) + 1.32 M off-policy z datasetów (WildChat, oasst2, aya, self-oss-instruct); generacja na A40 była wąskim gardłem (~100–140 tok/s przy `-np 32`).
- Bramka offline: zapas wyroczni +21% (all) i +27% (PL-proza), więc pilot ruszył; trzy przebiegi: −0.2%, +0.21%, +0.02%.
- Online (spec_sweep ABBA, A40): n=4 median 78.9 / 78.7 (A) vs 78.3 / 78.5 t/s (B); ms/krok bez zmian.
- Pień nietknięty: md5 plain i MTP identyczne dla oryginału i nowego pliku.
- Plik `~/models/draft-exp/Qwen3.8-27B-UD-Q4_K_XL-mtpPL.gguf` czeka na opcjonalny test potwierdzający na XTX.
Werdykt: nie skalować do 10 M tokenów; ewentualny mikro-zysk to blok MTP w Q6_K zamiast IQ4_XS (+0.45% offline).

## Ze scalonej notatki: Raport 11: pilot douczania głowicy MTP

Wynik negatywny (2026-10-16, RunPod A40, $2.14): douczona głowica MTP Qwen3.8-27B na 1.7 M tokenów zmienia tok/krok o ±2% (offline +0.2% w najlepszym przebiegu); fabryczna głowica jest już blisko optimum dla tej skali danych.

- Bramka offline (held-out on-policy): fabryczna głowica 3.266 tok/krok przy n=4, wyrocznia greedy 3.960 (+21%); PL-proza 3.009 vs 3.812 (+27%) – zapas jest u wyroczni, nie u głowicy.
- Trening FastMTP (K=5, β=0.65, 0.9·TV + 0.1·CE): train1 1.71 M tok −0.2%; train2 tylko on-policy 0.39 M +0.21%; train3 CE +0.02%. Dane off-policy szkodzą (3.281 → 3.235).
- Pomiar na A40 (spec_sweep ABBA): n=4 PL-proza 2.65 → 2.71 (+2.3%), pozostałe klasy 0 do −1.7%; ms/krok bez zmian.
- Pień nietknięty: greedy md5 plain `7f63dec8…` identyczne dla obu plików; bajty poza `blk.64.*` – 0 różnic.
- Głowica w pliku to Q6_K/Q8_0/F32 (351 008 768 B); IQ4_XS powstaje przy ładowaniu i kosztuje ok. −0.45% tok/krok offline.
- Lekcje: w kontenerze RunPod `llama-server` bierze 96 wątków przy limicie 7.65 CPU → `-t 6 -tb 6`; segfault forka z `--spec-mtp-type` i buforami CPU_REPACK (obejście `--no-repack`).
Rekomendacja: nie skalować do 10 M tokenów; test na XTX tylko jako potwierdzenie.

## Powiązane
- [[testy/2026-10-16-mtp-pl-pilot]]
- [[2026-10-12-mtp-trening-faza1]]
- [[glowica-mtp]]
- [[lekcja-mtp-glowica-optimum]]
- [[mtp-train]]
