# Multisite WireGuard VPN

**Real-world install guide:** [INSTALL.md](INSTALL.md) — hub VPS, site routers, phones, CCTV, firewall, testing.

Hub server: **172.245.110.29** · UDP **51820**  
Web dashboard: **http://172.245.110.29:10086** (login `admin` / `admin` — change on first login)

## Network layout

```
                    ┌─────────────────────────────┐
                    │  Hub 172.245.110.29 (wg0)   │
                    │  VPN: 10.8.0.1/24           │
                    └──────────┬──────────────────┘
           ┌───────────────────┼───────────────────┐
           │                   │                   │
    site1-router          site2-router         phone / laptop
    10.8.0.10             10.8.0.20           10.8.0.50 / .51
           │                   │
    192.168.10.0/24      192.168.20.0/24
    GW 192.168.10.1      GW 192.168.20.1
    CCTV .100-.101        CCTV .100
```

| Peer | WireGuard IP | Role | LAN reachable |
|------|--------------|------|----------------|
| **site1-router** | 10.8.0.10 | Site 1 VPN router | 192.168.10.0/24 |
| **site2-router** | 10.8.0.20 | Site 2 VPN router | 192.168.20.0/24 |
| **phone** | 10.8.0.50 | Mobile | All sites + VPN |
| **laptop** | 10.8.0.51 | Laptop | All sites + VPN |

## Setup order

1. **Hub** — already configured on the server (`wg0`).
2. **Site routers** — import `peers/site1-router.conf` and `peers/site2-router.conf` on each VPN router.
3. **Phones / laptops** — import `peers/phone.conf` or `peers/laptop.conf`.

Site routers must be online for other peers to reach that site’s LAN.

## Access CCTV from your phone

1. Import **`peers/phone.conf`** into the WireGuard app.
2. Turn the tunnel **on**.
3. Open the camera app or browser:
   - Site 1: `http://192.168.10.100` / `.101`
   - Site 2: `http://192.168.20.100`

Traffic uses split routing: only `10.8.0.0/24`, `192.168.10.0/24`, and `192.168.20.0/24` go through the VPN (not your full internet).

## Site router notes (OpenWrt / Linux)

Each router config includes `PostUp` rules for forwarding and NAT. Adjust **`br-lan`** to your LAN interface name (`eth1`, `lan`, etc.).

On the router you also need:

- **IP forwarding** enabled (often `sysctl net.ipv4.ip_forward=1`).
- Firewall: allow **forward** from `wg0` → LAN and LAN → `wg0`.
- WireGuard interface bound; no duplicate tunnel on the same port.

For **OpenWrt**: Network → Interfaces → add WireGuard, paste the `[Interface]` and `[Peer]` sections, or upload the `.conf` if your build supports it.

## WGDashboard (manage peers in browser)

| | |
|---|---|
| URL | http://172.245.110.29:10086 |
| Default login | `admin` / `admin` |
| Service | `systemctl status wg-dashboard` |

Use the dashboard to add peers, view status, download client configs, and see QR codes.  
If you add peers in the UI, set **Allowed IPs** on the hub for site routers to include their LAN subnet (e.g. `10.8.0.10/32, 192.168.10.0/24`).

Open **TCP 10086** in your VPS firewall if the UI is not reachable from your PC.

## Config files

| File | Use |
|------|-----|
| `peers/site1-router.conf` | Site 1 VPN router |
| `peers/site2-router.conf` | Site 2 VPN router |
| `peers/phone.conf` | Phone |
| `peers/laptop.conf` | Laptop |
| `server-wg0.conf` | Hub config (reference) |
| `peers-manifest.json` | Peer keys and IP map |

## Firewall (VPS provider)

- **UDP 51820** — WireGuard
- **TCP 10086** — WGDashboard (optional, restrict by IP if possible)

## Add more peers

**Option A — Dashboard:** http://172.245.110.29:10086 → add peer → set Allowed IPs (include LAN subnets for routers).

**Option B — Script:** edit `deploy_multisite.py`, add a peer entry, run:

```powershell
$env:WG_SERVER_PASSWORD = "your-root-password"
python deploy_multisite.py
```

For a new **site router**, give it a unique `10.8.0.x` address and set `server_allowed` to include its LAN (e.g. `192.168.30.0/24`). Update other peers’ `client_allowed` to include that LAN.

## Test WAN + LAN without real routers

Use the Docker lab in **`test-lab/`** — simulates both site VPN routers and fake CCTV at `192.168.10.100` and `192.168.20.100`. See `test-lab/README.md`.

## Security

- Change the root password and dashboard admin password.
- Do not commit `.conf` files or passwords to public git repos.
- Restrict dashboard port 10086 to your IP if possible.
