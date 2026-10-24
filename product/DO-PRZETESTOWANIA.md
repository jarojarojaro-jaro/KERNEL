# Do przetestowania

Wspólna lista pomysłów do testu z raportów researchu. Tylko dopisywanie (append), jeden pomysł na wiersz.

| pomysł | raport źródłowy | cel (XTX/3090) | szac. zysk | wysiłek | status |
|---|---|---|---|---|---|
| Alokacja 57g −1.0 GB z `attn_qkv` (GDN) nietkniętym (sygnał DCQ: qkv niszczy stan 25×) | 60c-quant-and-3090-engines.md (T1) | XTX, 3090 | KLD-PL ≥10% niższe niż plan 57g przy +4…+5% t/s vs U4 | ~30 min GPU + kwantyzacja CPU; wymaga BF16 | nowe |
| Bramka `--np 1` = `--np 4` (greedy md5, 6 promptów spec_sweep + 2 code-edit), wzór tqLLM `rc_gate.py` | 60c-quant-and-3090-engines.md (T2) | XTX, 3090 | 0 t/s; poprawność multi-slot | 15 min GPU | nowe |
| Próg na pozycję draftu MTP τ=0.9/0.8 vs stałe n=4 (ABBA, spec_sweep + long 32k), obok `LLAMA_DRAFT_CUMP` | 60c-quant-and-3090-engines.md (T3) | XTX | 0…+2% | 10–20 min GPU | nowe |
| tqLLM 1.2.3 Flash-Next vs nasz 27B na tej samej wynajętej 3090 (czat T=0/T=1, po 32K, TTFT) | 60c-quant-and-3090-engines.md (T4) | 3090 | wiedza konkurencyjna, 0 t/s dla nas | ~2 h wynajmu ≥128 GB RAM (~$1–2) + pobranie ~55 GB na Vast | nowe |
| Gyro-Coder (fork agentionai, Vulkan → próba HIP) vs nasz 27B: czat t/s + 8 zadań kodowych × 2 seedy | 60c-quant-and-3090-engines.md (T5) | XTX | nieznany; kill <95 t/s lub mniej zadań niż 27B | 0.5 dnia + 70.6 GiB pobrania | nowe |
| MTP na qwen35moe w topce (Qwen3.6-35B-A3B z blokiem nextn; tqLLM ×1.4–1.8) | 60c-quant-and-3090-engines.md (T6) | 3090, XTX (katalog 10–16 GB) | ×1.4–1.8 dla tieru MoE | 1 h GPU + GGUF z MTP (pobranie) | nowe |
| Pomiar: ile z ~1.1 s przywracania wpisu `--cache-ram` (2.3 GB) to transfer H2D z pageable (timery wokół `llama_state_seq_set_data_ext`, scenariusz 16f E4) | 60d-serving-kernels-cache.md (T1) | XTX | rozstrzyga T2 | 1 h GPU | nowe |
| Pinned staging + jedna seria async dla zapisu i przywracania wpisów `--cache-ram` (wzorzec `LLAMA_CKPT_VRAM=2`, HiCache I/O); bramka md5 | 60d-serving-kernels-cache.md (T2) | XTX, 3090 | start nowej sesji Qwena 1612 → ~800 ms | 1–2 dni + 1 h GPU | nowe |
| Lekki wpis „prefiks systemowy”: KV [0,P) + checkpoint GDN dokładnie na końcu promptu systemowego omp (HiCache #33639), zamiast kopii całego wpisu 53k | 60d-serving-kernels-cache.md (T3) | XTX, 3090 | nowa sesja podagenta ~1.6 s → ≤0.5 s | 2–3 dni + 2 h GPU | nowe |
| Wybór i eviction wpisów cache według `prompt_cache_key` od omp (URC session_id) zamiast samego `f_keep ≥ 0.25` | 60d-serving-kernels-cache.md (T4) | XTX, 3090 | brak re-prefillu 7–8 s przy przeplocie sesji | 1 dzień + 1 h GPU | nowe |
| Sufit AKV (drop starych wyników narzędzi): udział tokenów starych tool-outputów w kontekście tur omp przy 32k/64k/100k (CPU, transkrypty) | 60d-serving-kernels-cache.md (T5) | XTX | rozstrzyga AKV-drop; kill <30% kontekstu | 2 h CPU, $0 | nowe |
| hipBLASLt/`GGML_CUDA_FORCE_CUBLAS` (dekod raz do FP16 + GEMM, Maya `DS4_FAT_ROWS`) vs MMQ dla pp2048/pp8192 Qwena Q4_K_XL | 60d-serving-kernels-cache.md (T6) | XTX | −10…+15% pp (niepewne) | 1 build cpuheavy + 30 min GPU | nowe |
| Humming (vLLM ≥0.29, `--linear-backend humming`) W4A16 27B batch 1 vs nasz cuda-topka na tej samej 3090 | 60d-serving-kernels-cache.md (T7) | 3090 | wiedza, 0 t/s | ~1 h Vast + pobranie GPTQ-Int4 na Vast (decyzja użytkownika) | nowe |
| Sito głowicy draftu MTP: MMVQ na pierwszej połowie K (10 z 20 superbloków) dla słownika draftu 64k, top-128, dokładne dot dla 128 wierszy (spariev, mlx.fast #431) | 60b-apple-engines-bonsai.md (T1) | XTX, 3090 | +0.5–1.5% t/s (głowica ~178 MB/token draftu, −45% bajtów) | 1–2 dni + 20 min GPU; najpierw rocprof czasu głowicy | nowe |
| L2 `evict_first` (`createpolicy` + `ld.global.L2::cache_hint`) na strumieniu wag MMVQ/MMQ, przełącznik, md5 = baza (cuda.fast #74 zm. 9: ×1.033 na GB10) | 60b-apple-engines-bonsai.md (T2) | 3090 | +0.5–2% | 0.5 dnia + 30 min wynajmu | nowe |
| Taśma delt GDN: weryfikacja zapisuje `delta` i `g` wierszy oczekujących, przeliczenie w S4 bez redukcji k·S (mlx.fast #467) | 60b-apple-engines-bonsai.md (T3) | XTX, 3090 | +0.3–0.8% | 2–3 dni, bitowo | nowe |
| Audyt sufitu wzorca (R18 #12): ffn 5120×17408 Q4_K/Q5_K/IQ4_XS wzorcem MMVQ n=5 vs ciągłe przebiegi na CTA; motywacja cuda.fast #24 (230–236 vs 200–210 GB/s) | 60b-apple-engines-bonsai.md (T4) | XTX | 0–10% (kill <5%) | 1 h GPU | nowe |
| Audyt konwersji API Anthropic w llama-server: tekst `user` przed wiadomościami `tool` (`server-chat.cpp:524-542`) vs szablon Qwen3.8 i stabilność prefiksu w 2. turze (oMLX #4712) | 60b-apple-engines-bonsai.md (T5) | XTX, 3090 | TTFT agentów / poprawność, 0 t/s | 1 h CPU | nowe |
| Drzewo 15 węzłów w stałej W16 dla DFlash2 (restart GDN od zapisanego stanu, T drzewa per blok; mlx.fast #424/#433/#428): najpierw symulacja offline z kraty top-16 | 60b-apple-engines-bonsai.md (T6) | XTX | −7% rund przy W16 (tylko jeśli DFlash2 wygra z MTP) | 0.5 dnia CPU symulacja; kernel 10+ dni | nowe |
