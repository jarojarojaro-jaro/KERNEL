---
typ: produkt
tags: [produkt, plan, architektura]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/PLAN.md:130-193
status: aktualne
---
# Architektura systemu i silnik

**Komputer użytkownika (GUI Tauri, TUI, daemon Rust `appd`, llama-server jako proces potomny, tuner, updater Ed25519) + mały backend (katalog, baza profili, kolejka) + fabryka przepisów.**

- Silnik: cienka nakładka na tagach semver llama.cpp (v0.7.0 → kolejne, ~10 dni), rebase raz na wydanie, bot raportuje łatki, które przestały się nakładać.
- Łatki: małe rodziny z predykatami (arch, arch modelu, kwant, KV), każda z wyłącznikiem env i bramką w CI; budżet łatek – usuwana, jeśli przez N wydań nie weszła upstream i nigdzie nie daje ≥3% (`loo.py`).
- Strojone parametry w danych (tabele Kernel Tunera ładowane z profilu).
- Upstream ręcznie: sampler 0031/0048/0066–0069, host 0047, q8_1 0003/0015/0023, async wejścia 0029/0059.
- Detekcja w 3 etapach: inwentarz < 300 ms, test silnika w podprocesie, pomiar 3–10 s; zakazane WMI `AdapterRAM` i parsowanie `nvidia-smi`.
- Katalog jako podpisany manifest; domyślnie 24 GB → Qwen3.8-27B Q4_K_XL; LFM2.5 jako „najszybszy”, nie domyślny.

## Powiązane
- [[produkt/_hub|produkt]]
- [[produkt-fabryka]]
- [[produkt-stack]]
- [[latki-do-upstreamu]]
- [[raport-03-silniki]]
