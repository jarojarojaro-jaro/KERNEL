---
typ: lekcja
tags: [lekcje, chmura, vast]
aktualizacja: 2026-10-16
zrodlo: ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5353-5356,5395; ~/qwen-opt/cloud/env.sh:4-5
status: aktualne
---
# vast CLI wymaga jawnego --api-key

**`vastai show instances` po `source env.sh` w powłoce agenta zwrócił „Failed with error 403: This action requires login”; zadziałało dopiero `vastai --api-key "$(cat ~/.vast/key)" …` (2026-10-16).**

Kolejność odczytu klucza w vastai 1.8.3: `--api-key` > `$VAST_API_KEY` > `~/.config/vastai/vast_api_key`. Zmienna z `env.sh` nie dotarła do procesu CLI w tamtym wywołaniu, więc reguła dla agentów chmurowych: przed każdym przedłużeniem `vastai --api-key "$(cat ~/.vast/key)" show user`. Klucz zawsze z pliku z `chmod 600`, nigdy w repo ani w notatkach.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-brak-column-w-obrazie]]
- [[lekcja-5060ti-bezczynna]]
- [[vast-ai]]
- [[skrypty-chmury]]
