#!/usr/bin/env bash
set -euo pipefail

[[ -f auth/curl.conf ]] || { echo 'Run setup-local.ps1 first'; exit 1; }
args=(--noproxy '*' --silent --show-error --insecure --max-time 12 --resolve notes.local:443:127.0.0.1)
echo 'HTTP redirect:'
redirect=$(curl --noproxy '*' -sSI --resolve notes.local:80:127.0.0.1 http://notes.local/)
echo "$redirect" | head -n 4
echo "$redirect" | grep -q '301 Moved Permanently'

echo 'Backend identifiers:'
instances=''
for i in {1..20}; do
  current=$(curl "${args[@]}" -D - -o /dev/null https://notes.local/api/health | grep -i '^X-Backend-Instance:')
  echo "$current"
  instances+="$current "
  if [[ "$instances" == *backend-a* && "$instances" == *backend-b* ]]; then break; fi
  sleep 1
done
[[ "$instances" == *backend-a* && "$instances" == *backend-b* ]]

echo 'Failover after stopping backend-a:'
docker compose stop backend-a >/dev/null
trap 'docker compose start backend-a >/dev/null' EXIT
headers=$(curl "${args[@]}" -D - -o /dev/null https://notes.local/api/notes)
echo "$headers" | grep -E -i '^(HTTP/|X-Backend-Instance:)'
echo "$headers" | grep -q ' 200 '
echo "$headers" | grep -qi '^X-Backend-Instance: backend-b'
docker compose start backend-a >/dev/null
trap - EXIT

for path in /admin /admin/; do
  echo "Admin $path without password:"
  code=$(curl "${args[@]}" -o /dev/null -w '%{http_code}' "https://notes.local$path")
  echo "HTTP $code"; [[ "$code" == 401 ]]
  echo "Admin $path with password:"
  code=$(curl "${args[@]}" -K auth/curl.conf -o /dev/null -w '%{http_code}' "https://notes.local$path")
  echo "HTTP $code"; [[ "$code" == 200 ]]
done
echo 'Custom 404:'
code=$(curl "${args[@]}" -o /dev/null -w '%{http_code}' https://notes.local/no-such-page)
echo "HTTP $code"; [[ "$code" == 404 ]]
body=$(curl "${args[@]}" https://notes.local/no-such-page)
[[ "$body" == "$(cat 404.html)" ]]
echo 'Custom 404 body matches 404.html'
echo 'Alias /docs/:'
code=$(curl "${args[@]}" -o /dev/null -w '%{http_code}' https://notes.local/docs/)
echo "HTTP $code"; [[ "$code" == 200 ]]
echo 'Second virtual host:'
other=$(curl --noproxy '*' -ksS --resolve second.local:443:127.0.0.1 https://second.local/)
echo "$other" | head -c 200
[[ "$other" == *'Второй сайт'* ]]
echo
echo 'Unknown virtual host:'
if curl --noproxy '*' -ks --max-time 5 --resolve unknown.local:443:127.0.0.1 https://unknown.local/ -o /dev/null; then
  echo 'Unexpected response for unknown host'; exit 1
else
  echo 'Connection closed without serving either project'
fi
echo 'Rate limit (count of 429 responses):'
count=0
for i in {1..30}; do
  code=$(curl "${args[@]}" -o /dev/null -w '%{http_code}' https://notes.local/api/health)
  if [[ "$code" == 429 ]]; then count=$((count + 1)); fi
done
echo "$count"
[[ "$count" -gt 0 ]]
echo 'All nginx checks passed.'
