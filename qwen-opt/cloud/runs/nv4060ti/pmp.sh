#!/usr/bin/env bash
# ON the box: poor man's profiler of the T server's host threads during a 16k-context decode (report 31 host gaps).
#   pmp.sh <chars> <nsamples> [bin dir]   -> /root/res/prof/pmp.<chars>.txt (raw) + aggregated top frames on stdout
set -uo pipefail
chars=$1; n=$2; B=${3:-/root/bin/T}; P=/root/res/prof; mkdir -p $P; PORT=18762
env LD_LIBRARY_PATH=$B LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_GPU_VERIFY=1 \
    LLAMA_SERVER_REASONING_CONTROL=0 taskset -c 0-2,6-8 $B/llama-server -m /root/models/Qwen3.8-27B-UD-IQ4_XS.gguf -fit off \
    -ngl 99 -t 4 -fa on -ctk q4_0 -ctv q4_0 -c 40960 -np 1 --jinja --cache-ram 8192 --reasoning-effort low --host 127.0.0.1 \
    --port $PORT --no-webui --spec-type draft-mtp --spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0 \
    --spec-draft-vocab /root/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs \
    --spec-mtp-type iq4_xs > $P/pmp.server.log 2>&1 &
spid=$!
for _ in $(seq 300); do curl -sf http://127.0.0.1:$PORT/health > /dev/null && break; sleep 1; done
body=$(python3 -c "
import json; c=open('/root/corpus60k.txt').read()*2
t='Below is a long collection of documents.\n\n'+c[:$chars]+'\n\nWrite a structured summary of the documents above: the main topics, and for each one two or three key points.'
print(json.dumps({'messages':[{'role':'user','content':t}],'max_tokens':1024,'temperature':0.0,'cache_prompt':False,'chat_template_kwargs':{'enable_thinking':False}}))")
curl -sf http://127.0.0.1:$PORT/v1/chat/completions -H 'Content-Type: application/json' -d "$body" > $P/pmp.resp.json &
cpid=$!
# wait for decode: the first "n_gen" progress line or the end of prefill
for _ in $(seq 400); do grep -q 'n_gen =' $P/pmp.server.log && break; sleep 0.5; done
: > $P/pmp.$chars.txt
for i in $(seq $n); do
    gdb -p $spid -batch -ex 'thread apply all bt 14' 2>/dev/null | grep -E '^#|^Thread' >> $P/pmp.$chars.txt
    echo '----' >> $P/pmp.$chars.txt
    sleep 0.15
done
wait $cpid; kill $spid; wait $spid 2>/dev/null
python3 - $P/pmp.$chars.txt <<'EOF'
import collections, re, sys
txt = open(sys.argv[1]).read().split('----')
top = collections.Counter(); stacks = collections.Counter()
for s in txt:
    for th in s.split('Thread ')[1:]:
        fr = re.findall(r'#\d+\s+(?:0x[0-9a-f]+ in )?([^\s(]+)', th)
        if not fr or any(x in fr[0] for x in ('poll', 'epoll', 'futex', 'pthread_cond', 'nanosleep', '__GI___poll', 'clock_nanosleep', 'accept', 'recv')):
            continue
        top[fr[0]] += 1
        stacks[' < '.join(f[:50] for f in fr[:7])] += 1
print('busy-thread top frames:'); [print(f'  {c:4d} {f}') for f, c in top.most_common(20)]
print('stacks:'); [print(f'  {c:4d} {f}') for f, c in stacks.most_common(15)]
EOF
