---
typ: research
tags: [research, telegram, silniki, cuda-graph, weryfikacja-formalna, agentx]
aktualizacja: 2026-11-24
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

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- **Baseten: własny silnik, który się udał, wobec naszego Enigma Turbo, który się nie udał.** Ich warunki: jeden model, gotowy silnik referencyjny (SGLang) jako miara i cel portu, kernele pisane przez agentów czytających źródła FlashInfer i SGLang, README z dokładnym promptem, 30 przebiegami i polami logu `average_iteration_ms`, `average_accept_length` (https://explainx.ai/blog/baseten-deepseek-ultrafast-2060-tps-rust-inference-engine-2026, https://github.com/basetenlabs/deepseek-ultrafast). Enigma Turbo nie miał żadnej z tych bramek: testy na syntetycznym modelu, kod GPU niewołany, 0,7 t/s i bełkot ([[enigma-turbo-gemini-2026-11-20]]). Wniosek: własny silnik ma sens tylko z referencją od pierwszego dnia (md5/KLD względem llama.cpp na prawdziwym GGUF) i z portem z powrotem do silnika, który utrzymujemy.
- **InferenceForge: źródło pierwotne znalezione** (https://agenteconomics.org/posts/inference-forge, 2026-11-09). Zwykły agent kodujący w pętli: mierzy trafienia cache i czasy kerneli, pisze mikrobenchmarki, poprawia największe wąskie gardło, waliduje. 9 iteracji w 3 dni, każda poprawka jako PR do forka SGLang, każdy punkt to godzinny przebieg AgentX (powtórka sesji Claude Code) przy SLA 30 tok/s na użytkownika: Kimi K3 8,9k → 12,8k tok/s/GPU (+43%). Trzy poprawki wynikały z ruchu agentów (kilka bardzo długich kontekstów obok wielu krótkich): split-KV wybierany tylko od rozmiaru wsadu, skan równoległy stanu liniowej atencji (1199 → 426 µs), pakowanie prefiksu do FP8 jednym kernelem, bitowo (889 → 180 µs).
  - U nas: pętla fabryki i xtxbench mierzą jeden strumień przy 1,7k i 199k ([[xtxbench-szybki-ab]]), a nasz prawdziwy ruch to 4,9 : 1 prefill do dekodu i 37% czasu z ≥ 2 żądaniami ([[2026-10-19-workload-omp]]). Bierzemy metodę: cel pętli = powtórka naszego ruchu omp (mamy 458 sesji) przy progu interaktywności, nie dekod 1,7k. Ich poprawki są pod B300 i serwowanie wsadowe, do portu nic.
- **vstack: bramki przeciw oszukiwaniu to lekcja dla naszego procesu agentów, nie tylko „opcja przy K-001”.** README (https://github.com/hao-ai-lab/vstack) wymienia: rozdzielone role (koordynator, wykonawca, red team), specyfikacja przypięta hashem SHA-256, żeby wykonawca nie osłabił celu, każdy element modelu przypięty do `plik:linia@commit`, model musi upaść na historycznym błędzie, przejść z poprawką i upaść po usunięciu strażnika, znalezisko musi się powtórzyć na prawdziwym silniku. Liczba błędów urosła z 17 do 40+ (wpis 2026-11-17). VeriServe: 226 modułów dowodów, +0,18% p50 TPOT.
  - U nas: K-001 znaleźliśmy bez metod formalnych (hashe węzłów grafu, przyczyna: kernele FA czytają stare zamaskowane komórki, `KOLEJKA-TESTOW.md` wynik 2026-11-20), więc tamta opcja odpada. Zostaje wzór bramek: Enigma Turbo przeszedł własne „ALL PASS”, bo nikt nie przypiął celu ani nie sprawdził, czy test łapie znany błąd. Do naszych bramek (duo Kernel + Gemini, recenzent) dopisać: cel i warunek zaliczenia zapisane przed pracą i niezmienne, test musi złapać celowo wstawiony znany błąd (jak kanarki w [[bramka-kld-kanarki]]), dowód na prawdziwym modelu. Zob. [[reward-hacking-inferencji]].

## Powiązane
- [[research/_hub|research]]
- [[KOLEJKA-TESTOW]]
- [[megakernele-prior-art]]
- [[deepinfer]]
- [[2026-11-09-qwen-warp-vs-fork-3090]]
