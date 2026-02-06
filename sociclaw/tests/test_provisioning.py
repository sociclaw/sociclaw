from sociclaw.scripts.provisioning_client import ProvisioningClient


class DummyResponse:
    def __init__(self, json_data):
        self._json = json_data
        self.status_checked = False

    def raise_for_status(self):
        self.status_checked = True
        return None

    def json(self):
        return self._json


class DummySession:
    def __init__(self, response_json):
        self.response_json = response_json
        self.post_calls = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.post_calls.append(
            {
                "url": url,
                "headers": headers or {},
                "json": json,
                "timeout": timeout,
            }
        )
        return DummyResponse(self.response_json)


def test_provisioning_minimal_request_and_parse_top_level():
    sess = DummySession({"api_key": "sk_test_123", "wallet_address": "0xabc"})
    c = ProvisioningClient(openclaw_secret="secret", url="https://api.example.com/provision", session=sess)
    res = c.provision(provider="telegram", provider_user_id=123, create_api_key=True)

    assert res.provider == "telegram"
    assert res.provider_user_id == "123"
    assert res.api_key == "sk_test_123"
    assert res.wallet_address == "0xabc"

    assert len(sess.post_calls) == 1
    call = sess.post_calls[0]
    assert call["url"] == "https://api.example.com/provision"
    assert call["headers"]["x-openclaw-secret"] == "secret"
    assert call["headers"]["Content-Type"] == "application/json"
    assert call["json"] == {"provider": "telegram", "provider_user_id": "123", "create_api_key": True}
    assert isinstance(call["timeout"], int)


def test_provisioning_parse_nested_data():
    sess = DummySession({"data": {"api_key": "sk_nested", "wallet": "0xdef"}})
    c = ProvisioningClient(openclaw_secret="secret", url="https://api.example.com/provision", session=sess)
    res = c.provision(provider="telegram", provider_user_id="u1", create_api_key=True)

    assert res.api_key == "sk_nested"
    assert res.wallet_address == "0xdef"


def test_provisioning_requires_secret():
    try:
        ProvisioningClient(openclaw_secret="  ", url="https://api.example.com/provision")
    except ValueError as e:
        assert "openclaw_secret is required" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_provisioning_requires_url():
    try:
        ProvisioningClient(openclaw_secret="secret", url="  ")
    except ValueError as e:
        assert "Provisioning URL is required" in str(e)
    else:
        raise AssertionError("expected ValueError")

