# Opsec & Limitations

There's a few important caveats with these profiles, especially around opsec. The short version is, be smart about what you use, and when you use it.

For example, HTTP or FTP packets are "normal" to have larger amounts of data going through them. Something like NTP over UDP is likely not.

---

## What to Use When

This is not a be-all, end-all set of rules, just some suggestions for OPSEC based on the included profiles.

| Use Case | Good Fit | Why |
|---|---|---|
| Large file transfers, bulk exfil | HTTP, FTP | TCP, no size limit, large payloads are normal for these protocols |
| Low-and-slow persistence | NTP, DNS, SNMP | Small background protocols that blend into baseline traffic |
| Sensitive environment, expect monitoring | Encrypted HTTP | AES-GCM encrypted payload, HTTP framing still passes signature matching |
| DNS-only egress | DNS | Sometimes the only thing that gets out |
| Network/infra segments | SNMP | Plausible where management traffic is expected |
| Active operations, need responsiveness | HTTP, FTP | TCP handles rapid back-and-forth and large responses well |

---

## Transport Constraints

### TCP (HTTP, Encrypted HTTP, FTP, NTP-over-TCP, Debug)

- No per-message size limit. File downloads, large BOF output, and bulk exfil all work.
- One TCP connection per beacon/exfil cycle. Connection-tracking firewalls will see frequent short-lived connections.

### UDP (NTP, DNS, SNMP)

- Hard limit of **~65,507 bytes** per datagram. No application-layer chunking exists.
- Transform amplification reduces this further. After `base64url` (~1.33x) plus the protocol header, practical limit is roughly **48 KB**. Chaining `base64` + `netbios` drops it to around **24 KB**.
- If a UDP exfil exceeds the datagram limit after transforms, the send **silently fails** and data is lost.
- Use strategy switching to move the implant to a TCP channel before queuing large tasks.

---

## General Opsec

### Sleep Intervals

Your beacon interval is an extremely important opsec option. Match it to the protocol/goals for your usecase.

- **Low-and-slow** (hours, or days between beacons) for long-term access. Appropriate for NTP, DNS, SNMP — protocols where traffic is naturally infrequent.
- **Moderate** (30-120 seconds) for active operations. More defensible with HTTP than with NTP.
- **Fast** (< 30 seconds) for interactive work. Set the sleep back up when you're done. Rapid beaconing on any protocol is noisy.

### Data Size

Not every protocol carries large payloads in the real world. An NTP packet with kilobytes of data in an extension field is unusual. An HTTP POST with kilobytes of form data is not. Think about what "normal" looks like for the protocol you're mimicking before queuing large tasks.

If the implant is on a lightweight UDP profile and you need to do something data-heavy, `strat set` to a TCP strategy, run the operation, then switch back.

### Encryption

The implants don't encrypt their comms by default, however you can implement it via the `symcrypt` option in a profile.

- Add `symcrypt` as the **first** transform in any profile's chain to get AES-256-GCM encryption. The protocol framing stays plaintext (required for mimicry), the payload content becomes ciphertext.
- Generate a unique key per engagement. 

### Strategy Switching

The implant can carry multiple strategies. Use this to your advantage, beacon on a stealthy protocol for persistence, switch to a high-bandwidth protocol for data-heavy operations, switch back when done.

---

## Mimicry Limitations

These profiles produce wire traffic that passes basic protocol signature matching (port + expected header structure). They are not perfect protocol implementations. This is the tradeoff to allow for a wider range of network customization compared to more "traditional" C2's.

For example, some "flaws" of the default profiles:

- **HTTP**: No `Content-Length` header, no persistent connections. Fails deep session inspection.
- **FTP**: No 220 banner, no USER/PASS exchange. Fails stateful FTP session reconstruction.
- **NTP**: Static timestamps (all zeros), fixed fields. Fails NTP-aware protocol validation.
- **DNS**: Fixed transaction ID, repeated identical queries, private-use OPT option codes. Flags in passive DNS monitoring.
