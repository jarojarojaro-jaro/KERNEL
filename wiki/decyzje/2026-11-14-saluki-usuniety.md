---
typ: decyzja
tags: [decyzje, enigma, licencje, modele, strona]
aktualizacja: 2026-11-14
zrodlo: zlecenie operatora z rozmowy właściciela 2026-11-14 ~18:10 (Telegram „gpu” 19:29); ~/KERNEL/app/engine (katalog, planer, testy); ~/KERNEL/product/research/67-nvidia-vast-kampania.md:19-20,68; ~/KERNEL/product/SITE-NVIDIA.md
status: aktualne
---
# 2026-11-14: Saluki usunięty całkowicie; na stronie zawsze najnowsze pomiary

**Decyzje właściciela (2026-11-14): (1) Underdog Saluki 27B (CC BY-NC 4.0, tylko niekomercyjnie) znika ze strony i z aplikacji Enigma w całości. Słowa właściciela: „saluki wypierdalamy już totalnie”. (2) Na stronie zawsze najnowsze i najlepsze pomiary: „na tym to polega, updatujemy, dajemy nowsze i lepsze optymalizacje”.**

- **Strona:** enigmalabz.com bez klucza `saluki`, na żywo od 14.11 16:49 (KERNEL `0b73b58`, [[karty-nvidia-na-stronie]]).
- **Aplikacja Enigma:**
  - katalog bez modelu `saluki-27b` i bez licencji `cc-by-nc-4.0`;
  - planer bez wierszy Saluki, a w zamian zmierzony Bonsai 2 Q2_0 upstream 196 608 (4070, 3060);
  - z UI zniknęły tekst licencji niekomercyjnej i kolor modelu;
  - z testów zniknęły punkty VRAM Saluki; doszedł test, że Saluki nigdzie się nie pojawia.
- **Domyślne wybory na 12 GB:**
  - Linux z silnikiem prism: Bonsai 2 PTQ1_0 + MTP n2, 4070 208 896 (94,73 t/s), 3060 204 800 (58,31 t/s);
  - zwykły llama.cpp (Windows/macOS albo bez naszych silników): Bonsai 2 Q2_0, 4070 49,43 t/s, 3060 32,23 t/s przy 65 536.
  - Licencja w obu przypadkach Apache-2.0.
- **Stała procedura:** po każdej kampanii pomiarów zgłaszam właścicielowi, które karty na stronie odświeżyć (karta, stara → nowa liczba, źródło).
- **Wyjątek:** `app/landing/src/lib/data/cloud-results.json` ma jeszcze surowe wiersze Saluki z kampanii 2026-10-16. Stronę prowadzi Jarvo, więc tylko zgłoszone.

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[saluki]]
- [[final-recipes-nvidia]]
- [[lekcja-licencja-modelu-sie-zmienia]]
- [[2026-10-16-saluki-bonsai-na-3060]]
