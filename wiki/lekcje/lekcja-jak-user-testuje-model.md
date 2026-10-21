---
typ: lekcja
tags: [lekcje, omp, topka, uzytkownik, proces]
aktualizacja: 2026-10-21
zrodlo: ~/.omp/agent/config.yml:9 (`modelRoles.default: llama.cpp//home/jaro/models/lfm/LFM2.5-24B-A2B-Uncensored-AD-Q5_K_M.gguf`); `~/qwen-opt/run-llm.sh:32` (HOST domyślnie 127.0.0.1); rozmowa z użytkownikiem 2026-10-21
status: aktualne
---
# Jak użytkownik testuje model: omp na serwerze → llama.cpp na :8080

**Użytkownik łączy się z Windowsa przez SSH z serwerem i uruchamia omp NA SERWERZE. omp ma wbudowane wykrywanie llama.cpp pod `http://127.0.0.1:8080` (provider `llama.cpp`), a domyślny model w `~/.omp/agent/config.yml` to już `llama.cpp//home/jaro/models/lfm/LFM2.5-24B-A2B-Uncensored-AD-Q5_K_M.gguf`. Nic nie trzeba konfigurować: wystarczy, że topka słucha na :8080.**

- Start dla testów użytkownika: `HOST=0.0.0.0 ~/qwen-opt/run-topka.sh <qwen|uncensored|lfm|lfm-uncensored>` – słucha jednocześnie na 127.0.0.1 (omp na serwerze) i 192.168.10.230 (przeglądarka/aplikacje w LAN).
- Sam `HOST=192.168.10.230` psuje omp na serwerze (127.0.0.1:8080 nic nie ma); sam domyślny 127.0.0.1 nie wpuszcza LAN.
- Nie każ użytkownikowi ustawiać `LLAMA_CPP_BASE_URL` ani `setx` – wpisuje komendy w oknie SSH (bash), nie w PowerShell.
- Przed startem: testy GPU zatrzymane (`cancel.sh`), jeden serwer na :8080; zatrzymanie serwera tylko przy bezczynnych `/slots`, jednym SIGTERM (raport 55).
