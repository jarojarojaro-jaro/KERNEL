---
typ: metoda
tags: [metody, kernel, pomiar, bit-exact, rx-7900-xtx]
aktualizacja: 2026-11-09
zrodlo: ~/KERNEL/product/research/70-fa-d256-jak-to-zrobilismy.md §4–5; ~/qwen-opt/fa-d256/{common,gate,micro,md5,bench,arm}.sh, select.py, res/select.txt; ~/wt/fa-d256 32292cc0a (fattn-mma-f16.cuh:236-275,2213-2324)
status: aktualne
---
# Sweep wariantów kernela: jedna binarka, maska env, bramka bitowa, ABBA przy głębokości

**Pomysły na kernel kodujemy jako bity jednej maski env w jednej binarce. Przepuszczamy je przez bramkę bitową, mierzymy wszystkie kombinacje na kształtach produkcji, wybieramy automatycznie i potwierdzamy ABBA w reżimie pain pointu. Tak powstał FA D256 VAR 83: fill 255k +5,8%, bitowo = (2026-11-09).**

Kroki (wzór: `~/qwen-opt/fa-d256/`, 62 min GPU + 7 min build):
1. **Profil przed kodem:** udział kernela w czasie tam, gdzie boli (głębokość, kształt). Sufit = udział × spodziewany zysk kernela ([[lekcja-zysk-rosnie-z-glebokoscia]]).
2. **Kod:** parametr szablonu `int fv = 0`, każda decyzja jako `constexpr bool`, lista masek w X-makrze, env czytany raz, nieznana maska → 0 z ostrzeżeniem. VAR 0 = ISA produkcji (sprawdzić).
3. **ISA na CPU:** VGPR/spill/scratch per wariant (`isa.sh`). Spille w pętli to pierwszy cel.
4. **Bramka:** `test-backend-ops` PASS + linia wariantu w logu; md5 długiego promptu (wiele ubatchy) z top-5 logprobs, plus ramię produkcji. **Kontrola pozytywna:** wariant stratny musi dać inny md5, inaczej równe md5 nic nie dowodzi.
5. **Mikrobench:** wszystkie PASS × kształty/głębokości produkcji, kolejność S + odwrócone S.
6. **Wybór skryptem:** bitowy ∩ PASS ∩ md5 = VAR 0 ∩ VAR 0 = produkcja, wynik na kształcie pain pointu, próg z udziału.
7. **ABBA** `llama-bench -d …` na tej samej binarce, potem **ramiona produkcyjne** (md5 32k, spec_sweep, fill 255k, VRAM).

Reguły: przeszukiwać kombinacje (V2_32 sam −5,0%, z VT −12,2%); „bitowo z konstrukcji” potwierdza dopiero md5 (KQ4 przeszedł tbo, md5 ≠); przed jobem uruchomić każdą binarkę harnessu na CPU (rc=127 przez RUNPATH); krok bez danych kończy się rc≠0; w jobie nigdy `cpuheavy`. Kolejne cele: [raport 70 §5](../../product/research/70-fa-d256-jak-to-zrobilismy.md).

## Powiązane
- [[metody/_hub|metody]]
- [[pomiar-abba]]
- [[kernel-tuner]]
- [[mikrobench-granicy-kernela]]
- [[2026-11-08-fa-d256-prefill]]
- [[raport-24v-prefill-fa]]
- [[lekcja-cpuheavy-w-jobie-kolejki]]
- [[lekcja-flaga-bez-dowodu-dzialania]]
