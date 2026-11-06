---
typ: eksperyment
tags: [eksperymenty, termika, rx-7900-xtx, eco]
aktualizacja: 2026-11-06
zrodlo: komunikat Main do WikiQ63 2026-11-06; /var/backups/xtx-eco/20261106T120738; ~/qwen-opt/thermal/q63-stock.csv; ~/qwen-opt/thermal/INSTALL.sh
status: do-sprawdzenia
---
# xtx-eco: instalacja 2026-11-06 i fabryczny OD_SCLK zmienny między bootami

**Użytkownik zainstalował xtx-eco 2026-11-06 o 12:07 UTC (backup `/var/backups/xtx-eco/20261106T120738`); pierwszy commit xtx-fan (12:08:38) zapisał 2885 MHz jako „stock”, choć po starcie 12:00 fabryczny `OD_SCLK 1` wynosił 2935 MHz.**

- 2026-11-05 fabryczny `OD_SCLK 1` = 2885 MHz; 2026-11-06 zaraz po boocie = 2935 MHz. Wartość była wpisana na sztywno, więc „powrót do stock” obniżał limit o 50 MHz.
- Wniosek: stock trzeba odczytać **przy każdym boocie**, przed pierwszym zapisem OD, i zapisać jako stan tego bootu. Poprawka w toku (agent główny) — status do sprawdzenia.
- Telemetria stock 2026-11-05 (`q63-stock.csv`, wg Main, faza pomiarów q63): 281 W średnio przy capie 285 W, sclk średnio 2436 MHz, junction 65–66 °C, pamięć 71–74 °C, CPU 37 °C. Cały plik (14:41–16:32, wiersze ≥ 250 W, z prefillami 128k) daje junction do 89 °C.

## Powiązane
- [[eksperymenty/_hub|eksperymenty]]
- [[2026-11-05-q63-topka]]
- [[2026-11-05-termika-eco-test]]
- [[raport-64-termika]]
- [[lekcja-od-commit-gubi-krzywa]]
