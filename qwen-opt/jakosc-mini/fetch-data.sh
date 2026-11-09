#!/usr/bin/env bash
# jakość-mini: download the benchmark question files (data only, ~10 MB) at the pinned revisions into data/ and check
# them against data/SHA256SUMS. Only needed to rebuild subsets (run.py subsets); a run needs only subsets/.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)/data
dl() {  # repo revision file-in-repo local-file
    mkdir -p "$(dirname "$D/$4")"
    [ -s "$D/$4" ] || curl -sfL -m 600 -o "$D/$4" "https://huggingface.co/datasets/$1/resolve/$2/$3"
}
dl openai/gsm8k 740312add88f781978c0658806c59bc2815b9866 main/test-00000-of-00001.parquet gsm8k/test.parquet
dl TIGER-Lab/MMLU-Pro b189ec765aa7ed75c8acfea42df31fdae71f97be data/test-00000-of-00001.parquet mmlu_pro/test.parquet
dl CohereLabs/Global-MMLU 0e619dbeb34206cd48705a1a0ea7fb21cae09993 pl/test-00000-of-00001.parquet global_mmlu_pl/test.parquet
for c in simple multiple parallel; do
    for p in "" possible_answer/; do
        dl gorilla-llm/Berkeley-Function-Calling-Leaderboard 61fc0608cfd831fcfbbaa676ebdfef0ed963eeda \
            "${p}BFCL_v3_$c.json" "bfcl/${p}BFCL_v3_$c.json"
    done
done
cd "$D" && sha256sum -c --quiet SHA256SUMS && echo "data OK ($D)"
