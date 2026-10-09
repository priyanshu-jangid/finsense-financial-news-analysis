
from backend.app.core.security import hash_password, verify_password


def test_password_is_hashed():
    password = "StrongPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2")


def test_correct_password_verifies():
    password = "StrongPassword123!"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_incorrect_password_fails():
    hashed = hash_password("StrongPassword123!")

    assert verify_password("WrongPassword123!", hashed) is False

