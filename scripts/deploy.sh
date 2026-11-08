#!/usr/bin/env bash
# Deploy of portal-api on the EC2 host. Run by GitHub Actions (.github/workflows/ci-cd.yml)
# after `git pull`, as the `ubuntu` user, from the repository root:
#
#   bash scripts/deploy.sh [expected_commit_sha]
#
# Environment:
#   COLLECTSTATIC=true   force `collectstatic` (otherwise only when requirements.txt changed)
#   APP_DIR, SERVICE, HEALTH_URL   override the defaults below
set -euo pipefail

APP_DIR="${APP_DIR:-/home/portal-api}"
SERVICE="${SERVICE:-portal-api}"
HEALTH_URL="${HEALTH_URL:-https://apiportal.rodrigolim.com.br/api/v1/health/}"
EXPECTED_SHA="${1:-}"

cd "$APP_DIR"

# manage.py as root would leave root-owned cache files behind (see ARQUITETURA.md, deploy section).
if [[ "$(id -un)" == "root" ]]; then
  echo "deploy.sh must run as the service user (ubuntu), not root" >&2
  exit 1
fi

CURRENT_SHA="$(git rev-parse HEAD)"
PREVIOUS_SHA="$(git rev-parse 'HEAD@{1}' 2>/dev/null || echo "$CURRENT_SHA")"
if [[ -n "$EXPECTED_SHA" && "$CURRENT_SHA" != "$EXPECTED_SHA" ]]; then
  echo "HEAD is $CURRENT_SHA but the workflow expected $EXPECTED_SHA" >&2
  exit 1
fi
echo "Deploying $CURRENT_SHA (previous $PREVIOUS_SHA)"

echo "==> pip install"
venv/bin/pip install -q -r requirements.txt

echo "==> migrate"
venv/bin/python manage.py migrate --noinput

# collectstatic uploads to S3 and takes over a minute; static files only change with new packages.
if [[ "${COLLECTSTATIC:-}" == "true" ]] || ! git diff --quiet "$PREVIOUS_SHA" "$CURRENT_SHA" -- requirements.txt; then
  echo "==> collectstatic"
  venv/bin/python manage.py collectstatic --noinput
else
  echo "==> collectstatic skipped (requirements.txt unchanged)"
fi

echo "==> restart $SERVICE"
sudo -n systemctl restart "$SERVICE"

echo "==> health check $HEALTH_URL"
for _ in $(seq 1 20); do
  if curl -fsS -m 5 "$HEALTH_URL" >/dev/null; then
    echo "Deploy OK: $CURRENT_SHA"
    exit 0
  fi
  sleep 3
done

echo "Health check failed after restart" >&2
sudo -n systemctl status "$SERVICE" --no-pager | tail -n 20 >&2 || true
sudo -n journalctl -u "$SERVICE" --no-pager -n 40 >&2 || true
exit 1
