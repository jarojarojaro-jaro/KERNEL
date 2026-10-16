---
typ: produkt
tags: [produkt, app, onboarding]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/app/REPORT.md:14,37-39,79-89; ~/KERNEL/app/design/APP-ARCHITECTURE.md:234-260,330-345
status: aktualne
---
# Prototyp onboardingu (konto, 3 drogi, wynik)

**Ścieżki `/start/`, `paths`, `hardware`, `result`, `download`, `terminal` i `/scan/`: konto na początku (Google, GitHub, e-mail – bez backendu), trzy drogi i wynik z przedziałami z estymatora.**

Dokumenty: [REPORT.md](../../app/REPORT.md), [DESIGN.md](../../app/design/DESIGN.md), [APP-ARCHITECTURE.md](../../app/design/APP-ARCHITECTURE.md).

- Formularz sprzętu z autouzupełnianiem GPU (59 pozycji) i wklejaniem kodu skanu `HW1;…;sum=XXXX`; kod z tej maszyny wypełnił formularz poprawnie (RX 7900 XTX, 24 GB, 64 GB RAM, Linux), a kod z ręcznie zmienioną wartością odrzuciła suma kontrolna.
- Estymator na stronie: pamięć wzorem z raportu 04 z zapasem 1 GiB; prędkość przed optymalizacją η·BW/B_tok (η 0,55–0,67 dla gęstych, 0,31–0,55 dla MoE); po L1 ×1,5–2,2 tylko dla modeli ze zmierzonym MTP; L3 „wkrótce” poza RX 7900 XTX; zawsze przedział.
- Wszystko oznaczone jako prototyp: logowanie tylko w sessionStorage, lista oczekujących niczego nie wysyła, przycisk pobierania nieaktywny, komendy terminala to projekt.
- Architektura docelowa: maszyna stanów onboardingu (wariant A z kontem, wariant B bez – kandydat do testu A/B) i łączenie konta z aplikacją przez OAuth 2.0 Device Authorization Grant (RFC 8628).

## Powiązane
- [[produkt/_hub|produkt]]
- [[app-skrypty-skanu]]
- [[app-landing]]
- [[produkt-landing-i-onboarding]]
- [[raport-04-sprzet]]
