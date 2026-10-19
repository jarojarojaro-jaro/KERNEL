#!/usr/bin/env bash
# Remote BUILD SERVER (CPU-only use of a cheap many-core Vast box) for ~/qwen-opt/tools/rbuild.
#   buildfarm.sh up <offer_id> [--hours N] [--disk GB]   rent (label buildfarm-*, image ubuntu:24.04) + install toolchains
#   buildfarm.sh setup                                  (re)push the scripts and run the remote setup again
#   buildfarm.sh status                                 instance, idle age, ccache stats, credit
#   buildfarm.sh ssh [cmd...]                           shell / command on the build server
#   buildfarm.sh run '<cmd>'                            CPU job there (counts as activity: no idle self-destroy meanwhile)
#   buildfarm.sh down                                   destroy it now
#   buildfarm.sh find [max_$/h]                         offers ranked by effective vCPUs per $ (read-only)
# Kill timers: up.sh's local watchdog (N h, default 7) + on-instance self-destruct (N h + 15 min) + idle-kill.sh on the
# instance (30 min without a build). idle-watch.py skips buildfarm* labels (GPU util 0 is expected here).
# State: state/buildfarm.iid (instance id), state/buildfarm.env (BF_IID, BF_HOST, BF_PORT) used by rbuild.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
BFDIR=$CLOUD_DIR/buildfarm
BF_ENV=$STATE/buildfarm.env
CUDA_LOCAL=$HOME/opt/cuda-12.8

bf_ssh() { ssh "${SSH_OPTS[@]}" -p "$BF_PORT" "root@$BF_HOST" "$@"; }
load_env() { [ -f "$BF_ENV" ] || die "no build server (state/buildfarm.env); run: buildfarm.sh up <offer>"; . "$BF_ENV"; }

# the workstation's -march=native expansion for gcc, one token per line (--param=k=v keeps comma lists intact)
native_flags() {
    local v; v=$(gcc -march=native -E -v - < /dev/null 2>&1)
    grep -m1 '/cc1 ' <<<"$v" | python3 -c '
import shlex, sys
t = shlex.split(sys.stdin.read()); out = []; i = 0
while i < len(t):
    if t[i] == "--param": out.append("--param=" + t[i + 1]); i += 2; continue
    if t[i].startswith("-m") and t[i] != "-mno-red-zone": out.append(t[i])
    i += 1
print("\n".join(out))'
}

# exact toolchain identity, compared between workstation and build server
toolchain_id() {  # run locally or remotely through bash -s
    cat <<'EOF'
/opt/rocm/core-10.0/bin/hipcc --version 2>&1 | grep -E '^(HIP version|AMD clang)'
/opt/rocm/core-10.0/lib/llvm/bin/clang --version | head -1
dpkg-query -W -f '${Package} ${Version}\n' amdrocm-llvm10.0 amdrocm-runtime-dev10.0 amdrocm-blas-dev10.0 amdrocm-blas10.0-gfx1100 amdrocm-hipblas-common-dev10.0 2>/dev/null
/home/jaro/opt/cuda-12.8/bin/nvcc --version | tail -2
ls /home/jaro/opt/cuda-12.8/lib/ | grep -E '^lib(cublas|cublasLt|cudart)\.so\.[0-9.]+$' | LC_ALL=C sort
gcc --version | head -1; g++ --version | head -1; cmake --version | head -1
dpkg-query -W -f '${Package} ${Version}\n' gcc-13 g++-13 libstdc++-13-dev binutils libgomp1 libc6-dev
EOF
}

