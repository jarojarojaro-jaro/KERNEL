---
typ: narzedzie
tags: [narzedzia, windows, workflow]
aktualizacja: 2026-10-16
zrodlo: ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5198 (odpowiedź z 2026-10-15 23:23 UTC)
status: aktualne
---
# ss (zrzut ekranu z Windowsa na serwer)

**Funkcja PowerShella `ss` w profilu użytkownika: zapisuje obrazek ze schowka jako PNG i kopiuje go przez `scp` do `/tmp` na serwerze, żeby agent mógł go przeczytać.**

Powód (2026-10-15): wklejanie zrzutów do czatu nie działało („clipboard is empty”). Kroki: `notepad $PROFILE`, wklejenie funkcji, ewentualnie `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Użycie: Win+Shift+S → `ss` → wypisuje `/tmp/screen-HHmmss.png`, którą ścieżkę podaje się agentowi. Funkcja używa `System.Windows.Forms.Clipboard::GetImage()` i aliasu SSH `serwer`.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[wiki-py]]
- [[run-llm-sh]]
- [[aplikacja-w-budowie]]
- [[hip-na-windows]]
