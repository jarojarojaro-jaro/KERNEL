---
typ: research
tags: [research, inkling, moe, nvfp4, batch-invariance, blackwell]
aktualizacja: 2026-11-24
zrodlo: https://www.rightnowai.co/blog/bit-identical-fp4-moe-kernels-on-blackwell (2026-11-22); https://x.com/Akashi203/status/2124576912412737898; repo github.com/RightNow-AI/inkling-b300-kernels
status: aktualne
---
# RightNow AI: kernele MoE Inkling 2 Small na B300, bitowo identyczne przy 1 i 64 wierszach

**Agent RightNow AI napisał kernele NVFP4/MXFP8 dla Inkling 2 Small (594B) na 8 × B300: GEMM eksperta w13 przy jednym tokenie 104,4 → 20,5 µs (5,1×, NVFP4) i 184,3 → 24,6 µs (7,5×, MXFP8), logity 599/599 wierszy identyczne przy 1 i 64 wierszach na krok (pomiary autorów, 2026-11-21).**

## Liczby (B300, autorzy)
- w13 NVFP4 5,1×, MXFP8 7,5×; w2 1,0–4,6× zależnie od formy; różnica od vLLM 0,025 nat średnio (0,13 p95); testy 10/10.
- Pierwszy kernel: 40 CTA na 148 SM, 114 GB/s; po podziale K na CTA i nakładaniu ładowań: 583 GB/s.
- Cały krok dekodu wciąż ~16,35 ms (osobne kernele pod CUDA graph, nowy GEMM jeszcze niewpięty) — ten sam problem co u nas: kroku nie ogranicza pasmo, tylko liczba i jakość kerneli. Następny krok autorów: jeden trwały kernel dekodu na GPU (jak nasz plan ink-r9).

## Lekcje dla nas (każda karta)
- **Mało bloków przy n=1 = marnowane pasmo.** Jedna CTA na kafel eksperta dała 114 GB/s; podział K na wiele bloków + ostatni blok sumuje części stałym drzewem („bilet” atomicAdd, licznik zerowany dla powtórki grafu/taśmy) dał 5×. Do sprawdzenia w naszym MMVQ-ID dla Inkling na XTX (8 ekspertów × kafle przy n=1 to też mało bloków na 96 CU).
- **Niezmienność względem batcha (batch invariance):** stała kolejność sum (stałe kawałki, zrównoważone drzewo, bez automatycznego FMA) daje te same bity przy weryfikacji 8 tokenów i dekodzie po 1. To dokładnie warunek, żeby spekulacja była bezstratna bit w bit (u nas KLD zamiast bitów po INK_FUSE; K-001 był błędem tego typu).
- **„Zepsuty bliźniak” każdego testu:** każda właściwość ma celowo zepsuty wariant, który test musi złapać — dobry wzór dla naszych bramek md5/KLD (sprawdza, że test w ogóle coś mierzy).
- **Fosa CUDA (teza tweeta):** NVFP4 czyta tylko Blackwell (`tcgen05.mma … block16`); MI350/MI355 mają tylko MXFP4, więc wymagają konwersji (stratnej). Dla XTX (bez FP4/FP8) bez znaczenia: my idziemy przez GGUF Q4_K ([[nvfp4]]).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- **Proces agenta, nie tylko kernel.** Ich agent dał 5,1× na pojedynczym GEMM (104,4 → 20,5 µs), a krok dekodu został 16,35 ms, bo nowego kernela nie wpięto i reszta kroku to inne kernele. To ten sam wzór co nasz wyścig Kernel vs Gemini 24.11: 705 → 547 uruchomień/token, a rep2 Q6 112,9 → 113,6 (+0,6%) ([[maya-ik2-inkling]]).
- Lekcja dla naszego wyścigu: każda propozycja ma prognozę dla całego kroku (Δściany ≈ Δkerneli − usunięte uruchomienia × 1,8 µs na gfx1100), zanim agent zacznie pisać kernel ([[ashhart-skills-infra]]). Ich wpis jest uczciwy, bo sam podaje 16,35 ms; nasze raporty agentów podawały „+3–7%” bez takiej liczby.
- Ich bramki (10/10 testów, logity 599/599 identyczne przy 1 i 64 wierszach, zepsuty bliźniak każdego testu) to lepsza bramka niż nasz pojedynczy md5 T=0: sprawdza też szerokości okna weryfikacji. Dla Mayi: macierz sha tokenów przy wymuszonych szerokościach okna (1, 2, 3, 5, 7, 8).
- Dla serwowania: niezmienność względem batcha jest warunkiem, żeby wynik z draftem i bez był ten sam bit w bit — to też obietnica, którą Enigma może dać użytkownikowi (md5 w `optimize.ts` porównuje tylko T=0).

## Powiązane
- [[inkling-2-mini]]
- [[nvfp4]]
- [[pomiar-abba]]
