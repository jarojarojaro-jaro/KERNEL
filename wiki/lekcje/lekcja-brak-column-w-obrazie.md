---
typ: lekcja
tags: [lekcje, chmura, skrypty]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/bootstrap.sh:131; ~/qwen-opt/cloud/runs/5060ti/bootstrap.sh:131; ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5426
status: aktualne
---
# Brak programu `column` w obrazie CUDA zatrzymał benchmark

**Obraz `nvidia/cuda:12.8.1-devel-ubuntu24.04` nie ma `column`; wywołanie w `bootstrap.sh` przy `set -e` zatrzymywało benchmarki na wynajętej karcie (2026-10-16).**

Naprawa: `if command -v column …; then column -t …; else cat …; fi` (w kopii 5060 Ti po prostu `cat` z komentarzem „`column` is not in the CUDA image”). Lekcja: skrypty na wynajętej maszynie testować na tym samym obrazie (dry run w kontenerze) i nie używać narzędzi kosmetycznych spoza obrazu bazowego, bo każda minuta stojącej karty kosztuje.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-5060ti-bezczynna]]
- [[lekcja-vast-cli-klucz]]
- [[skrypty-chmury]]
- [[harness-chmurowy]]
