---
slug: /
---

# LongHaul C2 - Overview

Most frameworks are built to get you in. LongHaul is built to keep you there.

The implant ships clean. You load what you need through BOFs when you need it. Network profiles let you reshape your traffic on the fly. What your implant does, how it does it, what it looks like on the wire, and how long it stays, is entirely up to you and your team.

---

## Key Features

### **The implant isn't "traditional" malware:** 
---
...by default. The implant ships with basically zero offensive capability. If you need a capability, BOF it. Add, swap or store a capability mid-operation without recompiling or redeploying the implant.

#### [Command Reference](./02%20Implants/1.%20Commands.md)
#### [Memory Store](./02%20Implants/Systems/MemStore.md)

### **Small Footprint:** 
---
Less implant code means less surface area. The built-in feature set is intentionally lean: BOF execution, filesystem access, file transfer, in-memory store, strategy switching, SMB chaining. That's the whole list. Additionally, thanks to mimicry, no networking libraries (save for sockets) are needed. 

Additionally, the implant is built with some modularity in mind. Is a default command (like `ls`) getting you caught? Cool, tell that detection to ~~fuck off~~ "pound sand", and implement your own version. 

#### [Command Modules](./02%20Implants/Modules/Overview%20&%20Modifications)


### **Mimicry:**
---
Custom Traffic Creation. Implement new protocols in minutes. Define a network profile, load it into a listener, and your C2 traffic looks like whatever you need — HTTP, NTP, DNS, FTP, or something entirely custom.

#### [Mimicry](./06%20Network%20Profiles/Overview.md)


### **Built to Last:**
---
Rotate traffic profiles at runtime without spawning new implants. Chain over SMB to reach isolated segments. The implant is designed to stay resident for as long as you need.

- **API-First:** Nearly everything in the UI is an API call. Scripted rotations, automated tasking, third-party integrations — all first-class.

---

... dive right in?
