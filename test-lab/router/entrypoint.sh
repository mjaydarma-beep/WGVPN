#!/bin/bash
set -euo pipefail

LAN_IF="${LAN_IF:-eth0}"
CONF_SRC="${CONF_SRC:-/wg/peer.conf}"

if [[ ! -f "$CONF_SRC" ]]; then
  echo "Missing WireGuard config at $CONF_SRC"
  exit 1
fi

mkdir -p /etc/wireguard
sed "s/br-lan/${LAN_IF}/g" "$CONF_SRC" > /etc/wireguard/wg0.conf
chmod 600 /etc/wireguard/wg0.conf

# sysctl may fail on Docker Desktop; compose sysctls or privileged mode apply forwarding
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true

echo "[sim] Bringing up WireGuard..."
wg-quick up wg0 || { echo "[sim] wg-quick failed"; cat /etc/wireguard/wg0.conf; exit 1; }

# Ensure LAN forwarding (PostUp may target wrong iface; LAN is eth0 in this lab)
iptables -C FORWARD -i wg0 -o "$LAN_IF" -j ACCEPT 2>/dev/null || iptables -A FORWARD -i wg0 -o "$LAN_IF" -j ACCEPT
iptables -C FORWARD -i "$LAN_IF" -o wg0 -j ACCEPT 2>/dev/null || iptables -A FORWARD -i "$LAN_IF" -o wg0 -j ACCEPT
iptables -t nat -C POSTROUTING -o "$LAN_IF" -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -o "$LAN_IF" -j MASQUERADE

echo "[sim] WireGuard up. LAN=$LAN_IF ${LAN_CIDR:-}"
wg show
echo "[sim] Ready — leave container running."
exec sleep infinity
