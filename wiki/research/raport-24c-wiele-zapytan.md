---
typ: research
tags: [research, serwer, wiele-zapytan, wynik-negatywny]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24c-wiele-zapytan.md:3,14-35,47-50
status: aktualne
---
# Raport 24c: wiele zapytań naraz na topce (`-np 2/4`) – kill

**`-np 2` jest wolniejsze od `-np 1` na pojedynczym zapytaniu (−5…−17%) i na powtórce prawdziwego fan-outu omp (wall 287.4 vs 258.0 s, +11%), a przy `-kvu` greedy md5 zależy od historii serwera (2026-10-19).**

- Koszt slotu w hybrydzie GDN: `(1 + max(draft, LOOKUP_W))` kopii stanu, ~2.4 GB na slot przy W16; np2 W16 przy CTX 65536 padł z OOM w `hipGraphInstantiate` (`24c:27,31`).
- np4 W4: single −3% (2 prompty), wall niezmierzony – otwarte (`24c:19,49`).
- Prawdziwy koszt fan-outu w np1 to thrash cache: 15/32 tur bez trafienia, prefill 151 z 258 s (`24c:25,35`).
- Wspólny prefiks to tylko ~76% system promptu omp (`Your id is X` w środku) (`24c:34`).

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[ksztalt-ruchu-agentowego]]
- [[2026-10-19-workload-omp]]
- [[raport-24i-sciezka-agenta]]
