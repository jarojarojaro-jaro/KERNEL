---
typ: hub
tags: [latki, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Łatki

**Łatki forka llama.cpp (seria amd-opt 0001–0070 i dalsze), manifest i wyłączniki.**

Źródło prawdy o łatkach: `qwen-opt/patches/` i `product/research/patch-manifest.json`. Gałęzie i worktree: [[repo/_hub|Repo]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (8)

- [[latki-do-upstreamu|Kandydaci do upstreamu llama.cpp]] — Ogólne łatki (sampler, host, clamp, cache q8_1) warto oddać do upstreamu, bo każda łatka tam to jedna mniej do rebase'owania; wyróżnikiem produktu zostają przepisy per (GPU, model).
- [[klasyfikacja-latek|Klasyfikacja 70 łatek (raport 07)]] — Z 70 łatek 45 jest bitowo identycznych, a zysk Qwena (41.7 → 27.74 ms/krok) w ~48% pochodzi z łatek pod architekturę modelu, ~30% z łatek pod RDNA3, ~22% z ogólnych.
- [[patch-manifest|Manifest łatek (patch-manifest.json)]] — Maszynowy opis każdej z 70 łatek `amd-opt`: gdzie działa, jaka poprawność, jaki zysk i jaki wyłącznik; wynik analizy platformy z 2026-10-15.
- [[seria-amd-opt|Seria łatek amd-opt (0001–0070)]] — 70 commitów nałożonych liniowo na upstream llama.cpp `e60eff95f` (2026-10-09); gałąź `amd-opt` @ `f61994f58`, zainstalowana w `~/llama-opt`.
- [[wylaczniki-env|Wyłączniki env łatek]] — Każdy przełącznik jest domyślnie włączony; `=0` przywraca ścieżkę sprzed łatki w tej samej binarce.
- [[latki-hostowe|Łatki hostowe (CPU, pętla spekulacji)]] — Zmiany po stronie CPU, które skracają krok niezależnie od GPU: asynchroniczne wejścia, zbiorczy upload, tani rollback i maska KQ w pętli spekulacji.
- [[latki-oczekujace|Łatki oczekujące (poza amd-opt)]] — W `qwen-opt/patches/pending/` leżą łatki z gałęzi, które nie weszły do `amd-opt`: GDN fast (`opt-gdn6`) i runda 5 Qwena (`opt-qwen5`).
- [[latki-spekulacji|Łatki spekulacji (słownik draftu, requant, okno, adaptacja)]] — Łatki zmieniające sam mechanizm draftu MTP: część dała zysk (słownik 64k, draft IQ4_XS), część została opt-in albo okazała się negatywna.
<!-- AUTO:END -->
