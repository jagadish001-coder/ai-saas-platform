import pytest
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("MyPassword1")
        assert hashed != "MyPassword1"

    def test_correct_password_verifies(self):
        hashed = hash_password("MyPassword1")
        assert verify_password("MyPassword1", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("MyPassword1")
        assert verify_password("WrongPassword", hashed) is False

    def test_different_passwords_different_hashes(self):
        h1 = hash_password("Password1")
        h2 = hash_password("Password1")
        # bcrypt salts should differ
        assert h1 != h2


class TestJWT:
    def test_access_token_has_correct_type(self):
        token = create_access_token("user-123", role="user")
        payload = decode_token(token)
        assert payload["type"] == "access"
        assert payload["sub"] == "user-123"
        assert payload["role"] == "user"

    def test_refresh_token_has_correct_type(self):
        token = create_refresh_token("user-123")
        payload = decode_token(token)
        assert payload["type"] == "refresh"
        assert payload["sub"] == "user-123"

    def test_invalid_token_raises(self):
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_token("this.is.not.a.valid.token")

    def test_tampered_token_raises(self):
        from jose import JWTError
        token = create_access_token("user-123")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_token(tampered)
