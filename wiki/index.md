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

- [[decyzje/_hub|decyzje]] — Decyzje i korekty właściciela: wiążą i mają pierwszeństwo przed resztą wiki (37)
- [[modele/_hub|modele]] — Jedna notatka na model (też drafter, kwant): rozmiar, kwant, gdzie działa, najlepsze wyniki (27)
- [[llm/_hub|llm]] — Trening, dostrajanie, edycje wag i jakość modeli (poza optymalizacją silnika) (4)
- [[karty/_hub|karty]] — Jedna notatka na kartę, maszynę albo dostawcę chmury: parametry, sufity, stan, najlepsze wyniki (18)
- [[stos/_hub|stos]] — Nasz fork llama.cpp i gałęzie, ROCm/HIP/PM4/KFD, CUDA, sterowniki i architektury (39)
- [[optymalizacje/_hub|optymalizacje]] — Jedna notatka na technikę, kernel albo łatkę: werdykt (przyjete, odrzucone, w-toku), zysk, dowód (98)
- [[testy/_hub|testy]] — Eksperymenty i pomiary z datą (warunki, wynik, przyrost) i metoda pomiaru; kolejka w KOLEJKA-TESTOW (123)
- [[metody/_hub|metody]] — Jak pracujemy: playbook, bramki poprawności, fabryka, dowód z profilu (24)
- [[lekcje/_hub|lekcje]] — Lekcje z błędów: objaw, przyczyna, jak robić poprawnie (123)
- [[research/_hub|research]] — Raporty, zwiady i linki od właściciela z werdyktem; rejestr przebadanych źródeł w ZRODLA (81)
- [[ekosystem/_hub|ekosystem]] — Cudze silniki i repozytoria, konkurencja, firmy i ludzie: jedna notatka na podmiot (100)
- [[produkt/_hub|produkt]] — Enigma: plan produktu, strona, aplikacja, przepisy per klasa VRAM (29)
- [[narzedzia/_hub|narzedzia]] — Nasze skrypty i narzędzia: pomiar, bramki, kolejka GPU, chmura, wiki (33)
- [[archiwum/_hub|archiwum]] — Notatki scalone i wycofane (status nieaktualne, pole zastapiona_przez); poza przypomnieniem (47)

## Ostatnio aktualizowane

- 2026-11-22 [[runda-6|2026-10-15: runda 6 — epilog MMQ, GDN fast, narzędzia]]
- 2026-11-22 [[2026-11-07-kampania-nvidia-vast|Kampania NVIDIA na Vast: 17 kart, 262 144 z MTP na 24 i 32 GB (2026-11-07)]]
- 2026-11-22 [[2026-10-19-page-faulty-gpu-analiza|2026-10-16/19: page faulty GPU i 10 resetów XTX (analiza bez GPU)]]
- 2026-11-22 [[2026-10-19-build-topka|2026-10-19: build „topka” – ogon lookupu + współdzielenie cache, PM4 wyłączone]]
- 2026-11-22 [[2026-10-18-sprzezone-probkowanie-mtp|2026-10-18: E-X4 – sprzężone próbkowanie draftu MTP na XTX (nierozstrzygnięte)]]
- 2026-11-22 [[2026-10-18-pm4-pdl-x1|2026-10-16/18: X1 – mikrobench PM4-PDL na XTX (KILL)]]
- 2026-11-22 [[2026-10-18-magnitude-vulkan-xtx|2026-10-18: E-X5 – Magnitude przez Vulkan na RX 7900 XTX]]
- 2026-11-22 [[2026-10-18-lookup-ogon|2026-10-18/19: ogon z lookupu za MTP na XTX (W8/W16 + łańcuchy)]]
- 2026-11-22 [[2026-10-18-lfm-moe-pasmo|2026-10-16/18: pasmo kerneli MoE LFM2.5 na XTX]]
- 2026-11-22 [[2026-10-18-e1-kwanty-27b-kld|2026-10-16/18: E1 – nowe kwanty Qwen3.8-27B na 12–16 GB (KLD, zadania, prędkość)]]
- 2026-11-22 [[2026-10-16-nemotron-3090|2026-10-16: Nemotron 3.5 Bolt na RTX 3090 (Vast)]]
- 2026-11-22 [[2026-10-16-mtp-pl-pilot|2026-10-16: pilot douczania głowicy MTP (wynik negatywny)]]
- 2026-11-22 [[2026-10-16-magnitude-vs-fork|2026-10-16: X1 – Magnitude vs nasz fork vs upstream (3090, 5060 Ti)]]
- 2026-11-22 [[2026-10-16-kvq-cuda|2026-10-16: E1 – port `kvq` na CUDA (Ampere+)]]
- 2026-11-22 [[2026-10-16-kampania-nvidia|2026-10-16: pierwsza kampania na kartach NVIDIA (Vast)]]

Razem 783 notatek. Wygenerowano 2026-11-22 przez `tools/wiki.py index`.
<!-- AUTO:END -->
