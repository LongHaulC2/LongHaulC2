import requests

for i in range(1, 10000):
    # print("REQUEST")
    r = requests.post("http://10.0.0.30:45045/api/v1/implants")

    data = r.json()
    id = data.get("data").get("id")

    implant_data = {
        "external_ip": "203.0.113.10",
        "internal_ip": "10.0.0.15",
        "listener": "c2.example.com:443",
        "user": "SYSTEM",
        "system_hostname": "WIN-ABC123",
        "notes": "Initial check-in",
        "process": "msiexec.exe",
        "pid": 1234,
        "arch": "x64",
        "last_checkin": "11223344",
        "sleep_value": 60,
    }
    r = requests.put(f"http://10.0.0.30:45045/api/v1/implants/{i}", json=implant_data)
