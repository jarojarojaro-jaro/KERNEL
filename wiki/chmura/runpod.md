---
typ: chmura
tags: [chmura, runpod, nvidia]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:67,99-114; ~/qwen-opt/cloud/PLAN-TESTOW.md:11-13,21-22,138-142; ~/qwen-opt/cloud/env.sh (nagłówek); ~/KERNEL/product/research/11-mtp-pl-pilot.md:8,164-174
status: aktualne
---
# RunPod

**Druga chmura w harnessie: Community i Secure Cloud z kartami 3070…5090, jedyne AMD to MI300X ($2.39/h); u nas przewidziany dla RTX 4090 i 5090, których nie ma w pierwszej rundzie.**

- Oferta (raport 05): kontenery (Pod), Serverless, Clusters; kontenery bez trybu privileged; REST API, `runpodctl`, oficjalny serwer MCP.
- Ceny z tabeli raportu (najtańszy wariant wg computeprices 2026-10-15 / cena z runpod.io 2026-10-08, prawdopodobnie Secure Cloud; $/h): RTX 3090 0.22 / 0.50, 4090 0.34 / 0.89, 5090 0.69 / 1.19; MI300X Secure 2.39.
- Narzędzia u nas: `runpodctl` 3.0.1 (`cloud/bin`, sha256 z release sprawdzony), runpod SDK 1.11 w `cloud/.venv`; klucz w pliku na serwerze (`env.sh` eksportuje go jako zmienną; SDK Pythona czyta tylko swój plik konfiguracyjny albo wartość ustawioną w kodzie).
- Plan (PLAN-TESTOW §5): później tylko 4090 ($0.89/h) i 5090 ($1.19/h), bo 3060/3090/5060 Ti nie ma tam na liście; skrypty bootstrap/bench są niezależne od dostawcy, brakuje odpowiednika `up.sh` (`runpodctl pod create …`). Uwaga: `--cloud-type COMMUNITY` nie gwarantuje publicznego portu 22.

Użyty 2026-10-16 do pilota douczania głowicy MTP: A40 48 GB Secure $0.59/h + dysk 150 GB, 3.50 h, **$2.14** z limitu $6; pod usunięty (`podTerminate`, potwierdzone na liście podów). Drugi pod na koncie należy do użytkownika i nie był dotykany. W kontenerze `llama-server` bierze 96 wątków przy limicie 7.65 CPU → `-t 6 -tb 6`.

## Powiązane
- [[chmura/_hub|Chmura]]
- [[vast-ai]]
- [[harness-chmurowy]]
- [[mi300x]]
- [[inne-karty-nvidia]]
- [[2026-10-16-mtp-pl-pilot]]
- [[lekcja-limit-cpu-kontenera]]
