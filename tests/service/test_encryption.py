import pytest

from news.service.encryption import decrypt, encrypt

KEY = b"k" * 32
CONTEXT = b"reader:credential"


@pytest.mark.parametrize("plaintext", [b"", b"sentinel-provider-key", "clé privée".encode()])
def test_aes256_round_trip(plaintext: bytes) -> None:
    encrypted = encrypt(KEY, plaintext, CONTEXT, b"n" * 12)

    assert encrypted != plaintext
    assert decrypt(KEY, encrypted, CONTEXT) == plaintext


def test_nonces_produce_distinct_ciphertexts() -> None:
    assert encrypt(KEY, b"secret", CONTEXT, b"a" * 12) != encrypt(
        KEY, b"secret", CONTEXT, b"b" * 12
    )


@pytest.mark.parametrize("change", ["key", "context", "tamper", "truncated"])
def test_decryption_rejects_wrong_keys_context_and_damaged_data(change: str) -> None:
    encrypted = encrypt(KEY, b"sentinel-provider-key", CONTEXT, b"n" * 12)
    key, context = KEY, CONTEXT
    if change == "key":
        key = b"x" * 32
    elif change == "context":
        context = b"another-reader:credential"
    elif change == "tamper":
        encrypted = encrypted[:-1] + bytes([encrypted[-1] ^ 1])
    else:
        encrypted = encrypted[:10]

    with pytest.raises(ValueError, match="Cannot decrypt"):
        decrypt(key, encrypted, context)


@pytest.mark.parametrize("key", [b"", b"k" * 16, b"k" * 24, b"k" * 33])
def test_only_256_bit_keys_are_accepted(key: bytes) -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        encrypt(key, b"secret", CONTEXT, b"n" * 12)


@pytest.mark.parametrize("nonce", [b"", b"n" * 11, b"n" * 13])
def test_only_96_bit_nonces_are_accepted(nonce: bytes) -> None:
    with pytest.raises(ValueError, match="12 bytes"):
        encrypt(KEY, b"secret", CONTEXT, nonce)
