---
typ: research
tags: [research, telegram, silniki, cuda-graph, weryfikacja-formalna, agentx]
aktualizacja: 2026-11-14
zrodlo: https://x.com/waterloo_intern/status/2121391498159599785; https://x.com/saltyph/status/2121301307437027415; https://explainx.ai/blog/baseten-deepseek-ultrafast-2060-tps-rust-inference-engine-2026; https://x.com/kaiwei_chang/status/2121309776554688652; https://x.com/haoailab/status/2121320482876399825; https://github.com/hao-ai-lab/vstack (README, 2026-11-14)
status: aktualne
---
# Telegram 2026-11-14: własny silnik pod DeepSeek V4.1 Flash, InferenceForge, vstack

**Z czterech linków nic nie daje nowego zysku na naszej karcie. Silnik w Rust + CUDA pod jeden model (Baseten „deepseek-ultrafast”, ~1740 TPS na 4× B300, +15% vs SGLang) potwierdza kierunek, który już mamy w kolejce: cały krok spekulacji w jednym grafie (K-014). InferenceForge (+43% przepustowości na AgentX) i vstack (weryfikacja formalna serwerów) dotyczą serwowania wielu żądań w centrach danych.**

- **Silnik pod jeden model (wiadomości 1–2).** Ich teza to szybka iteracja we własnej piaskownicy, potem port do SGLang z tym samym wynikiem. Topka to już silnik specjalizowany pod Qwen3.8-27B. Konkretne techniki:
  - cały krok spec-dec (weryfikacja 7 tokenów) w jednym grafie CUDA, czyli nasze K-014;
  - fuzja routingu MoE i kernel na 4 strumienie rezydualne: dotyczy tylko DeepSeek, Qwen 27B jest gęsty;
  - sprzęt B300, poza naszym zasięgiem.
- **InferenceForge (wiadomość 3).** Agent profiluje i stroi serwer pod obciążenie agentowe AgentX; mierzy przepustowość przy SLA i wielu sesjach. Źródła pierwotnego (pracy, repo) nie znalazłem 2026-11-14, jest tylko wpis z wykresem. U nas pętla „agent stroi silnik” to już fabryka i xtxbench ([[petla-rsi-f]], [[xtxbench-szybki-ab]]). Kontekst AgentX: [[agentx-harness]].
- **vstack (wiadomość 4).** Umiejętności dla agentów kodujących: TLA+/Apalache/Z3 z bramkami przeciw oszukiwaniu. Znalazły 17 błędów w vLLM i SGLang (cykl życia stron KV, współbieżność). Dla nas jedynie opcja przy K-001 (wyciek stanu przy drugim restore slotu), gdyby powtarzalny test nie znalazł przyczyny. Nie przyspiesza.

## Powiązane
- [[research/_hub|research]]
- [[KOLEJKA-TESTOW]]
- [[megakernele-prior-art]]
- [[deepinfer]]
- [[2026-11-09-qwen-warp-vs-fork-3090]]
