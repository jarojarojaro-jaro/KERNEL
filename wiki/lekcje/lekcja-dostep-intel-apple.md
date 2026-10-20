---
typ: lekcja
tags: [lekcje, chmura, intel, apple]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/30-intel-apple-dostep.md:7-10,31,36-38,142-147; informacja użytkownika o Enverge przekazana przez Main 2026-10-20
status: aktualne
---
# Dostęp w chmurze: Intel Arc bez wynajmu godzinowego, Apple z minimum 24 h, Enverge co minutę

**Przed planowaniem testów na Intel/Apple: Arc nie ma wynajmu godzinowego nigdzie (Vast 2026-10-20: 0 z 5039 ofert), Apple u AWS/Scaleway ma minimum 24 h z licencji macOS, Enverge rozlicza co minutę, a Darkbloom to API inferencji, nie maszyna (raport 30).**

- **Intel Arc**: tylko dedyk miesięczny (GigaGPU Arc Pro B60 £129/mies.) albo zakup B580; Vast/TensorDock/Hetzner/OVH/Scaleway/Tiber – brak Arc. Na Vast działa składnia `gpu_arch=intel`, nie operator `~`.
- **Apple**: macOS SLA §3A wymaga leasingu ≥ 24 kolejnych godzin – AWS EC2 Mac, Scaleway i MyRemoteMac to egzekwują (Scaleway M4-M 32 GB: €6.96 za sesję).
- **Enverge**: Mac Studio M5 Ultra 256 GB, $2.50/h, rozliczenie co minutę, bez minimum – najtańszy krótki test Apple Silicon. Mały kanadyjski startup; użytkownik potwierdził 2026-10-20, że to prawdziwa firma [INFERENCE: weryfikacja użytkownika, nie nasza].
- **Darkbloom**: API zgodne z OpenAI na cudzych Makach, bez SSH i roota – do benchmarków się nie nadaje.
- Najtańszy start: M1 Pro użytkownika (0 zł).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[raport-30-intel-apple]]
- [[arc-b580-i-mac]]
- [[vast-ai]]
- [[raport-05-chmura]]
