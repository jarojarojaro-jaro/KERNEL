#!/usr/bin/env bash
# vast-reaper.sh: systemd --user timer on the Jarvo server, every 2 min (systemd/vast-reaper.{service,timer}).
# Owner 2026-11-19: "KARTY NIGDY NIE MOGĄ STAĆ BEZCZYNNIE". On 19.11 four instances sat idle ~70 min after their tests,
# because the fetch/destroy helpers were started from the agent's tool session and died with it. This runs outside any
# session. For every Vast instance of ours (label qwenbench-* or kernel-*; buildfarm-* is never touched):
#   /root/res/FINISHED (the runner chain ends with it)            -> copy /root/res, destroy, message to the Kernel inbox
#   runner gone without FINISHED (2 checks in a row)              -> same (partial results)
#   runner alive but every GPU < 5% for 5 checks after "ready"   -> same
#   no /root/res/phases.txt 20 min after start (setup never ran)  -> destroy, message
#   not running after 15 min, SSH down 5 checks, age > MAX_AGE    -> destroy (copy first when SSH works), message
# The inbox message (~/kernel/skrzynka/nowe/*-vast.json) starts a Kernel turn that writes up the results and reports to
# the owner, so a finished run always ends with a full update. The instance-side guard (onstart-guard.sh) is the backup
# when this server is down. Test: REAPER_INBOX=/tmp/x REAPER_RES=/tmp/y vast-reaper.sh (with the timer stopped).
set -uo pipefail
export PATH=$HOME/.local/bin:$PATH
D=$(cd "$(dirname "$0")" && pwd)
RES=${REAPER_RES:-$D/reaped}; ST=${REAPER_STATE:-$HOME/.local/state/vast-reaper}; INBOX=${REAPER_INBOX:-$HOME/kernel/skrzynka/nowe}
MAX_AGE=${REAPER_MAX_AGE:-6000}
mkdir -p "$RES" "$ST"
exec 9> "$ST/lock"; flock -n 9 || exit 0
log() { echo "$(date '+%F %T') $*" >> "$ST/reaper.log"; }
S=(-i "$HOME/.ssh/vast_kernel" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$ST/known_hosts"
   -o ConnectTimeout=15 -o BatchMode=yes)

inbox() {  # id label gpu dph age_min reason results_dir
    python3 - "$INBOX" "$@" <<'EOF'
import json, os, sys, time
inbox, iid, label, gpu, dph, age, reason, res = sys.argv[1:]
sys.path.insert(0, os.path.expanduser("~/kernel"))
try:
    import kernel
    czat, watek = kernel.watek_kernela() or ("", "")
except Exception:
    czat, watek = "", ""
os.makedirs(inbox, exist_ok=True)
tekst = (f"Vast reaper (skrypt na serwerze, nie właściciel): instancja {iid} ({label}, {gpu}, ${float(dph):.3f}/h) "
         f"usunięta po {age} min. Powód: {reason}. Wyniki: {res or 'brak (nic do skopiowania)'}. "
         "Zbierz wyniki tej instancji (summ.py z jej katalogu runnera, notatka eksperymentu, KOLEJKA-TESTOW, log, "
         "commit + push) i napisz właścicielowi pełny raport: co wyszło (baseline → teraz → %), koszt, co dalej. "
         "Jeśli w skrzynce są też inne instancje tej samej kampanii, jeden raport na całość.")
p = os.path.join(inbox, f"{time.strftime('%Y%m%d-%H%M%S')}-{iid}-vast.json")
tmp = p + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump({"dopisek": "gpu", "nazwa": "vast", "chat_id": czat, "watek": watek, "message_id": None,
               "czas": time.strftime("%Y-%m-%dT%H:%M:%S"), "media": [], "odpowiedz_na": None, "zrodlo": "vast",
               "tekst": tekst}, f, ensure_ascii=False, indent=1)
os.replace(tmp, p)
EOF
}

