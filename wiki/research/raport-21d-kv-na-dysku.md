---
typ: research
tags: [research, cache, ssd]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21d-kv-na-dysku.md:1-237
status: aktualne
---
# Raport 21d: KV na dysku (Strata, Mirai S Ada) i nasza polityka

**Zapis stanu KV na SSD jest bezpieczny dla dysku tylko przy polityce warstw (RAM/tmpfs najpierw, dysk przy shutdown, ≤ 10 GB/dzień); odczyty nie zużywają NAND; nasz obecny plik slotu jest ~2× za duży (7 checkpointów), nieatomowy i bez odcisku modelu (raport agenta, 2026-10-19).**

- Mirai S Ada (Qwen3.8-27B, q8_0 34 816 B/token): 245k = 8.53 GB wyliczone vs 8.3 deklarowane, restore 0.92 GB/s, prefill 468 t/s, „~9 min” = 8.7 min – spójne, ale bez receiptów; zapis przed żądaniem (23–74 s na turę) to antywzorzec; 6 GB w 227 s (26 MB/s) na wolnym dysku.
- [[strata]]: wersja 0.2.0 nie istnieje (najnowsza v0.1.45, 2026-10-17); session files wzorcowe (tmp + fsync + rename, fingerprint, O_DIRECT 16 MiB, tylko najgłębszy checkpoint); 63k = 1.20 GB, save 0.65 s, restore 1.05 s; uczciwie: identyczne tokeny po restarcie niegwarantowane (rozjazd od 28. tokenu); „park-gain” 2 251.9 GB → 3.26 GB kopii.
- Oczekiwany zysk przy 1 checkpoincie + MTP z SSD 1.05 GB/s: 53k ×47, 150k ×74, 200k ×86 względem prefillu `[INFERENCE]`.
- Plan: higiena pliku (0.5 dnia), sidecar MTP (0.5), tmpfs + polityka (1–2), segmenty natywne (2–3); eksperyment GPU z kill (restore z tmpfs ≥ 80% SSD; md5 różne w BITEXACT; replay dnia > 10 GB).

Notatki: [[kv-na-dysku-polityka]], [[dysk-serwera-pm9b1]], [[lekcja-restore-stanu-exactness]].

## Powiązane
- [[research/_hub|research]]
- [[cache-sesji-na-dysku]]
- [[raport-16f-xtx-szybkie]]
