import sys
import json
import re

# Use built-in library – no pip install needed
try:
    from urllib.request import urlopen
except ImportError:
    print("Your Python is too old. Use Python 3.")
    sys.exit(1)


def is_valid_ip(ip):
    pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
    return re.match(pattern, ip)


def locate_ip(ip):
    url = "http://ip-api.com/json/" + ip

    try:
        response = urlopen(url, timeout=5)
        data = json.loads(response.read().decode())

        if data.get("status") != "success":
            print("[!] API error:", data.get("message"))
            return

        print("\n=== IP LOCATION RESULT ===")
        print("IP:      ", data.get("query"))
        print("Country: ", data.get("country"))
        print("Region:  ", data.get("regionName"))
        print("City:    ", data.get("city"))
        print("ISP:     ", data.get("isp"))
        print("Org:     ", data.get("org"))
        print("Lat/Lon: ", data.get("lat"), data.get("lon"))
        print("Timezone:", data.get("timezone"))
        print("==========================\n")

    except Exception as e:
        print("\n[CRASH INFO]")
        print(type(e).__name__, ":", e)
        print("This usually means:")
        print("- no internet connection")
        print("- firewall blocking python")
        print("- invalid API response")
        print("- Python version issue\n")


def main():
    try:
        if len(sys.argv) > 1:
            ip = sys.argv[1]
        else:
            ip = input("Enter IP address: ").strip()

        if not is_valid_ip(ip):
            print("[!] Invalid IP format")
            return

        locate_ip(ip)

    except Exception as e:
        print("Fatal error:", e)

    input("Press ENTER to exit...")


if __name__ == "__main__":
    main()
