#!/usr/bin/env bash
# K-103 collector (detached on jaroserverai): wait for /root/res/DONE on instance 60693822 (until 22:12 UTC), copy the
# results to ~/qwen-opt/cloud/k103/res, then destroy the instance with down.sh. Log: ~/qwen-opt/cloud/k103/collect.log
cd ~/qwen-opt/cloud
end=1794694320
while [ "$(date +%s)" -lt $end ]; do
    timeout 40 /tmp/k103-ssh.sh "test -e /root/res/DONE" >/dev/null 2>&1 && { echo "$(date -u +%T) DONE seen"; break; }
    sleep 60
done
timeout 120 /tmp/k103-ssh.sh --get /root/res ~/qwen-opt/cloud/k103/ >/dev/null 2>&1; echo "$(date -u +%T) copied rc=$?"
ls ~/qwen-opt/cloud/k103/res | head -20
python3 ~/qwen-opt/cloud/k103/summ.py ~/qwen-opt/cloud/k103/res > ~/qwen-opt/cloud/k103/summary.txt 2>&1; cat ~/qwen-opt/cloud/k103/summary.txt
./down.sh 60693822 --go; echo "$(date -u +%T) down rc=$?"
