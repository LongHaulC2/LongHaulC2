import requests
from yarl import URL
import ipaddress

# setup server variables
api_url = URL("http://10.0.0.30:45045/")
implants_uri = api_url / "api" / "v1" / "implants"

# Define allowed IP range (change this to your actual subnet)
allowed_network = ipaddress.IPv4Network("10.0.0.0/24", strict=False)

print("=" * 50)
print("        CONNECTED IMPLANTS")
print("=" * 50)

# Request our implants list from the server
r = requests.get(str(implants_uri), timeout=5)

if r.status_code != 200:
    print(f"[!] Failed to fetch implants (status {r.status_code})")
    exit(1)

# Extract data field out of response.
implants = r.json().get("data", [])

if not implants:
    print("[*] No implants connected")
else:
    for implant in implants:
        implant_id = implant.get("id", "N/A")
        internal_ip = implant.get("internal_ip", "N/A")

        # Check if the external IP is in the allowed range
        try:
            ip = ipaddress.IPv4Address(internal_ip)
            if ip in allowed_network:
                print(f"ID: {implant_id:<10} | IP: {internal_ip} - In Scope")
            else:
                print(f"ID: {implant_id:<10} | IP: {internal_ip} - [!] Out of Scope")
        except ValueError:
            print(f"ID: {implant_id:<10} | IP: {internal_ip} - [!] Invalid IP")

print("=" * 50)

