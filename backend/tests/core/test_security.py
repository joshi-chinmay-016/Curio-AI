"""
Unit tests for core cryptographic and security utilities (Phase 2, Task 2):
- Bcrypt password hashing, salting, and verification.
- PyJWT token creation, claims, expiration, tampering, and invalid token handling.
"""
from datetime import timedelta
import time
import pytest
import jwt

from backend.app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_password_hashing():
    """Verify password hashing produces a non-empty, valid bcrypt hash."""
    plain = "SuperSecretPassword123!"
    hashed = get_password_hash(plain)

    assert isinstance(hashed, str)
    assert len(hashed) > 0
    assert hashed != plain
    # Bcrypt format check: $2b$ or $2a$ prefix
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


def test_password_salting():
    """Verify that hashing the same password twice yields distinct salted hashes."""
    plain = "IdenticalPasswordToHash"
    hash_1 = get_password_hash(plain)
    hash_2 = get_password_hash(plain)

    assert hash_1 != hash_2, "Salting failed: identical passwords produced identical hashes"
    assert verify_password(plain, hash_1) is True
    assert verify_password(plain, hash_2) is True


def test_password_verification_success():
    """Verify that the correct password verifies against the hash."""
    plain = "CorrectPassword_42"
    hashed = get_password_hash(plain)

    assert verify_password(plain, hashed) is True


def test_password_verification_failure():
    """Verify that an incorrect password fails verification."""
    plain = "CorrectPassword_42"
    hashed = get_password_hash(plain)

    assert verify_password("WrongPassword_99", hashed) is False


def test_password_verification_edge_cases():
    """Verify verification handles empty values and malformed hashes gracefully without crashing."""
    valid_hash = get_password_hash("test_password")

    # Empty inputs
    assert verify_password("", valid_hash) is False
    assert verify_password("test_password", "") is False
    assert verify_password("", "") is False

    # Malformed / garbage hash strings
    assert verify_password("test_password", "not_a_bcrypt_hash") is False
    assert verify_password("test_password", "$2b$invalid$malformed$hash$data") is False

    # Empty password to hasher raises ValueError
    with pytest.raises(ValueError, match="Password cannot be empty"):
        get_password_hash("")


def test_jwt_contains_expected_subject_and_expiration():
    """Verify access token payload contains 'sub', 'exp', and 'iat' claims."""
    subject = "user_uuid_123456"
    token = create_access_token(subject=subject)

    payload = decode_access_token(token)

    assert payload["sub"] == subject
    assert "exp" in payload
    assert "iat" in payload
    assert payload["exp"] > payload["iat"]


def test_jwt_valid_decode():
    """Verify a valid token decodes successfully and returns expected payload."""
    subject = "test@curio.ai"
    token = create_access_token(subject=subject, expires_delta=timedelta(minutes=15))

    payload = decode_access_token(token)
    assert payload["sub"] == subject


def test_jwt_expired_token_rejected():
    """Verify that an expired token is rejected with ExpiredSignatureError."""
    subject = "expired_user"
    # Create token that expired 10 seconds ago
    token = create_access_token(subject=subject, expires_delta=timedelta(seconds=-10))

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_jwt_tampered_token_rejected():
    """Verify that modifying the token signature or payload causes signature validation to fail."""
    subject = "legit_user"
    token = create_access_token(subject=subject)

    # Split JWT into header, payload, signature
    parts = token.split(".")
    assert len(parts) == 3

    # Tamper with the signature portion (flip characters)
    tampered_sig = parts[2][:-4] + ("XXXX" if not parts[2].endswith("XXXX") else "YYYY")
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered_token)

    # Tamper with the payload portion
    tampered_payload_token = f"{parts[0]}.eyJhZG1pbiI6dHJ1ZX0.{parts[2]}"
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered_payload_token)


def test_jwt_invalid_token_rejected():
    """Verify completely malformed or arbitrary strings are rejected with InvalidTokenError."""
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("this-is-not-a-jwt-token")

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("header.only")

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("")


def test_jwt_custom_expiration_duration():
    """Verify custom expires_delta sets appropriate expiration window."""
    subject = "custom_expiry_user"
    custom_minutes = 30
    token = create_access_token(subject=subject, expires_delta=timedelta(minutes=custom_minutes))

    payload = decode_access_token(token)
    expected_duration = custom_minutes * 60
    actual_duration = payload["exp"] - payload["iat"]

    # Allow slight execution clock skew (< 5s)
    assert abs(actual_duration - expected_duration) < 5
