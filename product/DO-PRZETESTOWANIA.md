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
