# Working setup snapshot (verified)

## Server

| Item | Value |
|------|--------|
| Hub | 172.245.110.29 |
| WireGuard | UDP 51820, interface wg0 |
| VPN subnet | 10.8.0.0/24 |
| Dashboard | http://172.245.110.29:10086 |

## Sites

| Site | LAN | Router VPN IP | CCTV test |
|------|-----|---------------|-----------|
| 1 | 192.168.10.0/24 | 10.8.0.10 | 192.168.10.100 |
| 2 | 192.168.20.0/24 | 10.8.0.20 | 192.168.20.100 |

## Client configs (import these)

| Device | File |
|--------|------|
| Phone / PC | `peers/phone.conf` |
| Laptop | `peers/laptop.conf` |
| Site 1 router | `peers/site1-router.conf` |
| Site 2 router | `peers/site2-router.conf` |

## Docker test lab

```powershell
cd d:\VPN_WG\test-lab
docker compose up -d --build
```

LAN sim uses router at 192.168.10.2 / 192.168.20.2 (CCTV at .100).

## Verified tests (PC + phone.conf)

```
ping 10.8.0.10
ping 10.8.0.20
ping 192.168.10.100
ping 192.168.20.100
```

Browser: http://192.168.10.100 , http://192.168.20.100

## Backup

Latest: `backup/YYYYMMDD/` — full config copy from server + peers.
