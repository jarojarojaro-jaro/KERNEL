---
typ: narzedzie
tags: [narzedzia, dostep, siec]
aktualizacja: 2026-11-06
zrodlo: tailscale status (2026-11-06); instalacja użytkownika (install.sh + tailscale up)
status: aktualne
---
# Tailscale: zdalny dostęp do serwera

**Od 2026-11-06 serwer jest w sieci Tailscale użytkownika (MagicDNS włączony, `tailscaled` uruchamiany przy starcie); zdalnie: `ssh jaro@jaroserverai` z urządzenia zalogowanego na to samo konto.**

- Urządzenia w tailnecie: serwer, komputer z Windowsem, iPhone, drugi serwer Linux.
- Tailscale jest tylko tunelem: logowanie zwykłym SSH (te same hasła/klucze), nic nie jest otwarte na routerze.
- `127.0.0.1:8080` (czat) zostaje lokalny; usługi słuchające na wszystkich interfejsach (np. strona plików Enigmy) widzą tylko urządzenia z tailnetu.
- Adresów IP z tailnetu nie zapisujemy w repo (publiczne).

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[reactor-monitor]]
- [[lekcja-jak-user-testuje-model]]
- [[rx-7900-xtx]]
