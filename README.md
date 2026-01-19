# Network Security Toolkit

Small collection of Python tools for basic network analysis and security auditing.  
Educational use only – for networks you own or have explicit permission to test. Everything else is illegal.

---

## Tools

### Sniffer.py – Packet Sniffer

Lightweight packet sniffer for inspecting live traffic.

- Captures traffic on all available interfaces.  
- Shows timestamp, source IP, destination IP and protocol.  
- Detects TCP/UDP and prints source/destination ports.  
- Displays payload if available (tries UTF‑8 decode, falls back to raw bytes).

> Requires admin/root privileges for full packet capture.

---

### Wifi_Audit.py – WiFi & DNS Audit

All‑in‑one **network audit** script for quick checks of your setup.

- External IP detection via `api.ipify.org`.  
- DNS leak test: compares system resolver with public DNS (1.1.1.1, 8.8.8.8).  
- Lists active external connections (local IP/port → remote IP/port, status, PID).  
- ARP scan in the local network and shows IP/MAC of discovered devices.

**Defaults**

- `NETWORK_RANGE = "192.168.1.0/24"` – change this to match your LAN (e.g. `192.168.0.0/24` or `10.0.0.0/24`).
- If `scapy` is not installed, only the ARP/device scan is skipped, other checks still work.

> Runs best with admin/root rights, otherwise some data (connections/scan) may be incomplete.

---

### IpLocator.py – IP Geolocation

Simple IP geolocation lookup using the free `ip-api.com` service.

- Pure standard library: `urllib`, `json`, `re`, `sys` – no extra pip install needed.
- Prints country, region, city, ISP, organization, latitude/longitude and timezone.
- Accepts IPv4 only; invalid formats are rejected early with a simple regex check.

---

## Requirements

### Python

- Python 3.x required (Python 2 is dead).

### Python Packages

Install all dependencies at once:

```bash
pip install scapy psutil requests dnspython
