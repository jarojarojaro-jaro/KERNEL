---
typ: research
tags: [research, spekulacja, lookup]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/16b-lookup-tail.md:1-180; ~/KERNEL/product/research/21c-copy-paste-lm.md:176-205
status: aktualne
---
# Raport 16b: ogon z lookupu za MTP (15b E1–E3, 16i E-X0–E-X3)

**Agent XtxLookupTail: MTP4 + ogon lookupu do 16 wierszy + łańcuchy daje na edycjach kodu ×2.26–×2.41 na XTX (mvs 401 t/s przy T=0) bez zmiany tekstu greedy i bez kosztu na czacie; kontroler szerokości nic nie dodaje ponad stałe W16.**

- Zalecenie: `LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16` w `run-llm.sh qwen` dla agentów kodujących, najpierw tydzień `LLAMA_SPEC_LOOKUP=1` (log na sucho) na prawdziwym ruchu omp – decyzja użytkownika ([[otwarte-decyzje-produktu]]).
- Potwierdzenie 15b: MTP już kopiuje (P(MTP d1 | lookup d1) = 0.995), lookup wnosi tylko ogon i pominięcie draftu ([[lekcja-mtp-juz-kopiuje]]).
- Prognoza 16i (×2.07–2.41) zgodna z pomiarem; vs Magnitude: W16 14.4 tok/krok przy 35.5 ms, ich DFlash2 7.88 przy 50.2 ms (3090).
- Dalej: kopia ≥ 64k z W16, W16 w BITEXACT (16i #5), krzywa V(w) na CUDA, łańcuchy przy T=1.

Notatki: [[2026-10-18-lookup-ogon]], [[2026-10-18-kontroler-szerokosci-zerowy]], [[koszt-szerokosci-weryfikacji]], [[zestaw-copy-mvs]], [[lekcja-ogon-zmienia-tekst-t1]].

Dalej (21c, 2026-10-19): reguła AGR wyboru kandydata zgodnego z draftami MTP, symulacja +3.7% na agencie ([[agr-lookup-zgodny-z-mtp]]).

## Powiązane
- [[research/_hub|research]]
- [[raport-15b-spekulacja-frontier]]
- [[raport-16i-magnitude]]
- [[2026-10-16-badamy-magnitude]]
