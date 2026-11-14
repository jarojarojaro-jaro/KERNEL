#!/usr/bin/env bash
# K-103 collector (detached on jaroserverai): wait for /root/res2/DONE on instance 60698445 (until 22:12 UTC), copy the
# results to ~/qwen-opt/cloud/k103/res, then destroy the instance with down.sh. Log: ~/qwen-opt/cloud/k103/collect.log
cd ~/qwen-opt/cloud
end=1794694080
while [ "$(date +%s)" -lt $end ]; do
    timeout 40 ~/qwen-opt/cloud/k103/k103b-ssh.sh "test -e /root/res2/DONE" >/dev/null 2>&1 && { echo "$(date -u +%T) DONE seen"; break; }
    sleep 60
done
timeout 120 ~/qwen-opt/cloud/k103/k103b-ssh.sh --get /root/res2 ~/qwen-opt/cloud/k103/ >/dev/null 2>&1; echo "$(date -u +%T) copied rc=$?"
ls ~/qwen-opt/cloud/k103/res2 | head -20
cat ~/qwen-opt/cloud/k103/res2/kld.txt; python3 ~/qwen-opt/cloud/k103/summ.py ~/qwen-opt/cloud/k103/res2 > ~/qwen-opt/cloud/k103/summary2.txt 2>&1; cat ~/qwen-opt/cloud/k103/summary2.txt
./down.sh 60698445 --go; echo "$(date -u +%T) down rc=$?"
