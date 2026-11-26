---
typ: llm
tags: [llm, edycja-wag, ablacja, rank-1, self-edit, research]
aktualizacja: 2026-11-26
zrodlo: arXiv 2202.05262 (ROME), 2210.07229 (MEMIT), 2110.11309 (MEND), 2406.11717 (kierunek odmowy), 2212.04089 (task vectors), 2306.01708 (TIES), 2311.03099 (DARE), 2506.10943 (SEAL), 2506.06105 (Text-to-LoRA), 2611.09382 (WSP), 2611.21885, 2611.28833 (Self-WSP), 2611.29513 (SELFWRITE), 2401.07453; rikiyat.github.io/blog/weight-space-programming; github.com/HomoHabilis/weight-space-programming (exp10); obraz pbs.twimg.com/media/HX_s4hPWAAAYc_k.jpg; panel JARO 2026-11-26 (x.com/shinboson/status/2125682378228072515)
status: aktualne
---
# Edycja wag (weight editing) od A do Z: co działa, co jest hype, co robimy my

**Edycja wag to cztery różne rzeczy: (1) zmiana faktów (ROME/MEMIT), (2) zmiana zachowania jednym kierunkiem (ablacja odmów, skracanie myślenia), (3) łączenie całych modeli (task vectors, TIES, DARE), (4) model sam edytuje swoje wagi (SEAL, WSP, 2026: „przepisywanie własnych wag”). Fala z listopada 2026 to (4): prawdziwa, ale zyski są małe i kruche (27B: +6,6 pkt na 490 zadaniach; Qwen3.8-27B: +1,45 pkt held-out), na 2B/4B/9B często zero albo model się psuje, a losowe szukanie edycji bywa równie dobre. Tweet @shinboson (Qwen3.5-4B 35 → 67% na 200 zadaniach matematycznych, 6 rund) jest na razie niezweryfikowany: widać tylko nagłówek bloga, bez kodu, metody i kontroli. Nie przełom; ciekawy kierunek, który my już stosujemy w wersji ręcznej (uncensored, Astra-Stop).**

## 1. Jak to działa (mechanizm)
- Warstwa liniowa to macierz W. Edycja rzędu 1: W' = W − α·u·(uᵀW) (wycina kierunek u z tego, co warstwa zapisuje) albo W' = W + α·u·vᵀ (dopisuje). u to kierunek w przestrzeni ukrytej znaleziony z aktywacji (np. średnia różnica „odmowa vs zgoda”, kierunek tokenu `</think>`).
- Scalona edycja zmienia tylko liczby w pliku: **prędkość dekodu bez zmian**. Edycja w locie (LoRA, ablacja na żądanie) kosztuje u nas 2–7%.
- „Self-edit”: model dostaje dostęp do własnych wag i interpretera Pythona, proponuje edycję (kod, który liczy u i α), edycja jest sprawdzana na zestawie bramkowym i zostaje albo jest cofana; „rekurencyjnie” = kolejna runda startuje z edytowanego modelu.

## 2. Mapa metod i dowody

| rodzina | przykłady | co zmienia | co pokazano (pierwotne źródło) | słabości |
|---|---|---|---|---|
| fakty | ROME 2202.05262, MEMIT 2210.07229, MEND, AlphaEdit | rank-1 w MLP środkowej warstwy | pojedyncze i tysiące faktów (GPT-J 6B, NeoX 20B) | po wielu edycjach stopniowe, potem katastrofalne zapominanie (2401.07453) |
| kierunek zachowania | ablacja odmów 2406.11717, RepE, wektory sterujące | W' = (I − r rᵀ)W na wszystkich warstwach zapisujących | odmowy sterowane jednym kierunkiem w 13 modelach do 72B | możliwa utrata jakości, mierzyć KLD |
| łączenie modeli | task vectors 2212.04089, soups, TIES 2306.01708, DARE 2311.03099 | suma/średnia różnic fine-tune'ów | soups bez kosztu inferencji; TIES: konflikty znaków są głównym problemem | wymaga wspólnej bazy |
| model edytuje siebie | SEAL 2506.10943 (przez SFT), Text-to-LoRA 2506.06105, WSP 2611.09382, 2611.21885, Self-WSP 2611.28833, SELFWRITE 2611.29513 | edycje rank-1/low-rank pisane jako kod, bez gradientu | 27B: 57,2 → 63,8% (490 zadań; 2B nic, 4B i 9B się psują); Qwen3.8-27B DAPO-Math held-out 76,30 → 77,75; 0,8B GSM8K 11,8 → 62,2% (ale „losowe szukanie czasem porównywalne”); WSP 9B: brak zysku | brak interpretacji, wątpliwe kontrole, skumulowanie rund niezmierzone albo małe |

## 3. Weryfikacja tweeta @shinboson (2026-11-25)
- **Widoczne:** nagłówek bloga „Recursive Self-Improvement at 4B via Self-Play Weight Editing”: Qwen3.5-4B, 200 zapieczętowanych zadań DeepScaleR, 16k tokenów myślenia, bez narzędzi i nauczyciela; 35,0 → 67,0% po 6 rundach (dla porównania nietknięte 27B 56,0%, 9B 45,0%).
- **Niewidoczne:** URL bloga, kod (repo autora nie ma tego projektu), kto proponuje edycje, baza porównawcza (RL/SFT przy tym samym koszcie, losowe edycje), seedy, wariancja. 95% CI przy 200 zadaniach to ok. ±6,6 pkt, więc skok 32 pkt byłby duży, ale bez kontroli to tylko deklaracja.
- **Ostrożność:** podobny eksperyment 4B (repo HomoHabilis/weight-space-programming exp10, edytor Opus 5.5): +5,3 pkt przy p = 0,13, łączenie edycji bez zysku; przy budżecie 16k tokenów edycja skracająca myślenie (jak Astra-Stop) może dać dużo „za darmo”.

## 4. Co już robimy my (to ta sama rodzina, ale cel wybiera człowiek)
- Qwen3.8-27B Uncensored = jeden kierunek wycięty z warstw zapisujących ([[uncensored-ablacja-kierunku]]); Inkling w Mai: ablacja w locie (`IK2_ABLATE`, odmowy 7/8 → 0/8, dekod −2…−5%); Nib: LoRA rank 1 (−7% T=0).
- Astra-Stop: rank-1 na `blk.63.ffn_down`, mediana myślenia −35,5%, ale wyciek `</think>` 11/32 ([[astra-stop]], odłożone 2026-11-09).

## 5. Tanie eksperymenty dla nas (do decyzji JARO, zmieniają odpowiedzi modelu)
1. **Skracanie myślenia jednym kierunkiem** (Astra-Stop) na naszym Qwen uncensored: α 0,5 / 1,0 / 1,5; miary: mediana tokenów myślenia, wyciek `</think>`, KLD na zwykłych promptach, jakość (HumanEval+/jakość-mini). Zysk dla użytkownika: odpowiedź szybciej przy tej samej prędkości t/s.
2. **Scalona ablacja zamiast ablacji w locie** w Mai/Nibie: ten sam kierunek wpisany w plik → odzyskanie 2–7% dekodu bez zmiany zachowania (bramka KLD).
3. **Mała pętla „self-edit” z bramką** (jak SELFWRITE) na Qwen3.8-27B: dopiero po 1–2, bo wymaga dużego zestawu ewaluacyjnego (setki zadań) i kontroli losowych edycji.

## Powiązane
- [[trening-llm-mapa]]
- [[uncensored-ablacja-kierunku]]
- [[astra-stop]]
- [[cspd-soft-prompt]]
