---
typ: eksperyment
tags: [eksperymenty, cache, agent, serwer]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16f-xtx-szybkie.md:15,151-190; ~/wt/quickwins/qw/e4.jsonl; ~/llama-master server-task.cpp:1824; commit `50c3a2f2a` (gałąź `quickwins`)
status: aktualne
---
# 2026-10-18: audyt cache promptu agenta (E4 z 16f)

**Przeliczenie ~7.3k tokenów na starcie nowej sesji omp to skutek obcego zapytania, które zajęło slot, i reguły `f_keep < 0.25` w `--cache-ram` (`server-task.cpp:1824`); łatka `LLAMA_SERVER_CACHE_SHARE_MIN=1024` skraca start sesji Qwena 8019 → 1612 ms i LFM 1357 → 230 ms.**

Co wysyła omp (18.10.4, przechwycone atrapą): prompt systemowy stały (md5 `f3b2fed4`, 10 194 znaków, 11 narzędzi), data i cwd w pierwszej wiadomości usera, w trybie `-p` jedno POST na turę; `prompt_cache_key` serwer ignoruje.

| scenariusz (sesja 53k → obce zapytanie → nowa sesja) | LFM przeliczone / wall | Qwen MTP |
|---|---|---|
| bez obcego zapytania | 502 / 554 ms | – |
| po obcym, bez łatki | 7276 / 1357 ms | 7341 / 8019 ms |
| `CACHE_SHARE_MIN=1024` | 502 / 230 ms | 63 / 1612 ms |
| + `LLAMA_LFM2_MSG_SPANS=1` | 60 / 166 ms | – |

Łatka przywraca kopię pominiętego wpisu (oryginał zostaje), md5 bez zmian (`c4708318` / `6f14e814` / `894e56e4`); `LFM2_MSG_SPANS` zmienia md5 LFM (`407b8411`), więc opcjonalny. Pozostały koszt Qwena: ~1.1 s przywracanie 2.3 GB stanu z RAM, ~200 ms checkpointy. `--cache-ram 16384` wystarcza.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[2026-10-12-cache-promptu-i-a7]]
- [[cache-sesji-na-dysku]]
- [[2026-10-18-hak-mtp-i-checkpointy]]
- [[wylaczniki-env]]
