---
typ: narzedzie
tags: [narzedzia, gpu, bezpieczenstwo]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/qwen-opt/tools/gpu-guard.sh:1-45; ~/KERNEL/AGENTS.md:5; ~/KERNEL/qwen-opt/tools/gpu-guard.sh:36-39; ~/qwen-opt/tools/gpu-guard.log:3
status: aktualne
---
# Strażnik GPU: `qwen-opt/tools/gpu-guard.sh`

**Skrypt odpytuje co 2 s log jądra i sensory XTX; przy zagrożeniu zabija wszystkie `llama-server` / `llama-bench` / `llama-perplexity` / `test-backend-ops` / `magnitude-engine` poza produkcją na :8080, zapisuje powód do `gpu-guard.log` i kończy się kodem 3, który budzi agenta głównego.**

Warunki zatrzymania:
- nowy w `journalctl -k`: page fault amdgpu, timeout ringu, `GPU reset begin`, „MES might be…”;
- hotspot ≥ 100 °C albo VRAM ≥ 98 °C;
- busy ≥ 50% przy wentylatorze < 2500 RPM przez 20 s, ale tylko gdy hotspot ≥ 80 °C albo VRAM ≥ 82 °C.

Wczesne ostrzeżenie (bez zabijania): VRAM ≥ 85 °C albo hotspot ≥ 90 °C. Wpis WARN w logu najwyżej raz na 60 s, **strażnik działa dalej**, więc progi zatrzymania nadal obowiązują.

Poprawki z 2026-11-19 (audyt Gemini, potwierdzony w kodzie):
- Przy ostrzeżeniu strażnik robił `exit 4` i przestawał pilnować karty. Wyższe progi (100/98 °C, wentylator, faulty) przestawały wtedy działać.
- Procesy wybierane po dokładnej nazwie (`pgrep '^(llama-server|…)$'`), nie `pgrep -f`, które łapało powłoki agentów ([[lekcja-pkill-wlasna-powloka]]).
- Produkcja chroniona też podczas ładowania: proces z binarki `~/llama-topka`, nie tylko nasłuchujący na :8080.
- Zatrzymanie: jeden SIGTERM, do 60 s czekania, potem SIGKILL (zasada właściciela; wcześniej SIGKILL po 3 s).
- `run-jobs.sh` uruchamia strażnika na czas całej kolejki (wcześniej tego nie robił) i zatrzymuje kolejkę po jobie, jeśli strażnik nie żyje.
- Test na makietach sysfs: 91 °C daje WARN i pracę dalej, 101 °C daje STOP i rc 3; proces ignorujący SIGTERM dostaje SIGKILL, a powłoka z „llama-bench” w poleceniu zostaje nietknięta.
- **Wdrożenie: jaroserverai ma własne `~/qwen-opt`, a poprawki są w repo `~/KERNEL/qwen-opt`. Przy najbliższym włączeniu skopiować `tools/gpu-guard.sh` i `queue/run-jobs.sh` (diff przed kopią) [sposób synchronizacji niesprawdzony].**

Poprawka (2026-10-19): „wentylator stoi pod obciążeniem” liczy się tylko przy hotspot ≥ 80 °C albo VRAM ≥ 82 °C – firmware zero-RPM trzyma 0 RPM do ~70 °C (fałszywy alarm 02:39:41 przy hotspot 67 °C, VRAM 70 °C; [[lekcja-wentylator-rdna3]]).

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
- [[lekcja-wentylator-rdna3]]
- [[serializacja-gpu]]
