#!/bin/sh
set -eu

run_pipeline() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] starting AI news pipeline"
  cd /app/apps/backend
  PYTHONPATH=. python -m app.scripts.run_news_pipeline_job
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] finished AI news pipeline"
}

if [ "${RUN_ON_STARTUP:-false}" = "true" ]; then
  run_pipeline || true
fi

while :; do
  now_epoch=$(date +%s)
  target_time="${AI_NEWS_GENERATION_TIME:-08:30:00}"
  today=$(date +%Y-%m-%d)
  target_epoch=$(date -j -f '%Y-%m-%d %H:%M:%S' "$today $target_time" +%s 2>/dev/null || date -d "$today $target_time" +%s)
  if [ "$target_epoch" -le "$now_epoch" ]; then
    tomorrow=$(date -v+1d +%Y-%m-%d 2>/dev/null || date -d tomorrow +%Y-%m-%d)
    target_epoch=$(date -j -f '%Y-%m-%d %H:%M:%S' "$tomorrow $target_time" +%s 2>/dev/null || date -d "$tomorrow $target_time" +%s)
  fi
  sleep_seconds=$((target_epoch - now_epoch))
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] next AI news pipeline at ${target_time} ${NEWS_SCHEDULE_TIMEZONE:-Asia/Seoul} in ${sleep_seconds}s"
  sleep "$sleep_seconds"
  run_pipeline || echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] AI news pipeline failed; scheduler will retry tomorrow"
done
