from sociclaw.scripts.validators import (
    validate_provider,
    validate_provider_user_id,
    validate_tx_hash,
)


def test_validate_provider_ok():
    assert validate_provider("telegram") == "telegram"
    assert validate_provider("my-provider_1") == "my-provider_1"


def test_validate_provider_rejects_invalid():
    try:
        validate_provider("x")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_validate_provider_user_id_ok():
    assert validate_provider_user_id("123:abc_xyz@test") == "123:abc_xyz@test"


def test_validate_tx_hash_ok():
    tx = "0x" + ("ab" * 32)
    assert validate_tx_hash(tx) == tx


def test_validate_tx_hash_rejects_invalid():
    try:
        validate_tx_hash("0x123")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
