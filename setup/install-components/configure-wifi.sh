#!/usr/bin/env bash
# Disable Wi-Fi power saving persistently and on current NetworkManager devices.
set -euo pipefail

if ! command -v nmcli >/dev/null 2>&1; then
  echo "NetworkManager not installed — skipping Wi-Fi power settings."
  exit 0
fi

if ! command -v iw >/dev/null 2>&1; then
  sudo apt-get install -y iw
fi

sudo mkdir -p /etc/NetworkManager/conf.d
# Sort after Ubuntu's default-wifi-powersave-on.conf.
sudo tee /etc/NetworkManager/conf.d/zz-octo-wifi-performance.conf >/dev/null <<'EOF'
# octo-setup: keep Wi-Fi awake for an always-on machine.
[connection]
wifi.powersave=2
EOF
sudo nmcli general reload conf

# Existing profiles can override the global default.
profiles="$(nmcli -t -f UUID,TYPE connection show)"
while IFS=: read -r uuid type; do
  [ "$type" = 802-11-wireless ] || continue
  sudo nmcli connection modify uuid "$uuid" 802-11-wireless.powersave 2
done <<< "$profiles"

# Apply immediately without disconnecting or restarting NetworkManager.
devices="$(nmcli -t -f DEVICE,TYPE device status)"
while IFS=: read -r device type; do
  [ "$type" = wifi ] || continue
  sudo iw dev "$device" set power_save off
  iw dev "$device" get power_save
done <<< "$devices"
echo "Wi-Fi power saving disabled; setting persists across reconnects and reboots."
