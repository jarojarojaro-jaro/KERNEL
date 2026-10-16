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

## Powiązane
- [[produkt/_hub|produkt]]
- [[produkt-architektura]]
- [[produkt-prawo]]
- [[raport-03-silniki]]
- [[rocm-stos]]
