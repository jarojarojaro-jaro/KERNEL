#!/usr/bin/env bash
# Campaign 67 (NVIDIA on Vast for the Enigma engine): local orchestration of one card class per instance.
#   camp.sh up <card> <offer> <hours> <download_gb> [disk_gb]   rent (ubuntu:24.04, self-destruct + local watchdog)
#   camp.sh push <card>       copy inst/* + cards/<card>.json + corpus, start setup.sh+nv67.py in the background
#   camp.sh ssh <card> [cmd]  run a command on the instance
#   camp.sh log <card>        last lines of the run log
#   camp.sh collect <card>    rsync /root/res -> ~/qwen-opt/cloud/results/nv67-<card>-<date>/
#   camp.sh down <card>       collect, then destroy the instance and print the credit
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
CLOUD=$HOME/qwen-opt/cloud
ARGV=("$@")
cmd=${1:-}; card=${2:-}
[ -n "$cmd" ] && [ -n "$card" ] || { sed -n 2,9p "$0"; exit 2; }
cd "$CLOUD"
set --
. ./lib.sh
ST=$HERE/state
mkdir -p "$ST"
set -- "${ARGV[@]}"
iid() { cat "$ST/$card.iid"; }
# ssh endpoint, cached per instance (parallel calls rate-limit the Vast API); the cache stays local (state/, not in git)
ep() {
    local f=$ST/$card.ep
    if [ -s "$f" ] && [ "$(cut -d' ' -f1 "$f")" = "$(iid)" ]; then read -r _ SSH_HOST SSH_PORT < "$f"; return 0; fi
    inst_ssh "$(iid)" || return 1
    echo "$(iid) $SSH_HOST $SSH_PORT" > "$f"
}
ssh_card() {
    ep || die "no ssh for $(iid)"
    ssh "${SSH_OPTS[@]}" -o LogLevel=ERROR -p "$SSH_PORT" "root@$SSH_HOST" "$@"
}
case $cmd in
    up)
        offer=$3; hours=$4; dl=$5; disk=${6:-70}
        out=$(MAX_DL_COST_PER_GB=${MAX_DL_COST_PER_GB:-0.0014} "$CLOUD/up.sh" "$offer" --hours "$hours" --disk "$disk" \
              --image ubuntu:24.04 --label "qwenbench-nv67-$card" --download-gb "$dl" --go 2>&1) || { echo "$out" | grep -v -E 'ssh |root@'; exit 1; }
        echo "$out" | grep -v -E 'ssh |root@|[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+'
        # parallel rentals: take the id from this up.sh run, not from the shared state/current
        sed -nE 's/^instance ([0-9]+) \(qwenbench-nv67-.*/\1/p' <<<"$out" | head -1 > "$ST/$card.iid"
        [ -s "$ST/$card.iid" ] || die "no instance id for $card"
        echo "$card -> instance $(iid)"
        # push as soon as sshd answers
        for _ in $(seq 30); do ssh_card true 2> /dev/null && break; sleep 10; done
        "$HERE/camp.sh" push "$card"
        ;;
    push)
        ssh_card "mkdir -p /root/nv"
        ep
        # card "files": own engine tarballs etc. (paths relative to this directory), copied next to the card
        mapfile -t extra < <(jq -r '.files[]? // empty' "$HERE/cards/$card.json" | sed "s|^|$HERE/|")
        scp "${SSH_OPTS[@]}" -o LogLevel=ERROR -P "$SSH_PORT" -q "$HERE/inst/nv67.py" "$HERE/inst/setup.sh" \
            "$HERE/inst/graft_mtp.py" "$HERE/cards/$card.json" "$HOME/KERNEL/app/engine/data/corpus.txt" \
            "${extra[@]}" "root@$SSH_HOST:/root/nv/"
        ssh_card "cd /root/nv && nohup setsid bash setup.sh /root/nv/$card.json > /root/run.log 2>&1 < /dev/null & echo started"
        ;;
    engput)  # engput <card> [tags...]: GitHub crawls on the host -> copy official engine tarballs from engcache/ (local
        # download of the same release assets) and install them there (inst/eng_local.sh)
        shift 2
        tags=("$@"); [ ${#tags[@]} -gt 0 ] || tags=(b11856 b12110)
        res=$(jq -r '.res // "/root/res"' "$HERE/cards/$card.json" 2> /dev/null || echo /root/res)
        files=("$HERE/engcache/cudart-llama-b12110-bin-ubuntu-cuda-12.8-x64.tar.gz")
        for t in "${tags[@]}"; do files+=("$HERE/engcache/llama-$t-bin-ubuntu-cuda-12.8-x64.tar.gz"); done
        ssh_card "mkdir -p /root/dl-local /root/nv"
        ep
        scp "${SSH_OPTS[@]}" -o LogLevel=ERROR -P "$SSH_PORT" -q "$HERE/inst/eng_local.sh" "root@$SSH_HOST:/root/nv/"
        scp "${SSH_OPTS[@]}" -o LogLevel=ERROR -P "$SSH_PORT" -q "${files[@]}" "root@$SSH_HOST:/root/dl-local/"
        ssh_card "RES=$res bash /root/nv/eng_local.sh ${tags[*]}"
        ;;
    chain)  # chain <card> <json...> [-- <extra files>]: after the running job, run each card json (own "res" dir) in order
        shift 2
        jsons=(); files=()
        while [ $# -gt 0 ] && [ "$1" != -- ]; do jsons+=("$1"); shift; done
        [ "${1:-}" = -- ] && { shift; files=("$@"); }
        ep
        # a running setup.sh must not be overwritten (bash reads scripts incrementally): the chain gets setup-f.sh
        scp "${SSH_OPTS[@]}" -o LogLevel=ERROR -P "$SSH_PORT" -q "$HERE/inst/setup.sh" "root@$SSH_HOST:/root/nv/setup-f.sh"
        scp "${SSH_OPTS[@]}" -o LogLevel=ERROR -P "$SSH_PORT" -q "$HERE/inst/nv67.py" "$HERE/inst/chain.sh" \
            "$HOME/KERNEL/app/engine/data/corpus.txt" "${jsons[@]}" "${files[@]}" "root@$SSH_HOST:/root/nv/"
        names=$(for j in "${jsons[@]}"; do printf '/root/nv/%s ' "$(basename "$j")"; done)
        ssh_card "nohup setsid bash /root/nv/chain.sh $names >> /root/run.log 2>&1 < /dev/null & echo chained"
        ;;
    ssh) shift 2; ssh_card "$@" ;;
    log) ssh_card "tail -n ${3:-25} /root/run.log" ;;
    collect)
        dst=$CLOUD/results/nv67-$card-$(date +%Y%m%d)
        mkdir -p "$dst"
        ep
        rsync -a -e "ssh ${SSH_OPTS[*]} -o LogLevel=ERROR -p $SSH_PORT" "root@$SSH_HOST:/root/res/" "$dst/" 2> /dev/null
        rsync -a -e "ssh ${SSH_OPTS[*]} -o LogLevel=ERROR -p $SSH_PORT" "root@$SSH_HOST:/root/run.log" "$dst/run.log"
        # final-phase cards write /root/res-<name>/
        for r in $(ssh_card 'ls -d /root/res-* 2> /dev/null'); do
            rsync -a -e "ssh ${SSH_OPTS[*]} -o LogLevel=ERROR -p $SSH_PORT" "root@$SSH_HOST:$r/" "$dst/$(basename "$r")/"
        done
        echo "collected -> $dst"
        ;;
    put)  # put <card> <files...>: copy files to /root/nv/
        shift 2
        ep
        scp "${SSH_OPTS[@]}" -o LogLevel=ERROR -P "$SSH_PORT" -q "$@" "root@$SSH_HOST:/root/nv/"
        ;;
    down)
        "$HERE/camp.sh" collect "$card" || echo "collect failed (instance gone?)"
        "$CLOUD/down.sh" "$(iid)" --go 2>&1 | grep -v -E 'root@|[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\.'
        ;;
    *) die "unknown command $cmd" ;;
esac
