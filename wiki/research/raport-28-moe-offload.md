---
typ: research
tags: [research, moe, offload, konkurencja]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/product/research/28-moe-offload-silniki.md:11-15,27-36,42,47,66-70
status: aktualne
---
# Raport 28: silniki MoE-offload TideLM i Xolotl – stratne z założenia

**Prędkości TideLM i Xolotl biorą się z nieliczenia ekspertów wybranych przez router (podstawianie, bias routingu do VRAM) i kwantów 2–3 bit; przy dokładnym routingu Xolotl sam podaje ~3.5 tok/s – dla naszych modeli (w całości w VRAM) offload nic nie daje (2026-10-20).**

- Górna granica bezstratnego offloadu: tok/s ≤ pasmo (RAM ~70 / PCIe ~25 / NVMe ~6 GB/s) ÷ bajty chybionych ekspertów na token (`28:69`).
- Jedyna przenośna technika: dynamiczna głębokość draftu (TideLM: kod +21% przy głębokości 5, proza −10%) (`28:42,68`) – u nas sprawdzona w [[raport-24q-adaptacyjna-spekulacja]] (md5 się zmienia).
- Lekcja: bit-exactness przy zmianie chunku GEMM nie istnieje; bezstratność mierzyć KL/top-1 (`28:47,70`).
- Nie portujemy route-bias, podstawiania, LOOP_BREAK ani KV FP4.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
Werdykt „stratne; dla nas tylko dynamiczna głębokość MTP” patrzył tylko na dekod gęstego 27B. R28 miał też lekcje dla produktu i procesu, które nie trafiły dalej:
- **Doradca Enigmy nie zna offloadu.** Enigma uruchamia model w całości na GPU albo w całości na CPU (`-ngl 999|0`, `app/engine/src/server/engine.ts:570`), a szacunek prędkości liczy tylko te dwa przypadki (`app/engine/src/server/catalog/score.ts:56-66`). Akcja 3 z R28 (górna granica bezstratnego offloadu: tok/s ≤ pasmo ÷ bajty chybionych ekspertów, `28:59-61`) nie trafiła do doradcy. Strata, Maya i TideLM to całe produkty dla ludzi z małą kartą i dużym RAM, czyli części klientów Enigmy.
- **Dziennik ślepych uliczek:** `docs/gotchas.md` TideLM to 134 sekcje odrzuconych prób z powodem (`28:4-6,49-56`). Ten sam wzór miał AKO4ALL (10-16, [[ako4all]]), a bierzemy go dopiero 24.11 z TensorFold ([[ashhart-skills-infra]]). Nasze [[wyniki-negatywne]] to tekst w NOTES, którego agent nie musi czytać przed startem.
- **Głębokość draftu z pomiaru zysku** (TideLM `engine/spec_depth.py`: wybór 3/5 co 60 tokenów, próg 3%) to ta sama idea co kontroler `SpecCtl` Mai, który na Inklingu przy T=0,7 tłumaczy ~2,3× przewagi ([[maya-ik2-inkling]]). U nas 24q sprawdził wariant zmieniający md5, a K-008 ma status „czeka na decyzję”, bo zmienna szerokość weryfikacji zmienia md5 przy T=0 ([[KOLEJKA-TESTOW]]).
- **Reguły dla szablonów Enigmy:** znacznik czasu w prompcie psuje dokładne dopasowanie cache prefiksów (`28:55`); cache prefiksów na dysku (6K w 0,2 s zamiast 19 s, `28:43`).
- **Xolotl i komunikacja:** fork pokazuje 27 t/s, a jego własny README podaje 3,5 t/s przy dokładnym routingu. W Enigmie przy każdej liczbie mówić, czy model liczy dokładnie (R28 akcja 3: „duże MoE z offloadem tylko bezstratnie, czyli ~kilka–20 tok/s”).

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[raport-24q-adaptacyjna-spekulacja]]
- [[raport-21n-strata-gyro]]
- [[model-kosztu-weryfikacji-moe]]
