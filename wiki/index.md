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

- [[decyzje/_hub|decyzje]] — Decyzje i korekty użytkownika (wiążące) (43)
- [[modele/_hub|modele]] — Modele i kwanty (23)
- [[karty/_hub|karty]] — Karty GPU: używane i planowane (12)
- [[rocm/_hub|rocm]] — Stos AMD: ROCm, HIP, ROCr, PM4, rocprof (23)
- [[nvidia/_hub|nvidia]] — Stos NVIDIA: CUDA, sm_xx, poprawki zgodności (10)
- [[kernele/_hub|kernele]] — Nasze kernele: rodziny, zysk, poprawność, wyłącznik (33)
- [[latki/_hub|latki]] — Łatki llama.cpp i gałęzie (8)
- [[metody/_hub|metody]] — Jak pracujemy: playbook, bramki, pomiar (58)
- [[eksperymenty/_hub|eksperymenty]] — Rundy i pomiary z datą (85)
- [[lekcje/_hub|lekcje]] — Lekcje z błędów (123)
- [[narzedzia/_hub|narzedzia]] — Nasze skrypty i narzędzia (31)
- [[chmura/_hub|chmura]] — Wynajem GPU i harness chmurowy (6)
- [[repo/_hub|repo]] — Repozytoria i projekty: cudze i nasze (91)
- [[research/_hub|research]] — Streszczenia raportów (166)
- [[produkt/_hub|produkt]] — Plan produktu i decyzje produktowe (36)
- [[ludzie-firmy/_hub|ludzie-firmy]] — Firmy, dostawcy, ludzie (28)
- [[llm/_hub|llm]] — LLM: trening, dostrajanie, edycje wag i jakość modeli (poza optymalizacją silnika) (7)

## Ostatnio aktualizowane

- 2026-11-22 [[kernel-od-a-do-z|Kernel od A do Z]]
- 2026-11-20 [[zwiad-2026-11-20|Zwiad 2026-11-20: błąd przywracania po odrzuconym drafcie w cache hybrydowym (ik_llama), weryfikacja kilku wierszy w oMLX, TensorRT-LLM 1.3 z Qwen3.5 MTP]]
- 2026-11-20 [[telegram-2026-11-20-linux-7-2-pamiec|Linux 7.2 a LLM: zmiany pamięci pomagają przy odciążaniu do RAM/SSD, nie przy modelu w całości w VRAM]]
- 2026-11-20 [[silniki-inferencji-2026-11-20|Silniki inferencji 2026-11-20: co bierzemy do Enigma Turbo (język zostaje C++/HIP)]]
- 2026-11-20 [[enigma-turbo-gemini-2026-11-20|„Enigma Turbo” od Gemini 4 Neon: README obiecuje silnik CUDA/HIP, a działa tylko wolny CPU i odpowiada bełkotem]]
- 2026-11-20 [[inkling-2-mini|Inkling 2 Mini (Thinking Machines, 2026-11-20): MoE z pętlą warstw, jakość jak Qwen3.8-27B przy ~5× mniejszym odczycie na token]]
- 2026-11-19 [[zwiad-2026-11-19|Zwiad 2026-11-19: prefill przez drugą kartę (oMLX ×5,3 dla Qwen3.8-27B), sparowana weryfikacja draftów (TensorFold +24–29% na Macu), błąd EOG w rejekcji]]
- 2026-11-19 [[audyt-gemini-2026-11-19|Audyt Gemini całego repo KERNEL (2026-11-19): co było prawdą, co naprawione, co odrzucone]]
- 2026-11-19 [[megakernel-zoo|megakernel-zoo (Xingyu Dang, Princeton): agent (Claude) pisze osobny megakernel dekodu dla każdego modelu i karty]]
- 2026-11-19 [[daisyrose-27b|DaisyRose-27B (RadixArk): pełny RL na Qwen3.8-27B, 144 × H200 przez 18 dni — duży koszt, mały zysk poza Terminal-Bench 4.1]]
- 2026-11-19 [[lekcja-tlo-z-sesji-agenta-ginie|Karty w chmurze nigdy nie stoją: zbieranie i usuwanie robi timer systemowy, nie sesja agenta]]
- 2026-11-19 [[lekcja-env-switch-domyslnie-wlaczony|`ggml_cuda_env_switch` jest włączony, gdy zmiennej nie ma: nie używaj go do wyłączników]]
- 2026-11-19 [[2026-11-19-k125-k001-xtx|2026-11-19: K-125 (KLD ścieżki kvq) i K-001 (wyciek stanu): XTX, topka-q70, Qwen3.8-27B-Uncensored Q4_K_M]]
- 2026-11-19 [[2026-11-19-k118-nvidia-pelna-moc|2026-11-19 K-118 / K-116a / K-127: fork CUDA Enigmy na 3090, 3060 i 4080 SUPER z pełną mocą]]
- 2026-11-19 [[2026-11-19-k111-k123-krok-xtx|2026-11-19 K-111 i K-123: gdzie ucieka krok MTP na XTX (bez karty, z istniejącego śladu) i błąd EOG w rejekcji]]

Razem 783 notatek. Wygenerowano 2026-11-22 przez `tools/wiki.py index`.
<!-- AUTO:END -->
