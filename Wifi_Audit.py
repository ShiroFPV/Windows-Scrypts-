#!/usr/bin/env python3

import os
import socket
import ctypes
import psutil
import requests
import dns.resolver

try:
    from scapy.all import ARP, Ether, srp
    SCAPY_OK = True
except:
    SCAPY_OK = False


# -------- CONFIG --------
TEST_DOMAINS = ["whoami.akamai.net", "example.com", "google.com"]
PUBLIC_DNS = ["1.1.1.1", "8.8.8.8"]
NETWORK_RANGE = "192.168.1.0/24"
# ------------------------


def is_admin():
    """Check for admin rights on Windows or root on Linux"""
    if os.name == 'nt':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    else:
        return os.geteuid() == 0


def get_external_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=5).text
    except Exception as e:
        return f"Error: {e}"


# ---------- DNS LEAK CHECK ----------
def check_dns_leak():
    print("\n[+] DNS LEAK TEST")
    system_results = {}

    for d in TEST_DOMAINS:
        try:
            ip = socket.gethostbyname(d)
            system_results[d] = ip
        except Exception as e:
            system_results[d] = str(e)

    public_results = {}

    for dns_server in PUBLIC_DNS:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [dns_server]
        public_results[dns_server] = {}

        for d in TEST_DOMAINS:
            try:
                ans = resolver.resolve(d, "A")
                public_results[dns_server][d] = ans[0].to_text()
            except Exception as e:
                public_results[dns_server][d] = str(e)

    print("\nSystem DNS results:")
    for k, v in system_results.items():
        print(f"  {k} -> {v}")

    print("\nPublic DNS comparison:")
    for server, results in public_results.items():
        print(f"\nResolver {server}:")
        for k, v in results.items():
            print(f"  {k} -> {v}")

    print("\nIf system results differ from public resolvers → possible DNS leak.")


# ---------- ACTIVE CONNECTIONS ----------
def show_external_connections():
    print("\n[+] ACTIVE EXTERNAL CONNECTIONS")

    try:
        conns = psutil.net_connections(kind="inet")

        for c in conns:
            if c.raddr:
                print(
                    f"{c.laddr.ip}:{c.laddr.port}  -->  "
                    f"{c.raddr.ip}:{c.raddr.port}  [{c.status}]  PID:{c.pid}"
                )
    except Exception as e:
        print("Error reading connections:", e)


# ---------- NETWORK DEVICE SCAN ----------
def arp_scan():
    print(f"\n[+] SCANNING NETWORK {NETWORK_RANGE}")

    if not SCAPY_OK:
        print("Scapy not installed – skipping device scan.")
        return

    try:
        packet = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=NETWORK_RANGE)
        result = srp(packet, timeout=3, verbose=False)[0]

        if not result:
            print("No devices found (or scan blocked).")
            return

        print("Found devices:")
        for sent, received in result:
            print(f"  IP: {received.psrc}   MAC: {received.hwsrc}")

    except Exception as e:
        print("ARP scan error:", e)


# ---------- MAIN ----------
def main():

    print("==== WIFI / DNS SECURITY AUDIT ====\n")

    if not is_admin():
        print("⚠ Run this as ADMINISTRATOR for full results!\n")

    print("External IP:", get_external_ip())

    check_dns_leak()

    show_external_connections()

    arp_scan()

    print("\n==== FINISHED ====")


if __name__ == "__main__":
    main()
    input("\nPress ENTER to exit...")
