---
typ: narzedzie
tags: [narzedzia, serwer, launcher]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/run-llm.sh:1-40; ~/KERNEL/qwen-opt/README.md:28-31; ~/KERNEL/qwen-opt/STATUS-NEXT.md:16
status: aktualne
---
# run-llm.sh — start produkcyjnego serwera

**Jeden skrypt, który uruchamia zoptymalizowany llama-server na RX 7900 XTX z naszymi ustawieniami dla każdego modelu.**

Użycie: `run-llm.sh [qwen|uncensored|lfm|lfm-uncensored] [mtp|dflash|none] [rocm|vulkan]` (domyślnie qwen, mtp, rocm; dla LFM bez spekulacji).

Nagłówek skryptu (pomiar 2026-10-14, ROCm, ctx 204800, KV q4_0, MTP n=4 + słownik 64k, draft IQ4_XS, 6 promptów EN/PL, T=1): qwen ~109 t/s, uncensored ~115 t/s, lfm ~294 t/s (ctx 131072, KV q8_0), lfm-uncensored ~264 t/s.

Zmienne środowiskowe: `CTX` (domyślnie 204800, LFM 131072), `PORT` (8080), `HOST` (127.0.0.1), `KV` (q4_0; q8_0 dla LFM), `EFFORT` (długość myślenia: low domyślnie, medium, xhigh, off), `DRAFT_N`, `P_MIN`, `DRAFT_SAMPLING`, `MTP_TYPE` (iq4_xs), `VISION=1`, `ROCM_DIR` (domyślnie `~/llama-opt`), `EXTRA_ARGS`, `LOG` (log w `~/qwen-opt/logs/`, najnowszy jako `latest.log`).

Inne ustawienia wbudowane: `--cache-ram 16384`, KV draftu q4_0, `LLAMA_SERVER_REASONING_CONTROL=0` (łatka 0065; `REASONING_CONTROL=1` przywraca flagę z web UI); bez roota trzyma kontekst KFD przez `gpu-keepawake`, żeby karta nie usypiała. Biblioteki: `LD_LIBRARY_PATH=$ROCM_DIR/lib:/opt/rocm/core-10.0/lib`.

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- gpu-power-i-keepawake
- [[qwen3-8-27b]]
- [[wylaczniki-env]]
- [[spec-sweep]]
