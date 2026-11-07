---
typ: lekcja
tags: [lekcje, produkcja, serwer, operacje]
aktualizacja: 2026-11-07
zrodlo: /proc/<pid>/cmdline serwera :8080 (2026-11-07 16:38 → 22:xx); ~/qwen-opt/run-topka.sh:1-25; zgłoszenie agenta XtxHostL1
status: aktualne
---
# Po restarcie maszyny czat wstał na starym silniku, bo uruchomiłem `run-llm.sh` zamiast `run-topka.sh`

**2026-11-07 po nocnym restarcie uruchomiłem czat przez `./run-llm.sh uncensored`, a ten bez `ROCM_DIR` startuje `~/llama-opt` z 2026-10-15 bez przełączników topki (PM4, lookup W16, GPU verify, SAFE_SPECIAL, lean reserve, poprawki MTP z q63); produkcja przez ~6 h chodziła na starym buildzie, choć `/health` i n_ctx 262144 wyglądały dobrze. Wykrył to agent XtxHostL1 z `/proc/<pid>/cmdline`.**

Reguła:
- produkcja = `~/qwen-opt/run-topka.sh uncensored` (silnik `~/llama-topka`, topka-q63);
- po każdym (re)starcie sprawdzić nie tylko `/health` i n_ctx, ale też ścieżkę binarki w `/proc/<pid>/cmdline` (`~/llama-topka/bin/llama-server`) i zmienne `GGML_HIP_PM4`, `LLAMA_SPEC_LOOKUP` w `/proc/<pid>/environ`;
- joby kolejki odtwarzają serwer z zapisanego cmdline+env, więc zły start się utrwala — najpierw naprawić produkcję, potem mierzyć.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[2026-11-06-final-mode]]
- [[2026-11-06-sesja-uzytkownika-final-mode]]
