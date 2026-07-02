"""Unit tests for transform operations, focused on symcrypt (AES-256-GCM) round-trips."""

import os

import pytest

from server.listeners.transform import (
    SYMCRYPT_NONCE_LEN,
    SYMCRYPT_TAG_LEN,
    apply_python_transforms,
    reverse_python_transforms,
    symcrypt_decrypt,
    symcrypt_encrypt,
)


@pytest.fixture
def aes_key() -> bytes:
    return os.urandom(32)


class TestSymcryptRoundTrip:
    def test_encrypt_decrypt_basic(self, aes_key):
        plaintext = b"hello world"
        encrypted = symcrypt_encrypt(plaintext, aes_key)
        decrypted = symcrypt_decrypt(encrypted, aes_key)
        assert decrypted == plaintext

    def test_encrypt_decrypt_empty(self, aes_key):
        encrypted = symcrypt_encrypt(b"", aes_key)
        decrypted = symcrypt_decrypt(encrypted, aes_key)
        assert decrypted == b""

    def test_encrypt_decrypt_large(self, aes_key):
        plaintext = os.urandom(64 * 1024)
        encrypted = symcrypt_encrypt(plaintext, aes_key)
        decrypted = symcrypt_decrypt(encrypted, aes_key)
        assert decrypted == plaintext

    def test_wire_format_layout(self, aes_key):
        """Verify wire format is [nonce (12)][tag (16)][ciphertext]."""
        plaintext = b"test data here"
        encrypted = symcrypt_encrypt(plaintext, aes_key)
        assert len(encrypted) == SYMCRYPT_NONCE_LEN + SYMCRYPT_TAG_LEN + len(plaintext)

    def test_different_nonces_per_call(self, aes_key):
        plaintext = b"same input"
        enc1 = symcrypt_encrypt(plaintext, aes_key)
        enc2 = symcrypt_encrypt(plaintext, aes_key)
        assert enc1[:SYMCRYPT_NONCE_LEN] != enc2[:SYMCRYPT_NONCE_LEN]
        assert enc1 != enc2

    def test_wrong_key_fails(self, aes_key):
        plaintext = b"secret"
        encrypted = symcrypt_encrypt(plaintext, aes_key)
        wrong_key = os.urandom(32)
        with pytest.raises(ValueError, match="symcrypt_decrypt"):
            symcrypt_decrypt(encrypted, wrong_key)

    def test_tampered_ciphertext_fails(self, aes_key):
        encrypted = symcrypt_encrypt(b"tamper test", aes_key)
        corrupted = bytearray(encrypted)
        corrupted[-1] ^= 0xFF
        with pytest.raises(ValueError):
            symcrypt_decrypt(bytes(corrupted), aes_key)

    def test_bad_key_length_encrypt(self):
        with pytest.raises(ValueError, match="32 bytes"):
            symcrypt_encrypt(b"data", b"short")

    def test_bad_key_length_decrypt(self):
        with pytest.raises(ValueError, match="32 bytes"):
            symcrypt_decrypt(b"x" * 40, b"short")

    def test_data_too_short_decrypt(self, aes_key):
        with pytest.raises(ValueError, match="too short"):
            symcrypt_decrypt(b"x" * 10, aes_key)


class TestSymcryptInTransformChain:
    """Test symcrypt via the apply/reverse pipeline, including TOML 'key' field support."""

    def test_chain_with_val_field(self, aes_key):
        transforms = [{"op": "symcrypt", "val": aes_key}]
        plaintext = b"pipeline test"
        encrypted = apply_python_transforms(plaintext, transforms)
        decrypted = reverse_python_transforms(encrypted, transforms)
        assert decrypted == plaintext

    def test_chain_with_key_field(self, aes_key):
        """TOML profiles use 'key' not 'val' for symcrypt."""
        transforms = [{"op": "symcrypt", "key": aes_key}]
        plaintext = b"toml key field"
        encrypted = apply_python_transforms(plaintext, transforms)
        decrypted = reverse_python_transforms(encrypted, transforms)
        assert decrypted == plaintext

    def test_symcrypt_with_base64(self, aes_key):
        transforms = [
            {"op": "symcrypt", "key": aes_key},
            {"op": "base64"},
        ]
        plaintext = b"encrypt then encode"
        encrypted = apply_python_transforms(plaintext, transforms)
        decrypted = reverse_python_transforms(encrypted, transforms)
        assert decrypted == plaintext

    def test_symcrypt_with_prepend_append(self, aes_key):
        transforms = [
            {"op": "symcrypt", "key": aes_key},
            {"op": "prepend", "val": "\\xAA\\xBB"},
            {"op": "append", "val": "\\xCC\\xDD"},
        ]
        plaintext = b"framing test"
        encrypted = apply_python_transforms(plaintext, transforms)
        decrypted = reverse_python_transforms(encrypted, transforms)
        assert decrypted == plaintext
