#!/usr/bin/env bash
set -euo pipefail

repo_dir="${1:-$HOME/evidence-first-orchestrator}"
config_dir="$HOME/.config/efo-monitor"
state_dir="$HOME/.local/state/efo-monitor"
begin_marker="# BEGIN EFO_MONITOR_MANAGED"
end_marker="# END EFO_MONITOR_MANAGED"

test -f "$repo_dir/monitor/config.example.json"
command -v crontab >/dev/null
command -v flock >/dev/null

install -d -m 700 "$config_dir" "$state_dir"
if [[ ! -f "$config_dir/config.json" ]]; then
  install -m 600 "$repo_dir/monitor/config.example.json" "$config_dir/config.json"
fi

existing="$(crontab -l 2>/dev/null || true)"
filtered="$(
  printf '%s\n' "$existing" |
    awk -v begin="$begin_marker" -v end="$end_marker" '
      $0 == begin { managed = 1; next }
      $0 == end { managed = 0; next }
      !managed { print }
    '
)"
temporary="$(mktemp)"
trap 'rm -f "$temporary"' EXIT
{
  printf '%s\n' "$filtered"
  printf '%s\n' "$begin_marker"
  printf '%s\n' \
    "*/2 * * * * cd $repo_dir && /usr/bin/flock -n $state_dir/collector.lock /usr/bin/python3 -m monitor.collector --config $config_dir/config.json >> $state_dir/collector.log 2>&1"
  printf '%s\n' "$end_marker"
} >"$temporary"
crontab "$temporary"

cd "$repo_dir"
/usr/bin/python3 -m monitor.collector --config "$config_dir/config.json"
crontab -l
