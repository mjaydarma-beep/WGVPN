# Peer configs (local only)

Your real `.conf` files with private keys live in this folder but are **not** committed to git (see root `.gitignore`).

| File | Device |
|------|--------|
| `site1-router.conf` | Site 1 VPN router (192.168.10.0/24) |
| `site2-router.conf` | Site 2 VPN router (192.168.20.0/24) |
| `phone.conf` | Phone / iPhone |
| `laptop.conf` | Laptop |

**Backup** this folder to a safe place (USB, password manager, encrypted drive).

To add devices via dashboard: http://172.245.110.29:10086 → **wg0** → Add peer → use **Generate key pair** for Download/QR.

See `phone.conf.example` for the correct client format.
