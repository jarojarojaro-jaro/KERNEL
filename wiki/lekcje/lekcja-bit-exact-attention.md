---
typ: lekcja
tags: [lekcje, determinizm, fa]
aktualizacja: 2026-10-16
zrodlo: ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5571,5575; git -C ~/llama-master log -1 77240c9b3
status: do-sprawdzenia
---
# Bit-exact: ostatnia różnica to atencja

**Test `llama-bx-diff` na 7900 XTX (2026-10-16): z przełącznikiem `LLAMA_SPEC_BITEXACT` warstwy 0–6 są identyczne bit w bit, a pierwsza różnica to wyjście atencji `kqv_out-3` (368 z 6144 liczb, o ~1·10⁻⁷).**

- Bez przełącznika różnice od warstwy 0 (do 0.33); bez trybu „lag” GDN to samo → GDN i jego replay niewinne. Pierwsza różnica w warstwie 7 jest malutka (3·10⁻⁵).
- Wniosek z kodu: dla 1 i 5 tokenów działa ten sam kernel FA kvq z tą samą arytmetyką na kolumnę; różnią się sąsiedzi w kafelku 16 kolumn (zera vs inne tokeny), a WMMA albo wspólny krok skalowania przenosi minimalny wpływ sąsiadów.
- Poprawka `77240c9b3`: w trybie bitexact jeden token na blok (`GGML_HIP_BITEXACT_FA_SHARED=1` przywraca wspólne kafle). Stan na 2026-10-16: jeszcze nietestowana; potem użytkownik zakazał testów na lokalnym GPU.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-spekulacja-zmienia-numeryke]]
- [[lekcja-ten-sam-serwer-pending-h]]
- [[llama-bx-diff]]
- [[fattn-kvq]]
