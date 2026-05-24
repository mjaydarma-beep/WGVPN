#!/usr/bin/env python3
"""Deploy multisite WireGuard hub with LAN routing and WGDashboard."""

import json
import os
import subprocess
import sys
import textwrap
import paramiko

HOST = "172.245.110.29"
USER = "root"
PASSWORD = os.environ.get("WG_SERVER_PASSWORD", "")
WG_PORT = 51820
ENDPOINT = f"{HOST}:{WG_PORT}"
PEERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "peers")

# Hub-and-spoke: server 10.8.0.1, site routers advertise LAN subnets
PEERS = [
    {
        "name": "site1-router",
        "address": "10.8.0.10/32",
        "description": "Site 1 VPN router — LAN 192.168.10.0/24 (gateway 192.168.10.1, CCTV .100-.101)",
        "server_allowed": ["10.8.0.10/32", "192.168.10.0/24"],
        "client_allowed": ["10.8.0.0/24", "192.168.20.0/24"],
        "persistent_keepalive": 25,
        "is_router": True,
        "lan": "192.168.10.0/24",
    },
    {
        "name": "site2-router",
        "address": "10.8.0.20/32",
        "description": "Site 2 VPN router — LAN 192.168.20.0/24 (gateway 192.168.20.1, CCTV .100)",
        "server_allowed": ["10.8.0.20/32", "192.168.20.0/24"],
        "client_allowed": ["10.8.0.0/24", "192.168.10.0/24"],
        "persistent_keepalive": 25,
        "is_router": True,
        "lan": "192.168.20.0/24",
    },
    {
        "name": "phone",
        "address": "10.8.0.50/32",
        "description": "Mobile phone — access all VPN and site LANs (CCTV, etc.)",
        "server_allowed": ["10.8.0.50/32"],
        "client_allowed": ["10.8.0.0/24", "192.168.10.0/24", "192.168.20.0/24"],
        "persistent_keepalive": 25,
        "is_router": False,
    },
    {
        "name": "laptop",
        "address": "10.8.0.51/32",
        "description": "Laptop — access all VPN and site LANs",
        "server_allowed": ["10.8.0.51/32"],
        "client_allowed": ["10.8.0.0/24", "192.168.10.0/24", "192.168.20.0/24"],
        "persistent_keepalive": 25,
        "is_router": False,
    },
]

ROUTER_POSTUP = textwrap.dedent("""
    # Enable forwarding and route VPN traffic to LAN (adjust br-lan to your LAN interface)
    PostUp = sysctl -w net.ipv4.ip_forward=1; iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o br-lan -j MASQUERADE
    PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o br-lan -j MASQUERADE
""").strip()


def ssh_run(ssh, cmd: str, timeout: int = 600) -> tuple[int, str, str]:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    code = stdout.channel.recv_exit_status()
    return code, stdout.read().decode("utf-8", errors="replace"), stderr.read().decode("utf-8", errors="replace")


def wg_keygen(ssh) -> tuple[str, str]:
    code, priv, _ = ssh_run(ssh, "wg genkey")
    if code != 0 or not priv.strip():
        raise RuntimeError("wg genkey failed")
    priv = priv.strip()
    code, pub, _ = ssh_run(ssh, f"echo '{priv}' | wg pubkey")
    if code != 0 or not pub.strip():
        raise RuntimeError("wg pubkey failed")
    return priv, pub.strip()


def build_server_conf(server_priv: str, peer_entries: list[dict]) -> str:
    lines = [
        "[Interface]",
        "Address = 10.8.0.1/24",
        f"ListenPort = {WG_PORT}",
        f"PrivateKey = {server_priv}",
        "PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE",
        "PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE",
        "",
    ]
    for p in peer_entries:
        lines.extend([
            f"# {p['description']}",
            "[Peer]",
            f"PublicKey = {p['public']}",
            f"AllowedIPs = {', '.join(p['server_allowed'])}",
            "",
        ])
    return "\n".join(lines)


def build_client_conf(
    name: str,
    priv: str,
    address: str,
    server_pub: str,
    allowed: list[str],
    keepalive: int | None,
    is_router: bool,
) -> str:
    lines = [
        f"# {name}",
        "[Interface]",
        f"PrivateKey = {priv}",
        f"Address = {address}",
        "DNS = 1.1.1.1, 8.8.8.8",
    ]
    if is_router:
        lines.append(ROUTER_POSTUP)
    lines.extend([
        "",
        "[Peer]",
        f"PublicKey = {server_pub}",
        f"Endpoint = {ENDPOINT}",
        f"AllowedIPs = {', '.join(allowed)}",
    ])
    if keepalive:
        lines.append(f"PersistentKeepalive = {keepalive}")
    return "\n".join(lines) + "\n"


