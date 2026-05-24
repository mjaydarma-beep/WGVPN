# Real-world installation guide — multisite WireGuard VPN

This guide is for a **production** setup like yours:

- **Hub** — cloud VPS (Ubuntu) with public IP  
- **Site 1** — VPN router + LAN `192.168.10.0/24` (CCTV, etc.)  
- **Site 2** — VPN router + LAN `192.168.20.0/24`  
- **Phones / laptops** — access all sites over VPN  

For local testing only (Docker simulators), see `test-lab/README.md`.

---

## 1. Network plan (fill in your values)

| Role | VPN IP | LAN / notes |
|------|--------|-------------|
| Hub server | `10.8.0.1/24` | Public IP e.g. `172.245.110.29` |
| Site 1 router | `10.8.0.10/32` | `192.168.10.0/24`, gateway `.1` |
| Site 2 router | `10.8.0.20/32` | `192.168.20.0/24`, gateway `.1` |
| Phone | `10.8.0.50/32` | No LAN |
| Laptop | `10.8.0.51/32` | No LAN |
| Extra peers | `10.8.0.52+` | As needed |

| Port | Protocol | Where |
|------|----------|--------|
| **51820** | UDP | VPS firewall + provider panel — **required** |
| **10086** | TCP | VPS — WGDashboard only (optional; restrict by IP) |

---

## 2. Architecture

```
                         INTERNET
                             |
              +--------------+--------------+
              |   Hub VPS (WireGuard wg0)   |
              |   10.8.0.1  UDP 51820       |
              +--------------+--------------+
                    /    |    \
                   /     |     \
        Site 1 router   Phone   Site 2 router
        10.8.0.10      10.8.0.50   10.8.0.20
              |                      |
     192.168.10.0/24        192.168.20.0/24
     CCTV .100-.101              CCTV .100
```

**Traffic flow (phone → Site 1 CCTV):**  
Phone → VPN tunnel → Hub → Site 1 router → `192.168.10.100`

Site routers must be **online** for their LAN to be reachable.

---

## 3. Install the hub (Ubuntu VPS)

### 3.1 Server requirements

- Ubuntu 20.04 / 22.04 (or similar Linux)  
- Root or sudo  
- Public IPv4  
- Provider firewall: allow **UDP 51820**  

### 3.2 Install WireGuard on the hub

SSH to the server:

```bash
ssh root@YOUR_SERVER_IP
```

```bash
apt update
apt install -y wireguard wireguard-tools iptables

# Generate hub keys
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
chmod 600 /etc/wireguard/server_private.key
```

Enable forwarding:

```bash
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p
```

Create `/etc/wireguard/wg0.conf` (peers added in step 4):

```ini
[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = YOUR_SERVER_PRIVATE_KEY
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
```

Replace `eth0` with your main interface if different (`ip route | grep default`).

Start and enable:

```bash
chmod 600 /etc/wireguard/wg0.conf
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0
wg show
```

### 3.3 Or deploy from your PC (this project)

On Windows, with peer definitions in `deploy_multisite.py`:

```powershell
cd d:\VPN_WG
$env:WG_SERVER_PASSWORD = "your-root-password"
python deploy_multisite.py
```

