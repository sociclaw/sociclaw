from sociclaw.scripts.provisioning_gateway import SociClawProvisioningGatewayClient


class DummyResponse:
    def __init__(self, json_data):
        self._json = json_data
        self.status_checked = False
        self.status_code = 200

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

    def request(self, method, url, headers=None, json=None, timeout=None):
        if str(method).upper() != "POST":
            raise AssertionError(f"Unexpected method: {method}")
        return self.post(url, headers=headers, json=json, timeout=timeout)


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


def test_gateway_api_key_contract_order_prefers_data_api_key():
    sess = DummySession(
        {
            "api_key": "sk_top",
            "image_api_key": "sk_top_image",
            "data": {
                "api_key": "sk_data",
                "image_api_key": "sk_data_image",
                "wallet_address": "0xabc",
            },
        }
    )
    c = SociClawProvisioningGatewayClient(
        url="https://example.com/api/sociclaw/provision",
        session=sess,
    )
    res = c.provision(provider="telegram", provider_user_id=123, create_api_key=True)

    assert res.api_key == "sk_data"

