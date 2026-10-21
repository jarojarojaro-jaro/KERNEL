#!/usr/bin/env bash
# Downloads the OrcaCyber Nano 1.0 files for the 3090 campaign. Runs ON the instance.
# The HF repo is gated:auto, so a token is required: it comes from $HF_TOKEN_FILE (chmod 600) written by run-orca.sh
# over ssh stdin, and is removed with shred after every file verified its sha256.
# aria2c gets a short-lived signed CDN URL from the HF redirect (the token is never handed to aria2c).
# HF_ENDPOINT overrides the host, e.g. https://hf-mirror.com on hosts where huggingface.co is not routable.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
MODELS=${MODELS:-/root/models}
TOKEN_FILE=${HF_TOKEN_FILE:-/root/.hf_token}
mkdir -p "$MODELS"
fail=0
now() { date -u +%T; }

token=
[ -s "$TOKEN_FILE" ] && token=$(tr -d '[:space:]' < "$TOKEN_FILE")
[ -n "$token" ] || { echo "no HF token in $TOKEN_FILE (repo is gated)"; exit 1; }

download_one() {  # repo rev file size sha
    local repo=$1 rev=$2 file=$3 size=$4 sha=$5
    local dest="$MODELS/$file" url head auth=()
    auth=(-H "Authorization: Bearer $token")
    if [ -f "$dest" ] && [ "$(stat -c %s "$dest")" = "$size" ] && echo "$sha  $dest" | sha256sum -c --status; then
        echo "$(date -u +%T) $file: cached, sha256 ok"
        return 0
    fi
    url="${HF_ENDPOINT:-https://huggingface.co}/$repo/resolve/$rev/$file"
    head=$(curl -sSIL --max-time 60 "${auth[@]}" "$url" | awk 'BEGIN{IGNORECASE=1} /^location:/{u=$2} END{gsub("\r","",u); print u}')
    if [ -z "$head" ] || [[ "$head" == *"huggingface.co/"* ]]; then
        # no CDN redirect, or a mirror that redirects back to huggingface.co: fetch with the token (resumable);
        # aria2c never gets the token, so the signed CDN URL is the only case it can handle
        echo "$(now) $file: direct (redirect -> $head), curl -L with the token"
        curl -fsSL -C - "${auth[@]}" -o "$dest" "$url" || return 1
    else
        echo "$(now) $file: downloading $size B from CDN"
        aria2c -q -x 8 -s 8 -c --file-allocation=none --checksum="sha-256=$sha" -d "$MODELS" -o "$file" "$head" || return 1
    fi
    sha256sum -c --status <<<"$sha  $dest"
}

while IFS=$'\t' read -r key gpus repo rev file size sha mtp notes; do
    [ "$key" = key ] && continue
    [ "$gpus" = 3090 ] || continue
    if ! download_one "$repo" "$rev" "$file" "$size" "$sha"; then
        echo "DOWNLOAD FAILED: $file" >&2
        fail=1
    fi
done < "$HERE/models-orca.tsv"

if [ "$fail" = 0 ]; then
    shred -u "$TOKEN_FILE" 2>/dev/null || rm -f "$TOKEN_FILE"
    echo "$(date -u +%T) all files verified, token removed"
else
    echo "$(date -u +%T) failures, token kept for a retry" >&2
fi
exit "$fail"
