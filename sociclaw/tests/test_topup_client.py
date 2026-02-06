from sociclaw.scripts.topup_client import TopupClient


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")
        return None

    def json(self):
        return self._payload


class DummySession:
    def __init__(self):
        self.calls = []

    def request(self, method, url, headers=None, json=None, timeout=None):
        self.calls.append(
            {
                "method": str(method).upper(),
                "url": url,
                "headers": headers or {},
                "json": json,
                "timeout": timeout,
            }
        )
        if "topup/start" in url:
            return DummyResponse(
                {
                    "sessionId": "sess_1",
                    "depositAddress": "0xdeposit",
                    "amountUsdcExact": "5.000000",
                }
            )
        if "topup/claim" in url:
            return DummyResponse({"success": True, "status": "credited", "sessionId": "sess_1"})
        if "topup/status" in url:
            return DummyResponse({"success": True, "status": "pending", "sessionId": "sess_1"})
        return DummyResponse({}, status_code=404)


def test_topup_client_start_claim_status():
    sess = DummySession()
    client = TopupClient(api_key="sk_test", base_url="https://api.sociclaw.com", session=sess)

    started = client.start_topup(expected_amount_usd=5)
    claimed = client.claim_topup(session_id=started.session_id, tx_hash="0x" + ("ab" * 32))
    status = client.status_topup(session_id=started.session_id)

    assert started.session_id == "sess_1"
    assert started.deposit_address == "0xdeposit"
    assert started.amount_usdc_exact == "5.000000"
    assert claimed["status"] == "credited"
    assert status["status"] == "pending"
    assert len(sess.calls) == 3


def test_topup_client_requires_base_url():
    try:
        TopupClient(api_key="sk_test", base_url="")
    except ValueError as e:
        assert "base_url is required" in str(e)
    else:
        raise AssertionError("expected ValueError")
