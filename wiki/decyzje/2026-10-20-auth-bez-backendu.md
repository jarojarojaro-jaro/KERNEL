---
typ: decyzja
tags: [decyzje, produkt, konto, auth]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/app/landing/AUTH.md:3-11,17,22; git `8a1d36d`
status: aktualne
---
# 2026-10-20: logowanie bez backendu – `PUBLIC_AUTH_PROVIDER=none`, wymienne Supabase / Auth.js

**Nie ma jeszcze backendu ani domeny, więc landing buduje się z `PUBLIC_AUTH_PROVIDER=none`: przyciski Google/GitHub widoczne, ale wyłączone, a pole e-mail zapisuje na listę oczekujących; backend wybieramy później przez zmianę jednej zmiennej (`supabase` albo `authjs`).**

- Krok konta rozmawia tylko z `src/lib/auth` (`signInWith`, `signInWithEmail`, `getSession`, `signOut`); inna wartość zmiennej przerywa build (`AUTH.md:3-11`).
- Oba żywe backendy wymagają prawdziwej domeny po https – Google odrzuca redirect na adres IP i `http` (`AUTH.md:11`).
- `.env` (commitowany) trzyma tylko wartości publiczne; sekrety w `.env.local` (git-ignored) (`AUTH.md:17`).
- Instrukcja wdrożenia: `app/landing/AUTH.md`. Pierwotna decyzja o koncie na początku: [[2026-10-16-landing-i-konto]].

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[2026-10-16-landing-i-konto]]
- [[app-landing]]
- [[app-onboarding-prototyp]]
