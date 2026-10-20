# 42 — safe-io: bezpieczne wyjście (token-type) + równoległa tokenizacja

Branch `safe-io` (llama.cpp, lokalny), commit `098ce134d` na bazie `b659634fd` (safe-special).

## Switche (domyślnie OFF)
- `LLAMA_SERVER_SAFE_TOOLS=1` — parser wyjścia (PEG) dopasowuje markery (`<tool_call>`, `</think>`, `<|tool_call_start|>` …) tylko, gdy w wygenerowanym strumieniu stoją jako **token specjalny/kontrolny**, nie jako zwykły tekst. Tekst modelu udający marker nie otwiera tool calla/reasoning. `common_peg_special_tokens` (vocab → tokeny control/user-defined), `common_chat_parser_params.specials`, literal/until w peg-parser sprawdzają granice tokenów.
- `LLAMA_TOKENIZE_PAR=N` — tokenizacja BPE długich promptów na N wątkach; fragmenty cięte tylko w miejscach, gdzie pre-tokenizacja nie zależy od kontekstu → wynik identyczny.

## Testy
- `test-chat-safe-tools` (nowy): Qwen3.5 + LFM2.5 template, strumień k-tokenowy, off vs on: prawdziwe tool calle/reasoning identyczne, fałszywe markery w tekście nie parsowane. OK.
- ctest `test-chat*|tokeniz*`: pass; jedyny fail `test-tokenizers-ggml-vocabs` = pliki LFS-pointer (`vers…`), istniał wcześniej, niezwiązany.

## Tokenizacja równoległa (CPU, 148 realnych promptów omp, best-of-3)
| model / zestaw | hash różnice | ms PAR=0 | ms PAR=8 |
|---|---|---|---|
| Qwen huge (13) | 0 | 599 | 125 |
| Qwen w13 (61) | 0 | 1492 | 329 |
| LFM huge (13) | 0 | 337 | 78 |
| LFM w13 (61) | 0 | 814 | 193 |

Bit-exact, ~4.6× szybciej (~40 ms oszczędności na prompt 200 KB).

## Adopcja
Przekazane do IntegTopka (merge `safe-io`, `LLAMA_TOKENIZE_PAR=8` + `LLAMA_SERVER_SAFE_TOOLS=1` w run-topka.sh, md5 gate na zainstalowanym binarnym).
