# VPN router & LAN test lab

Simulates **two site VPN routers** + **fake CCTV** web pages, connected to your real hub `172.245.110.29`.

## What it simulates

| Container | Role | LAN |
|-----------|------|-----|
| `wg-site1-router` | Site 1 VPN router (peer `10.8.0.10`) | 192.168.10.0/24 |
| `wg-site1-cctv` | Fake camera | 192.168.10.100 |
| `wg-site2-router` | Site 2 VPN router (peer `10.8.0.20`) | 192.168.20.0/24 |
| `wg-site2-cctv` | Fake camera | 192.168.20.100 |

Your **phone/PC** uses `peers/phone.conf` as the real client (not in Docker).

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows)
- Hub server online with peers already configured
- `peers/site1-router.conf` and `site2-router.conf` present (from deploy)

## Start simulators

```powershell
cd d:\VPN_WG\test-lab
docker compose up -d --build
```

Check routers joined the hub:

```powershell
docker exec wg-site1-router wg show
docker exec wg-site2-router wg show
```

You should see a **latest handshake** for each.

## Test as “phone” (your Windows PC)

1. Install [WireGuard for Windows](https://www.wireguard.com/install/).
2. Import `d:\VPN_WG\peers\phone.conf`.
3. Click **Activate**.
4. Test:

```powershell
ping 10.8.0.1
ping 10.8.0.10
ping 10.8.0.20
ping 192.168.10.100
ping 192.168.20.100
```

Browser:

- http://192.168.10.100 — Site 1 CCTV page
- http://192.168.20.100 — Site 2 CCTV page

## Test order

1. Start **site routers** (Docker) first.
2. Then **phone** tunnel on PC.
3. If LAN pings fail, site router is not connected to hub yet — check `wg show` handshake.

## Stop lab

```powershell
docker compose down
```

## Without Docker (minimal test)

Only tests hub ↔ phone (no fake LAN):

1. Import `phone.conf` in WireGuard.
2. `ping 10.8.0.1` — hub VPN IP must reply.

LAN/CCTV tests need site routers online (real hardware or Docker lab above).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No handshake | UDP **51820** open on VPS; routers running |
| Ping 10.8.0.x works, not 192.168.x | Site router container down or forwarding failed |
| Docker build fails | Start Docker Desktop; WSL2 backend enabled |
| `br-lan` errors | Lab replaces `br-lan` with `eth1` automatically |
