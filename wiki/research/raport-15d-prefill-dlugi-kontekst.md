---
typ: research
tags: [research, prefill, dlugi-kontekst, lucebox]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15d-prefill-dlugi-kontekst.md:1-41,99-126; ~/KERNEL/product/research/16c-kvq-cuda.md:10
status: aktualne
---
# Raport 15d: prefill i długi kontekst (PFlash v2, KVFlash, cache sesji)

**Największa bezstratna strata przy długim kontekście na NVIDIA to kernel atencji, nie prefill: port naszego `kvq` na CUDA to top pomysł; PFlash v2 to tryb stratny opt-in, KVFlash odrzucony, dyskowy cache sesji to realny bezstratny brak.**

Raport 2026-10-16, bez GPU, pilot na CPU.
- 3090 tg przy 64k: Qwen 27.2, LFM 147.7 t/s; model „vec czyta KV osobno dla każdej głowy Q” zgadza się z pomiarem (LFM +3.05 ms przewidziane vs +2.80 ms zmierzone; Qwen +7.7 ms przy 100% pasma vs +11.4 ms). MTP przy długim kontekście na NVIDIA nikt nie zmierzył.
- L1 port `kvq` na CUDA: tg@64k +36% (szacunek), MTP@64k +30–55%; upstream zamknął #29827 i #29846. Zrealizowane w [[raport-16c-kvq-cuda]]: +36.8% tg, MTP@64k +27.6%; korekta: baza MTP@64k na 3090 to już 70.3 t/s, nie szacowane ~52–55 t/s.
- PFlash v2 (Lucebox): drafter Qwen3.5-0.8B BF16 przelicza 15 bloków, trzy małe sieci tną prompt na jednostki; jakość 92/124 vs 94, LongBench-v2 4/12 vs 7/12, MTRAG 189/255 vs 197; TTFT ×3.7 na R9700, niezależnie ×3.3/×4.0/×5.4 przy 20K/40K/120K (#752). Dla agenta kodującego prawie zero (próg 16K nowych tokenów, historia surowa).
- Pilot CPU: sonda żądania (trenowana po angielsku) wskazała pytanie jako top-1 w 1/10 przypadków PL i 10/10 EN.
- KVFlash: nie (igła 14/16 vs 16/16, bazowy prefill 694 t/s wolniejszy niż llama.cpp 1168 t/s).
- Dyskowy cache sesji Lucebox: wznowienie 45K sesji po restarcie 2.6 s zamiast 56.2 s, bajtowo identycznie; llama-server ma tylko `--cache-ram` i ręczny zapis slotów.
- Przepis syv-ai (22.4 → 0.56 s) to prefix cache, który llama.cpp już ma.
- Prefill NVIDIA: fork −1.5…−1.9% w llama-bench; TTFT +4.8% vs A1, głównie hook MTP na prompt (150 ms przy 2k).
Ranking bezstratnych: L1 kvq CUDA, L2 audyt cache agenta, L3 dyskowy cache sesji, L4 hook MTP w grafie, L5 bisect prefillu NVIDIA, L6 LFM `-b 2048 -ub 2048`.

## Powiązane
- [[research/_hub|research]]
- [[fattn-kvq]]
- [[fa-kv-kwantyzowane-cuda]]
- [[2026-10-16-pflash-pilot-cpu]]
- [[lucebox]]
- [[tryb-stratny-pflash]]