def install_wgdashboard(ssh) -> str:
    """Install WGDashboard for web-based peer management."""
    install_script = r"""#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq git python3 python3-venv python3-pip curl

DASH_DIR="/opt/WGDashboard"
if [ ! -d "$DASH_DIR" ]; then
  git clone --depth 1 https://github.com/donaldzou/WGDashboard.git "$DASH_DIR"
fi

cd "$DASH_DIR/src"
chmod +x wgd.sh
./wgd.sh install << 'WGDINPUT'
y
WGDINPUT

# Allow dashboard through firewall if ufw exists
if command -v ufw >/dev/null 2>&1; then
  ufw allow 10086/tcp comment 'WGDashboard' 2>/dev/null || true
fi

systemctl enable wg-dashboard 2>/dev/null || systemctl enable wgdashboard 2>/dev/null || true
systemctl restart wg-dashboard 2>/dev/null || systemctl restart wgdashboard 2>/dev/null || true
sleep 2
systemctl is-active wg-dashboard 2>/dev/null || systemctl is-active wgdashboard 2>/dev/null || echo dashboard-service-unknown
"""
    code, out, err = ssh_run(ssh, f"bash -s << 'DEPLOY_EOF'\n{install_script}\nDEPLOY_EOF", timeout=900)
    return out + ("\nSTDERR: " + err if err else "")


def main() -> int:
    os.makedirs(PEERS_DIR, exist_ok=True)

    print(f"Connecting to {USER}@{HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30, look_for_keys=False, allow_agent=False)
    except Exception as e:
        print(f"SSH failed: {e}")
        return 1

    try:
        code, server_priv_raw, _ = ssh_run(ssh, "cat /etc/wireguard/server_private.key 2>/dev/null || cat /etc/wireguard/wg0.conf | grep PrivateKey | head -1 | awk '{print $3}'")
        server_priv = server_priv_raw.strip()
        if not server_priv or "=" not in server_priv:
            print("Could not read server private key")
            return 1

        code, server_pub, _ = ssh_run(ssh, f"echo '{server_priv}' | wg pubkey")
        server_pub = server_pub.strip()

        peer_entries = []
        manifest = {"endpoint": ENDPOINT, "server_public_key": server_pub, "peers": []}

        for spec in PEERS:
            print(f"Generating keys for {spec['name']}...")
            priv, pub = wg_keygen(ssh)
            entry = {**spec, "private": priv, "public": pub}
            peer_entries.append(entry)

            conf = build_client_conf(
                spec["name"],
                priv,
                spec["address"],
                server_pub,
                spec["client_allowed"],
                spec.get("persistent_keepalive"),
                spec.get("is_router", False),
            )
            path = os.path.join(PEERS_DIR, f"{spec['name']}.conf")
            with open(path, "w", encoding="utf-8") as f:
                f.write(conf)

            manifest["peers"].append({
                "name": spec["name"],
                "address": spec["address"],
                "public_key": pub,
                "allowed_ips_server": spec["server_allowed"],
                "allowed_ips_client": spec["client_allowed"],
                "description": spec["description"],
                "config_file": f"peers/{spec['name']}.conf",
            })

        server_conf = build_server_conf(server_priv, peer_entries)
        local_server = os.path.join(os.path.dirname(PEERS_DIR), "server-wg0.conf")
        with open(local_server, "w", encoding="utf-8") as f:
            f.write(server_conf)

        manifest_path = os.path.join(os.path.dirname(PEERS_DIR), "peers-manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        print("Deploying wg0.conf to server...")
        sftp = ssh.open_sftp()
        with sftp.file("/etc/wireguard/wg0.conf", "w") as f:
            f.write(server_conf)
        sftp.close()

        code, out, err = ssh_run(ssh, "chmod 600 /etc/wireguard/wg0.conf && systemctl restart wg-quick@wg0 && sleep 1 && wg show")
        print(out)
        if code != 0:
            print("WireGuard restart failed:", err)
            return code

        print("\nInstalling WGDashboard (web UI)...")
        dash_out = install_wgdashboard(ssh)
        print(dash_out)

        print("\n=== Deployment complete ===")
        print(f"Peer configs saved in: {PEERS_DIR}")
        print(f"Manifest: {manifest_path}")
        print(f"\nWGDashboard: http://{HOST}:10086")
        print("  Default login: admin / admin  (change immediately)")
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    sys.exit(main())
