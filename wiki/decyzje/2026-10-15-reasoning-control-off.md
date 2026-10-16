---
typ: decyzja
tags: [decyzje, sampler, ui]
aktualizacja: 2026-10-16
zrodlo: ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:4332-4334,4360,4380; ~/KERNEL/qwen-opt/NOTES.md:382
status: aktualne
---
# 2026-10-15: reasoning_control wyłączony domyślnie

**Użytkownik kazał samemu ustawić `reasoning_control` (2026-10-15 00:14 UTC: „NO DOBRA TO USTAW TO REASING CONTROL SAM”); serwer startuje z `{"reasoning_control": false}`, a łatka 0065 ignoruje tę flagę z web UI.**

Powód: flaga z web UI włączała wolną ścieżkę samplera (LFM 291.4 vs 255.6 t/s przy tym samym zapytaniu). Wykonanie: `run-llm.sh` wysyła `--ui-config` z `reasoning_control: false`; 0065 `LLAMA_SERVER_REASONING_CONTROL=0` sprawia, że serwer ignoruje flagę (`REASONING_CONTROL=1` w `run-llm.sh` przywraca). Jakość modelu się nie zmienia; poziomy Low/Medium/High w UI to osobne limity myślenia.

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[2026-10-14-lfm-kv-q8]]
- [[2026-10-15-czat-na-web-ui-llama]]
- [[lekcja-wolna-sciezka-samplera]]
- [[sampler-fast-path]]
