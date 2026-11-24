---
typ: ekosystem
tags: [ekosystem, konkurencja, cache, agent]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/product/research/63b-colibri-maya-delta.md:27-32,85-162; https://github.com/JustVugg/colibri (v2.1.0 `704a3f68`, kod `0a5504a1`, 2026-10-31)
status: aktualne
---
# colibri (JustVugg): silnik w czystym C dla dużych MoE

**CPU/Vulkan/CUDA/Metal, eksperci w VRAM → RAM → NVMe, od v2.1.0 natywny GGUF; Qwen3.8-27B obsługiwany, bez liczb na GPU (2026-10-31).**

- „256k w szybkości 64k” to poprawka planera RAM (bufor wyceniany na segment, nie na cały ctx) i KV f32 → f16, a nie technika atencji. Lekcja dla planera Enigmy: bufor obliczeń na ubatch.
- „Tura agenta 86 → 4.9 s”: snapshot o 1 token za daleko (`<think>`) i „park” stanu przy krótkim zapytaniu bocznym. llama-server ma odpowiedniki; brakuje nam pojemności cache ([[lekcja-cache-ram-za-maly]]).
- Wart skopiowania `COLI_PREFIX_LOG`: przy chybieniu cache log mówi, w którym tokenie i na jakim tekście prompt rozjechał się ze stanem → nasz `LLAMA_SERVER_PREFIX_LOG`.
- MTP Qwen3.6 do 120 t/s (1 draft najlepszy, bramka wartości E(k)/cost(k)) – dla topki nic nowego.
- Praca autora: ABBA i kontrola bitowa przy każdym commicie, współpraca z Claude.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
v2.2.0 (2026-11-22, `e479104`, https://github.com/JustVugg/colibri/releases/tag/v2.2.0). Dla silnika na XTX nadal nic (AMD tylko Vulkan, Inkling-2-Mini UD-Q4_K_XL 39,2 t/s Vulkan na RTX PRO 4000 vs Maya 113 na XTX), ale to jest produkt tego samego typu co Enigma i ma rzeczy, których nam brakuje:
- **`coli setup` mierzy maszynę** (pasmo RAM w 2 s, pamięć i pasmo każdej karty, typ dysku) i dla każdego modelu szacuje dekod; poleca najmocniejszy model z dekodem ≥ 20 t/s i pokazuje, gdzie model będzie liczony (karta / pół na pół / RAM / dysk). Wcześniej polecali ten sam model od 12 do 512 GB, czyli ten sam błąd co nasze APU pomylone z kartą ([[lekcja-enigma-apu-jako-karta]]).
- Enigma liczy pasmo RAM teoretycznie z SMBIOS (`app/engine/src/server/hw/ram.ts:60`, MT/s × 8 B × kanały) i ma domyślne 2 kanały, gdy SMBIOS milczy (`ram.ts:89`). Bierzemy: 2-sekundowy pomiar pasma RAM zamiast szacunku z firmware.
- **Prefix store** po treści promptu z logitami równymi zimnemu odczytowi, w każdym silniku; poprawka „krótsza rozmowa nigdy nie używała prefiksu przy `--kv-slots 1`” (#2703) to ten sam rodzaj błędu co nasze wyrzucanie cache agenta (E4, `LLAMA_SERVER_CACHE_SHARE_MIN`).
- Windows: odczyty GGUF szły po kolei; TTFT 4,5k tokenów 5,4 → 2,0 s, start 21 → 12,7 s (#2967). Dla Enigmy na Windows: mierzyć czas ładowania i pierwszego tokenu, nie tylko t/s.
- Okno desktop, które samo startuje i zatrzymuje serwer, i czat w terminalu — wzór „po gotowe” jak w [[inference-stack]].
- Ich dekod Inklinga w 1 ramce gęstych łańcuchów (CUDA 40,9 t/s) jest ~2,8× wolniejszy od Mayi na podobnym paśmie — silnik ogólny przegrywa z dedykowanym.

## Przegląd 2026-11-24: wiersz v2.1.0 (co z lekcji R63b faktycznie wdrożyliśmy)
Wiersz rejestru („256k w szybkości 64k = planer + KV f16; `COLI_PREFIX_LOG` do skopiowania”) zapisał trzy akcje z `product/research/63b-colibri-maya-delta.md:§1.1–1.2`. Stan 24.11 w naszym kodzie:
- **Planer Enigmy liczy bufor obliczeń na ubatch, nie na cały kontekst:** wdrożone (`app/engine/src/server/catalog/memory.ts:11,30`).
- **Enigma Chat odsyła `reasoning_content`, żeby kolejna tura szła ze stanu żywego (3 linie, 0,3–1 s na turę [INFERENCE]):** niewdrożone. Historia wysyłana jest jako sama `{role, content}` (`app/engine/src/ui/components/Chat.svelte:40`).
- **`LLAMA_SERVER_PREFIX_LOG` na wzór `COLI_PREFIX_LOG`** (przy chybieniu cache: LCP i 16 tokenów tekstu po obu stronach miejsca rozjazdu; 0,5 dnia): w forku `~/praca/llama-duo` (`83d0326`) nie ma tej zmiennej, a K-020 już planuje test „z `LLAMA_SERVER_PREFIX_LOG`” ([[KOLEJKA-TESTOW]]). Kod topki na serwerze jaroserverai nie był sprawdzany.
- **„Park” krótkiego bocznego zapytania** (zachować tylko wiersze, które ono nadpisze): u nas ten sam problem rozwiązuje kopia całego slotu do `--cache-ram` (E4, `LLAMA_SERVER_CACHE_SHARE_MIN`), drożej, ale działa.
- **Lekcja procesu:** dobre akcje z raportów giną, gdy wiersz rejestru nie ma właściciela ani daty sprawdzenia. Dwie z trzech tanich akcji (razem < 1 dzień) leżą od 2026-11-05.

## Powiązane
- [[project-maya]]
- [[wspolny-poczatek-promptu]]
- [[raport-63-synteza]]
