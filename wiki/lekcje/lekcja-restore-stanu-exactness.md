---
typ: lekcja
tags: [lekcje, cache, determinizm]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21d-kv-na-dysku.md:89-102,154-166
status: aktualne
---
# Restore stanu ≠ zimny prefill; „bajt w bajt” wymaga draftu MTP i zerowania zamaskowanych wierszy

**Nasz zapis slotu (`/slots?action=save`) nie ma fsync, pliku tymczasowego ani rename (`llama-context.cpp:3629` pisze `"wb"` w miejscu), nie ma odcisku modelu (`TODO: add more model-specific info`, `:3657`), a restore czyści kontekst draftu MTP (`server-context.cpp:2717-2719`) – przy 46 niebezpiecznych wyłączeniach dysku i Uncensored o tych samych kształtach to realne ryzyko wczytania uszkodzonego lub obcego stanu (raport 21d, 2026-10-19).**

- Restore == żywy serwer (bajt w bajt) jest osiągalne tylko przy greedy w trybie BITEXACT, z sidecarem draftu MTP, zapisem checkpointu z końca promptu i fingerprintem builda/flag/modelu (zamaskowane wiersze KV zmieniają WMMA o 1–2 ulp, [[lekcja-bit-exact-attention]]).
- Restore == zimny prefill: nie i nie trzeba – inne granice ubatchy dają inną numerykę ([[lfm-czulosc-na-podzial-batcha]]); restore jest wierniejszy.
- Deduplikacja między sesjami tylko po hashu bajtów, nie tokenów.

Reguła: plik stanu = tmp → fsync → rename → fsync katalogu + fingerprint + hash payloadu; uszkodzony plik → ponowny prefill, nigdy dekodowanie z częściowego stanu (wzorzec Straty).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[kv-na-dysku-polityka]]
- [[2026-10-16-bit-exact]]
- [[dysk-serwera-pm9b1]]
