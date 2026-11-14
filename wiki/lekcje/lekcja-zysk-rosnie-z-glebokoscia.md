---
typ: lekcja
tags: [lekcje, prefill, flash-attention, pomiar, dlugi-kontekst]
aktualizacja: 2026-11-09
zrodlo: ~/KERNEL/product/research/70-fa-d256-jak-to-zrobilismy.md §2, §3.5; ~/KERNEL/product/research/24v-prefill-fa.md (Werdykt, Profil); ~/qwen-opt/fa-d256/res/{bench,fill,select}.txt
status: aktualne
---
# Zysk kernela FA rośnie z głębokością: wynik negatywny ważny tylko w swoim reżimie

**Ten sam kernel 0,878× daje +0,5% przy d4k, +1,9% przy d32k i +5,8% przy d128k oraz w fillu 255k (2026-11-09). Bariery z raportu 24v odrzucono 2026-10-20 przy d32k (+0,84%), a przy 128k były częścią wygranej.**

Mechanizm: koszt FA na ubatch rośnie liniowo z głębokością, a reszta ubatcha (MMQ, GDN) jest stała. Udział FA (model z 24v): ~4% przy 4k, ~24% przy 32k, ~56% przy 128k. Zysk e2e ≈ udział × zysk kernela, więc krótkie prompty nigdy nie pokażą zmiany w FA.

Reguły:
- Mierzyć w reżimie pain pointu (dziś: 128k–255k), nie przy d=0 i nie tylko przy 32k.
- Wynik negatywny zapisywać razem z warunkami (głębokość, udział kernela). Gdy pain point się przesuwa, przejrzeć odrzucone pomysły z tym samym kernelem.
- Próg wyboru wariantu liczyć z udziału: 2% kernela przy udziale ~53% ≈ +1% e2e.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-wyrazna-wygrana-albo-nic]]
- [[lekcja-mikrobench-klamie]]
- [[sweep-wariantow-kernela]]
- [[2026-11-08-fa-d256-prefill]]
- [[raport-24v-prefill-fa]]