now=$(date +%s)
vastai show instances --raw > "$ST/instances.json" 2> "$ST/vastai.err" || { log "vastai show instances failed: $(tail -c 300 "$ST/vastai.err")"; exit 0; }
jq -c '.[] | select((.label // "") | test("^(qwenbench|kernel)-")) | {id, label, st: (.actual_status // ""),
    start: ((.start_date // 0) | floor), dph: (.dph_total // 0), gpu: (.gpu_name // "?"),
    h: ((.public_ipaddr // "") | gsub("\\s"; "")), p: (.ports["22/tcp"][0].HostPort // ""), sh: (.ssh_host // ""), sp: (.ssh_port // "")}' \
    "$ST/instances.json" | while read -r j; do
    id=$(jq -r .id <<<"$j"); label=$(jq -r .label <<<"$j"); st=$(jq -r .st <<<"$j"); gpu=$(jq -r .gpu <<<"$j"); dph=$(jq -r .dph <<<"$j")
    age=$(( now - $(jq -r .start <<<"$j") )); H=$(jq -r .h <<<"$j"); P=$(jq -r .p <<<"$j")
    [ -n "$H" ] && [ -n "$P" ] || { H=$(jq -r .sh <<<"$j"); P=$(jq -r .sp <<<"$j"); }
    C=$ST/$id.cnt; read -r down dead idle 2> /dev/null < "$C" || { down=0 dead=0 idle=0; }
    reason="" fetch=0 probe=""
    if [ "$st" != running ]; then
        [ $age -gt 900 ] && reason="status '$st' po 15 min (nie wystartowała)"
    else
        probe=$(ssh -n "${S[@]}" -p "$P" root@"$H" 'f=0; [ -f /root/res/FINISHED ] && f=1; p=0; [ -f /root/res/phases.txt ] && p=1
            r=0; pgrep -f "[/]root/k114/run" > /dev/null && r=1; y=0; grep -q " ready" /root/res/phases.txt 2> /dev/null && y=1
            u=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2> /dev/null | sort -n | tail -1)
            echo "OK $f $p $r $y ${u:-0}"' 2> /dev/null | grep '^OK ')
        if [ -z "$probe" ]; then
            down=$((down + 1)); [ $down -ge 5 ] && [ $age -gt 900 ] && reason="SSH nie odpowiada od 10 min"
        else
            read -r _ f p r y u <<<"$probe"; down=0
            if [ "$f" = 1 ]; then reason="skończone (FINISHED)"; fetch=1
            elif [ "$p" = 0 ]; then [ $age -gt 1200 ] && reason="runner nie wystartował w 20 min"
            elif [ "$r" = 0 ]; then dead=$((dead + 1)); [ $dead -ge 2 ] && { reason="runner przerwał się bez FINISHED"; fetch=1; }
            else
                dead=0
                if [ "$y" = 1 ] && [ "${u:-0}" -lt 5 ]; then idle=$((idle + 1)); else idle=0; fi
                [ $idle -ge 5 ] && { reason="GPU bezczynna 10 min przy żywym runnerze"; fetch=1; }
            fi
        fi
        [ -z "$reason" ] && [ $age -gt "$MAX_AGE" ] && { reason="limit czasu $((MAX_AGE / 60)) min"; [ -n "$probe" ] && fetch=1; }
    fi
    if [ -z "$reason" ]; then
        echo "$down $dead $idle" > "$C"; continue
    fi
    out=""
    if [ $fetch = 1 ]; then
        out=$RES/$label-$id; mkdir -p "$out"
        timeout 600 scp -q -r "${S[@]}" -P "$P" root@"$H":/root/res/. "$out/" < /dev/null 2>> "$ST/reaper.log" || log "$id: copy incomplete"
    fi
    if vastai destroy instance "$id" -y < /dev/null >> "$ST/reaper.log" 2>&1; then
        log "$id $label ($gpu): destroyed after $((age / 60)) min: $reason${out:+, results $out}"
        rm -f "$C"
        inbox "$id" "$label" "$gpu" "$dph" "$((age / 60))" "$reason" "${out#$HOME/dev/KERNEL/}"
    else
        log "$id: destroy FAILED ($reason), retry next run"
        echo "$down $dead $idle" > "$C"
    fi
done
