<img width="2000" height="400" alt="LongHaulC2" src="https://github.com/user-attachments/assets/174ea327-8bbb-406c-a8b6-aec0e903a22f" />

---

Quiet and Flexible. 

## Key Features

### **The implant isn't "traditional" malware:** 
---
...by default. The implant ships with basically zero offensive capability. If you need a capability, BOF it. Add, swap or store a capability mid-operation without recompiling or redeploying the implant.

#### [Command Reference](./02%20Implants/1.%20Commands.md)
#### [Memory Store](./02%20Implants/Systems/MemStore.md)

### **Mimicry:**
---
Custom Traffic Creation. Implement new protocols in minutes. Define a network profile, load it into a listener, and your C2 traffic looks like whatever you need — HTTP, NTP, DNS, FTP, or something entirely custom.

#### [Mimicry](./06%20Network%20Profiles/Overview.md)


### **Small Footprint:** 
---
Less implant code means less surface area. The built-in feature set is intentionally lean: BOF execution, filesystem access, file transfer, in-memory store, strategy switching, SMB chaining. That's the whole list. Additionally, thanks to mimicry, no networking libraries (save for sockets) are needed. 

Additionally, the implant is built with some modularity in mind. Is a default command (like `ls`) getting you caught? Cool, tell that detection to ~~fuck off~~ "pound sand", and implement your own version. 

#### [Command Modules](./02%20Implants/Modules/Overview%20&%20Modifications)

Get started here: [docs.longhaulc2.com](https://docs.longhaulc2.com)

---

# Bug Reports & Feature Requests:

If you find a bug, or have a feature request, please open an issue, and use the appropriate template to fill out your request. Thanks!

---

# Pics:

## Operations tab
<img width="1911" height="1063" alt="image" src="https://github.com/user-attachments/assets/3448a8ce-4a62-41e2-9caf-fcd3c391983a" />

## Engagement Map
<img width="1912" height="1063" alt="image" src="https://github.com/user-attachments/assets/25c86186-8345-48dc-a5ed-018feace4fcd" />

## Audit Log
<img width="1912" height="1063" alt="image" src="https://github.com/user-attachments/assets/e7c1fc7a-5881-4618-8116-658d7f025a99" />

## Profiles
<img width="1906" height="945" alt="image" src="https://github.com/user-attachments/assets/e666511d-8003-4286-b97e-b791b559d1c6" />


