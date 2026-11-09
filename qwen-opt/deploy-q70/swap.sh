#!/usr/bin/env bash
# Swap production to topka-q70 (only after GATE_OK); rollback: mv ~/llama-topka ~/llama-topka.q70 && mv ~/llama-topka.c0576e3e8 ~/llama-topka
set -euo pipefail
[ -f "$HOME/qwen-opt/deploy-q70/GATE_OK" ] || { echo "no GATE_OK: production unchanged"; exit 0; }
pgrep -f "llama-topka/bin/llama-server" && { echo "production server still running"; exit 1; }
[ -e "$HOME/llama-topka.c0576e3e8" ] && { echo "backup exists already"; exit 1; }
mv "$HOME/llama-topka" "$HOME/llama-topka.c0576e3e8" && mv "$HOME/llama-topka.q70" "$HOME/llama-topka"
echo "production = $(cat "$HOME/llama-topka/ENGINE"), backup ~/llama-topka.c0576e3e8"
