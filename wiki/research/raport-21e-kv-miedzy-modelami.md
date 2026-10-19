---
typ: research
tags: [research, kv, modele]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21e-kv-miedzy-modelami.md:1-267; https://arxiv.org/abs/2608.03893
status: aktualne
---
# Raport 21e: KV między modelami (NVIDIA 2608.03893) i Uncensored jako edycja rank-1

**Przenoszenie KV z małego modelu do dużego (ridge per głowica, matched-KV, tylko dense full-attention) nie pasuje do naszych hybryd, a jego obietnica nie wynika z danych pracy; za to analiza wag pokazała, że oba nasze modele Uncensored to dokładne ablacje kierunku na Mainie – więc przełączanie Main ↔ Uncensored może być niemal darmowe.**

- Paper: 73–98% retencji na 4/6 parach (63–96% po normalizacji do losowego), 2.7–25× vs re-prefill na 8×H100 (bez prefillu źródła i wczytania mappera 4–12 GB). Brak bazy „zostań na źródle”: transfer < źródło na średniej z 5 benchmarków we wszystkich 4 udanych parach (Qwen3 14B→32B 76.07 vs 76.50; 8B→32B 67.59 vs 72.76; Llama 8B→70B 54.57 vs 63.71; Ministral 3B→8B 53.72 vs 65.64), na GSM8K zawsze gorszy.
- Dla nas wprost nie: hybrydy (Qwen 48 GDN + 16 atencji, LFM 30 shortconv + 10 atencji), LFM ↔ Qwen to różne tokenizery (128 000 vs 248 320). LFM w ogólnym przypadku łatwy (stan shortconv ≤ 60 tokenów), Qwen GDN trudny ([[pamiec-stanu-gdn]]).
- Uncensored: [[uncensored-ablacja-kierunku]]; przełączanie: [[przelaczanie-main-uncensored]].
- Eksperymenty: E1 (CPU, 15 min) kontrola rank-1 dla wszystkich writerów; E2 (XTX ~1 h) identity transfer Main → Uncensored, bramka KLD ≤ 0.01 i różnica refusal rate ≤ 5 pp (kill: KLD > 0.05 albo > 10 pp); E3 (2–3 dni) tryb w locie z wyłącznikiem, narzut ≤ 2% bez fuzji.

## Powiązane
- [[research/_hub|research]]
- [[qwen3-8-27b-uncensored]]
- [[lfm2-5-uncensored]]
- [[kv-na-dysku-polityka]]
