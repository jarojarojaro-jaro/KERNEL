---
typ: rocm
tags: [rocm, amdgpu, kfd, do-zbadania]
aktualizacja: 2026-11-05
zrodlo: komunikat Main do WikiQ63 2026-11-06; journalctl -k (2026-10-25 … 2026-11-05)
status: do-sprawdzenia
---
# `amdgpu: init_user_pages: Failed to get user pages: -1` przy starcie serwera

**Każdy start llama-server na XTX wypisuje do logu jądra ~16 tys. wierszy `amdgpu: init_user_pages: Failed to get user pages: -1`; zjawisko trwa co najmniej od 2026-10-25, bez page faultów, resetów i wpływu na wyniki (md5 bramek zgodne).**

- `init_user_pages` to rejestracja pamięci użytkownika (userptr) w KFD; `-1` (EPERM) zwykle oznacza, że `get_user_pages` odmówił zakresu, np. mapowania pliku lub pamięci, której nie da się przypiąć `[INFERENCE]`.
- Podejrzani: rejestracja `mmap` modelu GGUF albo buforów hosta przez HIP (`hipHostRegister`) — por. [[hip-kopie-stronicowane-zostawiaja-svm]].
- Do zrobienia: skorelować liczbę wierszy z rozmiarem modelu i flagami `--mmap`/`--no-mmap`; sprawdzić, czy którekolwiek wywołanie HIP zwraca błąd w samym serwerze. Do czasu wyjaśnienia: tylko obserwacja.

## Powiązane
- [[rocm/_hub|rocm]]
- [[dekodowanie-page-fault-amdgpu]]
- [[kfd-smi-eventy]]
- [[2026-11-05-q63-topka]]
