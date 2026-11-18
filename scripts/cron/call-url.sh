#!/usr/bin/env bash
# Requests one external URL for a cron job and gives up after a time limit (default 20 minutes).
# Called by /etc/cron.d/portal-api, which scripts/deploy.sh installs from scripts/cron/portal-api.cron.
#
#   bash scripts/cron/call-url.sh <name> <url> [max_seconds]
#
# Every run writes start and result lines to the journal (journalctl -t portal-cron) and to stdout.
# Exit code: 0 on HTTP 2xx/3xx, 1 on timeout, connection error or HTTP >= 400.
set -uo pipefail

name="${1:?usage: call-url.sh <name> <url> [max_seconds]}"
url="${2:?usage: call-url.sh <name> <url> [max_seconds]}"
max_seconds="${3:-1200}"

log() {
  echo "$(date '+%F %T') [$name] $*"
  if command -v logger >/dev/null 2>&1; then
    logger -t portal-cron -- "[$name] $*"
  fi
}

body="$(mktemp)"
errors="$(mktemp)"
trap 'rm -f "$body" "$errors"' EXIT

log "start $url (limit ${max_seconds}s)"
started=$SECONDS

# --max-time covers the whole request (DNS, connect, waiting for the page, download), so the
# call never outlives the limit. The remote PHP script may keep running after we hang up.
http_code="$(
  curl --silent --show-error --location \
    --connect-timeout 30 \
    --max-time "$max_seconds" \
    --output "$body" \
    --write-out '%{http_code}' \
    "$url" 2>"$errors"
)"
curl_exit=$?
elapsed=$((SECONDS - started))
snippet="$(head -c 300 "$body" | tr -s '\r\n\t' '   ')"

if [[ $curl_exit -eq 28 ]]; then
  log "TIMEOUT after ${elapsed}s (limit ${max_seconds}s)"
  exit 1
fi
if [[ $curl_exit -ne 0 ]]; then
  log "FAILED curl exit $curl_exit after ${elapsed}s: $(head -c 300 "$errors" | tr -s '\r\n' '  ')"
  exit 1
fi
if [[ $http_code -ge 400 ]]; then
  log "FAILED HTTP $http_code after ${elapsed}s: $snippet"
  exit 1
fi
log "OK HTTP $http_code in ${elapsed}s: $snippet"
