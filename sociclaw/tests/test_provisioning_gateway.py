from sociclaw.scripts.provisioning_gateway import SociClawProvisioningGatewayClient


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
        self.post_calls.append({"url": url, "headers": headers or {}, "json": json, "timeout": timeout})
        return DummyResponse(self.response_json)


def test_gateway_provisioning_sends_optional_auth_header():
    sess = DummySession({"data": {"api_key": "sk_u", "wallet_address": "0xabc"}})
    c = SociClawProvisioningGatewayClient(url="https://example.com/api/sociclaw/provision", internal_token="t", session=sess)
    res = c.provision(provider="telegram", provider_user_id=123, create_api_key=True)

    assert res.api_key == "sk_u"
    assert res.wallet_address == "0xabc"

    assert len(sess.post_calls) == 1
    call = sess.post_calls[0]
    assert call["headers"]["Authorization"] == "Bearer t"
    assert call["headers"]["Content-Type"] == "application/json"
    assert call["json"]["provider_user_id"] == "123"


def test_gateway_requires_url():
    try:
        SociClawProvisioningGatewayClient(url="  ")
    except ValueError as e:
        assert "url is required" in str(e)
    else:
        raise AssertionError("expected ValueError")

