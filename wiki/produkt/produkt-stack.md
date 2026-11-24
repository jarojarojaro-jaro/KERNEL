---
typ: produkt
tags: [produkt, plan, stack]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/PLAN.md:301-313
status: aktualne
---
# Stack technologiczny

**llama.cpp jako cienka nakładka, daemon i TUI w Rust (ratatui), GUI w Tauri 2 z web UI llama.cpp, API OpenAI/Anthropic/Ollama tylko na 127.0.0.1 z tokenem.**

- Silnik: llama.cpp na tagach semver, paczki per arch, parametry w danych; alternatywy MLX (Mac, faza 3), turbo-silnik per model (faza 4).
- Daemon: Rust, silnik jako proces potomny (izolacja crashy); alternatywa Go.
- GUI: Tauri 2 (instalator 3–15 MB) + web UI z llama.cpp; na Linuksie GUI jako beta (WebKitGTK); alternatywa Electron.
- Paczki: instalator CPU + Vulkan albo Metal; CUDA / HIP per rodzina dociągane po detekcji, podpisane.
- Aktualizacje: updater Tauri/Velopack + manifest Ed25519 ze slotami A/B i rollbackiem po teście md5 i prędkości.
- Backend: Postgres + object storage w UE. CI: GitHub-hosted build, testy GPU na self-hosted (GitHub nie ma runnerów AMD GPU).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

- Ten opis (Rust `appd`, Tauri 2, Velopack, llama-cpp-rs, Textual/TUI) to plan z raportów 03 i 06, nie to, co zbudowaliśmy. Aplikacja w `app/engine` to Bun (`Bun.serve`) + Svelte 5/Vite w przeglądarce na 127.0.0.1, jedna binarka z `bun build --compile` (`app/engine/README.md:8-9`, `app/engine/package.json`); w kodzie aplikacji nie ma Tauri, Velopack ani llama-cpp-rs.
- Zmiana stosu sama w sobie nie jest błędem (Bun skrócił drogę do działającego przebiegu skan → model → pomiar → endpoint). Błędem jest to, że razem ze stosem wypadły rzeczy, które Tauri/Velopack dawały z pudełka: **aktualizacja z kopią poprzedniej wersji i powrotem przy błędzie** (pkt „Aktualizacje” wyżej) oraz instalator kilku MB. Nic z tego nie powstało, tak samo jak nadzorca procesu silnika ([[inference-stack]], hipoteza 1).
- Porównanie: Inference Stack ma instalator z sumą kontrolną, kopię poprzedniej wersji i powrót przy błędzie; Jan i Lemonade mają małe paczki z backendem na żądanie ([[raport-01-konkurencja]]).
- Lekcja: przy zmianie stosu spisać, co stary stos dawał gratis, i każdą taką rzecz albo przenieść, albo świadomie skreślić w CONTRACT.
- Co bierzemy: updater z podpisem Ed25519 (klucze już mamy) i slotami A/B na stosie Bun; punkt 5 listy w [[inference-stack]].

## Powiązane
- [[produkt/_hub|produkt]]
- [[produkt-architektura]]
- [[produkt-prawo]]
- [[raport-03-silniki]]
- [[rocm-stos]]
