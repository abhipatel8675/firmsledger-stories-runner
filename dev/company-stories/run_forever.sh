#!/usr/bin/env bash
cd "$(dirname "$0")/../.."
for b in work/batch-*/; do
  [ -f "$b/DONE" ] && continue
  echo "$(date) start $b"
  bash dev/company-stories/batch.sh "$b" > "$b/run.log" 2>&1 && echo "$(date) done $b" || echo "$(date) FAILED $b (rerun resumes)"
done
echo "$(date) all batches done"
