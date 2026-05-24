# VPN_WG — Project summary

**Status:** Deployed and saved locally.

## Server

| Item | Value |
|------|--------|
| Hub IP | 172.245.110.29 |
| WireGuard | UDP 51820 (`wg0`) |
| Dashboard | http://172.245.110.29:10086 |
| VPN subnet | 10.8.0.0/24 |

## Sites

| Site | LAN | VPN router IP | CCTV |
|------|-----|---------------|------|
| 1 | 192.168.10.0/24 | 10.8.0.10 | .100–.101 |
| 2 | 192.168.20.0/24 | 10.8.0.20 | .100 |

## Local files (contain secrets — backup separately)

- `peers/*.conf` — import into WireGuard on each device
- `peers-manifest.json` — peer public keys map
- `server-wg0.conf` — hub config copy

## Documentation

| Doc | Purpose |
|-----|---------|
| **[INSTALL.md](INSTALL.md)** | Full real-world installation (production) |
| [WORKING-SETUP.md](WORKING-SETUP.md) | Your verified IPs and test commands |
| [test-lab/README.md](test-lab/README.md) | Docker simulator only |

## Scripts

| Script | Purpose |
|--------|---------|
| `deploy_multisite.py` | Redeploy hub + regenerate all peers |
| `setup_wg_server.py` | Initial single-server install |

```powershell
$env:WG_SERVER_PASSWORD = "your-password"
python deploy_multisite.py
```

## Quick checklist

- [ ] Import `site1-router.conf` / `site2-router.conf` on VPN routers
- [ ] Import `phone.conf` on iPhone
- [ ] Open UDP 51820 + TCP 10086 on VPS firewall
- [ ] Change dashboard password (`admin` / `admin`)
- [ ] Change server root password
