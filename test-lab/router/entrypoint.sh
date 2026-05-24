#!/bin/bash
set -euo pipefail

LAN_IF="${LAN_IF:-eth1}"
CONF_SRC="${CONF_SRC:-/wg/peer.conf}"

if [[ ! -f "$CONF_SRC" ]]; then
  echo "Missing WireGuard config at $CONF_SRC"
  exit 1
fi

mkdir -p /etc/wireguard
sed "s/br-lan/${LAN_IF}/g" "$CONF_SRC" > /etc/wireguard/wg0.conf
chmod 600 /etc/wireguard/wg0.conf

sysctl -w net.ipv4.ip_forward=1 >/dev/null

echo "[sim] Bringing up WireGuard..."
wg-quick up wg0

if [[ -n "${LAN_CIDR:-}" ]]; then
  ip link set "$LAN_IF" up 2>/dev/null || true
  ip addr add "$LAN_CIDR" dev "$LAN_IF" 2>/dev/null || true
fi

echo "[sim] WireGuard up. LAN=$LAN_IF ${LAN_CIDR:-}"
wg show
echo "[sim] Ready — leave container running."
exec sleep infinity
