# Qwen3.8-27B: jak wyjść z ~60 t/s na czacie (research 2026-10-10)

Szczegóły i źródła: `drafters.md`, `training.md`, `algorithms.md`, `stepcost.md` (raporty agentów),
`vkperf-6tok.txt` (profil Vulkan).

## 1. Skąd bierze się 60 t/s (pomiary)

t/s = (tokeny przyjęte na krok) / (czas kroku).

**Czas kroku** (Vulkan, llama-bench, kontekst 2048):

| tokenów w weryfikacji | ms |
|---|---|
| 1 | 32.2 |
| 2 | 33.7 |
| 4 | 37.7 |
| 6 | 39.2 |
| 8 | 44.6 |
| 9–16 | 108–110 (wypada z kerneli matvec do MMQ) |

Krok MTP n=5 = weryfikacja 6 tokenów (~39 ms) + 5 przejść draftu (~1–2 ms każde) ≈ 44–46 ms.
W weryfikacji: matvec 27.8 ms przy 592 GB/s (62% z 960), reszta operacji 6.9 ms (~1800 małych dispatchy).

**Tokeny na krok**: kod ~4.0–4.2, tech ~3.3, czat/proza ~2.6–3.2.
Czat 2.7 tok / 45 ms = 60 t/s. Kod 4.1 / 45 = 91 t/s.

## 2. Wniosek

- Żaden gotowy drafter nie jest wyraźnie lepszy od MTP na czacie (publikowane AL 2.8–4.1, MTP-7 na MT-Bench 3.74).
  Nie istnieje EAGLE-3 dla Qwen3.8-27B. DSpark-y działają, ale na czacie nie lepiej niż MTP.
- Drzewa draftu odpadają: GDN (warstwy rekurencyjne) w llama.cpp obsługuje tylko pojedynczy łańcuch.
- 2× na czacie bez zmiany rozkładu wyjścia jest nierealne. Realnie: **60 → 80–90 t/s** przez połączenie
  tańszego kroku i lepszego draftu. Jedyna droga do więcej: weryfikacja stratna (typical acceptance) —
  zmienia jakość, decyzja użytkownika.

## 3. Plan (kolejność = zysk/koszt)

| # | Zmiana | Typ | Szac. zysk czat | Koszt |
|---|---|---|---|---|
| 1 | Adaptacyjna długość draftu: stop, gdy iloczyn pewności < τ (n_max 7) | akceptacja | +10–15% | niski, `common/speculative.cpp` |
| 2 | Tanie poprawki kroku: matvec małych M (ssm_alpha/beta 1.3 ms), jeden CPY snapshotów conv, GPU sampling celu (`-bs`), połączenie catch-up z draftem #1 | czas kroku | −3–5 ms (+8–12%) | niski–średni |
| 3 | Fuzja zapisu stanu GDN do cache na Vulkanie (jak CUDA PR #23940) + fuzja norm/gate w GDN | czas kroku | −2–3.5 ms (+5–8%) | średni |
| 4 | Cały łańcuch draftu MTP w jednym grafie | czas kroku | −1–2 ms, kod +20% | wysoki |
| 5 | DFlash2: probabilistyczny wybór ścieżki + rejection sampling (upstream tak robi; MT-Bench T=1 AL 4.10 vs MTP 3.74) | akceptacja | +20% EN czat (szac.) | średni, ~50 linii |
| 6 | Douczenie głowicy MTP na wyjściach Q4 (FastMTP, TV/KL) | akceptacja | +10–17% (do +25–30% z próbkowaniem) | wysoki: 1.5–2 dni, PyTorch ROCm, ~22 GB dysku |
| 7 | Tuning 6-kolumnowego MMVQ (IQ4_XS/Q4_K/Q5_K: 592 → ~680 GB/s) | czas kroku | −2–2.4 ms | wysoki |

Suma 1–4: krok 45 → ~33–36 ms, przy AL czatu ~3.0 → **~85 t/s czat, ~115 t/s kod** [szacunek].
5 lub 6 dokłada akceptację na czacie.

Każdy punkt mierzony `spec_sweep.sh` (6 promptów, T=1, dwa seedy) przed i po.
