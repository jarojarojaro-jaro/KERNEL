---
typ: lekcja
tags: [lekcje, determinizm, fa]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/12-bit-exact-spekulacja.md:154-197; ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5571,5575; git -C ~/llama-master log -1 77240c9b3
status: aktualne
---
# Bit-exact: ostatnia różnica to atencja

**Test `llama-bx-diff` na 7900 XTX (2026-10-16): z przełącznikiem `LLAMA_SPEC_BITEXACT` warstwy 0–6 są identyczne bit w bit, a pierwsza różnica to wyjście atencji `kqv_out-3` (368 z 6144 liczb, max |d| 1.19e-7); poprawka „jeden token na blok” nic nie zmieniła, więc przyczyna leży gdzie indziej.**

- Bez przełącznika różnice od warstwy 0 (do 0.33); `--no-lag` daje to samo → GDN i jego replay niewinne; Q/K/V przed FA identyczne.
- Pierwsza hipoteza: sąsiedzi w kafelku 16 kolumn (zera vs inne tokeny) wpływają przez WMMA lub wspólne skalowanie. Poprawka `77240c9b3` (jeden token na blok) i wspólne kafle dały **bitowo te same** różnice – hipoteza obalona.
- Pozostali kandydaci: inne komórki cache w kontekście z LAG, inna treść wiersza tokenu 0 w cache, inna maska, niewykonana ścieżka bitexact. Narzędzia gotowe (`6e261fdb4`: log FA, porównanie maski i wierszy cache); dwie komendy GPU (< 2 min) czekają na zgodę.
Lekcja: zanim się naprawia kernel, porównać wszystkie jego wejścia (maska, wiersze cache, adresy), nie tylko Q/K/V.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-spekulacja-zmienia-numeryke]]
- [[lekcja-md5-wzgledem-upstreamu]]
- [[llama-bx-diff]]
- [[fattn-kvq]]
- [[raport-12-bit-exact]]
