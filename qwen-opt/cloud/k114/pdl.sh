#!/usr/bin/env bash
# pdl.sh <url> <dest> <size> [parts]: parallel HTTP range download (HF throttles single connections to ~2 MB/s on
# some Vast hosts, 2026-11-17). Parts -> <dest>.pN, concatenated and size-checked. Exit 0 only on exact size.
set -uo pipefail
U=$1 D=$2 SZ=$3 N=${4:-16}
step=$(( (SZ + N - 1) / N ))
for i in $(seq 0 $((N - 1))); do
    a=$(( i * step )); b=$(( a + step - 1 )); [ $b -ge $SZ ] && b=$(( SZ - 1 ))
    ( for t in 1 2 3 4 5; do
          curl -fsSL -r "$a-$b" -o "$D.p$i" "$U" && [ "$(stat -c %s "$D.p$i")" = $(( b - a + 1 )) ] && exit 0; sleep 3
      done; exit 1 ) &
done
wait
ok=1; for i in $(seq 0 $((N - 1))); do [ -f "$D.p$i" ] || ok=0; done
[ $ok = 1 ] || exit 1
cat $(for i in $(seq 0 $((N - 1))); do echo "$D.p$i"; done) > "$D" && rm -f "$D".p*
[ "$(stat -c %s "$D")" = "$SZ" ]
