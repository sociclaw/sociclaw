import requests

from sociclaw.scripts.http_retry import request_with_retry


class DummyResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FlakySession:
    def __init__(self, sequence):
        self.sequence = list(sequence)
        self.calls = 0

    def request(self, method, url, headers=None, json=None, timeout=None):
        self.calls += 1
        current = self.sequence.pop(0)
        if isinstance(current, Exception):
            raise current
        return current


def test_request_with_retry_retries_on_status(monkeypatch):
    monkeypatch.setattr("sociclaw.scripts.http_retry.time.sleep", lambda _: None)
    monkeypatch.setattr("sociclaw.scripts.http_retry.random.uniform", lambda a, b: 0.0)

    session = FlakySession([DummyResponse(429), DummyResponse(200)])
    resp = request_with_retry(
        session=session,
        method="POST",
        url="https://example.com",
        max_retries=2,
    )

    assert resp.status_code == 200
    assert session.calls == 2


def test_request_with_retry_retries_on_exception(monkeypatch):
    monkeypatch.setattr("sociclaw.scripts.http_retry.time.sleep", lambda _: None)
    monkeypatch.setattr("sociclaw.scripts.http_retry.random.uniform", lambda a, b: 0.0)

    session = FlakySession(
        [requests.Timeout("timeout"), DummyResponse(200)]
    )
    resp = request_with_retry(
        session=session,
        method="GET",
        url="https://example.com",
        max_retries=2,
    )

    assert resp.status_code == 200
    assert session.calls == 2


def test_request_with_retry_raises_after_retries(monkeypatch):
    monkeypatch.setattr("sociclaw.scripts.http_retry.time.sleep", lambda _: None)
    monkeypatch.setattr("sociclaw.scripts.http_retry.random.uniform", lambda a, b: 0.0)

    session = FlakySession([requests.ConnectionError("boom"), requests.ConnectionError("boom2")])

    try:
        request_with_retry(
            session=session,
            method="GET",
            url="https://example.com",
            max_retries=1,
        )
    except requests.ConnectionError:
        pass
    else:
        raise AssertionError("Expected requests.ConnectionError")

    assert session.calls == 2
