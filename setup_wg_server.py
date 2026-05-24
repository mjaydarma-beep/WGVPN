#!/usr/bin/env python3
"""Install and configure WireGuard VPN server on remote Ubuntu host."""

import os
import sys
import paramiko

HOST = "172.245.110.29"
USER = "root"
PASSWORD = os.environ.get("WG_SERVER_PASSWORD", "")
WG_PORT = 51820
SERVER_VPN_IP = "10.8.0.1/24"
CLIENT_VPN_IP = "10.8.0.2/32"

SETUP_SCRIPT = """#!/bin/bash
set -euo pipefail

WG_PORT="${WG_PORT}"
SERVER_VPN_IP="${SERVER_VPN_IP}"
CLIENT_VPN_IP="${CLIENT_VPN_IP}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq wireguard wireguard-tools qrencode iptables curl

mkdir -p /etc/wireguard
chmod 700 /etc/wireguard

if [ ! -f /etc/wireguard/server_private.key ]; then
  wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
  wg genkey | tee /etc/wireguard/client_private.key | wg pubkey > /etc/wireguard/client_public.key
  chmod 600 /etc/wireguard/*.key
fi

SERVER_PRIV=$(cat /etc/wireguard/server_private.key)
SERVER_PUB=$(cat /etc/wireguard/server_public.key)
CLIENT_PRIV=$(cat /etc/wireguard/client_private.key)
CLIENT_PUB=$(cat /etc/wireguard/client_public.key)

MAIN_IF=$(ip -4 route show default | awk '{print $5; exit}')
SERVER_PUBLIC_IP=$(curl -4 -s --max-time 10 ifconfig.me || curl -4 -s --max-time 10 icanhazip.com || hostname -I | awk '{print $1}')

cat > /etc/wireguard/wg0.conf << WGEOF
[Interface]
Address = ${SERVER_VPN_IP}
ListenPort = ${WG_PORT}
PrivateKey = ${SERVER_PRIV}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o ${MAIN_IF} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o ${MAIN_IF} -j MASQUERADE

[Peer]
PublicKey = ${CLIENT_PUB}
AllowedIPs = ${CLIENT_VPN_IP}
WGEOF

grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf 2>/dev/null || echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -w net.ipv4.ip_forward=1 >/dev/null

chmod 600 /etc/wireguard/wg0.conf
systemctl enable wg-quick@wg0
systemctl restart wg-quick@wg0

if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q 'Status: active'; then
  ufw allow "${WG_PORT}/udp" comment 'WireGuard' || true
fi

mkdir -p /root/wireguard-client
cat > /root/wireguard-client/client.conf << CLIENTEOF
[Interface]
PrivateKey = ${CLIENT_PRIV}
Address = 10.8.0.2/32
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = ${SERVER_PUB}
Endpoint = ${SERVER_PUBLIC_IP}:${WG_PORT}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
CLIENTEOF

echo "===WG_SETUP_DONE==="
echo "SERVER_PUBLIC_IP=${SERVER_PUBLIC_IP}"
echo "MAIN_IF=${MAIN_IF}"
wg show
echo "===CLIENT_CONFIG_START==="
cat /root/wireguard-client/client.conf
echo "===CLIENT_CONFIG_END==="
"""


def run_remote(ssh: paramiko.SSHClient, command: str, timeout: int = 600) -> tuple[int, str, str]:
    _, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return exit_code, out, err


def main() -> int:
    print(f"Connecting to {USER}@{HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30, look_for_keys=False, allow_agent=False)
    except Exception as e:
        print(f"SSH connection failed: {e}")
        return 1

    try:
        print("Running WireGuard installation (may take 1-2 minutes)...")
        sftp = ssh.open_sftp()
        remote_path = "/tmp/setup_wg.sh"
        with sftp.file(remote_path, "w") as f:
            f.write(SETUP_SCRIPT)
        sftp.chmod(remote_path, 0o700)
        sftp.close()

        env = f"WG_PORT={WG_PORT} SERVER_VPN_IP={SERVER_VPN_IP} CLIENT_VPN_IP={CLIENT_VPN_IP}"
        code, out, err = run_remote(ssh, f"{env} bash {remote_path}")
        print(out)
        if err:
            print("STDERR:", err, file=sys.stderr)
        if code != 0:
            print(f"Setup failed with exit code {code}")
            return code

        if "===CLIENT_CONFIG_START===" not in out:
            print("Setup may have failed - client config not found in output")
            return 1

        client_conf = out.split("===CLIENT_CONFIG_START===")[1].split("===CLIENT_CONFIG_END===")[0].strip()
        local_dir = os.path.dirname(os.path.abspath(__file__))
        client_path = os.path.join(local_dir, "client.conf")
        with open(client_path, "w", encoding="utf-8") as f:
            f.write(client_conf + "\n")

        print(f"\nClient config saved to: {client_path}")
        print("\nWireGuard server is running. Import client.conf into the WireGuard app on your device.")
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    sys.exit(main())
