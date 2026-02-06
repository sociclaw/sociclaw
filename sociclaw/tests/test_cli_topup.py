import json
from pathlib import Path

from sociclaw.scripts.cli import build_parser
from sociclaw.scripts.local_session_store import LocalSessionStore
from sociclaw.scripts.state_store import StateStore


class FakeTopupClient:
    def __init__(self, api_key, base_url=None):
        self.api_key = api_key
        self.base_url = base_url

    class Started:
        def __init__(self):
            self.session_id = "sess_test"
            self.deposit_address = "0xdeposit"
            self.amount_usdc_exact = "3.000000"

    def start_topup(self, expected_amount_usd):
        return FakeTopupClient.Started()

    def claim_topup(self, session_id, tx_hash):
        return {"success": True, "status": "credited", "sessionId": session_id, "txHash": tx_hash}

    def status_topup(self, session_id):
        return {"success": True, "status": "pending", "sessionId": session_id}


class FakeTopupClientWait(FakeTopupClient):
    def __init__(self, api_key, base_url=None):
        super().__init__(api_key, base_url)
        self._status_calls = 0

    def claim_topup(self, session_id, tx_hash):
        return {"success": True, "status": "confirming", "sessionId": session_id, "txHash": tx_hash}

    def status_topup(self, session_id):
        self._status_calls += 1
        if self._status_calls >= 1:
            return {"success": True, "status": "credited", "sessionId": session_id}
        return {"success": True, "status": "confirming", "sessionId": session_id}


def _prepare_user(state_path: Path, provider="telegram", provider_user_id="123"):
    store = StateStore(state_path)
    store.upsert_user(
        provider=provider,
        provider_user_id=provider_user_id,
        image_api_key="sk_user_abc",
    )


VALID_TX_HASH = "0x" + ("ab" * 32)


def test_cli_topup_start_stores_session(tmp_path, monkeypatch, capsys):
    state_path = tmp_path / "state.json"
    session_db = tmp_path / "sessions.db"
    _prepare_user(state_path)

    monkeypatch.setattr("sociclaw.scripts.cli.TopupClient", FakeTopupClient)
    parser = build_parser()
    args = parser.parse_args(
        [
            "topup-start",
            "--provider",
            "telegram",
            "--provider-user-id",
            "123",
            "--amount-usd",
            "3",
            "--state-path",
            str(state_path),
            "--session-db-path",
            str(session_db),
            "--base-url",
            "https://api.sociclaw.com",
        ]
    )
    rc = args.func(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["session_id"] == "sess_test"

    sessions = LocalSessionStore(session_db)
    record = sessions.get_session("telegram:123")
    assert record is not None
    assert record.session_id == "sess_test"


def test_cli_topup_claim_uses_stored_session_and_clears_on_credit(tmp_path, monkeypatch, capsys):
    state_path = tmp_path / "state.json"
    session_db = tmp_path / "sessions.db"
    _prepare_user(state_path)

    sessions = LocalSessionStore(session_db)
    sessions.upsert_session("telegram:123", "sess_test")

    monkeypatch.setattr("sociclaw.scripts.cli.TopupClient", FakeTopupClient)
    parser = build_parser()
    args = parser.parse_args(
        [
            "topup-claim",
            "--provider",
            "telegram",
            "--provider-user-id",
            "123",
            "--tx-hash",
            VALID_TX_HASH,
            "--state-path",
            str(state_path),
            "--session-db-path",
            str(session_db),
            "--base-url",
            "https://api.sociclaw.com",
        ]
    )
    rc = args.func(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "credited"
    assert sessions.get_session("telegram:123") is None


def test_cli_topup_claim_waits_until_terminal_status(tmp_path, monkeypatch, capsys):
    state_path = tmp_path / "state.json"
    session_db = tmp_path / "sessions.db"
    _prepare_user(state_path)

    sessions = LocalSessionStore(session_db)
    sessions.upsert_session("telegram:123", "sess_test")

    monkeypatch.setattr("sociclaw.scripts.cli.TopupClient", FakeTopupClientWait)
    monkeypatch.setattr("sociclaw.scripts.cli.time.sleep", lambda _: None)
    parser = build_parser()
    args = parser.parse_args(
        [
            "topup-claim",
            "--provider",
            "telegram",
            "--provider-user-id",
            "123",
            "--tx-hash",
            VALID_TX_HASH,
            "--wait",
            "--wait-timeout-seconds",
            "10",
            "--wait-interval-seconds",
            "1",
            "--state-path",
            str(state_path),
            "--session-db-path",
            str(session_db),
            "--base-url",
            "https://api.sociclaw.com",
        ]
    )
    rc = args.func(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "credited"
    assert sessions.get_session("telegram:123") is None


def test_cli_topup_claim_rejects_invalid_tx_hash(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    session_db = tmp_path / "sessions.db"
    _prepare_user(state_path)
    LocalSessionStore(session_db).upsert_session("telegram:123", "sess_test")

    monkeypatch.setattr("sociclaw.scripts.cli.TopupClient", FakeTopupClientWait)
    parser = build_parser()
    args = parser.parse_args(
        [
            "topup-claim",
            "--provider",
            "telegram",
            "--provider-user-id",
            "123",
            "--tx-hash",
            "bad_hash",
            "--state-path",
            str(state_path),
            "--session-db-path",
            str(session_db),
            "--base-url",
            "https://api.sociclaw.com",
        ]
    )

    try:
        args.func(args)
    except SystemExit as e:
        assert "Invalid tx hash format" in str(e)
    else:
        raise AssertionError("expected SystemExit")
