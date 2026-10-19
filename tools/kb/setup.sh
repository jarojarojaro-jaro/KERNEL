#!/usr/bin/env bash
# Instalacja `kb`: ONNX Runtime (statycznie), model e5-small (int8), build, ~/.local/bin/kb, indeks.
# Tylko CPU. Ponowne uruchomienie pomija to, co już jest.
set -euo pipefail
cd "$(dirname "$0")"

ORT_URL=https://cdn.pyke.io/0/pyke:ort-rs/ms@1.22.0/x86_64-unknown-linux-gnu.tgz
ORT_SHA=ed1716de95974bf47ab0223ca33734a0b5a5d09a181225d0e8ed62d070aea893
MODEL_DIR=${KB_MODEL:-$HOME/models/kb/multilingual-e5-small}
HF=https://huggingface.co/Xenova/multilingual-e5-small/resolve/main

if [ ! -f .ort/onnxruntime/lib/libonnxruntime.a ]; then
  mkdir -p .ort
  curl -fsSL -o .ort/ort.tgz "$ORT_URL"
  echo "$ORT_SHA  .ort/ort.tgz" | sha256sum -c -
  tar xzf .ort/ort.tgz -C .ort && rm .ort/ort.tgz
fi

mkdir -p "$MODEL_DIR"
for f in onnx/model_quantized.onnx tokenizer.json config.json; do
  [ -s "$MODEL_DIR/$(basename "$f")" ] || curl -fsSL -o "$MODEL_DIR/$(basename "$f")" "$HF/$f"
done

export PATH="$HOME/.cargo/bin:$PATH"
nice -n 10 cargo build --release -j6
mkdir -p "$HOME/.local/bin"
install -m 755 target/release/kb "$HOME/.local/bin/kb"
KB_THREADS=${KB_THREADS:-4} nice -n 19 "$HOME/.local/bin/kb" reindex
