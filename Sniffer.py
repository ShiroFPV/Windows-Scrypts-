from scapy.all import sniff, IP, TCP, UDP, Raw
import datetime

def packet_callback(pkt):
    time = datetime.datetime.now().strftime("%H:%M:%S")

    if IP in pkt:
        src = pkt[IP].src
        dst = pkt[IP].dst
        proto = pkt[IP].proto

        print(f"\n[{time}] {src}  --->  {dst}")

        # TCP
        if TCP in pkt:
            print(f" Protocol: TCP  Port: {pkt[TCP].sport} -> {pkt[TCP].dport}")

        # UDP
        elif UDP in pkt:
            print(f" Protocol: UDP  Port: {pkt[UDP].sport} -> {pkt[UDP].dport}")

        # Payload anzeigen wenn vorhanden
        if Raw in pkt:
            data = pkt[Raw].load
            try:
                print(" Data:", data.decode(errors="ignore")[:200])
            except:
                print(" Data (raw):", data[:200])


def main():
    print("=== Simple Scapy Packet Sniffer ===")
    print("Drücke STRG+C zum Beenden\n")

    # sniffen auf allen Interfaces
    sniff(prn=packet_callback, store=False)


if __name__ == "__main__":
    main()
