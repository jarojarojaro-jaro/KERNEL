---
typ: research
tags: [research, nvidia, 3090, qwen-warp, mmvq, spekulacja, pasmo]
aktualizacja: 2026-11-26
zrodlo: github.com/tuan3w/qwen-warp (engine/src/gemv.cu, head_q.cu, engine.cu, mtp_sample.cu, kvrot.cuh przy v0.12.0; PERFORMANCE/CHANGELOG/ARCHITECTURE przy main 0.13.0); nagłówki safetensors ukisai/Swift-1.5-Qwen3.8-27b-INT4 i GGUF z ~/models (2026-11-26); qwen-opt/cloud/results/nv3090-20261020/box3-56913501/prof/*.csv (nsys forka); reaped/qwenbench-nvq2-3090-11260059-62599501; testy/2026-11-19-k118-nvidia-pelna-moc.md
status: aktualne
---
# Dlaczego qwen-warp jest szybszy od naszego forka na 3090 i jak go przebić bez straty jakości

**Odpowiedź w dwóch częściach. (1) Na czacie ok. ¾ przewagi (×1,24 z ×1,31) to po prostu mniej bajtów na token: warp czyta ok. 13,3 GB (ciało W4 g128 12,59 GB + lm_head int4 ok. 0,66 GB), my 16,5 GB (ciało UD-Q4_K_XL 15,44 + lm_head Q6_K 1,04). To lżejszy kwant, a jakość ich wag względem BF16 nie jest nigdzie zmierzona, więc tej części nie kopiujemy. (2) Reszta, a zwłaszcza kopia 64k (×1,78), to silnik: ich kernel wag czyta pamięć z 92–96% pasma i weryfikuje do 16 tokenów jednym przejściem po wagach (16 wierszy kosztuje ×1,52 jednego), a nasz fork osiąga 57% pasma i 5 wierszy kosztuje już ×1,59 jednego. To jest bezstratna dźwignia i tu mamy do odrobienia najwięcej.**

## Bajty na token (policzone z nagłówków 2026-11-26)

| | ciało (MLP + atencja/GDN) | lm_head czytany w dekodzie | razem | czat (3090, 2026-11-26) | kopia 64k |
|---|---|---|---|---|---|
| warp, Swift-1.5 INT4 (W4A16 g128) | 12,59 GB | ok. 0,66 GB (int4/int8 + dokładny bf16 rescore top-16/64) | ok. 13,25 GB | 117,9 t/s | 137,1 t/s |
| nasz fork, UD-Q4_K_XL | 15,44 GB | 1,04 GB (Q6_K) | 16,48 GB | 90,2 t/s | 77,0 t/s |
| (nasza produkcja Q4_K_M) | 14,78 GB | 1,04 GB | 15,82 GB | – | – |

Plik warpa ma 19,45 GB, ale osadzenia bf16 (2,54 GB, czytany 1 wiersz na token), wizja (0,92 GB) i pełny bf16 lm_head (używany tylko do rescore kandydatów) nie przechodzą przez pasmo w każdym kroku ([[lekcja-rozmiar-pliku-to-nie-bajty-na-token]]). Kontekst: oba silniki mieszczą pełne 262 144 tokeny na 24 GB (warp: KV int4 z rotacją WHT + dokładny pierścień fp16 496 wierszy i 4 sinki, dKL 0,069% wobec bf16 przy 32k; my: KV q4_0).

## Silnik: składnik po składniku

| składnik | warp | nasz fork (3090) | luka |
|---|---|---|---|
| GEMV wag przy weryfikacji | rdzenie tensorowe `mma.m16n8k16`, wagi jako A (16 wierszy na kafel), tokeny jako B (do 8, dwa kafle = 16); trwały strumień (kafel, grupa) z prefetchem; **820–855 GB/s = 92–96% pasma** (`gemv.cu` `k_w4`) | MMVQ na rdzeniach CUDA: Q6_K n=5 555–772 GB/s (148–154 rejestry, 12 warpów/SM), cały krok weryfikacji ok. 57% pasma (nsys 2026-10-20) | **największa**: przy tych samych bajtach ok. 35–40% czasu kroku |
| koszt szerokości weryfikacji | 1 wiersz 17,3 ms, 8 wierszy 23,7 (×1,37), 16 wierszy 26,3 (×1,52) | V(5)/V(1) = 1,59 (K-118) | warp weryfikuje 3× więcej tokenów za podobną cenę → kopia 64k ×1,78 |
| ogon lookup przy kopii | do 8 (szeroko 16) wierszy, 6,6 tok/cykl na przepisywaniu | jest (`LLAMA_SPEC_LOOKUP=3`, W16 w teście), ale każdy wiersz drogi | ta sama idea, inny koszt wiersza |
| lm_head | int8/int4 GEMV + top-R + dokładny bf16 rescore R=16 (greedy) / 64 (próbkowanie) | Q6_K pełny GEMV 92% pasma | mała (ok. 0,4–0,5 GB) i nie w pełni bezstratna dla T>0 (obcięcie do top-64) |
| cykl spekulacji | jeden graf CUDA na (T, tryb głowicy, próbkowanie), bezczynność startu 0,04 ms/cykl | ok. 3,0 ms/krok czasu API kopii + 0,8 ms startów grafów (nsys), do potwierdzenia (K-014) | 1–3 ms/krok |
| próbkowanie T=1 | dokładne odrzucanie min(1, p/q) na GPU, Philox | na hoście; −7% (krótki) do −12% (262k) przy T=1 | 3–5 ms-ekwiwalent |
| GDN | stan fp32, pierścień 9 (17) slotów na wycofanie | ok. 1,2 ms/krok | mała |

## Jak to zrobić lepiej (bezstratnie, ten sam plik wag)
1. **Kernel weryfikacji na rdzeniach tensorowych dla K-quantów (Q4_K/Q5_K/Q6_K) przy 2–16 wierszach**, wzór `k_w4`: wagi czytane raz na kafel 16 wierszy, dekwantyzacja do bf16/fp16 w rejestrach, `mma` z tokenami jako drugą macierzą, trwały strumień zadań. Cel: ≥ 85% pasma i V(8)/V(1) ≤ 1,4. Szacunek: krok weryfikacji 43,5 → ok. 28 ms przy tych samych bajtach (przypuszczam). To K-182; najpierw pomiar GB/s naszych kerneli przy n=1…16 per typ na 3090 (10 min w następnej fali Vast).
2. **Szerszy ogon lookup tylko wtedy, gdy wiersz jest tani** (po punkcie 1): kopia/edycja to miejsce, gdzie warp wygrywa ×1,78.
3. **Cały cykl w jednym grafie + dokładne próbkowanie T=1 na GPU** (K-014, K-004): 1–3 ms/krok plus odzyskanie 7–12% przy T=1.
4. **lm_head: kwantyzowany wybór + dokładny rescore** tylko dla T=0 (greedy, sprawdzić odsetek pominiętego argmaxu); przy T>0 obcięcie do top-64 zmienia rozkład, więc nie.
5. Na XTX ta sama lekcja: K-131/K-009 pokazały, że nasze MMVQ/MMQ nie dochodzą do pasma; wzór warpa (kafel 16 wierszy, trwały strumień, prefetch) jest kandydatem także dla RDNA3 (WMMA zamiast mma).

## Na później
- **Lżejszy kwant W4 warpa (13,25 vs 16,48 GB/token):** gdy JARO dopuści inny plik wag z bramką jakości, to największa pojedyncza dźwignia dekodu (~20% mniej bajtów).
- **DFlash2 W4A16 w warp (K-071, nvq3):** +7,5% czat i +22,8% kopia 64k na 3090 — kandydat dla Enigmy na NVIDII, gdy będziemy obsługiwać warp albo jego format draftera.
- **Kernel GEMV 92–96% pasma:** na naszych kształtach K-182b dał tylko ×1,05; wrócić przy kartach o innym stosunku pasma do mocy (RDNA4, Blackwell).

## Powiązane
- [[qwen-warp]]
- [[2026-11-26-nvq2-3090-k071-k066]]
- [[2026-11-19-k118-nvidia-pelna-moc]]
- [[final-recipes-nvidia]]
