---
typ: ekosystem
tags: [ekosystem, silnik, spekulacja, megakernel]
aktualizacja: 2026-11-14
zrodlo: ~/KERNEL/product/research/66b-1cat-tokenspeed.md:53-70,186-194,222-223; https://github.com/lightseekorg/tokenspeed (b941508); https://lightseek.org/blog/tokenspeed-kimi-k3-agentx.html (2026-11-10); https://x.com/zainhas/status/2120806646356295682 (Telegram „gpu” 2026-11-14)
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

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
„Skala klastra, dla nas 0%” to prawda dla prędkości jednej karty. TokenSpeed to jednak silnik budowany pod ten sam typ ruchu co nasz, czyli tury agenta z długim, powtarzanym prefiksem. Warstwa po warstwie (66b:53-70, 186-194; blog Kimi K3 2026-11-10):
- **Cache jako warstwa systemu:** wspólna pamięć hosta 5,45 TB przez RDMA daje ~95% trafień prefiksu. U nas ta sama zasada działa w małej skali: `--cache-ram 40960` i `CACHE_SHARE_MIN=1024` w topce (nowa sesja agenta Qwen 8,0 → 1,6 s, [[inference-stack]]). Wniosek z obu stron: w ruchu agentowym o TTFT decyduje trafienie w cache, a nie szybkość prefillu.
- **Kompromis, który trzeba nazwać:** 1,92× tok/s na GPU kosztuje TTFT 13–14 s zamiast 1 s. Operator chmury wybiera przepustowość, a Enigma (jeden użytkownik) powinna wybierać TTFT. Każdą cudzą liczbę tok/s/GPU trzeba więc czytać razem z TTFT.
- **Rozdział prefill/dekod:** inne ustawienia dla prefillu (DWDP) i dla dekodu (DEP16). Na jednej karcie robimy mniejszą wersję tego samego: osobne `-ub` i chunk dla prefillu oraz MTP dla dekodu.
- **Budowa serwera:** pętla zdarzeń w Ruście hostuje harmonogram C++, bezpieczeństwo KV pilnują typy w czasie kompilacji, jeden wątek wydaje pracę GPU, a na ścieżce żądania nie ma Pythona. Porównanie z llama-server (jeden proces, IPC na krok = 0) i proxy Bun w Enigmie: [[anatomia-serwowania-kumar]].
- **Uczciwość liczb:** komentarz „580 vs 377 t/s” przy własnym wpisie CI 443 to ten sam błąd co nagłówki 1Cat. Ich CI z warunkami (`test/ci/perf/*.yaml`) to wzór: każda liczba ma plik z konfiguracją i może ją zweryfikować ktoś obcy.

## Powiązane
- [[1cat-vllm]]
- [[megakernele-prior-art]]
- [[vllm-monokernel]]
- [[raport-66-synteza]]
