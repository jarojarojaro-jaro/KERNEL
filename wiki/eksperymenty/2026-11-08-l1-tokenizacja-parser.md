---
typ: eksperyment
tags: [eksperymenty, rx-7900-xtx, serwer, host, tokenizacja, agent]
aktualizacja: 2026-11-09
zrodlo: ~/qwen-opt/l1tok/results.jsonl (ramiona A1, B1, B2; 2026-11-08 00:58–01:25); ~/qwen-opt/l1tok/NOTE.md; branch l1-tokparse 8a18c3077; ~/KERNEL/qwen-opt/patches/l1-tokparse/
status: aktualne
---
# Cache tokenizacji na ścieżce SAFE_SPECIAL + parser przyrostowy: tokenizacja 14,0 → 6,6 ms, wyjście identyczne (2026-11-08, pomiar częściowy)

**Na prawdziwym replayu 2 wątków agenta (82–119k kontekstu, 16 tur na ramię) `LLAMA_SERVER_TOK_CACHE=1` + `LLAMA_SERVER_PARSE_INC=1` skróciły tokenizację z mediany 14,0 do 6,6 ms i czas tury poza prefillem z 1 704 do 1 619 ms (−85 ms), przy identycznym md5 greedy, identycznym tekście strumienia i 0 rozbieżności tokenów; decode bez zmian (spec_sweep 110,0 → 110,1 t/s). Pomiar przerwany przed ramieniem A2 (koniec testów na polecenie użytkownika), więc to jedna para A→B, nie pełne ABBA.**

Warunki: final mode (eco 2200), produkcja `~/llama-topka` (A) vs `~/wt/l1-tokparse/build-hip` z przełącznikami (B1: TOK_CACHE + PARSE_INC, B2: + STREAM_STEP), `run-topka.sh uncensored`, n_ctx 262 144.

| Pomiar | A1 (produkcja) | B1 | B2 | Δ B1 vs A1 |
|---|---|---|---|---|
| tokenizacja, mediana (16 tur 82–119k) | 14,0 ms | 6,6 ms | 6,5 ms | −53% |
| tura poza prefillem (wall − prompt), mediana | 1 704 ms | 1 619 ms | 1 592 ms | −85 ms (−5%) |
| tura całkowita, mediana | 14 538 ms | 14 488 ms | 14 462 ms | −0,3% |
| rozbieżności tokenów | 0 | 0 | 0 | – |
| strumień 12k: t/s (stream) / CPU serwera | 146,0 / 89,7 s | 146,1 / 87,1 s | – | +0,1% / −2,9% |
| md5 tekstu strumienia (off / on) | 9b4c1dfc / d5ac41fc | 9b4c1dfc / d5ac41fc | – | = |
| md5 greedy | 64c507b6 | 64c507b6 | – | = |
| spec_sweep T=1 (seed 1) | 110,0 t/s, 26,84 ms/krok | 110,1 t/s, 26,83 ms/krok | – | 0% |

Dowody CPU (2026-11-07): `test-tok-cache` 257 prawdziwych zapytań do 284k — 0 rozbieżności, przy 90k+ pełna tokenizacja 123–187 ms → z cache 1,3–2,1 ms (pojedynczy wątek; w produkcji `TOKENIZE_PAR=8` już skraca pełną do ~14 ms); `test-chat-stream-inc` 1 237 wyjść / 746k tokenów — wyrocznia 0 rozbieżności, 574/574 tool calli, CPU parsera 36,1 → 0,98 s.

**Werdykt:** bezstratne i spełnia kryterium „B nie wolniejsze”; zysk na turze agenta to ~85 ms przy 80–120k (głównie tokenizacja), decode bez zmian. Kryterium z NOTE („tokenizacja ≥ 10 ms niżej”) nie jest spełnione przy `TOKENIZE_PAR=8` (−7,4 ms), więc do wdrożenia tylko jako ulga CPU, po dokończeniu A2 (ABBA) i ramienia kontrolnego C (`=2`, wyrocznia na GPU).

## Stan / do wznowienia
- `run-jobs.sh ~/qwen-opt/l1tok/l1tok.jobs` z samymi ramionami A2 i C (A1/B1/B2 są w `results.jsonl`); build gotowy.
- Nic nie wdrożone; przełączniki domyślnie wyłączone.

## Powiązane
- [[eksperymenty/_hub|eksperymenty]]
- [[strumien-on-wyrocznia]]
- [[raport-66-synteza]]
- [[2026-11-08-kvq-once-profil]]
