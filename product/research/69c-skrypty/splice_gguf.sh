#!/bin/bash
# Bake Astra-Stop into a COPY of the served GGUF: replace only blk.63.ffn_down.weight (Q6_K, 73,113,600 B)
# with the error-feedback re-quantised blob from splice_variants.py (u^T W ratio 2.005, cos 0.99998).
# Same type and size -> header, offsets and the other 865 tensors stay byte-identical.
# Needs ~16.8 GB free disk (ext4, no reflink). CPU/IO only; run when the GPU queue does not care about IO.
set -euo pipefail
SRC=${1:-$HOME/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf}
DST=${2:-$HOME/models/orca/Qwen3.8-27B-Uncensored-AstraStop-Q4_K_M.gguf}
BLOB=${3:-$(dirname "$0")/blk63_ffn_down_astra_unc_errfb.q6k}
OFF=16373996928   # absolute data offset of blk.63.ffn_down.weight in the Orca Uncensored Q4_K_M (gguf-py, verified)
SZ=73113600
[ "$(stat -c %s "$BLOB")" = "$SZ" ] || { echo "blob size mismatch"; exit 2; }
[ "$(stat -c %s "$SRC")" = 16810714496 ] || { echo "unexpected source GGUF size (offset is file-specific)"; exit 2; }
nice -n 19 ionice -c3 cp "$SRC" "$DST.part"
nice -n 19 dd if="$BLOB" of="$DST.part" bs=1M seek="$OFF" oflag=seek_bytes conv=notrunc status=none
cmp -l "$SRC" "$DST.part" | awk -v o=$OFF -v s=$SZ '{p=$1-1; if (p<o || p>=o+s) {print "byte outside tensor changed at " p; exit 3}}'
mv "$DST.part" "$DST"
sha256sum "$DST"
