---
typ: ekosystem
tags: [ekosystem, megakernel, nvidia, konkurencja]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66c-hyperkernel-megakernele.md:11-87; https://github.com/Hyperstitioncc/Hyperkernel (7048c586); https://x.com/hyperstition_cc/status/2118432349352595528
status: aktualne
---
# Hyperkernel (Hyperstition): rezydentny megakernel na B300

**Repo zawiera tylko gotowe pakiety SASS/cubin dla B300 (`sm_103a`) i host w Ruście, bez generatora i źródeł kerneli; ścieżki AMD nie ma (0 trafień `hip|rocm|amd|gfx`), więc na gfx1100 nie ma czego portować (raport 66c, 2026-11-07).**

- Konstrukcja (z symboli SASS): jeden kooperacyjny `mega_main`, 148 CTA × 384 wątki, klaster 16, 227 KB SMEM, uruchomiony raz na całe życie serwera. Statyczny harmonogram per SM, 140 etapów `spine_body*`, zależności przez monotoniczne liczniki (atomik bez odpowiedzi + poll wątku 0). Próbkowanie i akceptacja draftu (blok 6) na GPU; host daje „grant” na 2 kroki naprzód.
- Nagłówek +36.7% (1129.6 vs 826.5 tok/s/user, 4×B300, DeepSeek-V4.1-Flash): bazą jest liczba vLLM opublikowana przez NVIDIA, nie powtórzona. AgentX wymusza akceptację w bazach, a Hyperkernel liczy na prawdziwej, której nie podaje. Słupek C4 +90.6% porównuje ze słabszą bazą. Jakość: 7 pytań z odpowiedziami, bez KL.
- Generator zapowiedziany „w kilka tygodni”; AMD tylko jako zdanie w wątku.
- Wzorce warte zapamiętania: ≤ 1 atomik na WG na etap, liczniki co 128 B, prefetch wag przed czekaniem, grant z horyzontem dla pętli MTP, znaczniki czasu per etap.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
„Tylko binaria B300, AMD brak” zamykało temat jako „nie ma czego portować”. Repo i nasz pomiar przy okazji uczą jednak trzech rzeczy (66c:55-60, 104-126, 146):
- **Serwer, w którym host nigdy nie czeka:** pierścienie zleceń i odpowiedzi w przypiętej pamięci hosta, grant „wolno do kroku t+2”, a próbkowanie, akceptacja draftu i zapis logprobów dzieją się na GPU (`gpu/ring.rs:1-69`, `engine/clock.rs:3,20-29`). U nas GPU stoi 410 µs/krok między taśmami (R37), a llama-server czeka na wynik każdego kroku. To ten sam kierunek co plan #11 (overlap), z liczbą: +1…+1,5% (66c pomysł C).
- **Nasz własny wynik, który przy okazji wyszedł:** fuzje z raportu 54 zabrały 126 dispatchy na krok (13%), a proza zmieniła się o +0,24% (szum), `mvs` o 0,0% (ABBA x54, `qwen-opt/launchcut/logs/prose.jsonl`). Mniej uruchomień to jeszcze nie szybciej: płaci się za ogony i rampy w łańcuchach MMVQ → norma → MMVQ.
- **Ryzyko w produkcie:** kernel rezydentny „na zawsze” nie przejdzie na Windows (TDR), a port NVIDIA mega zawiesił produkcję 2× w 12,5 h i wrócił na zwykłą ścieżkę (66c:126,135). Dla Enigmy (Windows, karty klientów) stabilność jest ważniejsza niż +5% dekodu.
- **Czytanie twierdzeń:** baza to liczba opublikowana przez NVIDIA, a nie powtórzona; jakość sprawdza 7 pytań; „60–100 linii na megakernel” i „generator w 20 dni” są nie do sprawdzenia. To ten sam wzór co README Enigmy Turbo („ALL PASS”, „Dual CUDA/HIP”) ([[enigma-turbo-gemini-2026-11-20]]). Bez kodu i bez naszego pomiaru to tylko deklaracja.
- Do zrobienia zostaje tani PoC-A (1–1,5 dnia, hand-off w trwałej siatce 96–192 WG). Pełny megakernel Qwena to 40–70 osobodni `[SZACUNEK]`, więc dopiero po planach #1–#8 z 63.

## Powiązane
- [[megakernele-prior-art]]
- [[budzet-megakernela-qwen-xtx]]
- [[lekcja-tps-z-zalozonej-akceptacji]]
- [[firma-nvidia]]
- [[raport-66-synteza]]
