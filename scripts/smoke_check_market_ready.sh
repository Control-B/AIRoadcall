#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://roadcall.ai}"
API_URL="${API_URL:-https://airoadcall-i76ba.ondigitalocean.app/api}"
HEALTH_URL="${HEALTH_URL:-https://airoadcall-i76ba.ondigitalocean.app/health}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-12}"

PAGES=(
  "/"
  "/pricing"
  "/shops/onboarding"
  "/demo"
  "/search"
  "/admin/login"
)

APIS=(
  "/admin/auth-status"
)

status=0

check_url() {
  local url="$1"
  local code
  local total
  code=$(curl -m "$TIMEOUT_SECONDS" -sS -o /dev/null -w "%{http_code}" "$url" || echo "000")
  total=$(curl -m "$TIMEOUT_SECONDS" -sS -o /dev/null -w "%{time_total}" "$url" || echo "-1")

  if [[ "$code" =~ ^2[0-9][0-9]$ || "$code" =~ ^3[0-9][0-9]$ ]]; then
    printf "PASS  %-70s code=%s time=%ss\n" "$url" "$code" "$total"
  else
    printf "FAIL  %-70s code=%s time=%ss\n" "$url" "$code" "$total"
    status=1
  fi
}

echo "== Roadcall market-ready smoke check =="
echo "BASE_URL=$BASE_URL"
echo "API_URL=$API_URL"
echo "HEALTH_URL=$HEALTH_URL"
echo

echo "-- Public pages --"
for path in "${PAGES[@]}"; do
  check_url "${BASE_URL}${path}"
done

echo
echo "-- Backend API --"
check_url "$HEALTH_URL"
for path in "${APIS[@]}"; do
  check_url "${API_URL}${path}"
done

echo
if [[ "$status" -eq 0 ]]; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi

exit "$status"
