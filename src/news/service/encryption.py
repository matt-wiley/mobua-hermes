"""Authenticated encryption for Reader Data Keys and credentials (ADR 0009)."""

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionError(ValueError):
    """Key configuration or ciphertext authentication failed; messages contain no key data."""


def _validate_key(key: bytes) -> None:
    if len(key) != 32:
        raise EncryptionError("Encryption keys must be exactly 32 bytes")


def encrypt(key: bytes, plaintext: bytes, context: bytes, nonce: bytes) -> bytes:
    _validate_key(key)
    if len(nonce) != 12:
        raise EncryptionError("Encryption nonces must be exactly 12 bytes")
    return nonce + AESGCM(key).encrypt(nonce, plaintext, context)


def decrypt(key: bytes, ciphertext: bytes, context: bytes) -> bytes:
    _validate_key(key)
    if len(ciphertext) < 28:
        raise EncryptionError("Cannot decrypt credential or Data Key")
    try:
        return AESGCM(key).decrypt(ciphertext[:12], ciphertext[12:], context)
    except InvalidTag:
        raise EncryptionError("Cannot decrypt credential or Data Key") from None
