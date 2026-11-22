---
typ: test
tags: [testy, spekulacja, lookup, build]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/20-build-topka.md:1-85; ~/qwen-opt/topka/logs/copy_bench.jsonl (fast-qwen-mtponly, fast-qwen-topka, fast-unc-topka); ~/qwen-opt/topka/greedy/; ~/KERNEL/product/research/20-build-topka.md:5-17,59,63-68,82-84
status: aktualne
---
# 2026-10-19: build „topka” – ogon lookupu + współdzielenie cache, PM4 wyłączone

**Gałąź `topka` (od `amd-opt` @ `f61994f58`: `6c21a3e9f` = ogon lookupu, `22e2b0f55` = `CACHE_SHARE_MIN`, bez kontrolera) zainstalowana w `~/llama-topka` daje na code-edit `mvs` przy T=0 Qwen 166.1 → **396.9 t/s (×2.39)** i Uncensored **414.8 t/s**, z PM4 wyłączonym i tekstem greedy jak w produkcji (szybka ścieżka, jeden przebieg).**

Launcher `~/qwen-opt/run-topka.sh qwen|uncensored` = `run-llm.sh` (port 8080) + `LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 GGML_HIP_PM4=0 DRAFT_N=4`. Stop: `pkill -f 'llama-topka/bin/llama-server'`; powrót: `~/qwen-opt/run-llm.sh qwen` (`~/llama-opt` nietknięte).

| model | obciążenie | wynik | tok/krok, ms/krok |
|---|---|---|---|
| Qwen | `mvs` T=0 | 396.9 t/s (391.1–405.8) | 14.03–14.42, 35.5–36.1 ms |
| Qwen | `spec_sweep` T=1, 1 seed | 105.1 t/s | 29.10 ms/krok |
| Uncensored | `mvs` T=0 | 414.8 t/s (406.1–421.1) | 14.03–14.42, 34.3–34.8 ms |
| Uncensored | `spec_sweep` T=1, 1 seed | 106.9 t/s | 28.03 ms/krok |

Odniesienie bez PM4: 103.7 / 109.9 t/s (`NOTES.md:375`); czat przy 1 seedzie to szum tekstu ([[lekcja-ogon-zmienia-tekst-t1]]). Poprawność: greedy `c4708318` / `6f14e814` = produkcja; `mvs` T=0 4/4 md5 jak MTP-only. Page faulty w `journalctl -k -b 0`: 31 przed, 31 po. Lookup na `mvs`: 1043 kroki, łańcuchy 239 (3320/3562 przyjętych), host 2.5 ms łącznie. VRAM ~23.5 / ~22.9 GiB (przybliżone).

Pierwszy przebieg zatrzymał [[gpu-guard]] fałszywym alarmem zero-RPM ([[lekcja-wentylator-rdna3]]); wyniki odrzucone, blok powtórzony. Nie zrobione: ABBA vs produkcja, ≥ 5 seedów, `copy`/`long`, TTFT nowej sesji, `DRAFT_N` 4/5/6 (harness `~/qwen-opt/topka/arm.sh`). PM4 dopiero po poprawce z raportu 17.

## Ze scalonej notatki: Raport 20: build „topka” (ogon lookupu + współdzielenie cache promptu)

Topka = amd-opt @ `f61994f58` + ogon lookupu (`6c21a3e9f`) + `CACHE_SHARE_MIN` (`22e2b0f55`), PM4 wyłączone; greedy md5 = produkcja, code-edit `mvs` T=0 Qwen 166.1 → 396.9 t/s, Uncensored 414.8 t/s (2026-10-19).

- Launcher `~/qwen-opt/run-topka.sh qwen|uncensored`: `LLAMA_SPEC_LOOKUP=3 W=16`, `LLAMA_SERVER_CACHE_SHARE_MIN=1024`, `GGML_HIP_PM4=0`, `DRAFT_N=4` (`20:10`).
- Poprawność: plain `c4708318`, MTP `6f14e814`; `mvs` T=0 4/4 md5 jak MTP-only; page faulty 31 → 31 (`20:12-14`).
- Czat T=1, 1 seed: Qwen 105.1, Uncensored 106.9 t/s – w szumie tekstu T=1 (`20:17`).
- Fałszywy alarm gpu-guard (zero-RPM firmware) – guard poprawiony (`20:59`).
- Szczegóły eksperymentu: [[2026-10-19-build-topka]]. Późniejszy stan topki (PM4 WA=2, GPU verify): [[raport-26-kolejka-gpu]], [[raport-wyniki-xtx-2026-10-19]].

## Powiązane
- [[2026-10-18-lookup-ogon]]
- [[2026-10-18-cache-promptu-agenta]]
- [[testy/2026-10-19-page-faulty-gpu-analiza]]
- [[REKORDY]]
