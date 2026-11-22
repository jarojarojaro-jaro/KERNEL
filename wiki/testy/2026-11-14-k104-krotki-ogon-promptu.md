---
typ: test
tags: [testy, xtx, ttft, checkpointy, gdn, kolejka]
aktualizacja: 2026-11-14
zrodlo: ~/KERNEL/qwen-opt/k104/{k104.py,k104.jobs,res/k104.json,res/xtxbench.log}; ~/KERNEL/qwen-opt/patches/k104/0001-*.patch (gałąź k104-short-tail @ 5bbc8d442 na topka-q70)
status: aktualne
model: qwen3-8-27b-uncensored
karta: rx-7900-xtx
wyniki:
  - qwen3-8-27b-uncensored | rx-7900-xtx | 128,0 t/s | dekod 1,7k; SHORT_TAIL=32 (KILL, produkcja 135,4) | 2026-11-14
  - qwen3-8-27b-uncensored | rx-7900-xtx | 148,5 ms | prompt krótkiej tury mediana; SHORT_TAIL=32 (produkcja 148,7) | 2026-11-14
k: K-104
---
# 2026-11-14: K-104 — krótki ogon promptu w jednym przebiegu: KILL (0 ms zysku, zmienia md5, −5,5% dekodu)

**Przełącznik `LLAMA_SERVER_SHORT_TAIL=32` przetwarza ogon promptu ≤ 32 tokenów w jednym batchu, bez cięcia na ostatniej wiadomości użytkownika i na n−4. Na 40 krótkich turach czatu nie skraca promptu: 148,7 → 148,5 ms (mediana). Zmienia za to odpowiedzi (greedy i decode 1,7k) i obniża decode przy 1,7k: 135,4 → 128,0 t/s. Odrzucone.**

| ramię (świeży serwer, XTX eco 2200, port testowy) | prompt ms mediana / średnia | ściana mediana | 40 tur md5 | greedy md5 | 1,7k md5 | decode 1,7k |
|---|---|---|---|---|---|---|
| P: produkcja `~/llama-topka` | 148,7 / 150,6 | 471,4 | 2796eeae | 7dfc9b71 / 76ba8207 | 3f26f79c | 135,4 |
| C: nowy build, flaga wyłączona | 149,6 / 151,6 | 471,8 | 2796eeae | 7dfc9b71 / 76ba8207 | 3f26f79c | 135,6 |
| V: `SHORT_TAIL=32` | 148,5 / 150,8 | 470,1 | 2796eeae | **a0dde0fa / 456a8b51** | **67daa383** | **128,0** |
| P2: produkcja (powtórka) | 149,3 / 151,1 | 472,5 | 2796eeae | 7dfc9b71 / 76ba8207 | 3f26f79c | 135,5 |

**Wnioski:**
- Diagnoza z K-003 („prefill krótkiego ogona w 2–3 przebiegach to ~80–100 ms”) była błędna. W krótkich turach ogon nie jest dzielony, a koszt promptu (~149 ms przy max_tokens 32) to:
  - przywrócenie checkpointu GDN;
  - nowe checkpointy;
  - jeden przebieg z hakiem MTP.
- Zmiana md5 w V pochodzi z dłuższych promptów: greedy czatu i 1,7k mają ogon ≤ 32 i inny podział ubatchy, więc inna kolejność sum. Spadek decode przy 1,7k bierze się z innej akceptacji draftu na tym tekście.
- Następny kandydat na koszt stały krótkiej tury to mniej kopii checkpointów, np. nie odtwarzać checkpointu, z którego właśnie przywracamy. Najpierw sprawdzić w kodzie na CPU; niezmierzone.

## Powiązane
- [[KOLEJKA-TESTOW]]
- [[2026-11-14-k002-k003-k013-xtx]]
- [[2026-11-14-k001-wyciek-stanu-restore]]
- [[siatka-checkpointow-gdn]]
