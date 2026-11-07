---
typ: repo
tags: [repo, silnik, spekulacja, megakernel]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66b-1cat-tokenspeed.md:53-70,186-194,222-223; https://github.com/lightseekorg/tokenspeed (b941508)
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

## Powiązane
- [[repo/_hub|repo]]
- [[1cat-vllm]]
- [[megakernele-prior-art]]
- [[vllm-monokernel]]
- [[raport-66-synteza]]
