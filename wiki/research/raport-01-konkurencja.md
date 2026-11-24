---
typ: research
tags: [research, konkurencja, rynek]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/01-konkurencja.md:1,14-72; ~/KERNEL/product/research/15c-nowe-silniki.md:374-396
status: aktualne
---
# Raport 01: konkurencja

**Detekcja sprzętu i rekomendacja modelu to już standard; żaden produkt konsumencki nie łączy pomiaru, długiej optymalizacji poza flagami, weryfikacji bitowej i raportu przed → po (stan 2026-10-15).**

- Sprawdzone m.in.: LM Studio, Ollama, Jan, GPT4All, Msty, KoboldCpp, llamafile, Lemonade, Foundry Local.
- Najbliżej luki: flag-tunery (TurboLLM 285★: 74.7 vs 61 t/s na tej samej llama.cpp co LM Studio), silniki jednego modelu (Strata 25.4k★, MTPLX 14.4 → 23.0 tok/s), AMD Lemonade „Auto-Tune” (nic nie wydano), NVIDIA TensorRT for RTX.
- Popyt: Strata 25.4k★, llmfit 38k★, w trackerze Ollamy 190 issues ze „slow” i 165 z etykietą `amd`.
- Producenci sprzętu to kanał, nie konkurent: NVIDIA zamknęła ChatRTX 2026-01-21, AMD dołącza Ollamę i LM Studio do sterownika, Intel zarchiwizował IPEX-LLM 2026-01-28.
- Najgroźniejszy scenariusz: LM Studio/Ollama/Jan same włączą spekulację. Upstream z ręczną spekulacją na 7900 XTX: 68.6 t/s (MTP, ROCm), 85.6 t/s (MTP, Vulkan), 97.7 t/s (DFlash2); nasze kernele dokładają +10–25%.
Werdykt: nisza jest, ale wąska i łatwa do skopiowania; bronią nas dane i bramki.

Aktualizacja (raport 15c, 2026-10-16): teza „kernele u konsumenta: nikt” jest nieaktualna – Magnitude stroi kernele na urządzeniu (60 s, bramka α = 8, nie bitowa), a tqLLM wybiera warianty bit-identyczne przy ładowaniu. Nowa teza: nikt nie łączy strojenia z bitową bramką ani z publikowanym KLD. Nowe wiersze: Magnitude (6.9k★ w 4 miesiące), tqLLM, Actual Computer.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

- Zdanie „nikt nie łączy pomiaru, optymalizacji i bitowej weryfikacji” jest prawdziwe, ale patrzy tylko na nasz wyróżnik. Ci gracze wygrywają tam, gdzie Enigma jest najsłabsza: w dowiezieniu i utrzymaniu działania ([[inference-stack]], „dlaczego Enigma wyszła gorzej”).
- **Instalacja i paczki:** Lemonade 10 MB + backendy dociągane na żądanie, wersja „embeddable” 5–7 MB ([[lemonade]]); LM Studio runtime packs na żądanie ([[lm-studio]]); Jan 530 MB Windows / 95 MB DMG ([[jan]]). U nas jedna binarka Bun, bez aktualizacji z wycofaniem.
- **Izolacja i odporność:** Jan od 0.8.5 trzyma silnik w osobnym procesie (crash nie zabija aplikacji); Ollama ma odkrywanie runnerów z timeoutem. U nas po `ready` nikt nie pilnuje llama-server, klient dostaje 502 ([[inference-stack]]).
- **Dopasowanie do pamięci:** Ollama mierzy pamięć przed załadowaniem; LM Studio pokazuje „Full GPU offload possible” i ma guardraile; Jan „Fits / May be slow / Won't fit”. U nas jest lepiej (zmierzone konfiguracje z kampanii 67 w `app/engine/src/server/catalog/index.ts:205-246`, minimum 131k kontekstu), ale tylko dla kart, które wynajęliśmy.
- **Nasz wyróżnik nie dociera:** jedyny silnik AMD z naszymi kernelami ma `distribution: local` (`app/engine/data/engines.json:264-272`), więc posiadacz Radeona dostaje to samo upstream llama.cpp co w Ollamie, a 165 zgłoszeń `amd` w Ollamie to dokładnie ci klienci.
- Co bierzemy: z Jana osobny proces + watchdog, z Lemonade małe paczki z backendem na żądanie, z Ollamy pomiar pamięci przed ładowaniem jako bezpiecznik obok naszej tabeli; „auto-tune” Lemonade śledzić dalej w CompWatch.

## Powiązane
- [[research/_hub|research]]
- [[raport-02-autotuning]]
- [[raport-06-produkt]]
- [[turbollm]]
- [[ollama]]
- [[raport-15c-nowe-silniki]]
- [[magnitude]]
