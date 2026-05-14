#!/bin/sh
set -eu

run_pipeline() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] starting AI news pipeline"
  cd /app/apps/backend
  PYTHONPATH=. python -m app.scripts.run_news_pipeline_job
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] finished AI news pipeline"
}

run_pipeline_with_retries() {
  max_attempts="${PIPELINE_MAX_ATTEMPTS:-2}"
  retry_delay="${PIPELINE_RETRY_DELAY_SECONDS:-60}"
  attempt=1

  while [ "$attempt" -le "$max_attempts" ]; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] AI news pipeline attempt ${attempt}/${max_attempts}"
    if run_pipeline; then
      return 0
    fi

    if [ "$attempt" -ge "$max_attempts" ]; then
      echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] AI news pipeline failed after ${max_attempts} attempts"
      return 1
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] retrying AI news pipeline in ${retry_delay}s"
    sleep "$retry_delay"
    attempt=$((attempt + 1))
  done
}

if [ "${RUN_ON_STARTUP:-false}" = "true" ]; then
  run_pipeline_with_retries || exit 1
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
  run_pipeline_with_retries || echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] AI news pipeline failed; scheduler will retry at the next scheduled run"
done