This installs WireGuard, writes `wg0.conf`, and creates files in `peers\`.

---

## 4. Add peers on the hub

Each peer needs a **key pair**. On the hub:

```bash
wg genkey | tee client_private.key | wg pubkey > client_public.key
```

On the hub `wg0.conf`, each `[Peer]` block looks like:

**Site router (Site 1 example):**

```ini
# Site 1 — advertises LAN 192.168.10.0/24
[Peer]
PublicKey = SITE1_ROUTER_PUBLIC_KEY
AllowedIPs = 10.8.0.10/32, 192.168.10.0/24
```

**Phone:**

```ini
[Peer]
PublicKey = PHONE_PUBLIC_KEY
AllowedIPs = 10.8.0.50/32
```

After editing:

```bash
systemctl restart wg-quick@wg0
```

### Allowed IPs rules (important)

| Peer type | Hub `[Peer]` AllowedIPs | Client `[Peer]` AllowedIPs (to hub) |
|-----------|-------------------------|-------------------------------------|
| Site 1 router | `10.8.0.10/32, 192.168.10.0/24` | `10.8.0.0/24, 192.168.20.0/24` |
| Site 2 router | `10.8.0.20/32, 192.168.20.0/24` | `10.8.0.0/24, 192.168.10.0/24` |
| Phone / laptop | `10.8.0.50/32` (one IP) | `10.8.0.0/24, 192.168.10.0/24, 192.168.20.0/24` |

- Hub **AllowedIPs** = what traffic to send **to** that peer.  
- Client **AllowedIPs** = what traffic goes **into** the tunnel from that device.

---

## 5. Site VPN router (real hardware)

Use the file `peers/site1-router.conf` or `site2-router.conf` from this project (each site gets its own file).

### 5.1 Site 1 client config (example)

```ini
[Interface]
PrivateKey = SITE1_PRIVATE_KEY
Address = 10.8.0.10/32
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = HUB_PUBLIC_KEY
Endpoint = YOUR_SERVER_IP:51820
AllowedIPs = 10.8.0.0/24, 192.168.20.0/24
PersistentKeepalive = 25
```

Site 2: same pattern with `10.8.0.20` and `AllowedIPs` including `192.168.10.0/24`.

### 5.2 Router requirements (all platforms)

1. **IP forwarding** enabled.  
2. **Firewall** allows forward: VPN interface ↔ LAN.  
3. **NAT (MASQUERADE)** from VPN to LAN so devices (CCTV) can reply.  
4. **PersistentKeepalive = 25** (router behind NAT must reach hub).  

### 5.3 OpenWrt (common VPN router)

1. Install packages: `wireguard-tools` `kmod-wireguard` (or use LuCI **WireGuard**).  
2. **Network → Interfaces → Add → WireGuard**  
3. Paste **Interface** section (private key, address `10.8.0.10/32`).  
4. Add **peer**: hub public key, endpoint `IP:51820`, allowed IPs as above.  
5. **Firewall** → assign WireGuard to `wan` zone or custom zone; allow forward to `lan`.  
6. On LAN devices, gateway remains `192.168.10.1` (local router).  

**PostUp (if using .conf file on Linux/OpenWrt):** change `br-lan` to your LAN interface (`br-lan`, `eth1`, `lan`, etc.):

```bash
PostUp = sysctl -w net.ipv4.ip_forward=1; iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o br-lan -j MASQUERADE
```

### 5.4 MikroTik (brief)

- **Interfaces → WireGuard** → add interface, listen port local.  
- **Peers** → public key, endpoint, allowed address `10.8.0.0/24,...`.  
- **IP → Routes** — WireGuard usually installs routes from allowed IPs.  
- **IP → Firewall → NAT** masquerade VPN → LAN.  
- **IP → Settings** enable IP forwarding.  

### 5.5 Generic Linux router

```bash
cp site1-router.conf /etc/wireguard/wg0.conf
# Edit PostUp: set correct LAN interface name
wg-quick up wg0
systemctl enable wg-quick@wg0
```

---

## 6. Phones and laptops

Use `peers/phone.conf` or `peers/laptop.conf`.

```ini
[Interface]
PrivateKey = PHONE_PRIVATE_KEY
Address = 10.8.0.50/32
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = HUB_PUBLIC_KEY
Endpoint = YOUR_SERVER_IP:51820
AllowedIPs = 10.8.0.0/24, 192.168.10.0/24, 192.168.20.0/24
PersistentKeepalive = 25
```

| Platform | Steps |
|----------|--------|
| **iPhone** | App Store → WireGuard → + → scan QR or import file |
| **Android** | Play Store → WireGuard → + → import |
| **Windows** | Install WireGuard → Import tunnel → Activate |

**AllowedIPs** above = split tunnel (only VPN + site LANs). For full internet via VPN use `0.0.0.0/0` (not required for CCTV).

---

## 7. WGDashboard (manage peers in browser)

Already installed on your hub at **http://YOUR_SERVER_IP:10086**.

| | |
|---|---|
| Default login | `admin` / `admin` — **change immediately** |
| Service | `systemctl status wg-dashboard` |

### Add a new peer in the dashboard

1. Open **wg0** (do not create a second “configuration” unless you need another tunnel).  
2. **Add peer** → use **Generate key pair** (required for QR/download).  
3. Set VPN IP e.g. `10.8.0.52/32`.  
4. For a **site router**, set hub Allowed IPs: `10.8.0.52/32, 192.168.30.0/24` (your LAN).  
5. Download config or scan QR.  

If you see *“no private key set”* — peer was added manually on server only; re-add with **Generate key pair** or use the `.conf` from `peers\`.

---

## 8. Install order (real deployment)

| Step | Action |
|------|--------|
| 1 | Hub VPS: WireGuard + firewall UDP 51820 |
| 2 | Generate keys; build `wg0.conf` with all `[Peer]` blocks |
| 3 | **Site 1 router** — import config, verify handshake on hub: `wg show` |
| 4 | **Site 2 router** — same |
| 5 | **Phones/laptops** — import config |
| 6 | Test (section 9) |
| 7 | Change passwords; backup `peers\` folder |

---

## 9. Testing (real network)

With **phone VPN on**, run (use 4 pings: `ping -n 4` on Windows):

```text
ping 10.8.0.1          → hub
ping 10.8.0.10         → site 1 router
ping 10.8.0.20         → site 2 router
ping 192.168.10.100    → site 1 CCTV
ping 192.168.20.100    → site 2 CCTV
```

Browser: `http://192.168.10.100` (camera web UI).