setup() {
    load_env
    native_flags > "$STATE/buildfarm-native-flags"
    jq -r '"\(.url)#\(.md5)"' "$CUDA_LOCAL"/conda-meta/*.json | sort > "$STATE/buildfarm-cuda-explicit.txt"
    sed -i '1i @EXPLICIT' "$STATE/buildfarm-cuda-explicit.txt"
    bf_ssh mkdir -p /root/bf
    scp -q "${SSH_OPTS[@]}" -P "$BF_PORT" "$BFDIR/setup.sh" "$BFDIR/idle-kill.sh" "$BFDIR/ccache-wrap" "$BFDIR/remote-build.sh" \
        /etc/apt/keyrings/rocm.gpg "root@$BF_HOST:/root/bf/"
    scp -q "${SSH_OPTS[@]}" -P "$BF_PORT" "$STATE/buildfarm-native-flags" "root@$BF_HOST:/root/bf/native-flags"
    scp -q "${SSH_OPTS[@]}" -P "$BF_PORT" "$STATE/buildfarm-cuda-explicit.txt" "root@$BF_HOST:/root/bf/cuda-explicit.txt"
    # detached: a dropped connection must not kill apt halfway
    bf_ssh 'rm -f /root/bf/setup.done; setsid nohup bash -c "/root/bf/setup.sh > /root/bf/setup.log 2>&1; echo \$? > /root/bf/setup.done" < /dev/null > /dev/null 2>&1 &'
    echo "setup running on the build server (log /root/bf/setup.log)"
    local t0; t0=$(date +%s)
    until rc=$(bf_ssh cat /root/bf/setup.done 2>/dev/null); do sleep 20; printf '\r  %d s' $(( $(date +%s) - t0 )); done
    echo
    bf_ssh tail -3 /root/bf/setup.log
    [ "$rc" = 0 ] || die "remote setup failed (rc $rc)"
    echo "setup took $(( $(date +%s) - t0 )) s; comparing toolchains"
    diff <(toolchain_id | bash -s 2>&1) <(toolchain_id | bf_ssh 'bash -s 2>&1' 2>/dev/null) \
        && echo "TOOLCHAIN MATCH (ROCm, LLVM, CUDA, gcc, cmake identical)" \
        || die "toolchain differs from the workstation (diff above: < local, > remote)"
    bf_ssh "nproc; free -g | sed -n 2p; df -h /root | tail -1"
}

cmd=${1:-}; shift || true
case $cmd in
    up)
        offer=${1:?offer id}; shift
        hours=7; disk=50
        while [ $# -gt 0 ]; do case $1 in --hours) hours=$2; shift 2 ;; --disk) disk=$2; shift 2 ;; *) die "unknown $1" ;; esac; done
        need_key
        "$CLOUD_DIR/up.sh" "$offer" --hours "$hours" --disk "$disk" --image ubuntu:24.04 \
            --label "buildfarm-$(date +%Y%m%d-%H%M)" --go
        iid=$(cat "$STATE/buildfarm.iid")
        inst_ssh "$iid" || die "instance $iid has no ssh endpoint"
        j=$(inst_json "$iid")
        BF_JOBS=$(jq -r '.cpu_cores_effective | floor' <<<"$j")    # Vast's allotment, not the host's nproc
        BF_HOST=$SSH_HOST BF_PORT=$SSH_PORT
        for _ in $(seq 6); do bf_ssh true 2>/dev/null && break; sleep 10; done
        if ! bf_ssh true 2>/dev/null; then                         # direct port filtered: use the Vast ssh proxy
            BF_HOST=$(jq -r .ssh_host <<<"$j") BF_PORT=$(jq -r .ssh_port <<<"$j")
            bf_ssh true || die "no ssh to $iid (direct and proxy)"
        fi
        printf 'BF_IID=%s\nBF_HOST=%s\nBF_PORT=%s\nBF_JOBS=%s\n' "$iid" "$BF_HOST" "$BF_PORT" "$BF_JOBS" > "$BF_ENV"
        setup
        ;;
    setup) setup ;;
    status)
        load_env
        echo "build server $BF_IID root@$BF_HOST:$BF_PORT"
        bf_ssh 'echo "idle $(( $(date +%s) - $(stat -c %Y /root/bf/last-activity) )) s (destroys itself at 1800)"; uptime; ccache -s | grep -E "Hits|Misses|Cache size"' || echo "unreachable"
        print_balance
        ;;
    ssh) load_env; bf_ssh "$@" ;;
    run)
        load_env
        bf_ssh "touch /root/bf/last-activity; flock -s /root/bf/active.lock bash -c $(printf %q "$*"); rc=\$?; touch /root/bf/last-activity; exit \$rc"
        ;;
    down)
        load_env; need_key
        vastai destroy instance "$BF_IID" -y
        rm -f "$BF_ENV"
        print_balance
        ;;
    find)
        max=${1:-0.25}
        vastai search offers "num_gpus>=1 reliability>=0.95 rentable=true direct_port_count>=1 cpu_cores_effective>=16 \
cpu_ram>=24 disk_space>=50 inet_down>=200 dph_total<=$max geolocation notin [CN]" --storage 50 -o dph_total --limit 400 --raw |
        jq -r 'map(. + {cpd: (.cpu_cores_effective / .dph_total)}) | sort_by(-.cpd) | .[:12][]
               | [.id, (.dph_total*1000|round/1000), (.cpu_cores_effective|floor), .cpu_name, (.cpu_ram/1000|round),
                  (.inet_down|round), (.inet_down_cost*1000|round), .geolocation, (.reliability*1000|round/1000)] | @tsv' |
        column -t -s $'\t' -N 'id,$/h,vCPU,cpu,RAM_GB,Mbps,$/TB_down,where,rel'
        ;;
    *) sed -n 2,12p "$0"; exit 2 ;;
esac
