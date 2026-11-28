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

- [[decyzje/_hub|decyzje]] — Decyzje i korekty właściciela: wiążą i mają pierwszeństwo przed resztą wiki (47)
- [[modele/_hub|modele]] — Jedna notatka na model (też drafter, kwant): rozmiar, kwant, gdzie działa, najlepsze wyniki (30)
- [[llm/_hub|llm]] — Trening, dostrajanie, edycje wag i jakość modeli (poza optymalizacją silnika) (10)
- [[karty/_hub|karty]] — Jedna notatka na kartę, maszynę albo dostawcę chmury: parametry, sufity, stan, najlepsze wyniki (21)
- [[stos/_hub|stos]] — Nasz fork llama.cpp i gałęzie, ROCm/HIP/PM4/KFD, CUDA, sterowniki i architektury (40)
- [[platformy/_hub|platformy]] — Playbook na dzień, w którym dostajemy sprzęt: build, sufit pasma, kolejność optymalizacji, testy, pułapki (14)
- [[optymalizacje/_hub|optymalizacje]] — Jedna notatka na technikę, kernel albo łatkę: werdykt (przyjete, odrzucone, w-toku), zysk, dowód (99)
- [[testy/_hub|testy]] — Eksperymenty i pomiary z datą (warunki, wynik, przyrost) i metoda pomiaru; kolejka w KOLEJKA-TESTOW (134)
- [[metody/_hub|metody]] — Jak pracujemy: playbook, bramki poprawności, fabryka, dowód z profilu (30)
- [[lekcje/_hub|lekcje]] — Lekcje z błędów: objaw, przyczyna, jak robić poprawnie (139)
- [[research/_hub|research]] — Raporty, zwiady i linki od właściciela z werdyktem; rejestr przebadanych źródeł w ZRODLA (95)
- [[ekosystem/_hub|ekosystem]] — Cudze silniki i repozytoria, konkurencja, firmy i ludzie: jedna notatka na podmiot (116)
- [[produkt/_hub|produkt]] — Enigma: plan produktu, strona, aplikacja, przepisy per klasa VRAM (29)
- [[narzedzia/_hub|narzedzia]] — Nasze skrypty i narzędzia: pomiar, bramki, kolejka GPU, chmura, wiki (36)
- [[archiwum/_hub|archiwum]] — Notatki scalone i wycofane (status nieaktualne, pole zastapiona_przez); poza przypomnieniem (47)

## Ostatnio aktualizowane

- 2026-11-28 [[2026-11-28-k207-ablacja-zamiast-lora|2026-11-28 K-207: ablacja kierunku zamiast LoRA w llama.cpp (Inkling 2 Mini, 5060 Ti)]]
- 2026-11-28 [[2026-11-27-k204-enigma-16gb-inkling|2026-11-27 K-204: Enigma 16 GB z Inklingiem IQ3_S bez cenzury i pełnym kontekstem (5060 Ti, 4060 Ti)]]
- 2026-11-28 [[topki|Topki: najlepszy zmierzony wariant każdego modelu na każdej karcie]]
- 2026-11-28 [[zwiad-2026-11-28|Zwiad 2026-11-28: G2GFAST 687,5 t/s (+3,6%), Maya na 3090 210 t/s to inne obciążenie, nib na RDNA4 przy 50% przepustowości]]
- 2026-11-28 [[linki-2026-11-28-wieczor|Linki 2026-11-28 wieczór: Bonsai na CPU 19,7 t/s, Gemma 4 K=V, Cortheon, V100 OC, „matematyka LLM”]]
- 2026-11-28 [[linki-2026-11-28-gdn-spekulacja|Linki 2026-11-28: spekulacja z drafterem na hybrydzie GDN ×0,41–0,60 (llama.cpp #32776) i DFly2 (delta)]]
- 2026-11-28 [[final-recipes-nvidia|Finalne przepisy NVIDIA per klasa VRAM (na stronę)]]
- 2026-11-28 [[rodzaje-modeli|Rodzaje modeli: kolejność pracy i nasze dowody]]
- 2026-11-28 [[procedura-znany-model-nowa-karta|Procedura: znany model na nowej karcie]]
- 2026-11-28 [[procedura-nowy-model-znana-karta|Procedura: nowy model na znanej karcie]]
- 2026-11-28 [[nvidia-hopper-sm90|NVIDIA Hopper sm_90 (H100, H200): playbook topki]]
- 2026-11-28 [[nvidia-blackwell-sm120|NVIDIA Blackwell sm_120 (RTX 5060 Ti, 5070, 5080, 5090): playbook topki]]
- 2026-11-28 [[nvidia-blackwell-sm100|NVIDIA Blackwell sm_100 (B200, GB200): playbook topki]]
- 2026-11-28 [[nvidia-ampere-sm86|NVIDIA Ampere sm_86 (RTX 3060, 3070, 3080, 3090): playbook topki]]
- 2026-11-28 [[nvidia-ada-sm89|NVIDIA Ada sm_89 (RTX 4060 Ti, 4070, 4080 SUPER, 4090, L4): playbook topki]]

Razem 887 notatek. Wygenerowano 2026-11-28 przez `tools/wiki.py index`.
<!-- AUTO:END -->
