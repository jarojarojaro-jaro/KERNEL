#!/bin/bash
# K-013 kernel level: MUL_MAT q4_K / q6_K with n = 1,5,8,16 on the production fork vs upstream few-row (#31533 HIP port)
R=/opt/rocm/core-10.0/lib; export GGML_HIP_PM4=0
for B in ~/wt/l1-cachesave/build-hip/bin ~/wt/fewrow-hip/build-hip/bin ~/wt/fewrow-hip/build/bin; do
  [ -x $B/test-backend-ops ] || continue
  echo "== $B"
  LD_LIBRARY_PATH=$B:$R timeout 280 $B/test-backend-ops perf -o MUL_MAT 2>&1 | grep -E "MUL_MAT\(type_a=(q4_K|q6_K),type_b=f32,m=[0-9]+,n=(1|2|4|5|8|16)," | sed -E 's/ +/ /g' | head -40
done
