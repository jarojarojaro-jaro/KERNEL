---
typ: eksperyment
tags: [eksperymenty, mtp, trening, wynik-negatywny]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/11-mtp-pl-pilot.md:3-9,66-93,104-132,164-171
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

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[raport-11-mtp-pl-pilot]]
- [[2026-10-12-mtp-trening-faza1]]
- [[glowica-mtp]]
- [[lekcja-mtp-glowica-optimum]]
- [[mtp-train]]
