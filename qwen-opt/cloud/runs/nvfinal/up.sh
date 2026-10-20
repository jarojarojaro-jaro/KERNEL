#!/usr/bin/env bash
# Rent one Vast offer as an SSH instance with a CUDA devel image, with two independent kill timers.
#   up.sh <offer_id> [--hours N] [--disk GB] [--image IMG] [--go]
# Dry run by default (prints the commands); --go creates the instance and starts spending.
#   --hours N  hard lifetime (default 3). Vast has no max-duration/auto-destroy for on-demand instances
#              (scheduled jobs are only HOURLY/DAILY/WEEKLY repeats of reboot/bid), so:
#              1) local watchdog.sh destroys the instance after N h (runs detached on this server),
#              2) the instance destroys itself after N h + 15 min through the per-instance CONTAINER_API_KEY
#                 (DELETE /api/v0/instances/$CONTAINER_ID/) in case this server or the watchdog dies.
#   --disk GB  default: models of the GPU class + 35 GB (image, two builds, ccache), min 60.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
offer=; hours=3; disk=; image=$IMAGE_DEFAULT
while [ $# -gt 0 ]; do
    case $1 in
        --hours) hours=$2; shift 2 ;;
        --disk) disk=$2; shift 2 ;;
        --image) image=$2; shift 2 ;;
        -h|--help) sed -n 2,11p "$0"; exit 0 ;;
        *) [ -z "$offer" ] || die "unexpected argument $1"; offer=$1; shift ;;
    esac
done
[ -n "$offer" ] || { sed -n 2,11p "$0"; exit 2; }
awk -v h="$hours" 'BEGIN { exit !(h > 0 && h <= 10) }' || die "--hours must be in (0, 10]"

# the offer (read-only lookup, needs no key)
[[ $offer =~ ^[0-9]+$ ]] || die "offer id must be a number"
oj=$(offer_json "$offer" || true)
if [ -n "$oj" ]; then
    gpu=$(jq -r .gpu_name <<<"$oj")
    class=$(gpu_class "$gpu")
    [ "$class" != unknown ] || class=3090
    disk=${disk:-$(est_disk_gb "$class")}
    jq -r --argjson h "$hours" --argjson d "$disk" '
      "offer \(.id): \(.gpu_name) \(.gpu_ram/1024|floor) GB, \(.geolocation), reliability \(.reliability*1000|round/1000), CUDA \(.cuda_max_good), driver \(.driver_version)",
      "  $\(.dph_base*1000|round/1000)/h GPU + storage $\(.storage_cost*1000|round/1000)/GB/month x \($d) GB, bandwidth down $\(.inet_down_cost*1000|round)/TB up $\(.inet_up_cost*1000|round)/TB",
      "  worst case for \($h) h: $\((.dph_base + .storage_cost * $d / 730) * $h * 100 | round / 100) + traffic"' <<<"$oj"
else
    echo "warning: offer $offer not found in search (rented or gone); using defaults" >&2
    gpu=unknown; class=3090; disk=${disk:-$(est_disk_gb 3090)}
fi
date_tag=$(date +%Y%m%d-%H%M)
label="$LABEL_PREFIX-$class-$date_tag-$offer"

# onstart: export the Vast variables for SSH sessions (CONTAINER_ID etc. are not visible there otherwise) and arm
# the on-instance self-destruct timer
onstart=$STATE/onstart-$offer.sh
self_destruct_s=$(awk -v h="$hours" 'BEGIN { printf "%d", h * 3600 + 900 }')
cat > "$onstart" <<EOF
env | grep -E '^(CONTAINER_ID|CONTAINER_API_KEY|VAST_[A-Z0-9_]+|PUBLIC_IPADDR|GPU_COUNT)=' >> /etc/environment
echo "$label" > /root/qwenbench-label
# bench.sh stops starting new work 20 min before this (local watchdog deadline), so results can be collected
echo \$(( \$(date +%s) + $(awk -v h="$hours" 'BEGIN { printf "%d", h * 3600 }') )) > /root/qwenbench-deadline
nohup setsid bash -c 'sleep $self_destruct_s; curl -fsS -X DELETE -H "Authorization: Bearer \$CONTAINER_API_KEY" \
  "https://console.vast.ai/api/v0/instances/\$CONTAINER_ID/"' > /root/self-destruct.log 2>&1 < /dev/null &
EOF
echo "onstart script: $onstart (self-destruct after ${self_destruct_s}s)"

create=(vastai create instance "$offer" --image "$image" --disk "$disk" --ssh --direct --label "$label"
        --cancel-unavail --onstart "$onstart" --raw)
if [ "$GO" != 1 ]; then
    run "${create[@]}"
    run setsid nohup "$RUN_DIR/watchdog.sh" "<instance_id>" "$hours" --go
    echo "then: wait for actual_status=running, print: ssh -i $CLOUD_SSH_KEY -p <port> root@<host>"
    exit 0
fi

need_key
out=$(run "${create[@]}")
echo "$out"
iid=$(python3 -c 'import ast,json,sys; s=sys.stdin.read(); s=s[s.find("{"):]
try: d=json.loads(s)
except Exception: d=ast.literal_eval(s)
print(d.get("new_contract") or "")' <<<"$out")
[ -n "$iid" ] || die "no instance id in the create response"
echo "$iid" > "$STATE/current"
echo "$iid" > "$RUN_DIR/INSTANCE"
jq -n --arg iid "$iid" --arg offer "$offer" --arg gpu "$gpu" --arg class "$class" --arg label "$label" \
      --argjson hours "$hours" --argjson disk "$disk" --arg image "$image" --argjson t "$(date +%s)" \
      '{instance: $iid, offer: $offer, gpu: $gpu, class: $class, label: $label, hours: $hours, disk: $disk,
        image: $image, created: $t, deadline: ($t + $hours * 3600)}' > "$STATE/$iid.json"
setsid nohup "$RUN_DIR/watchdog.sh" "$iid" "$hours" --go > "$STATE/watchdog-$iid.log" 2>&1 < /dev/null &
echo "instance $iid ($label); local watchdog pid $! destroys it at $(date -d "@$(jq -r '.deadline | floor' "$STATE/$iid.json")" +%H:%M) [log state/watchdog-$iid.log]"

for _ in $(seq 90); do
    st=$(inst_json "$iid" | jq -r '.actual_status // "?"')
    [ "$st" = running ] && inst_ssh "$iid" && break
    printf '\r%s status: %s   ' "$(date +%T)" "$st"; sleep 10
done
echo
if [ "${st:-}" = running ]; then
    echo "ssh ${SSH_OPTS[*]} -p $SSH_PORT root@$SSH_HOST"
    echo "next: ./push.sh $iid --go   (bundle + scripts, then bootstrap+bench in the background)"
else
    echo "not running after 15 min (status ${st:-?}); the watchdog still destroys it on time. Check: vastai show instance $iid"
fi
print_balance
