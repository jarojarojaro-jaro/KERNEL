---
typ: lekcja
tags: [lekcje, gpu, nadzor]
aktualizacja: 2026-10-19
zrodlo: komunikat Main do WikiIngest 2026-10-19
status: aktualne
---
# Agent główny nie patrzył na temperatury; `journalctl -k` widzi tylko bieżący boot

**2026-10-18/19 agent główny sam nie śledził temperatur GPU – to użytkownik zgłosił 90 °C pamięci VRAM; ponadto agent błędnie stwierdził „brak innych resetów od 15.10”, bo `journalctl -k` pokazuje tylko bieżący boot, a resetów było 10 w bootach −2, −1 i 0.**

Reguły:
- przy każdym długim przebiegu GPU działa [[gpu-guard]] z wczesnym ostrzeżeniem (VRAM ≥ 85 °C, hotspot ≥ 90 °C), a agent główny reaguje na nie sam;
- historia zdarzeń sterownika: `journalctl --list-boots`, potem `journalctl -k -b <n>` dla każdego bootu; twierdzenia „nie było” sprawdzać na wszystkich bootach.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
- [[lekcja-wentylator-rdna3]]
- [[lekcja-tmp-po-restarcie]]
