#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/../.."
B=${1%/}/
S=dev/company-stories
[ -f "$B/DONE" ] && exit 0
python3 -u $S/fast.py "$B/pages" &&
python3 $S/collect.py "$B" &&
python3 $S/fix.py "$B/pages" &&
python3 $S/collect.py "$B" &&
OUT="$B" python3 -u $S/verify.py &&
python3 $S/strip.py "$B" &&
python3 $S/make_sql.py "$B" &&
touch "$B/DONE"
