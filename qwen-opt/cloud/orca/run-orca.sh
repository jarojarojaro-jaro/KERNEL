#!/usr/bin/env bash
# One-command OrcaCyber-3090 campaign: rent the offer, push the harness, run setup + orca.sh detached.
#   run-orca.sh [--go] [--hours 4] [--offer 57039731] [--disk 100]
# Dry run by default. The offer must be a paid-traffic host only with --allow-paid-traffic (up.sh guard);
# here the download cost is checked and printed, then passed explicitly.
set -euo pipefail
. "$(dirname "$0")/../lib.sh"
offer=${OFFER:-57039731}; hours=${HOURS:-4}; disk=${DISK:-100}; max_dph=${MAX_DPH:-0.40}
for a in "$@"; do :; done
while [ $# -gt 0 ]; do
    case $1 in
        --go) GO=1; shift ;;
        --hours) hours=$2; shift 2 ;;
        --offer) offer=$2; shift 2 ;;
        --disk) disk=$2; shift 2 ;;
        *) die "unknown argument $1" ;;
    esac
done
[[ $offer =~ ^[0-9]+$ ]] || die "offer id must be a number"
oj=$(offer_json "$offer") || die "offer $offer not found"
jq -r '"offer \(.id): \(.gpu_name) \(.gpu_ram/1024|floor) GB, \(.geolocation), rel \(.reliability), CUDA \(.cuda_max_good), driver \(.driver_version)",
 "  $\(.dph_base*1000|round/1000)/h + storage $\(.storage_cost*1000|round/1000)/GB/mo; download $\(.inet_down_cost*1000|round/1000)/GB (\(.inet_down|round) Mbps)",
 "  100 GB disk -> $\(( .dph_base + .storage_cost * 100 / 730 ) * 1000 | round / 1000)/h; 25 GB download -> $\(.inet_down_cost * 25 | . * 100 | round / 100)"' <<<"$oj"
awk -v p="$(jq -r .dph_base <<<"$oj")" -v m="$max_dph" 'BEGIN { exit !(p <= m) }' \
    || die "GPU price above \$$max_dph/h (MAX_DPH)"

# staging: scripts + header-only models.tsv (bootstrap must not pull the other model set)
stage=$STATE/orca-stage
rm -rf "$stage"; mkdir -p "$stage"
cp "$CLOUD_DIR/bootstrap.sh" "$CLOUD_DIR/../spec_sweep.py" "$stage/"
cp "$CLOUD_DIR/orca/"*.sh "$CLOUD_DIR/orca/"*.py "$CLOUD_DIR/orca/models-orca.tsv" "$stage/"
head -1 "$CLOUD_DIR/models.tsv" > "$stage/models.tsv"
cp "$HOME/models/draft/draft_vocab_qwen38.txt" "$stage/"
repo=${LLAMA_REPO:-$HOME/llama-master}; base=e60eff95fda7b6e46bf402a8e9f1e86d88ab29c8
git -C "$repo" bundle create "$stage/llama-fork.bundle" "$base..${BRANCH:-topka}"
echo "fork: ${BRANCH:-topka} @ $(git -C "$repo" rev-parse --short "${BRANCH:-topka}"), bundle $(du -h "$stage/llama-fork.bundle" | cut -f1)"

if [ "$GO" != 1 ]; then
    echo "[dry-run] $CLOUD_DIR/up.sh $offer --hours $hours --disk $disk --download-gb 25 --allow-paid-traffic --label orca3090-$(date +%Y%m%d) --go"
    echo "[dry-run] scp $stage/* -> root@<host>:/root/cloud/"
    echo "[dry-run] ssh ... 'cd /root/cloud && setsid nohup bash -c \"./setup-orca.sh && ./orca.sh\" > /root/run.log 2>&1 &'"
    exit 0
fi

need_key
"$CLOUD_DIR/up.sh" "$offer" --hours "$hours" --disk "$disk" --download-gb 25 --allow-paid-traffic \
    --label "orca3090-$(date +%Y%m%d-%H%M)" --go
iid=$(inst_id)
inst_ssh "$iid" || die "no ssh endpoint for $iid"
echo "instance $iid -> $SSH_HOST:$SSH_PORT"

ssh "${SSH_OPTS[@]}" -p "$SSH_PORT" "root@$SSH_HOST" 'rm -rf /root/cloud; mkdir -p /root/cloud'
scp "${SSH_OPTS[@]}" -P "$SSH_PORT" "$stage"/* "root@$SSH_HOST:/root/cloud/"
# HF token (repo is gated:auto): stdin only, 600, download-orca.sh shreds it after the sha256 check
if [ -s "$HOME/.cache/huggingface/token" ]; then
    ssh "${SSH_OPTS[@]}" -p "$SSH_PORT" "root@$SSH_HOST" 'umask 077; cat > /root/.hf_token && chmod 600 /root/.hf_token' \
        < "$HOME/.cache/huggingface/token"
else
    die "no local HF token in ~/.cache/huggingface/token (repo is gated)"
fi
ssh "${SSH_OPTS[@]}" -p "$SSH_PORT" "root@$SSH_HOST" \
    "cd /root/cloud && chmod +x *.sh && setsid nohup bash -c './setup-orca.sh && ./orca.sh' > /root/run.log 2>&1 < /dev/null & echo started"
echo "follow: ssh ${SSH_OPTS[*]} -p $SSH_PORT root@$SSH_HOST tail -f /root/run.log"
