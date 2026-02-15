# Memory Store (MemStore) Architecture

The **MemStore** is a volatile, in-memory storage engine. It serves as a (somewhat) secure staging ground for files, tools, or any data you want, allowing various workflows without extra disk interactions. 

### Design Philosophy & Motivation

Traditional tradecraft often involves dropping files to disk (e.g., in `C:\Temp\` or `%APPDATA%`) to execute them or exfiltrate them. While you *can* do this with the `file upload` and `file download` commands, this creates artifacts that are easily inspected by Antivirus and EDR solutions.

The MemStore solves this by creating a (very simple) **virtual file store entirely in RAM**.

* **Artifact Reduction:** Files stored here exist only in volatile memory. If the process is killed or the host reboots, the data vanishes instantly, leaving no forensic trace on the disk.

### Storage Strategy

At its core, the MemStore functions as a **Key-Value Store** (it literally uses a `std::map<std::string, uint8_t>`).

* **Keys:** Simple string identifiers (filenames) used to reference the data.
* **Values:** The raw binary data.

### Heap Obfuscation (Data Masking)

To protect sensitive data while it resides in the implant's memory (heap), the MemStore implements a continuous obfuscation strategy. Raw data is **never** stored in plain text.

1. **Ingestion (XOR Encoding):**
When data is stored, it is immediately scrambled using an XOR operation. The encryption key used for this process is the **filename (Key)** itself. It's not super secure, but it's enough to ensuring that two identical files stored under different names will look completely different to a memory scanner (which is the whole point here, detection evasion). The key name can be as long as you want, it's stored via a `std::string`, so go ham. 

2. **At Rest:**
While sitting in memory, the data remains in this scrambled state. This aims to defeat memory scanners that look for specific static signatures (like PE headers or config strings) within the implant's allocated memory.

3. **Retrieval:**
The data is only decoded when explicitly needed (e.g., C2 operator using the value). The retrieval process creates a temporary copy, unscrambles it to restore the original format, and returns it for immediate use.

### Memory Hygiene & Ownership

[ need to verify to be 100% sure ]

The MemStore is designed to minimize the proliferation of sensitive data copies in memory.

* **Ownership Transfer:** When a module passes data to the store, ownership is transferred rather than copied. This prevents "ghost copies" of the data from lingering in the memory of the calling function.
* **Destructive Updates:** Overwriting a key completely replaces the underlying data, releasing the old memory block immediately.

### Integration with C2 Commands [not implemented]

The MemStore is the backend that powers the **Dereference Operator (`*`)**. (see the `Commands` docs)

When a user issues a command like `file upload C:\Target\out.exe *my_tool`, the implant:

1. Detects the `*` prefix.
2. Looks up `my_tool` in the MemStore.
3. Decodes the binary data on the fly.
4. Uses that data for the upload.

This allows operators to upload tools to the implant *once*, and then deploy them to multiple locations or use them in multiple ways without re-transmitting data over the network.