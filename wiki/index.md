---
typ: hub
tags: [index, hub]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/qwen-opt/STATUS-NEXT.md:5-16; git -C ~/llama-master branch -v; ~/KERNEL/product/research/09-chmura-3090.md:201-233; ~/KERNEL/product/research/09-chmura-5060ti.md:214-256; ~/KERNEL/product/research/09-chmura-3060.md:233-275; ~/KERNEL/product/research/11-mtp-pl-pilot.md:3-9; ~/KERNEL/product/research/12-bit-exact-spekulacja.md:154-197; ~/KERNEL/wiki/AUDYT.md
status: aktualne
---
# KERNEL: baza wiedzy

**Wiedza projektu w jednym miejscu: szybkie lokalne LLM na RX 7900 XTX i kartach NVIDIA, nasze kernele i łatki llama.cpp oraz plan produktu.**

Notatki streszczają źródła i do nich linkują; źródła (NOTES.md, PLAN.md, raporty, manifest łatek) zostają tam, gdzie są. **Rekordy (najlepsze zmierzone wyniki): [[REKORDY]]. Podręcznik optymalizacji GPU: [[podrecznik-gpu]]. Rejestr przebadanych źródeł (przed każdym researchem): [[ZRODLA]]. Kolejka testów na karcie (co sprawdzić, gdy jaroserverai działa): [[KOLEJKA-TESTOW]]. LLM jako takie (trening, dostrajanie, jakość modeli), osobno od optymalizacji silnika: [[llm/_hub|llm]].** Zasady pisania: [[KONWENCJE]]. Historia zmian wiki: [[log]]. Decyzje użytkownika w [[decyzje/_hub|decyzje/]] są wiążące.

## Stan na dziś

**Produkcja (od 2026-11-09): `~/llama-topka` = topka-q70** ([[2026-11-09-wdrozenie-topka-q70]]); najlepsze wyniki w [[REKORDY]]. Tabela niżej to historyczny stan z 2026-10-15: `~/llama-opt`, gałąź `amd-opt` @ f61994f58, 70 łatek. Pomiar finalny 2026-10-15 (spec_sweep 6 promptów × 3 seedy, T=1; prefill i tg128 z llama-bench `-fa 1 -p 4096 -n 128 -r 2`):

| model | generowanie t/s | ms/krok | pp4096 t/s | tg128 bez spec. |
|---|---|---|---|---|
| [[qwen3-8-27b]] UD-Q4_K_XL, MTP, KV q4_0 | 109.0 | 27.74 | 1115 | 43.2 |
| [[qwen3-8-27b-uncensored]] Q4_K_M, MTP, KV q4_0 | 115.5 | 26.68 | 1109 | 44.0 |
| [[lfm2-5-24b-a2b]] Q5_K_M, KV q8_0 | 293.7 | 3.41 | 6175 | 289.7 |
| [[lfm2-5-uncensored]] AD-Q5_K_M, KV q8_0 | 267.3 | 3.74 | 6291 | 264.3 |

Szczegóły: [[stan-2026-10-15]].

Wyniki NVIDIA z chmury (2026-10-16, finalne; decode t/s, spec_sweep 6 promptów × 3 seedy, T=1; A0 = upstream tylko `-m`, A1 = najlepsze flagi upstream, „nasz” = fork z profilem karty):

| karta, model | A0 | A1 | nasz |
|---|---|---|---|
| [[rtx-3090]], Qwen3.8-27B UD-Q4_K_XL | 39.0 | 63.3 | 78.0 |
| [[rtx-3090]], LFM2.5 Q5_K_M | 180.2 | 176.0 | 263.9 |
| [[rtx-5060-ti]], Qwen3.8-27B UD-Q3_K_XL | 28.07 | 37.32 | 51.66 |
| [[rtx-5060-ti]], LFM2.5 Q4_K_M | 147.69 | 144.47 | 207.86 |
| [[rtx-3060]], Saluki 27B IQ2-mix | 22.1 | 22.3 | 23.4 |
| [[rtx-3060]], Bonsai 2 27B (Q2_0; fork prism z PTQ1_0: 44.8) | — | 33.1 | 35.5 |

Greedy forka ≠ upstream (łatki 0001/0002 i 0013, KLD na poziomie szumu): [[lekcja-md5-wzgledem-upstreamu]]. Szczegóły: [[testy/2026-10-16-kampania-nvidia]]. Pilot douczania głowicy MTP: wynik negatywny ([[2026-10-16-mtp-pl-pilot]]).

Wydatki: Vast ≈ $2.77 z $5, RunPod $2.14 z $6; wszystkie nasze instancje i pody zniszczone ([[karty/vast-ai]]).

**Bit-exact osiągnięty (2026-10-16):** MTP i zwykły greedy dają ten sam tekst na XTX (md5 `74952fd5…`), [[2026-10-16-bit-exact]]; walidacja i pomiar kosztu w przygotowaniu.

**W toku (2026-10-16 po południu):** eksperymenty na XTX (PM4-PDL, ogon kopiowania, szybkie testy, pasmo MoE LFM), w chmurze port `kvq` na CUDA, Magnitude vs nasz fork + KLD Nemotrona, jakość kwantów Swift/Saluki/Bonsai; fabryka v1 (CPU); nowy landing i strona z kartami ([[raport-15-synteza]]).
- [[otwarte-decyzje-produktu]] (nazwa, kolor, ceny, konto, prawo, port API, domena); prototyp aplikacji jest gotowy lokalnie ([[aplikacja-w-budowie]]).

