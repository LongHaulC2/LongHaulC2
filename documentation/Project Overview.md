---
slug: /
---

# LongHaul C2 - Overview

Most frameworks are built to compromise targets. LongHaul is built to stay on them.

Minimal by design. Extensible at runtime. The implant ships clean — no offensive capability, no hardcoded protocols. BOFs load what you need mid-operation. Network profiles define your traffic shape in minutes. What your implant does, what it looks like on the wire, and how long it persists are all operator decisions made at runtime, not compile time.

Built for red teams that need to adapt fast and stay resident long.

---

## Key Features

### **The implant isn't malware:** 
---
...by default. The implant ships with basically zero offensive capability. Offensive tooling is loaded at runtime via BOFs. Add, swap or store a capability mid-operation without recompiling or redeploying the implant. - commands link here? -

#### [Command Reference](./02%20Implants/1.%20Commands.md)


### **Small Footprint:** 
---
Less implant code means less surface area. The built-in feature set is intentionally lean: BOF execution, filesystem access, file transfer, in-memory store, strategy switching, SMB chaining. That's the whole list. Additionally, thanks to mimicry, no networking libraries (save for sockets) are needed.

### **Mimicry:**
---
Custom Traffic Creation. Implement new protocols in minutes. Define a network profile, load it into a listener, and your C2 traffic looks like whatever you need — HTTP, NTP, DNS, FTP, or something entirely custom. The framework imposes zero protocol constraints.

#### [Mimicry](./06%20Network%20Profiles/Overview.md)


### **Built to Last:**
---
Rotate traffic profiles at runtime without spawning new implants. Chain over SMB to reach isolated segments. The implant is designed to stay resident for as long as you need.

- **API-First:** Nearly everything in the UI is an API call. Scripted rotations, automated tasking, third-party integrations — all first-class.

---

... dive right in?

<!-- ## Architecture

### Domain Separation

The product has two completely separate codebases. They communicate only via the REST API.

| Domain | Path | Description |
|---|---|---|
| Server | `server/` | Python/Flask-RestX REST API, all C2 orchestration logic |
| Client (UI) | `client/` | Python/NiceGUI web frontend |
| Implant | `implant_templates/win_implant_base/` | C++ Windows implant, compiled server-side on demand |
| Tests | `tests/` | Integration and schema tests | -->
