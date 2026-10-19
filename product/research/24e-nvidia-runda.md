# 24e — runda NVIDIA: topka na CUDA (RTX 3090), L2 prefetch MMVQ, TensorFold 1.1.0

Data: 2026-10-19. Vast, 1 sesja, RTX 3090 24 GB (instancja 56743386, Norwegia, Threadripper PRO 5975WX, 15 wątków, driver 595.91).
Koszt: ok. $0.92 (kredyt $2.11 → $1.16, w tym kilka centów buildfarmu P40 Maina). Po sesji zostało ≥ $0.40.
Dane: `~/qwen-opt/cloud/results/nv24e-3090-20261019/` (`x/xbench.jsonl`, `servers.jsonl`, `logs/`, `hw/`). Skrypty: `~/qwen-opt/cloud/runs/nv24e/`.

## Werdykt

1. **Topka na CUDA działa i daje duży zysk na edycji kodu i kopii.** Lookup W16 + cache share (`cuda-topka` 2e13c77c2) wobec `cuda-3090-opt` (3da7a02ec): code-edit mvs **×2.55** (320.6 vs 125.8 t/s), kopia 64k **×3.0** (245 vs 81.5 t/s). Czat bez zmian (−0.5% t/s, w szumie).
2. **Z lookupem wyłączonym topka = 3090-opt bitowo.** Greedy md5 identyczne na 6/6 promptach sweepa oraz na wszystkich kopiach i edycjach; tempo identyczne (±0.3%).
3. **Uwaga, różnica względem AMD:** przy `LLAMA_SPEC_LOOKUP=3` greedy md5 zmienia się na 1/6 promptów (en-code), za każdym razem tak samo (on.1, on.2, pf.1, pf.2). Na XTX raport 16b miał 11/11 bez zmian. [INFERENCE] Na CUDA weryfikacja partii 5 i 17 tokenów idzie innymi kernelami (MMVQ vs MMQ), więc wynik nie jest bitowo niezależny od szerokości partii. Kopie i edycje (md5) się zgadzają.
4. **`GGML_CUDA_MMVQ_L2PF=1` (prefetch L2, 2–8 kolumn): przegrana, kill.** Wolniej o 0.4–0.8% ms/step we wszystkich trzech pomiarach, tekst bez zmian.
5. **Evict-first: nie ma go w buildzie** (żaden commit w `~/wt/cuda-topka` go nie dodaje), nie mierzone. **PDL (`GGML_CUDA_PDL`)** działa dopiero od sm_90, na 3090 (sm_86) jest no-op, nie mierzone.
6. **TensorFold 1.1.0 instaluje się headless** (tarball + `pull`, ok. 6 min), ale na 3090 przegrywa: czat 73.9 vs 77.3 t/s, kopia 107 vs 245 t/s, prefill 64k trwa **317 s vs 69 s**. Na edycji kodu jest blisko nas (309 vs 317 t/s). Tekst wyjściowy identyczny z naszym (md5 kopii i edycji).

## Liczby (Qwen3.8-27B UD-Q4_K_XL, MTP4 iq4_xs + vocab 64k, KV q4_0, ctx 67584, ABBA na świeżych serwerach)

| tryb (sesje) | czat sweep 5 seedów T=1: t/s / ms/step | greedy T=0 t/s | kopia 64k: t/s / tok/step | code-edit mvs ×4: t/s / tok/step |
|---|---|---|---|---|
| 3090-opt (opt.1, opt.2) | 77.75 / 37.82 | 87.75 | 81.5 / 4.49 | 125.8 / 4.91 |
| topka OFF (`LOOKUP=0`; off.1, off.2) | 77.5 / 37.94 | 87.55 | 81.35 / 4.49 | 125.8 / 4.91 |
| **topka ON** (W16 + share; on.1, on.2) | 77.15 / 38.07 | 87.4 | **245.0** / 14.22 | **320.6** / 14.22 |
| topka ON + L2PF (pf.1, pf.2) | 76.55 / 38.39 | 86.8 | 244.1 / 14.22 | 319.2 / 14.22 |
| TensorFold 1.1.0 MLX-4bit + DFlash2 (tf.1, streaming) | 73.9 | — | 106.8 (prefill 317 s) | 309.3 |
| topka ON, streaming (on.3s, ten sam pomiar co TF) | 77.3 | — | 245.5 (prefill 69–72 s) | 316.6 (2 z 4 plików) |

ms/step na edycji kodu: ON 44.35, L2PF 44.56, OFF 39.0. Na kopii: ON 58.07, L2PF 58.27, OFF 55.2. VRAM po załadowaniu: opt 19.5 GB, topka 19.6 GB.

## Adopt / kill

| zmiana | decyzja |
|---|---|
| topka (lookup W16 + cache share) na CUDA sm_86 | **adopt** jako domyślna konfiguracja NVIDIA dla edycji/kopii (×2.55 / ×3.0, czat bez zmian). Zastrzeżenie: greedy md5 na CUDA nie jest niezmiennikiem lookupu (pkt 3). |
| `GGML_CUDA_MMVQ_L2PF=1` | **kill** (−0.4…−0.8%), zostaje domyślnie wyłączone |
| evict-first | nie zbudowane, poza rundą |
| PDL na Ampere | nie dotyczy (sm_90+) |
| TensorFold 1.1.0 na 3090 | odrzucony jako alternatywa: prefill ×4.6 wolniejszy, kopia ×2.3 wolniejsza |

Pominięte z braku budżetu: 12 GB (3060, LFM2.5 `l3060.sh` gotowy) oraz sm_120 (5060 Ti / 5090). Drugie przejście TensorFold (tf.2) ucięte terminem.

## Problemy w trakcie (naprawione)
- Obraz `cuda:12.8.1-runtime` nie ma `libgomp1`, więc w pierwszym przebiegu każdy serwer padł przy ładowaniu. `boot.sh` instaluje go teraz w apt.
- `srv_start` dawał `--host/--port` przed podkomendą `tensorfold-native serve`. Naprawione wrapperem `/root/tfserve.sh` w `q3090.sh`.
- Pierwsza oferta (55991279) odrzucała klucz SSH, choć był przypięty. Instancję zniszczyłem po ok. 5 min.
- `push.sh` przerywał na katalogu `inst/__pycache__` (scp). Katalog usunięty.

## Do bazy wiedzy
- Topka na RTX 3090 (Qwen3.8-27B Q4_K_XL, MTP4 + lookup W16): mvs 320.6 t/s (×2.55 vs 3090-opt 125.8), kopia 64k 245 t/s (×3.0), czat 77 t/s bez zmian. Z lookupem off = 3090-opt bitowo.
- Na CUDA lookup zmienia greedy md5 na 1/6 promptów czatu (en-code), na XTX 0/11. Bramka md5 dla lookupu na NVIDIA musi porównywać z ON, nie z OFF.
- `GGML_CUDA_MMVQ_L2PF` na sm_86: −0.4…−0.8%, negatyw.
- TensorFold 1.1.0 na 3090: instalacja headless działa (~6 min). Prefill 64k zajmuje 317 s (nasz 69 s), kopia 107 t/s; na edycji kodu 309 t/s (nasz 317).
- Vast runtime image: dodać `libgomp1` przy wysyłce gotowych binarek llama.cpp.
