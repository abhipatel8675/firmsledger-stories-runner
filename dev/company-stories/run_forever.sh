#!/usr/bin/env bash
cd "$(dirname "$0")/../.."
for b in work/batch-*/; do
  [ -f "$b/DONE" ] && continue
  echo "$(date) start $b"
  bash dev/company-stories/batch.sh "$b" > "$b/run.log" 2>&1
  code=$?
  if [ $code -eq 0 ]; then echo "$(date) done $b"
  elif [ $code -eq 3 ]; then echo "$(date) API failing in $b - stopping; next run resumes"; exit 1
  else echo "$(date) FAILED $b (code $code) - skipping to next batch; it will be retried next run"; tail -5 "$b/run.log"
  fi
done
echo "$(date) pass finished"
