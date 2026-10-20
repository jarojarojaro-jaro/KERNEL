# Shared helpers for the local cloud scripts (find/up/push/collect/down/watchdog). Sourced, not executed.
# Every script is a dry run unless --go is given: `run` prints the command instead of executing it.

# final 3090 before/after round (nv-final): shared tools/env from ~/qwen-opt/cloud, own scripts and state in runs/nvfinal
RUN_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CLOUD_DIR=$HOME/qwen-opt/cloud
# shellcheck source=env.sh
. "$CLOUD_DIR/env.sh" 2>/dev/null
# lesson lekcja-vast-cli-klucz: the CLI must get the key explicitly
vastai() { command vastai --api-key "$(cat "$HOME/.vast/key")" "$@"; }
STATE=$RUN_DIR/state
mkdir -p "$STATE"
LABEL_PREFIX=nv-final
IMAGE_DEFAULT=nvidia/cuda:12.8.1-runtime-ubuntu24.04  # prebuilt binaries: runtime only (cudart, cuBLAS)
IMAGE_GB=2                                            # image pull, counted as download in the cost estimate [SZACUNEK]

GO=0
ARGS=()
for a in "$@"; do
    if [ "$a" = --go ]; then GO=1; else ARGS+=("$a"); fi
done
set -- "${ARGS[@]+"${ARGS[@]}"}"

run() {  # print (dry run) or execute a command
    if [ "$GO" = 1 ]; then
        printf '+' >&2; printf ' %q' "$@" >&2; echo >&2
        "$@"
    else
        printf '[dry-run]'; printf ' %q' "$@"; echo
    fi
}

die() { echo "error: $*" >&2; exit 1; }
need_key() { [ -n "${VAST_API_KEY:-}" ] || die "no Vast key: put it in ~/.vast/key (chmod 600)"; }

# GPU name as Vast reports it ("RTX 5060 Ti") -> class used by models.tsv and the CUDA arch to build
gpu_class() {
    case "${1// /_}" in
        RTX_5060_Ti) echo 5060ti ;; RTX_4060_Ti) echo 4060ti ;; RTX_3060) echo 3060 ;;
        RTX_3090|RTX_3090_Ti) echo 3090 ;; RTX_4090) echo 4090 ;; RTX_5090) echo 5090 ;; RTX_A5000) echo a5000 ;;
        *) echo unknown ;;
    esac
}
class_arch() { case $1 in 5060ti|5090) echo 120 ;; 4060ti|4090) echo 89 ;; 3060|3090|a5000) echo 86 ;; *) echo native ;; esac; }
class_min_vram_gb() { case $1 in 3060) echo 11 ;; 5060ti|4060ti) echo 15 ;; *) echo 23 ;; esac; }
# 24/32 GB cards run the 3090 model list
model_class() { case $1 in 4090|5090|a5000) echo 3090 ;; *) echo "$1" ;; esac; }

models_rows() {  # class -> models.tsv rows (without header) for that class
    local mc; mc=$(model_class "$1")
    awk -F'\t' -v c="$mc" 'NR > 1 && ("," $2 ",") ~ ("," c ",")' "$CLOUD_DIR/models.tsv"
}
models_gb() { models_rows "$1" | awk -F'\t' '{ s += $6 } END { printf "%.1f\n", s / 1e9 }'; }
models_n() { models_rows "$1" | awk -F'\t' '$8 != "draft"' | wc -l; }
# hours: setup (image, deps, 2 builds, downloads overlap) + per model (tbo/greedy/llama-bench/spec_sweep ABBA) [SZACUNEK]
est_hours() { awk -v n="$(models_n "$1")" 'BEGIN { printf "%.2f\n", 0.75 + 0.5 * n }'; }
est_disk_gb() { awk -v m="$(models_gb "$1")" 'BEGIN { d = int(m + 35); if (d < 60) d = 60; print d }'; }

SSH_OPTS=(-i "$CLOUD_SSH_KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new
          -o UserKnownHostsFile="$STATE/known_hosts" -o ServerAliveInterval=30 -o ConnectTimeout=20)

inst_json() { vastai show instance "$1" --raw 2>/dev/null; }
# sets SSH_HOST/SSH_PORT for an instance: direct port if mapped, else the Vast ssh proxy
inst_ssh() {
    local j; j=$(inst_json "$1") || return 1
    SSH_HOST=$(jq -r '.public_ipaddr // empty' <<<"$j" | tr -d '[:space:]')
    SSH_PORT=$(jq -r '.ports["22/tcp"][0].HostPort // empty' <<<"$j")
    if [ -z "$SSH_HOST" ] || [ -z "$SSH_PORT" ]; then
        SSH_HOST=$(jq -r '.ssh_host // empty' <<<"$j"); SSH_PORT=$(jq -r '.ssh_port // empty' <<<"$j")
    fi
    [ -n "$SSH_HOST" ] && [ -n "$SSH_PORT" ]
}
# instance id: explicit argument, else the one up.sh recorded last
inst_id() {
    if [ -n "${1:-}" ]; then echo "$1"; elif [ -f "$STATE/current" ]; then cat "$STATE/current"
    else echo "no instance id (pass it, or run up.sh first)" >&2; return 1; fi
}

# one offer by id (read-only, no key). The CLI sends `id=` as a string and finds nothing; the API matches
# ask_contract_id (== offer id) as an integer.
offer_json() {
    curl -fsS -X POST https://console.vast.ai/api/v0/bundles/ -H 'Content-Type: application/json' \
        -d "{\"ask_contract_id\":{\"eq\":$1},\"type\":\"on-demand\",\"allocated_storage\":${2:-60}}" | jq '.offers[0] // empty'
}

print_balance() {
    [ -n "${VAST_API_KEY:-}" ] || { echo "balance: (no Vast key)"; return; }
    local u; u=$(vastai show user --raw 2>/dev/null) || { echo "balance: (query failed)"; return; }
    jq -r '"Vast credit: $\(.credit // "?")  (balance field \(.balance // "?"))"' <<<"$u"
    vastai show instances --raw 2>/dev/null | jq -r --arg p "$LABEL_PREFIX" \
        '"live instances: \(length) (ours: \([.[] | select((.label // "") | startswith($p))] | length))" ,
         (.[] | "  \(.id) \(.label // "-") \(.gpu_name) \(.actual_status) $\(.dph_total // 0 | . * 1000 | round / 1000)/h")'
}
