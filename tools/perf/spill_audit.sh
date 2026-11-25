#!/usr/bin/env bash
# Register-spill audit of a ggml HIP build (after Nib scripts/spill_audit.sh): every gfx1100 code object in the build's
# ggml-hip objects -> per-kernel VGPR/SGPR/LDS/scratch; prints kernels with spills or scratch and, with --base FILE, only
# kernels whose spill/scratch got worse than in FILE (a previous run's --out). Exit 1 on a new spill.
# usage: spill_audit.sh BUILD_DIR [--out FILE] [--base FILE]
set -uo pipefail
B=$1; shift; OUT=""; BASE=""
while [ $# -gt 0 ]; do case $1 in --out) OUT=$2; shift 2;; --base) BASE=$2; shift 2;; *) shift;; esac; done
L=${ROCM_PATH:-/opt/rocm/core-10.0}/lib/llvm/bin; T=${GPU_TARGET:-gfx1100}
W=$(mktemp -d); trap 'rm -rf $W' EXIT
: > $W/all.tsv
for o in $(find "$B" -path "*ggml-hip.dir*" -name "*.o"); do
  "$L/llvm-objcopy" --dump-section .hip_fatbin=$W/f.bin "$o" 2>/dev/null || continue; [ -s $W/f.bin ] || continue
  "$L/clang-offload-bundler" -type=o -unbundle -input=$W/f.bin -targets="hipv4-amdgcn-amd-amdhsa--$T" -output=$W/d.o >/dev/null 2>&1 || continue
  "$L/llvm-readobj" --notes $W/d.o 2>/dev/null | python3 -c "
import sys,re
cur={}
for l in sys.stdin:
    m=re.match(r'\s*\.(name|vgpr_count|sgpr_count|vgpr_spill_count|sgpr_spill_count|private_segment_fixed_size|group_segment_fixed_size):\s*(\S+)',l)
    if not m: continue
    k,v=m.groups()
    if k=='name' and cur.get('name'):
        pass
    cur[k]=v
    if all(x in cur for x in ('name','vgpr_count','vgpr_spill_count','sgpr_spill_count','private_segment_fixed_size')):
        print('\t'.join([cur['name'][:180],cur['vgpr_count'],cur.get('sgpr_count','0'),cur['vgpr_spill_count'],cur['sgpr_spill_count'],cur['private_segment_fixed_size'],cur.get('group_segment_fixed_size','0'),'$(basename $o)']))
        cur={}
" >> $W/all.tsv
  rm -f $W/f.bin $W/d.o
done
n=$(wc -l < $W/all.tsv); bad=$(awk -F'\t' '$4>0||$5>0||$6>0' $W/all.tsv | wc -l)
echo "spill audit $B: $n kernels, $bad with spills/scratch"
[ -n "$OUT" ] && sort -u $W/all.tsv > "$OUT"
if [ -n "$BASE" ] && [ -s "$BASE" ]; then
  python3 - "$BASE" $W/all.tsv <<'PY'
import sys
def rd(p):
    d={}
    for l in open(p):
        f=l.rstrip('\n').split('\t')
        if len(f)>=6: d[f[0]]=(int(f[3]),int(f[4]),int(f[5]),int(f[1]))
    return d
b,c=rd(sys.argv[1]),rd(sys.argv[2]); worse=[]
for k,v in c.items():
    o=b.get(k,(0,0,0,0))
    if v[0]>o[0] or v[1]>o[1] or v[2]>o[2]: worse.append((k,o,v))
for k,o,v in worse[:40]: print(f"NEW/WORSE spill {k[:120]}: vgpr_spill {o[0]}->{v[0]} sgpr_spill {o[1]}->{v[1]} scratch {o[2]}->{v[2]} (vgpr {v[3]})")
print(f"spill audit vs base: {len(worse)} kernels worse"); sys.exit(1 if worse else 0)
PY
else
  awk -F'\t' '$4>0||$5>0||$6>0 {printf "spill %s vgpr=%s vspill=%s sspill=%s scratch=%s\n",substr($1,1,110),$2,$4,$5,$6}' $W/all.tsv | head -30
fi
