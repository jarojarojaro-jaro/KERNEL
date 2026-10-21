---
typ: lekcja
tags: [lekcje, pm4, awarie, kolejka]
aktualizacja: 2026-10-21
zrodlo: journalctl -k 2026-10-21 04:07:21 (gfxhub page fault, llama-server pid 1293181, SQC (inst), PERMISSION_FAULTS 0x3); ~/qwen-opt/queue/logs/queue.log 04:06:43 START s53c-A1; ~/qwen-opt/queue/cancel.sh
status: aktualne
---
# Nie zabijaj serwera PM4 w trakcie taśmy (SIGKILL → page fault)

**2026-10-21 04:07 przy zatrzymaniu kolejki `cancel.sh` wysłał SIGKILL 3 s po SIGTERM do `llama-server` z profilem topki (PM4 WA=2 + GUARD, ramię A bez nowego kodu). Karta zgłosiła page fault SQC (inst) w trakcie zamykania procesu – taśma PM4 wykonywała się dalej, gdy pamięć kodu procesu była już zwalniana. Resetu nie było, karta po chwili bezczynna (0% / VRAM 0%, 42 °C).**

Wniosek: fault nie pochodził z testowanej zmiany, tylko z brutalnego zatrzymania. Reguły:
- procesy GPU kończymy SIGTERM i czekamy do 45 s; SIGKILL tylko gdy nadal żyją (`cancel.sh` poprawiony, najpierw zatrzymuje runnera `SIGSTOP`, żeby nie wystartował następnego zadania);
- `pkill -f llama-server` bez czekania jest zakazany przy działającej kolejce;
- po takim faulcie: sprawdzić `journalctl -k` pod kątem resetu, stan karty, dopiero potem dalsza praca.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-pm4-zamienia-fault-w-reset]]
- [[lekcja-pm4-zawsze-jawnie]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