Lokalna produkcja bez zmian: [[amd-opt]].

Audyt liczb: [[AUDYT]].

## Jak szukać

- `python3 tools/wiki.py search słowa…`: przeszukuje tytuły, streszczenia i tagi.
- W Obsidianie: wyszukiwanie (Ctrl+Shift+F), tagi `#rocm`, `#kernele`…, widok grafu (kolory = foldery).

<!-- AUTO:START -->
## Kategorie

- [[decyzje/_hub|decyzje]] — Decyzje i korekty właściciela: wiążą i mają pierwszeństwo przed resztą wiki (40)
- [[modele/_hub|modele]] — Jedna notatka na model (też drafter, kwant): rozmiar, kwant, gdzie działa, najlepsze wyniki (29)
- [[llm/_hub|llm]] — Trening, dostrajanie, edycje wag i jakość modeli (poza optymalizacją silnika) (5)
- [[karty/_hub|karty]] — Jedna notatka na kartę, maszynę albo dostawcę chmury: parametry, sufity, stan, najlepsze wyniki (21)
- [[stos/_hub|stos]] — Nasz fork llama.cpp i gałęzie, ROCm/HIP/PM4/KFD, CUDA, sterowniki i architektury (39)
- [[optymalizacje/_hub|optymalizacje]] — Jedna notatka na technikę, kernel albo łatkę: werdykt (przyjete, odrzucone, w-toku), zysk, dowód (99)
- [[testy/_hub|testy]] — Eksperymenty i pomiary z datą (warunki, wynik, przyrost) i metoda pomiaru; kolejka w KOLEJKA-TESTOW (124)
- [[metody/_hub|metody]] — Jak pracujemy: playbook, bramki poprawności, fabryka, dowód z profilu (28)
- [[lekcje/_hub|lekcje]] — Lekcje z błędów: objaw, przyczyna, jak robić poprawnie (128)
- [[research/_hub|research]] — Raporty, zwiady i linki od właściciela z werdyktem; rejestr przebadanych źródeł w ZRODLA (84)
- [[ekosystem/_hub|ekosystem]] — Cudze silniki i repozytoria, konkurencja, firmy i ludzie: jedna notatka na podmiot (113)
- [[produkt/_hub|produkt]] — Enigma: plan produktu, strona, aplikacja, przepisy per klasa VRAM (29)
- [[narzedzia/_hub|narzedzia]] — Nasze skrypty i narzędzia: pomiar, bramki, kolejka GPU, chmura, wiki (35)
- [[archiwum/_hub|archiwum]] — Notatki scalone i wycofane (status nieaktualne, pole zastapiona_przez); poza przypomnieniem (47)

## Ostatnio aktualizowane

- 2026-11-24 [[zwiad-2026-11-20|Zwiad 2026-11-20: błąd przywracania po odrzuconym drafcie w cache hybrydowym (ik_llama), weryfikacja kilku wierszy w oMLX, TensorRT-LLM 1.3 z Qwen3.5 MTP]]
- 2026-11-24 [[wafer-gpu-perf-lista|Lista wafer-ai „gpu-perf-engineering-resources”: ocena]]
- 2026-11-24 [[telegram-2026-11-14-silniki-agenci|Telegram 2026-11-14: własny silnik pod DeepSeek V4.1 Flash, InferenceForge, vstack]]
- 2026-11-24 [[telegram-2026-11-14-pearlquant-llamacpp-v1|Telegram 2026-11-14: PearlQuant (KV na kracie E8) i llama.cpp v1.0.0]]
- 2026-11-24 [[silniki-inferencji-2026-11-20|Silniki inferencji 2026-11-20: co bierzemy do Enigma Turbo (język zostaje C++/HIP)]]
- 2026-11-24 [[rightnow-inkling-b300-kernele|RightNow AI: kernele MoE Inkling 2 Small na B300, bitowo identyczne przy 1 i 64 wierszach]]
- 2026-11-24 [[raport-28-moe-offload|Raport 28: silniki MoE-offload TideLM i Xolotl – stratne z założenia]]
- 2026-11-24 [[raport-23a-rea|Raport 23a: morluto/rea („Reverse Engineer Anything”) – bez wsparcia GPU]]
- 2026-11-24 [[raport-21i-rsi-inference-bench|Raport 21i: RSI-Inference Bench (Apple) – co mierzy i co bierzemy do fabryki]]
- 2026-11-24 [[raport-03-silniki|Raport 03: silniki inferencji i stack]]
- 2026-11-24 [[przeglad-zrodla-2026-11-24|Przegląd ZRODLA 2026-11-24: zmienione oceny (cała inferencja i nauka, nie tylko prędkość)]]
- 2026-11-24 [[kv4-hopper-2611-30027|kv4-hopper (arXiv 2611.30027): dlaczego 4-bitowe KV bywa wolniejsze od FP8 i co z tego dla XTX]]
- 2026-11-24 [[amd-adrenalin-zapisy-ssd|AMD Adrenalin: ciągłe zapisy SSD przez `atieclxx.exe` (Windows)]]
- 2026-11-24 [[gdn-replay|GDN z opóźnieniem: cofanie przez przeliczenie (S4)]]
- 2026-11-24 [[speed-bench|SPEED-Bench (NVIDIA): wspólny standard pomiaru spekulacji, którym podają liczby wszyscy poza nami]]

Razem 821 notatek. Wygenerowano 2026-11-24 przez `tools/wiki.py index`.
<!-- AUTO:END -->
