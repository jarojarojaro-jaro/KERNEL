---
typ: hub
tags: [index, hub]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/STATUS-NEXT.md:5-16; git -C ~/llama-master branch -v; ~/qwen-opt/cloud/PLAN-TESTOW.md:55-58; ~/qwen-opt/cloud/results/3090-20261016/scorecard.md:1-30 (03:03 UTC); ~/qwen-opt/cloud/results/3060-20261016/summary.md:1-25 (03:20 UTC); ~/KERNEL/wiki/AUDYT.md
status: aktualne
---
# KERNEL: baza wiedzy

**Wiedza projektu w jednym miejscu: szybkie lokalne LLM na RX 7900 XTX i kartach NVIDIA, nasze kernele i łatki llama.cpp oraz plan produktu.**

Notatki streszczają źródła i do nich linkują; źródła (NOTES.md, PLAN.md, raporty, manifest łatek) zostają tam, gdzie są. Zasady pisania: [[KONWENCJE]]. Historia zmian wiki: [[log]]. Decyzje użytkownika w [[decyzje/_hub|decyzje/]] są wiążące.

## Stan na dziś

Zainstalowane: `~/llama-opt`, gałąź `amd-opt` @ f61994f58, 70 łatek. Pomiar finalny 2026-10-15 (spec_sweep 6 promptów × 3 seedy, T=1; prefill i tg128 z llama-bench `-fa 1 -p 4096 -n 128 -r 2`):

| model | generowanie t/s | ms/krok | pp4096 t/s | tg128 bez spec. |
|---|---|---|---|---|
| [[qwen3-8-27b]] UD-Q4_K_XL, MTP, KV q4_0 | 109.0 | 27.74 | 1115 | 43.2 |
| [[qwen3-8-27b-uncensored]] Q4_K_M, MTP, KV q4_0 | 115.5 | 26.68 | 1109 | 44.0 |
| [[lfm2-5-24b-a2b]] Q5_K_M, KV q8_0 | 293.7 | 3.41 | 6175 | 289.7 |
| [[lfm2-5-uncensored]] AD-Q5_K_M, KV q8_0 | 267.3 | 3.74 | 6291 | 264.3 |

Szczegóły: [[stan-2026-10-15]].

Wstępne wyniki z chmury (2026-10-16, w toku, `do-sprawdzenia`; A0 = upstream tylko z `-m`, „typowa aplikacja”; A2 = nasz fork z flagami A1: `-fit on -fa on`, KV q8_0, MTP n=4 dla Qwena; A2s = A2 z 31 przełącznikami = 0):

| karta, model | A0 decode t/s | A2 decode t/s | źródło |
|---|---|---|---|
| [[rtx-3090]], LFM2.5 Q5_K_M | 180.2 | 249.3 (×1.38) | `results/3090-20261016/scorecard.md` |
| [[rtx-3090]], Qwen3.8-27B UD-Q4_K_XL | 39.0 | 78.0 | jw. |
| [[rtx-3060]], Saluki 27B IQ2 (spec_sweep) | 22.14 | 22.68 (A2s: 23.06) | `results/3060-20261016/summary.md` |

Szczegóły i testy poprawności: [[nvidia-wyniki-2026-10-16]], [[2026-10-16-kampania-nvidia]].

Teraz trwa (2026-10-16): kampanie Vast na [[rtx-3060]] (Saluki + Bonsai), [[rtx-3090]] i [[rtx-5060-ti]] w ramach [[2026-10-16-budzety-chmury|$5]] (gałęzie: [[cuda-v070]]); trening głowicy MTP na RunPod ([[mtp-train]], limit $6). Prototyp aplikacji gotowy lokalnie, niewdrożony ([[aplikacja-w-budowie]]); czeka na [[otwarte-decyzje-produktu]]. Czeka na test na Radeonie, którego teraz nie robimy ([[2026-10-16-bez-lokalnego-gpu]]): poprawka atencji w [[batch-invariant]] i [[amd-opt-v070]]. Lokalna produkcja bez zmian: [[amd-opt]].

Audyt liczb: [[AUDYT]].

## Jak szukać

- `python3 tools/wiki.py search słowa…`: przeszukuje tytuły, streszczenia i tagi.
- W Obsidianie: wyszukiwanie (Ctrl+Shift+F), tagi `#rocm`, `#kernele`…, widok grafu (kolory = foldery).

<!-- AUTO:START -->
## Kategorie

- [[decyzje/_hub|decyzje]] — Decyzje i korekty użytkownika (wiążące) (17)
- [[modele/_hub|modele]] — Modele i kwanty (11)
- [[karty/_hub|karty]] — Karty GPU: używane i planowane (10)
- [[rocm/_hub|rocm]] — Stos AMD: ROCm, HIP, ROCr, PM4, rocprof (14)
- [[nvidia/_hub|nvidia]] — Stos NVIDIA: CUDA, sm_xx, poprawki zgodności (6)
- [[kernele/_hub|kernele]] — Nasze kernele: rodziny, zysk, poprawność, wyłącznik (23)
- [[latki/_hub|latki]] — Łatki llama.cpp i gałęzie (8)
- [[metody/_hub|metody]] — Jak pracujemy: playbook, bramki, pomiar (16)
- [[eksperymenty/_hub|eksperymenty]] — Rundy i pomiary z datą (26)
- [[lekcje/_hub|lekcje]] — Lekcje z błędów (25)
- [[narzedzia/_hub|narzedzia]] — Nasze skrypty i narzędzia (17)
- [[chmura/_hub|chmura]] — Wynajem GPU i harness chmurowy (6)
- [[repo/_hub|repo]] — Repozytoria i projekty: cudze i nasze (49)
- [[research/_hub|research]] — Streszczenia raportów (13)
- [[produkt/_hub|produkt]] — Plan produktu i decyzje produktowe (22)
- [[ludzie-firmy/_hub|ludzie-firmy]] — Firmy, dostawcy, ludzie (23)

## Ostatnio aktualizowane

- 2026-10-16 [[wsl2-rocm|ROCm w WSL2 (tech preview 10.1)]]
- 2026-10-16 [[therock|TheRock: system budowania i wydań ROCm]]
- 2026-10-16 [[rocr|ROCr (HSA runtime) i KFD]]
- 2026-10-16 [[rocprof|rocprofv3 i profilowanie na gfx1100]]
- 2026-10-16 [[rocm-vs-vulkan|ROCm czy Vulkan na RX 7900 XTX]]
- 2026-10-16 [[rocm-stos|Stos ROCm na naszym serwerze]]
- 2026-10-16 [[rocm-10-1|ROCm 10.1: co daje na gfx1100]]
- 2026-10-16 [[rdna3-gfx1100|RDNA3 / gfx1100: architektura, pod którą piszemy]]
- 2026-10-16 [[pm4|PM4: bufory poleceń procesora poleceń GPU]]
- 2026-10-16 [[hip|HIP: jak piszemy kernele pod gfx1100]]
- 2026-10-16 [[hip-na-windows|HIP na Windows: PAL zamiast ROCr]]
- 2026-10-16 [[hip-graph-narzut|Narzut grafu HIP: ~3 µs na kernel]]
- 2026-10-16 [[amdgpu-moc-i-termika|Sterownik amdgpu: limit mocy, termika, usypianie]]
- 2026-10-16 [[amd-smi|AMD SMI (amd-smi)]]
- 2026-10-16 [[runda-6-raporty|Runda 6: raporty GDN, MMQ i narzędzi]]

Razem 286 notatek. Wygenerowano 2026-10-16 przez `tools/wiki.py index`.
<!-- AUTO:END -->
