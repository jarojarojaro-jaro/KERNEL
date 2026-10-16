---
typ: lekcja
tags: [lekcje, determinizm, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:265; ~/KERNEL/product/research/12-bit-exact-spekulacja.md:8
status: aktualne
---
# Spekulacja zmienia numerykę batcha

**MTP rozjeżdża się z plain po 129 znakach, DFlash po 229; zmiana draftu zmienia tekst przy remisie, więc MTP porównujemy z bazą MTP, nie z plain.**

Przyczyna (raport 12): ta sama pozycja tokenu liczona jest innym kernelem przy N=1 (plain) i przy N=2..6 (weryfikacja). Dziś na 7900 XTX: Qwen plain md5 `c4708318`, MTP `6f14e814`. Konsekwencja produktowa: obietnica „identyczne z poprzednim buildem w tym samym trybie”, nie „identyczne z dekodowaniem bez spekulacji” – dopóki tryb `LLAMA_SPEC_BITEXACT` tego nie zmieni.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-ten-sam-serwer-pending-h]]
- [[lekcja-bit-exact-attention]]
- [[zgodnosc-bitowa-md5]]
- [[raport-12-bit-exact]]
