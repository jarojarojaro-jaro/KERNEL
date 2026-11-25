---
typ: llm
tags: [llm, trening, peft, soft-prompt, destylacja, rl]
aktualizacja: 2026-11-25
zrodlo: arXiv 2611.27376 (UCSB-AI, 2026-11-24); github.com/UCSB-AI/CSPD README (licencja CC BY-NC 4.0); panel JARO 2026-11-25 (x.com/zhenzhangzz/status/2125028517733974400)
status: aktualne
---
# CSPD: destylacja eksperta RL do soft promptu 256 tokenów

**Zamiast łączyć wagi po treningu RL, każdego eksperta (matematyka, kod, nauka, wykonywanie poleceń) destyluje się do soft promptu: 256 wektorów wejściowych (ok. 0,01% parametrów), trenowanych na zamrożonym modelu sprzed RL na odpowiedziach nauczyciela. Jeden prompt odzyskuje co najmniej 90% zysku z RL w 22 z 23 ustawień (7B–35B, dense i MoE). Cztery osobno wytrenowane prompty po prostu się skleja: 67,83 vs 67,79 dla destylacji wielu nauczycieli (MOPD), a na 6 testach spoza domeny 56,6 (MOPD traci 3,6 pkt na TruthfulQA).**

## Mechanizm
- Nauczyciel (checkpoint po RL) generuje odpowiedzi offline. Uczone są tylko wektory promptu, z lossem języka na samej odpowiedzi, wstawione zaraz po nagłówku systemowym.
- Serwowanie: inny prompt na każde żądanie, przepustowość w granicach 1,5% od gołego modelu, 2,40× więcej niż LoRA rank 4 (B200). Powód: wagi się nie zmieniają, więc batch wielu użytkowników idzie jednym kernelem, a koszt to 256 tokenów KV (raz, w cache prefiksu).
- Licencja kodu CC BY-NC 4.0: do badań tak, do produktu nie.

## Co to znaczy dla nas
- **Prędkość bez kosztu adaptera:** Nib + LoRA uncensored (K-165) i Maya z ablacją zmieniają wagi albo liczą adapter w każdym kroku. Soft prompt zostawia wagi i drafter bez zmian. To ten sam plik wag, więc nie łamie zasady „ten sam model”, a różni się tylko 256 tokenami prefiksu.
- **Otwarte pytania:** (1) czy zachowanie „bez odmów” da się zdestylować do soft promptu tak jak umiejętność z RL (praca bada tylko zyski z RL, nie usuwanie odmów); (2) llama.cpp nie ma wejścia „soft prompt” w serwerze. Potrzebna łatka: osadzenia w miejscu tokenów specjalnych, podobnie jak mmproj wstawia obraz.
- **Eksperyment (llm, nie silnik):** Qwen3.5-9B albo Inkling 2 Mini, nauczyciel = wersja AtomicChat/ablacja, uczeń = baza + soft prompt, ocena: odmowy 5/5 → ?, KLD do nauczyciela. Trening wymaga GPU (Colab A100 ok. 6,7 jedn./h, ok. 2–4 h według skali pracy, przypuszczam), więc tylko za zgodą JARO.

## Powiązane
- [[trening-llm-mapa]]
- [[peft-lora-warianty]]
- [[qwen38-27b-pi-adapter]]
