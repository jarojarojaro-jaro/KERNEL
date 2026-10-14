# Brief: analiza repozytoriów o kernelach GPU pod nasz setup AMD

Cel: z każdego repo wyciągnąć techniki, procesy i pomysły, które mogą przyspieszyć **nasze** inferencje LLM na AMD RX 7900 XTX (HIP/ROCm), także jeśli repo jest o CUDA/NVIDIA. Myśl jak ekspert z chłodną głową: co jest wartościowe, co da się przenieść na RDNA3 w innej formie, co jest marketingiem albo błędem. Bądź ciekawy, szukaj nieoczywistych pomysłów, ale każdą tezę opieraj na kodzie/dokumentach repo (plik:linia) albo oznacz jako `[WNIOSEK]`.

## Nasz sprzęt
- GPU: **RX 7900 XTX, gfx1100 (RDNA3)**: 96 CU, wave32 (i wave64), WMMA 16x16x16 (f16/bf16/iu8, brak FP8, brak sparsity), 24 GB GDDR6 ~960 GB/s, 96 MB Infinity Cache (MALL), LDS 64 KB/CU (WGP 128 KB), DPP/ds_swizzle, brak thread-block clusters/TMA/async-copy w stylu Hopper. Limit mocy 285 W.
- ROCm 10.0 (`/opt/rocm/core-10.0`, clang 23), HIP graphs włączone. Host: Ryzen 7 5700X (8C/16T), 64 GB DDR4, PCIe 4.0. Cel to wyłącznie AMD/7900 XTX. Techniki NVIDIA (Hopper/Blackwell: TMA, clusters, tcgen05, FP4/FP8 itd.) analizuj jako technologie i pomysły do przeniesienia na RDNA3, nie pod konkretną kartę NVIDIA.
- Fork llama.cpp (`~/llama-master`, gałąź `amd-opt`, 54 łatki na upstream; lista: `~/KERNEL/qwen-opt/patches/llama.cpp-amd-opt/`). Wszystko na ggml-cuda kompilowanym jako HIP.
- **Qwen3.8-27B** (dense hybryda: 48 warstw Gated DeltaNet + 16 full attention, głowica MTP), wagi Q4_K/Q5_K/Q6_K/IQ4_XS (GGUF), KV q4_0, ctx 204800. Decode memory-bound; spekulacja MTP n=4 → weryfikacja 5 kolumn naraz. **104 t/s**, krok 28.9 ms (próg pasma ~17 ms). Prefill ~950 t/s (MMQ int8 WMMA, ~50 TFLOPS efektywnie).
- **LFM2.5-24B-A2B** (MoE 64 ekspertów / 4 aktywne, 30 warstw shortconv + 10 GQA, emb 2048), Q5_K_M, KV q8_0, bez spekulacji. **~240 t/s**, 4.1 ms/token, próg pasma ~1.9 ms. **Launch-bound**: 416 kerneli/token, każda granica kernela w grafie HIP ~2.5 µs, MMVQ ~700 GB/s.
- Co już zrobiliśmy (nie proponuj tego jako nowości, ale możesz proponować lepsze warianty): multi-column MMVQ 2–16 kolumn strojony pod RDNA3 (waves_per_eu, buffer loads GLC/DLC), WMMA dla weryfikacji 9–16 kolumn, kernel FA czytający KV q4_0 bezpośrednio, fuzje (norm+mul+q8_1, producenci piszący q8_1, residual/bias epilogi, MoE down+ważenie+residual w jednym kernelu, norm+router+top-k z „ostatnim blokiem”/ticket, conv w in_proj), stan GDN z opóźnieniem (rollback przez replay), MTP draft jednym grafem, szybkie top-k, kafle MMQ/FA dla prefillu, asynchroniczne wejścia grafu.
- Przeczytaj przed pisaniem: `~/KERNEL/qwen-opt/NOTES.md` (zwłaszcza „Wyniki negatywne” — nie proponuj ponownie bez nowego argumentu), `~/KERNEL/qwen-opt/research/lfm-decode.md` i `lfm-decode-round2.md` (koszty uruchomień, co nie wyszło), `research/strata/README.md`, `research/tensorfold/README.md`. Główne otwarte wąskie gardła: koszt uruchomień kerneli (MoE), pasmo MMVQ przy 1 i 5 kolumnach (~700 GB/s z 960), atencja decode przy długim kontekście (KV q8_0), prefill (~50 TFLOPS z ~123), małe kernele latency-bound.

## Zasady pracy (sprzęt chroniony)
- **Nie używaj GPU** (żadnych benchmarków, buildów HIP/CUDA, testów). **Nie kompiluj niczego** i nie instaluj pakietów. Tylko czytanie.
- Klonuj płytko: `git clone --depth 1 --single-branch <url> /tmp/repos/<nazwa>`; dla ogromnych repo (> ~500 MB) użyj `--filter=blob:none --sparse` + `git sparse-checkout set <katalogi>` albo czytaj przez GitHub (raw/API). Po skończeniu usuń swój klon z `/tmp/repos`.
- Działaj na `nice -n 10`. Nie dotykaj innych plików niż Twój raport.
- Jeśli repo ma artykuł/blog, możesz je przeczytać (web), cytuj linki.

## Raport
Zapisz do `~/KERNEL/qwen-opt/research/repos/<NN>-<nazwa>.md` (po polsku, zwięźle, bez lania wody):
1. **Co to jest** (2–4 zdania, stan repo: aktywność, licencja, na jakim sprzęcie).
2. **Kluczowe techniki** — lista z dowodami (plik:linia, liczby z repo z zaznaczeniem, czyje to pomiary).
3. **Przeniesienie na AMD/HIP/RDNA3** — dla każdej techniki: czy da się, jak (konkretny odpowiednik: WMMA zamiast mma.sync, DPP zamiast shfl, buffer loads zamiast TMA itd.), co się nie przeniesie i dlaczego.
4. **Pomysły dla nas** — konkretne eksperymenty na nasze modele (Qwen3.8 i/lub LFM2.5), każdy z: co zmienić (który kernel/plik w ggml-cuda), oczekiwany zysk z uzasadnieniem `[SZACUNEK]`, koszt pracy, ryzyko, jak zmierzyć. Także pomysły „outside the box”.
5. **Krytyka** — co jest przesadzone, błędne, nieaktualne, nieistotne dla nas.
6. **Werdykt**: jedno z {wysoka wartość / średnia / niska / brak} + 1 zdanie dlaczego.
Na końcu ostatniej odpowiedzi (do rodzica) podaj 3–5 linijek streszczenia i ścieżkę raportu.
