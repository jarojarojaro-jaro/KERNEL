---
typ: research
tags: [research, spekulacja, drafter]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21a-dspine.md:1-328
status: aktualne
---
# Raport 21a: DSpine vs MTP4 + ogon W16 na XTX

**DSpine to uczciwie ulepszona wersja DFlash2 (+4–7% τ przy tych samych danych), ale na XTX nie zastąpi MTP n=4 (109 t/s) na czacie ani ogona lookupu W16 (401 t/s) na code-edit; sens ma tylko jako drafter klasy „nowy kod” w kontrolerze per klasa ruchu przy kontekście ≤ 32k (agent ResDSpine, tylko CPU).**

Model per klasa (τ DFlash2-27B × 1.05–1.20, krok 36–40 ms przy 2k): pl-proza −38…−51%, pl-tech −23…−40%, en-chat −20…+2%, en-tech −17…+6%, nowy kod pl-kod +9…+39%, en-code −6…+19%. Code-edit: sufit 16 tok/krok przy kroku ≥ 36 ms ≤ 444 t/s, przy p = 0.97–0.99 321–413 t/s (−20…+3%); przy długim kontekście przegrywa wyraźnie. Polski to ryzyko nr 1 (dane bez PL; DFlash2 u nas pl-proza 1.32 vs MTP 1.97 tok/krok).

Plan: teraz nic na GPU; opcjonalnie E0 na CPU (teacher-forced τ na Qwen3-8B, kill: τ(pl-proza)/τ(en-chat) < 0.6). W dniu premiery 27B: G0 config (1 h), G1 τ offline na CPU (kill K1), G2 port 5–7 dni za `LLAMA_SPEC_DSPINE=1`, G3 czas draftu (kill K2: D(2k) > 10 ms albo D(64k) > 14 ms), G4 ABBA (kill K3: < +10% na nowym kodzie przy 8k). Oczekiwanie, jeśli przejdzie: mieszanka agenta +2…+7% `[INFERENCE]`.

## Powiązane
- [[research/_hub|research]]
- [[drafter-dspine]]
- [[raport-16i-magnitude]]
- [[lekcja-akceptacja-h100-nie-przenosi-sie]]
