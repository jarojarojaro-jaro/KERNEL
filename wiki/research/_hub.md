---
typ: hub
tags: [research, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Research

**Streszczenia raportów badawczych: produktowych (01–10), technicznych i głównego raportu o AMD.**

Pełne raporty leżą w `product/research/`, `qwen-opt/research/` i `reports/`; tu są wnioski z liczbami i linkami.

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (13)

- [[repos-30-przeglad|Przegląd 30 repozytoriów (REPOS-PODSUMOWANIE)]] — Przegląd 30 repo o kernelach GPU + aktualizacja TensorFold (2026-10-14): werdykty, ranking eksperymentów dla LFM i Qwena oraz lista odrzuconych pomysłów.
- [[raport-01-konkurencja|Raport 01: konkurencja]] — Detekcja sprzętu i rekomendacja modelu to już standard; żaden produkt konsumencki nie łączy pomiaru, długiej optymalizacji poza flagami, weryfikacji bitowej i raportu przed → po (stan 2026-10-15).
- [[raport-02-autotuning|Raport 02: autotuning i agenci kerneli]] — Duże „przed → po” robi praca wykonana raz w labie, nie strojenie u użytkownika; agenci kerneli działają tylko z mocną bramką i zostają w labie.
- [[raport-03-silniki|Raport 03: silniki inferencji i stack]] — Bazą zostaje llama.cpp jako cienki overlay łatek, nie twardy fork; rdzeń w Rust, GUI w Tauri 2, daemon z API OpenAI na 127.0.0.1.
- [[raport-04-sprzet|Raport 04: wykrywanie sprzętu i dobór modeli]] — Wykrywanie sprzętu dwuwarstwowe (inwentarz API + capability probe w podprocesie), estymacja pamięci z llama.cpp `--fit`, a prędkości z modelu dwuczłonowego pasmo + liczba kerneli.
- [[raport-05-chmura|Raport 05: chmura GPU do testów]] — NVIDIA wynajmujemy tanio (Vast od 0.08 $/h), a konsumenckich Radeonów z rootem w chmurze praktycznie nie ma, więc AMD, Intel kupujemy, Apple wynajmujemy w Scaleway.
- [[raport-06-produkt|Raport 06: produkt, UX, prawo, biznes]] — Nisza „lokalne przyspieszenie twojej karty” jest pusta, ale łatwa do skopiowania; obrona to katalog profili i bitowa identyczność, a AI Act dotyczy nas jako providera aplikacji czatu.
- [[raport-07-metody|Raport 07: nasze metody i uogólnienie]] — 70 łatek: 45 bitowo identycznych, 6 te same tokeny, 3 tylko drafty, 3 poprawki, 7 zmienia numerykę (4 przeszły KLD); proces jest powtarzalny, ~60 h zegarowych w 6.4 dnia.
- [[raport-08-platforma|Raport 08: analiza platformy 70 łatek]] — HIP na Windows działa na PAL, nie na ROCr, więc PM4 replay (0060, 0061) tam nie działa; z zysku XTX na NVIDIA pewne jest 25% (host), realnie do testu ok. +14–16%.
- [[raport-10-post-training|Raport 10: trening i post-training]] — Do obietnicy produktu najlepiej pasuje trening draftera, nie modelu: fine-tune głowicy MTP Qwen3.8-27B przez self-distillation na trunku Q4, szacunek +10–17% tok/krok na czacie PL za $0–4.
- [[raport-12-bit-exact|Raport 12: bitowo identyczna spekulacja]] — Plain greedy (`c4708318`) i MTP (`6f14e814`) dają różne md5, bo ta sama pozycja liczona jest innym kernelem przy N=1 i N=2..6; tryb `LLAMA_SPEC_BITEXACT=1` daje N=1 arytmetykę kerneli wielokolumnowych.
- [[raport-13-rocm-10-1|Raport 13: ROCm 10.1]] — ROCm 10.1 nic istotnego nie daje na gfx1100: zostajemy na 10.0, a 10.1 trzymamy obok jako tarball user-local; ważniejsze odkrycia to ATT na gfx1100 i przyczyna PMC = 0.
- [[runda-6-raporty|Runda 6: raporty GDN, MMQ i narzędzi]] — Trzy raporty rundy 6 (2026-10-15), wszystkie bez GPU: szybki kernel GDN bitowy z konstrukcji, epilog MMQ w VOPD oraz narzędzia LOO / kanarki KLD / Kernel Tuner.
<!-- AUTO:END -->
