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

- [[decyzje/_hub|decyzje]] — Decyzje i korekty użytkownika (wiążące) (34)
- [[modele/_hub|modele]] — Modele i kwanty (17)
- [[karty/_hub|karty]] — Karty GPU: używane i planowane (12)
- [[rocm/_hub|rocm]] — Stos AMD: ROCm, HIP, ROCr, PM4, rocprof (22)
- [[nvidia/_hub|nvidia]] — Stos NVIDIA: CUDA, sm_xx, poprawki zgodności (9)
- [[kernele/_hub|kernele]] — Nasze kernele: rodziny, zysk, poprawność, wyłącznik (30)
- [[latki/_hub|latki]] — Łatki llama.cpp i gałęzie (8)
- [[metody/_hub|metody]] — Jak pracujemy: playbook, bramki, pomiar (34)
- [[eksperymenty/_hub|eksperymenty]] — Rundy i pomiary z datą (59)
- [[lekcje/_hub|lekcje]] — Lekcje z błędów (92)
- [[narzedzia/_hub|narzedzia]] — Nasze skrypty i narzędzia (28)
- [[chmura/_hub|chmura]] — Wynajem GPU i harness chmurowy (6)
- [[repo/_hub|repo]] — Repozytoria i projekty: cudze i nasze (68)
- [[research/_hub|research]] — Streszczenia raportów (99)
- [[produkt/_hub|produkt]] — Plan produktu i decyzje produktowe (28)
- [[ludzie-firmy/_hub|ludzie-firmy]] — Firmy, dostawcy, ludzie (27)

## Ostatnio aktualizowane

- 2026-10-20 [[raporty-2026-10-19-20|Raporty 2026-10-19/20 (20–30, WYNIKI-XTX): przegląd]]
- 2026-10-20 [[raport-wyniki-xtx-2026-10-19|Wyniki RX 7900 XTX 2026-10-19/20: upstream → topka (ten sam skrypt, ABBA)]]
- 2026-10-20 [[raport-30-intel-apple|Raport 30: dostęp do Intel Arc i Apple Silicon + plan testów na M1 Pro]]
- 2026-10-20 [[raport-29-4060ti|Raport 29: RTX 4060 Ti 16 GB – przed/po (Qwen Q3_K_XL, LFM QAD-Q4_0)]]
- 2026-10-20 [[raport-28-moe-offload|Raport 28: silniki MoE-offload TideLM i Xolotl – stratne z założenia]]
- 2026-10-20 [[raport-27-3090-final|Raport 27: RTX 3090 i 3060 – finał przed/po (Qwen, Uncensored, Saluki)]]
- 2026-10-20 [[raport-26-kolejka-gpu|Raport 26: kolejka GPU 2026-10-19 wieczorem – testy odłożone przez pauzę]]
- 2026-10-20 [[raport-25-buildfarm|Raport 25: zdalny serwer buildów (Vast) i `rbuild`]]
- 2026-10-20 [[raport-24w-pair2|Raport 24w: PAIR2 (para MMVQ dla mieszanych typów) na topce – odrzucone (+0.4%)]]
- 2026-10-20 [[raport-24v-prefill-fa|Raport 24v: FA D=256 w prefillu Qwena – spille usunięte, zysk za mały]]
- 2026-10-20 [[raport-24u-norm-quant|Raport 24u: osobny kernel rms_norm × w + quantize q8_1 – stop, zysk ≈ 0]]
- 2026-10-20 [[raport-24t-entropia-wag|Raport 24t: bezstratna kompresja entropijna wag GGUF (DFloat11/ZipNN) – kill]]
- 2026-10-20 [[raport-24s-drzewa-proza|Raport 24s: drzewa draftu MTP i temperatura draftu na prozie – sufit offline]]
- 2026-10-20 [[raport-24r-mmvq-pasmo|Raport 24r: pasmo MMVQ weryfikacji n=5 – sufit 926 GB/s]]
- 2026-10-20 [[raport-24q-adaptacyjna-spekulacja|Raport 24q: adaptacyjna spekulacja – bramka ogona i głębokość MTP z akceptacji]]

Razem 573 notatek. Wygenerowano 2026-10-20 przez `tools/wiki.py index`.
<!-- AUTO:END -->
