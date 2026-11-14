---
typ: repo
tags: [repo, silnik, spekulacja, megakernel]
aktualizacja: 2026-11-14
zrodlo: ~/KERNEL/product/research/66b-1cat-tokenspeed.md:53-70,186-194,222-223; https://github.com/lightseekorg/tokenspeed (b941508); https://lightseek.org/blog/tokenspeed-kimi-k3-agentx.html (2026-11-10, Telegram „gpu” 2026-11-14)
status: aktualne
---
# TokenSpeed (LightSeek Foundation)

**Silnik pod obciążenie agentowe (MIT, od 2026-05) z harmonogramem C++ w pętli zdarzeń Rusta, tylko NVIDIA sm90+ i AMD gfx950/gfx1250 (gfx1201 przez przenośny Triton); gfx11, Apple i Intela nie obsługuje, więc dla nas liczą się tylko wzorce (raport 66b, 2026-11-07).**

- ReplaySSM (weryfikacja tylko czyta stan GDN, po akceptacji jedno odtworzenie): mamy jako `rs_lag` ([[gdn-replay]]).
- Zbalansowany split-KV liczony raz na krok na GPU; wiersze bloku (tokeny weryfikacji × GQA) dzielą przejazd po kluczach, czyli to samo co Pack-GQA ([[kv-raz-na-weryfikacje]]).
- **Lekcja z błędu overlapu:** przy spekulacji CPU obcinało wynik na stop-tokenie, a GPU zatwierdzało wszystkie zaakceptowane tokeny i psuło opublikowany checkpoint GDN. Poprawka: obcinanie długości na GPU. Obowiązkowe dla planu #11 z 63.
- Monokernel dekodu (jedno trwałe uruchomienie na warstwę, skrzynki 64-bitowe, „same math, not the same bits”): komentarz „580 vs 377 t/s” na MI350X, a wpis CI podaje 443 ([[lekcja-tps-z-zalozonej-akceptacji]]).
- Flash-Next na 4× GB300: 691.82 t/s na użytkownika przy C=1 (CI), NVFP4, MTP3.
- Stratne opcje (KV fp8/mxfp8, stan SSM bf16, BLASST, QSA): zaparkowane.
- **Delta 2026-11-14 (blog Kimi K3 na AgentX):** 331 tok/s na GPU na 32× GB300, czyli 1,92× bazy DCP8.
  - Mechanizmy: prefill DWDP (wagi ekspertów ściągane do tokenów, bez synchronizacji warstw), dekod DEP16 + TP4 dla projekcji, wspólna pamięć hosta 5,45 TB przez RDMA (trafienia cache ~95%).
  - Koszt: TTFT 13–14 s zamiast 1 s.
  - Werdykt: skala klastra, dla jednej karty 0%. Jedyny wzorzec dla nas: fuzja conv1d + rekurencja + norma w kernelu weryfikacji KDA, ta sama idea co K-047 w [[KOLEJKA-TESTOW]].

## Powiązane
- [[repo/_hub|repo]]
- [[1cat-vllm]]
- [[megakernele-prior-art]]
- [[vllm-monokernel]]
- [[raport-66-synteza]]
