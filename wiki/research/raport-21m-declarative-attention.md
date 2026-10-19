---
typ: research
tags: [research, atencja, dlugi-kontekst]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21m-declarative-attention.md:1-61; https://arxiv.org/abs/2609.02737
status: aktualne
---
# Raport 21m: Declarative Attention (KAIST + Google DeepMind) – nie dla nas

**Model sam deklaruje w CoT (`<global>`/`<focus>`/`<local>`), które ~2K-tokenowe fragmenty kontekstu atencja ma czytać, a silnik przepisuje block table (tylko warstwy globalne); na Qwen-3.6-27B daje −19.6 ± 7.4% obsłużonych tokenów KV przy −2.10 pp jakości i +32% tokenów wyjścia, więc u nas decode zwalnia o 25–30% (raport 21m, triage bez eksperymentu, 2026-10-19).**

| | 29.5k | 94k |
|---|---|---|
| krok MTP n=4 Qwen3.8-27B na XTX (przy 1.7k: 30.0 ms) | 31.4 ms | 35.0 ms |
| część kroku zależna od kontekstu | 1.4 ms (4.5%) | 5.0 ms (14.3%) |
| idealny DA: decode / sesja agenta | −4.5% / −1.4% | −14% / −4.6% |
| DA wg pracy (1.32× kroków, 0.8× odczytów) | +30% czasu decode | +25% |

Prefill nic nie zyskuje (+4.6% tokenów promptu), metoda jest stratna (md5 i bramka KLD nie mają sensu), działa tylko z wyłączonym myśleniem, a zawężanie atencji głowicy MTP już przegrało (S3 `--spec-mtp-window 8192`: akceptacja 3.31 → 2.78, 105 → 90 t/s). Zysk w pracy pochodzi z modelu B200 przy dużym batchu, gdzie globalny odczyt KV to 86% kroku ([[lekcja-odczyty-kv-batch1]]).

## Powiązane
- [[research/_hub|research]]
- [[raport-15d-prefill-dlugi-kontekst]]
- [[2026-10-19-kv-tylko-w-ram]]
