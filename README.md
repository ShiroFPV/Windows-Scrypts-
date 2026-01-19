# Network Security Toolkit

Small collection of Python tools for basic network analysis and security auditing.  
Educational use only – for networks you own or have explicit permission to test. Everything else ist illegal, uncool und komplett dein Problem.[file:1][file:2][file:3]

---

## Tools

### Sniffer.py – Packet Sniffer

Lightweight packet sniffer for inspecting live traffic.[file:3]

- Captures traffic on all available interfaces.  
- Shows timestamp, source IP, destination IP and protocol.  
- Detects TCP/UDP and prints source/destination ports.  
- Displays payload if available (tries UTF‑8 decode, falls back to raw bytes).[file:3]

> Requires admin/root privileges for full packet capture.

---

### Wifi_Audit.py – WiFi & DNS Audit

All‑in‑one **network audit** script for quick checks of your setup.[file:1]

- External IP detection via `api.ipify.org`.  
- DNS leak test: compares system resolver with public DNS (1.1.1.1, 8.8.8.8).  
- Lists active external connections (local IP/port → remote IP/port, status, PID).  
- ARP scan in the local network and shows IP/MAC of discovered devices.[file:1]

**Defaults**

- `NETWORK_RANGE = "192.168.1.0/24"` – change this to match your LAN (e.g. `192.168.0.0/24` or `10.0.0.0/24`).[file:1]  
- If `scapy` is not installed, only the ARP/device scan is skipped, other checks still work.[file:1]

> Runs best with admin/root rights, otherwise some data (connections/scan) may be incomplete.

---

### IpLocator.py – IP Geolocation

Simple IP geolocation lookup using the free `ip-api.com` service.[file:2]

- Pure standard library: `urllib`, `json`, `re`, `sys` – no extra pip install needed.[file:2]  
- Prints country, region, city, ISP, organization, latitude/longitude and timezone.[file:2]  
- Accepts IPv4 only; invalid formats are rejected early with a simple regex check.[file:2]

---

## Requirements

### Python

- Python 3.x required (Python 2 is dead).[file:2]

### Python Packages

Install all dependencies at once:

```bash
pip install scapy psutil requests dnspython
