---
typ: lekcja
tags: [lekcje, omp, topka, uzytkownik, proces]
aktualizacja: 2026-10-21
zrodlo: ~/.omp/agent/config.yml:9 (`modelRoles.default: llama.cpp//home/jaro/models/lfm/LFM2.5-24B-A2B-Uncensored-AD-Q5_K_M.gguf`); `~/qwen-opt/run-llm.sh:32` (HOST domyślnie 127.0.0.1); rozmowa z użytkownikiem 2026-10-21
status: aktualne
---
# Jak użytkownik testuje model: omp na serwerze → llama.cpp na :8080

**Użytkownik łączy się z Windowsa przez SSH z serwerem i uruchamia omp NA SERWERZE. omp ma wbudowane wykrywanie llama.cpp pod `http://127.0.0.1:8080` (provider `llama.cpp`), a domyślny model w `~/.omp/agent/config.yml` to już `llama.cpp//home/jaro/models/lfm/LFM2.5-24B-A2B-Uncensored-AD-Q5_K_M.gguf`. Nic nie trzeba konfigurować: wystarczy, że topka słucha na :8080.**

- **Od 2026-10-21 standard: przełącznik modeli `~/qwen-opt/tools/model-swap.py`** (`setsid nohup ~/qwen-opt/tools/model-swap.py > ~/qwen-opt/logs/model-swap.log 2>&1 &`). Słucha na 0.0.0.0:8080, `/v1/models` pokazuje dwa modele (LFM2.5-24B Uncensored i Qwen3.8-27B Uncensored, id = ścieżki GGUF jak w llama-server), a żądanie z drugim modelem czeka na koniec bieżących, zatrzymuje serwer (bezczynne /slots, jeden SIGTERM) i startuje drugi profil `run-topka.sh` na 127.0.0.1:8081. Zmiana: LFM→Qwen 6–8 s (pierwszy raz 43 s: budowa cache MTP), Qwen→LFM ~6 s. W omp: `/model` → `llama.cpp` → wybór modelu. `run-jobs.sh` zatrzymuje przełącznik przed testami GPU; po testach uruchomić go ponownie.
- Pojedynczy model bez przełącznika: `HOST=0.0.0.0 ~/qwen-opt/run-topka.sh <qwen|uncensored|lfm|lfm-uncensored>` (127.0.0.1 + LAN).
- Sam `HOST=192.168.10.230` psuje omp na serwerze (127.0.0.1:8080 nic nie ma); sam domyślny 127.0.0.1 nie wpuszcza LAN.
- Nie każ użytkownikowi ustawiać `LLAMA_CPP_BASE_URL` ani `setx` – wpisuje komendy w oknie SSH (bash), nie w PowerShell.
- Przed startem: testy GPU zatrzymane (`cancel.sh`), jeden serwer na :8080; zatrzymanie serwera tylko przy bezczynnych `/slots`, jednym SIGTERM (raport 55).
