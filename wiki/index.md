---
typ: hub
tags: [index, hub]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/qwen-opt/STATUS-NEXT.md:5-16; git -C ~/llama-master branch -v; ~/KERNEL/product/research/09-chmura-3090.md:201-233; ~/KERNEL/product/research/09-chmura-5060ti.md:214-256; ~/KERNEL/product/research/09-chmura-3060.md:233-275; ~/KERNEL/product/research/11-mtp-pl-pilot.md:3-9; ~/KERNEL/product/research/12-bit-exact-spekulacja.md:154-197; ~/KERNEL/wiki/AUDYT.md
status: aktualne
---
# KERNEL: baza wiedzy

**Wiedza projektu w jednym miejscu: szybkie lokalne LLM na RX 7900 XTX i kartach NVIDIA, nasze kernele i łatki llama.cpp oraz plan produktu.**

Notatki streszczają źródła i do nich linkują; źródła (NOTES.md, PLAN.md, raporty, manifest łatek) zostają tam, gdzie są. **Rekordy (najlepsze zmierzone wyniki): [[REKORDY]]. Podręcznik optymalizacji GPU: [[podrecznik-gpu]]. Rejestr przebadanych źródeł (przed każdym researchem): [[ZRODLA]].** Zasady pisania: [[KONWENCJE]]. Historia zmian wiki: [[log]]. Decyzje użytkownika w [[decyzje/_hub|decyzje/]] są wiążące.

## Stan na dziś

Zainstalowane: `~/llama-opt`, gałąź `amd-opt` @ f61994f58, 70 łatek. Pomiar finalny 2026-10-15 (spec_sweep 6 promptów × 3 seedy, T=1; prefill i tg128 z llama-bench `-fa 1 -p 4096 -n 128 -r 2`):

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

Greedy forka ≠ upstream (łatki 0001/0002 i 0013, KLD na poziomie szumu): [[lekcja-md5-wzgledem-upstreamu]]. Szczegóły: [[nvidia-wyniki-2026-10-16]]. Pilot douczania głowicy MTP: wynik negatywny ([[2026-10-16-mtp-pl-pilot]]).

Wydatki: Vast ≈ $2.77 z $5, RunPod $2.14 z $6; wszystkie nasze instancje i pody zniszczone ([[2026-10-16-budzety-chmury]]).

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

- [[decyzje/_hub|decyzje]] — Decyzje i korekty użytkownika (wiążące) (26)
- [[modele/_hub|modele]] — Modele i kwanty (17)
- [[karty/_hub|karty]] — Karty GPU: używane i planowane (11)
- [[rocm/_hub|rocm]] — Stos AMD: ROCm, HIP, ROCr, PM4, rocprof (22)
- [[nvidia/_hub|nvidia]] — Stos NVIDIA: CUDA, sm_xx, poprawki zgodności (9)
- [[kernele/_hub|kernele]] — Nasze kernele: rodziny, zysk, poprawność, wyłącznik (30)
- [[latki/_hub|latki]] — Łatki llama.cpp i gałęzie (8)
- [[metody/_hub|metody]] — Jak pracujemy: playbook, bramki, pomiar (34)
- [[eksperymenty/_hub|eksperymenty]] — Rundy i pomiary z datą (58)
- [[lekcje/_hub|lekcje]] — Lekcje z błędów (86)
- [[narzedzia/_hub|narzedzia]] — Nasze skrypty i narzędzia (28)
- [[chmura/_hub|chmura]] — Wynajem GPU i harness chmurowy (6)
- [[repo/_hub|repo]] — Repozytoria i projekty: cudze i nasze (68)
- [[research/_hub|research]] — Streszczenia raportów (60)
- [[produkt/_hub|produkt]] — Plan produktu i decyzje produktowe (28)
- [[ludzie-firmy/_hub|ludzie-firmy]] — Firmy, dostawcy, ludzie (27)

## Ostatnio aktualizowane

- 2026-10-19 [[trwala-siatka-bez-pm4|XTX bez PM4: trwała siatka wraca do gry (warunkowo)]]
- 2026-10-19 [[rocprof|rocprofv3 i profilowanie na gfx1100]]
- 2026-10-19 [[rdna3-gfx1100|RDNA3 / gfx1100: architektura, pod którą piszemy]]
- 2026-10-19 [[mec-fw-dispatch-aql-gfx11|Firmware MEC gfx11: co robi z pakietem AQL, a czego nie robi z `DISPATCH_DIRECT`]]
- 2026-10-19 [[kfd-smi-eventy|Zdarzenia KFD SMI (`AMDKFD_IOC_SMI_EVENTS`) bez roota]]
- 2026-10-19 [[kfd-ewikcja-kolejek-gfx11|Ewikcja i przywracanie kolejek KFD + MES na gfx11 (Linux 6.8)]]
- 2026-10-19 [[hip-kopie-stronicowane-zostawiaja-svm|Kopie HIP z pamięci stronicowanej zostawiają zmapowane zakresy SVM]]
- 2026-10-19 [[hip-graph-narzut|Narzut grafu HIP: ~3 µs na kernel]]
- 2026-10-19 [[gfx11-pm4-dispatch-priv|Własny dispatch PM4 na GFX11 musi ustawić `COMPUTE_PGM_RSRC1.PRIV=1`]]
- 2026-10-19 [[dekodowanie-page-fault-amdgpu|Dekodowanie page faultu amdgpu (gfx11)]]
- 2026-10-19 [[wafer-gpu-perf-lista|Lista wafer-ai „gpu-perf-engineering-resources”: ocena]]
- 2026-10-19 [[single-neuron-safety-2605-08513|arXiv 2605.08513 to nie InferenceX (praca o alignmencie)]]
- 2026-10-19 [[raport-23e-re-silniki|Raport 23e: RE kerneli dekodu konkurencyjnych silników]]
- 2026-10-19 [[raport-23c-re-kernele-nvidia|Raport 23c: kernele NVIDIA (cuBLASLt, FlashInfer, Marlin, exllamav3) vs nasz ggml-cuda]]
- 2026-10-19 [[raport-23b-re-kernele-amd|Raport 23b: kernele AMD (gfx1100) vs nasze MMVQ, weryfikacja i atencja]]

Razem 518 notatek. Wygenerowano 2026-10-19 przez `tools/wiki.py index`.
<!-- AUTO:END -->
