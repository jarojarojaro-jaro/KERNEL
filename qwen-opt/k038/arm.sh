#!/usr/bin/env bash
# K-038 (speculation flag search) one arm: production topka-q70 config (qprep/srv.sh) with arm switches on top, the
# qprep-spec build for every arm (its new switches stay off, so it runs the production code path).
#   arm.sh LABEL dev     [VAR=VALUE ...]   screening: spec_sweep T=1 seeds 1,2 + copy_bench short T=0 + mvs T=0
#   arm.sh LABEL holdout [VAR=VALUE ...|@winner]   sealed set (factory/sealed, never used for selection): T=1 seeds
#                                          1,2,3 + T=0 seed 1; @winner = the VAR=VALUE lines of k038/winner.env
# VAR=VALUE: any srv.sh/server env (GGML_HIP_PM4_MIN_DISPATCH=32, LLAMA_SPEC_LOOKUP_MMIN=8, KVD=q8_0, ...); none = production.
# usage from the GPU queue only.
set -u
label=$1; kind=$2; shift 2
. "$HOME/qwen-opt/qprep/srv.sh"
trap srv_kill EXIT
d=$HOME/qwen-opt/k038
vars=("$@")
if [ "${vars[0]:-}" = @winner ]; then
    [ -s "$d/winner.env" ] || { echo "$label: no $d/winner.env (write the screening winner there first)"; exit 2; }
    mapfile -t vars < <(grep -E '^[A-Z_0-9]+=' "$d/winner.env")
fi
for v in "${vars[@]}"; do export "$v"; done
echo "$label: $kind ${vars[*]:-production}"
dir=$d/logs
srv_start "$label" "$dir" || exit 1
py=$HOME/qwen-opt/.venv/bin/python
cd "$dir"
case $kind in
    dev)
        taskset -c 6-9 "$py" "$HOME/qwen-opt/spec_sweep.py" --label "$label" --port "$PORT" --temps 1.0 --seeds 1,2 --tokens 400
        taskset -c 6-9 "$py" "$HOME/qwen-opt/lookup/copy_bench.py" --label "$label" --port "$PORT" --out "$dir/copy_bench.jsonl" \
            --set short --temps 0.0 --tokens 512
        taskset -c 6-9 "$py" "$HOME/qwen-opt/lookup/copy_bench.py" --label "$label" --port "$PORT" --out "$dir/copy_bench.jsonl" \
            --set mvs --temps 0.0 --tokens 1024 ;;
    holdout)
        taskset -c 6-9 "$py" "$d/sealed_bench.py" --label "$label" --port "$PORT" --temps 1.0,0.0 --seeds 1,2,3 \
            --out "$dir/sealed.jsonl" ;;
    *) echo "kind dev|holdout" >&2; exit 2 ;;
esac
srv_stop
grep -h "context lookup:" "$dir/$label.server.log" | tail -1
