# 39e — TorchTPU (open source, 2026-10-20)

## TL;DR
TorchTPU (github.com/google-pytorch/torch_tpu; repo z 2026-03-09, 258★, C++, PyPI 0.2.0) to backend PyTorcha dla TPU: własne kernele ATen (eager), cache kompilacji XLA i integracja z `torch.compile` (graph mode). Do tego dochodzą natywny backend vLLM (kernele Pallas, z Inferact) i TorchTitan (SimpleFSDP). **Dla dekodowania na XTX nie ma znaczenia.** Nic z tego nie przenosi się do llama.cpp na gfx1100/CUDA: robimy już capture grafu, PM4 replay i fuzję. Ewentualnie przyda się jako tani compute do treningu głowicy MTP, i to tylko wtedy, gdy dostaniemy darmowe TRC. Dla produktu to sygnał rynkowy: Google wpycha PyTorch + vLLM na TPU, czyli w serwowanie w chmurze z batchowaniem. To nie nasza nisza (lokalny decode dla jednego użytkownika).

## Tabela tez
| Teza | Weryfikacja | Werdykt |
|---|---|---|
| „Native PyTorch na TPU” | README: kernele ATen + XLA compile cache + `torch.compile`. Pod spodem nadal XLA/MLIR (`libxla_base.so`), więc jest to następca podejścia torch_xla, tylko bez lazy tensorów w API | Potwierdzone (to „natywność” z poziomu API, kompilator to dalej XLA) |
| vLLM na TPU z ciągłym batchowaniem, kwantyzacją i TP | Blog, kodu vLLM nie czytałem | [INFERENCE] wiarygodne, poza naszym zakresem |
| Trening na skalę (TorchTitan, FSDP) | Blog i przykłady Llama/Qwen w repo | Potwierdzone na poziomie deklaracji |
| Idee kompilatorowe do przeniesienia | Cache kompilacji = nasz cache grafów/PM4; Pallas ≈ Triton | Obalone: nic nowego dla nas |

## Co dotyczy nas (ranking)
1. **Trening MTP-head / KLD / imatrix na TPU.** Zysk jest niepewny. Program TRC (TPU Research Cloud) daje darmowe v4/v5e po akceptacji wniosku, a Colab TPU jest darmowy, ale ma limity sesji. Koszt: port skryptów i Python 3.11+. Ryzyko bierze się z tego, że imatrix i KLD to narzędzia llama.cpp (GGUF, kwanty), których nie da się uruchomić na TPU. Na TPU sensownie da się trenować tylko głowicę MTP w PyTorchu (raporty 10/11). Bezstratność nie ma tu znaczenia (to trening). Rekomendacja: złożyć wniosek do TRC tylko wtedy, gdy trening MTP stanie się wąskim gardłem.
2. **Graph/fusion na decode.** Zysk wynosi 0 ms. W budżecie 27,38 ms/krok (raport 36) koszt stały launchu to ok. 2,4 ms i już go adresujemy przez PM4 replay. XLA nie wnosi tu żadnej techniki, która nie jest już w naszym stosie.
3. **Produkt.** Konkurencja Google Cloud dotyczy serwowania w chmurze, a nie lokalnej inferencji na AMD/Mac. Nasze pozycjonowanie (szybki lokalny decode dla jednego użytkownika) się nie zmienia.

## Eksperymenty XTX ≤10 min
Brak. Nic nie da się przetestować na XTX.

## Do bazy wiedzy
| Źródło | Data/wersja | Q/ref | Wartość | Status |
|---|---|---|---|---|
| TorchTPU (google-pytorch/torch_tpu) | 0.2.0, 2026-10-20 | 39e | Niska (TPU; ewentualnie TRC do treningu MTP) | – |
| Blog GCP „TorchTPU is now open source” | 2026-10-20 | 39e | Niska (sygnał rynkowy: vLLM/SGLang na TPU) | – |
