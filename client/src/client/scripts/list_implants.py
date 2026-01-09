import requests
from yarl import URL

# setup server variables
api_url = URL("http://10.0.0.30:45045/")
implants_uri = api_url / "api" / "v1" / "implants"

print("=" * 50)
print("        CONNECTED IMPLANTS")
print("=" * 50)

# Request our implants list from the server
r = requests.get(str(implants_uri), timeout=5)

if r.status_code != 200:
    print(f"[!] Failed to fetch implants (status {r.status_code})")
    exit(1)

# extract data field out of response.
implants = r.json().get("data", [])

if not implants:
    print("[*] No implants connected")
else:
    for implant in implants:
        implant_uuid = implant.get("id", "N/A")
        external_ip = implant.get("external_ip", "N/A")
        print(f"ID: {implant_uuid:<10} | IP: {external_ip}")

print("=" * 50)
