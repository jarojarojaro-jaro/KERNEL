---
typ: ekosystem
tags: [ekosystem, kv, serwowanie, cache]
aktualizacja: 2026-11-24
zrodlo: https://vllm.ai/blog/2026-11-23-skip-the-dram-tier; zwiad 2026-11-24 (podagent ZwInfra)
status: aktualne
---
# MoRI UMBP (AMD): pula KV na NVMe zamiast DRAM i czego uczy o naszym cache sesji

**Na 16× MI355X pula KV 1,8 TB na NVMe dorównała puli DRAM tej samej wielkości (±1%, Kimi-K3, 48–96 sesji agentów), bo przepustowość zależy od odsetka trafień, a nie od nośnika, a ładowanie asynchroniczne chowa się w kolejce prefillu. Bez kolejki NVMe dodaje ~0,4 s na prefiks 128K.**
- Dla serwera topki (1 strumień) zysk nie występuje, bo brak kolejki, w której odczyt mógłby się schować; decyzja [[decyzje/2026-10-19-kv-tylko-w-ram]] zostaje.
- „Touch”: gdy prefiks trafia w szybszej warstwie, niższa warstwa musi o tym wiedzieć, inaczej LRU wyrzuca najgorętsze wpisy (+2,1–3,9%, p99 TTFT o połowę). U nas brakuje tego w ścieżce kopii wspólnego prefiksu (`server-task.cpp:1867-1898`); to samo naprawił Flare v0.3.0 (`425ab2d`).
- Hybrydy: checkpoint stanu co 7168 tokenów dał +33% (trafienia 91,4 → 95,6%), co jest niezależnym potwierdzeniem [[siatka-checkpointow-gdn]] (K-005).
- Koszt NVMe rośnie z zapisami, nie z pojemnością: 1 zapis dysku/dzień × 5 lat = ~$0,36/TB zapisany.

## Powiązane
- [[inference-stack]]
- [[siatka-checkpointow-gdn]]
