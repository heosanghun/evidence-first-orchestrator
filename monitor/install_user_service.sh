#!/usr/bin/env bash
set -euo pipefail

repo_dir="${1:-$HOME/evidence-first-orchestrator}"
config_dir="$HOME/.config/efo-monitor"
state_dir="$HOME/.local/state/efo-monitor"
unit_dir="$HOME/.config/systemd/user"

test -f "$repo_dir/monitor/config.example.json"
install -d -m 700 "$config_dir" "$state_dir"
install -d -m 755 "$unit_dir"

if [[ ! -f "$config_dir/config.json" ]]; then
  install -m 600 "$repo_dir/monitor/config.example.json" "$config_dir/config.json"
fi

install -m 644 "$repo_dir/monitor/efo-monitor.service" "$unit_dir/efo-monitor.service"
install -m 644 "$repo_dir/monitor/efo-monitor.timer" "$unit_dir/efo-monitor.timer"

systemctl --user daemon-reload
systemctl --user enable --now efo-monitor.timer
systemctl --user start efo-monitor.service
systemctl --user --no-pager status efo-monitor.timer
