#!/usr/bin/env bash
set -euo pipefail

NEWS_URL=https://43.162.115.148/
cpus=$(nproc)
memory_kib=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
available_kib=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
disk_kib=$(df --output=avail / | tail -n 1 | tr -d ' ')
news_status=$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' "$NEWS_URL")

printf 'CPUs: %s\nRAM KiB: %s\nAvailable RAM KiB: %s\nAvailable disk KiB: %s\nNews HTTP: %s\n' \
  "$cpus" "$memory_kib" "$available_kib" "$disk_kib" "$news_status"

test "$cpus" -ge 2
# A marketed 4 GB VPS commonly reports roughly 3.6 GiB usable RAM.
test "$memory_kib" -ge 3500000
test "$available_kib" -ge 1572864
test "$disk_kib" -ge 15728640
test "$news_status" = 200
test "$(systemctl is-active finance-observatory)" = active
test "$(systemctl is-active caddy)" = active
! ss -ltn | grep -Eq ':(3001|8443)[[:space:]]'

echo 'Preflight gates passed.'

