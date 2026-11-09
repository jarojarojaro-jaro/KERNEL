---
typ: produkt
tags: [produkt, windows, amd, ssd, ux]
aktualizacja: 2026-11-09
zrodlo: ~/KERNEL/product/research/69d-amd-sterownik-ssd.md:6-11,16-28,31-50,55-58; https://wccftech.com/amd-acknowledges-radeon-driver-bug-causing-constant-ssd-writes-fix-in-the-works/; https://windowsforum.com/news/amd-radeon-ssd-write-bug-how-to-check-atieclxx-exe-on-windows-10-and-11.450605/
status: do-sprawdzenia
---
# AMD Adrenalin: ciągłe zapisy SSD przez `atieclxx.exe` (Windows)

**Usługa AMD External Events Utility (`atieclxx.exe`) w sterownikach 26.6.4–26.10.2 stale zapisuje na dysk systemowy, typowo 0.3–1.5 MB/s (26–130 GB/dzień); nasz serwer Linux nie jest dotknięty, a Enigma na Windows+AMD powinna ostrzegać na podstawie pomiaru i nigdy nie radzić wyłączania ReBAR (2026-11-09).**

- **Fakty:** AMD potwierdziło błąd (forum, październik); przyczyna wg przedstawiciela AMD (za Neowin, 8.11): interakcja z filtrem PCIe Microsoftu, poprawka w walidacji, bez daty. Numer „26.11.1” niepotwierdzony. „432 GB/dzień” = jedno zgłoszenie 5 MB/s × 24 h zapisów hosta. Ta sama wersja (26.10.2) działa u jednych źle, u innych dobrze – sama wersja nie wystarcza.
- **Obejścia:** zatrzymanie usługi (odwracalne, ale psuje FreeSync, hotkeye, hot-plug monitorów); wyłączenie ReBAR (obejście AMD). **Nigdy nie radzić wyłączania ReBAR:** bez niego okno BAR ma 256 MB, ładowanie wag i offload idą przez staging `[INFERENCE: niemierzone]`.
- **Serwer:** amdgpu, brak odpowiednika usługi; ReBAR aktywny (BAR0 32 GiB). Nie dotyczy.
- **Polityka KV:** sam błąd to 2.6–13× naszego budżetu zapisu 10 GB/dzień – argument za „KV w RAM” ([[kv-na-dysku-polityka]]).
- **Proponowana karta UX** (hardware scan, tylko Windows+AMD): wersja z rejestru → 30 s pomiaru zapisów `atieclxx` w bezczynności → przy ≥ 0.2 MB/s żółte ostrzeżenie (aktualizuj sterownik po poprawce; opcjonalnie zatrzymaj usługę; nie wyłączaj ReBAR), bez automatycznych akcji; osobna informacja, gdy ReBAR wyłączony. Decyzja: [[raport-69-synteza]].

## Powiązane
- [[produkt/_hub|Produkt]]
- [[kv-na-dysku-polityka]]
- [[produkt-optymalizacja-u-uzytkownika]]
- [[raport-21d-kv-na-dysku]]
- [[wsl2-rocm]]