On the **hub**:

```bash
wg show
```

Each peer should show **latest handshake** within 1–2 minutes.

| Symptom | Likely cause |
|---------|----------------|
| No handshake | UDP 51820 blocked; wrong endpoint; router off |
| Hub OK, not LAN | Site router forwarding/NAT; wrong `br-lan` in PostUp |
| Site 1 OK, not Site 2 | Site 2 router down; check its handshake on hub |
| Slow (~500 ms) | Normal if VPS is far away |

---

## 10. CCTV / devices on LAN

- Cameras stay on **local LAN IP** (e.g. `192.168.10.100`).  
- No WireGuard on the camera itself.  
- Phone reaches them **through** the site VPN router.  
- Site router must have hub AllowedIPs including the **whole LAN subnet** (`192.168.10.0/24`).  

---

## 11. Security checklist

- [ ] Change VPS root password; use SSH keys  
- [ ] Change WGDashboard `admin` password  
- [ ] Restrict TCP 10086 to your IP if possible  
- [ ] Backup `peers\` and `backup\` folders offline  
- [ ] Never commit `.conf` files to public GitHub  

---

## 12. Backup and restore

| Backup | Location |
|--------|----------|
| Auto snapshot | `d:\VPN_WG\backup\YYYYMMDD\` |
| Hub config | `server-wg0.conf` |
| Clients | `peers\*.conf` |

**Restore hub:** copy `server-wg0.conf` → `/etc/wireguard/wg0.conf`, then `systemctl restart wg-quick@wg0`.

---

## 13. Your live reference (this project)

| Item | Your value |
|------|------------|
| Hub IP | `172.245.110.29` |
| WireGuard port | `51820` UDP |
| Dashboard | `http://172.245.110.29:10086` |
| Site 1 LAN | `192.168.10.0/24` |
| Site 2 LAN | `192.168.20.0/24` |
| Config files | `d:\VPN_WG\peers\` |

See also: `WORKING-SETUP.md`, `README.md`, `PROJECT.md`.

---

## 14. Add a third site (example)

1. Pick VPN IP: `10.8.0.30`, LAN: `192.168.30.0/24`.  
2. Generate keys; add hub peer: `AllowedIPs = 10.8.0.30/32, 192.168.30.0/24`.  
3. Update **all phones/laptops** client AllowedIPs to include `192.168.30.0/24`.  
4. Update **other site routers** client AllowedIPs to include `192.168.30.0/24`.  
5. Restart `wg-quick@wg0` on hub; bring up new site router.  
