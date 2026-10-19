# 24b — Pełna głowica draftu dla tokenów spoza słownika 64k: ODRZUCONE

Data: 2026-10-19. Źródło: analiza CPU `~/qwen-opt/re/oov_draft_analysis.md` (agent OptDraftOov2, przerwany przez awarię sieci po analizie; wniosek wynika z jej tabel).

## Werdykt
**Nie wdrażamy.** Przełączanie draftu MTP na pełny słownik (248k), gdy w kontekście pojawiają się tokeny spoza naszego słownika draftu (64k), daje **ujemny sufit netto we wszystkich grupach**, także po polsku: zysk tokenów/krok jest mniejszy niż koszt droższej głowicy.

| grupa | tokeny spoza 64k (następny) | sufit tok/krok | koszt kroku (pełna głowica, W=16) | netto t/s (W=16) | netto (zawsze pełna) |
|---|---|---|---|---|---|
| wszystkie (69 036 pozycji) | 2.8% | +3.1% | +1.89% | **−0.51%** | −2.40% |
| polski | 3.7% | +3.8% | — | — | — |
| polska proza | 5.0% | +5.1% | +2.04%* | — | — |
| angielski | 2.0% | +2.4% | +1.46% | −0.60% | −3.02% |

\* koszt dla en-prose przy W=16; pełna tabela per grupa i okno W=4/16/64/zawsze w pliku źródłowym. Sufit to wariant idealny (każdy token OOV trafiony), więc realny wynik byłby jeszcze gorszy.

Dlaczego: tokeny spoza 64k to tylko 2–5% kolejnych tokenów, a pełna głowica (248k × 5120) kosztuje +5.6% kroku przy stałym użyciu; nawet okno tylko po OOV (W=4) jest na minusie (−0.13%).

## Do bazy wiedzy
| folder | tytuł | treść |
|---|---|---|
| `eksperymenty/` | 2026-10-19 pełna głowica draftu dla OOV — odrzucone | OOV 2.8% (PL 3.7%, PL proza 5.0%); sufit netto −0.13…−2.40% we wszystkich grupach (`oov_draft_analysis.md`) |
| `lekcje/` | słownik draftu 64k zostaje | zysk z pokrycia OOV < koszt pełnej głowicy nawet w idealnym wariancie |
