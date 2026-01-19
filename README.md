Network Security Toolkit
A small collection of Python tools for basic network analysis and security auditing.
Educational use only – for networks you own or have explicit permission to test. Everything else ist illegal, uncool und komplett dein Problem.
​

Tools
Sniffer.py – Packet Sniffer
Lightweight packet sniffer for inspecting live traffic.
​

Captures traffic on all available interfaces.

Shows timestamp, source IP, destination IP and protocol.

Detects TCP/UDP and prints source/destination ports.

Displays payload if available (tries UTF‑8 decode, falls back to raw bytes).
​

Requires elevated privileges for full packet capture.

Wifi_Audit.py – WiFi & DNS Audit
All‑in‑one network audit script for quick sanity checks of your setup.
​
Features:

External IP detection via api.ipify.org.
​

DNS leak test: compares system resolver with public DNS (1.1.1.1, 8.8.8.8).
​

Lists active external connections (local IP/port → remote IP/port, status, PID).
​

ARP scan in the local network and shows IP/MAC of discovered devices.
​

Defaults:

NETWORK_RANGE = "192.168.1.0/24" – change this to match your LAN (e.g. 192.168.0.0/24 or 10.0.0.0/24).
​

If scapy is not installed, the ARP/device scan is skipped, all other checks still work.
​

Runs best with admin/root rights, otherwise some data (connections/scan) may be incomplete.
​

IpLocator.py – IP Geolocation
Simple IP geolocation lookup using the free ip-api.com service.
​

Pure standard library: urllib, json, re, sys – no extra pip install needed.
​

Prints country, region, city, ISP, organization, latitude/longitude and timezone.
​

Accepts IPv4 only; basic regex validation – invalid formats are rejected early.
​

Useful for quick checks of where an IP claims to be located.

Requirements
Python
Python 3.x required (Python 2 is dead).
​

Python Packages
Install all dependencies at once:

bash
pip install scapy psutil requests dnspython
Used by each script:

Sniffer.py:
​

scapy – packet capture and parsing

Wifi_Audit.py:
​

scapy – ARP scan and low-level network packets

psutil – system and network connection info

requests – external IP lookup

dnspython – DNS leak testing

IpLocator.py:
​

no external dependencies

System packages (Linux):

bash
sudo apt-get install libpcap-dev
Usage
Clone the repo and install dependencies:

bash
git clone https://github.com/ShiroFPV/Windows-Scrypts-
cd Windows-Scrypts-
pip install scapy psutil requests dnspython
Run the tools:

bash
# Packet Sniffer (admin/root recommended)
sudo python3 Sniffer.py
bash
# WiFi / DNS Security Audit (admin/root for full results)
sudo python3 Wifi_Audit.py
bash
# IP Locator – direct call
python3 IpLocator.py 8.8.8.8

# or interactive mode:
python3 IpLocator.py
# then enter an IP, e.g. 1.1.1.1
Technical Notes
Sniffer.py:
​

Uses scapy.sniff() with a custom callback.

Inspects IP layer and prints metadata for TCP, UDP and payload (Raw).

Wifi_Audit.py:
​

Privilege check via ctypes on Windows or os.geteuid() on Unix.

External IP via https://api.ipify.org.

DNS comparison using socket.gethostbyname (system) vs. dns.resolver.Resolver with 1.1.1.1 / 8.8.8.8.

Active connections via psutil.net_connections(kind="inet").

ARP scan via scapy.srp(Ether()/ARP(), pdst=NETWORK_RANGE).

IpLocator.py:
​

Validates IP with a simple IPv4 regex.

Queries http://ip-api.com/json/<IP> using urllib.request.urlopen.

Parses JSON response and prints relevant fields, with basic error handling.
