import json

from sociclaw.scripts.cli import build_parser


def test_cli_trello_normalize_success(monkeypatch, capsys):
    class DummyList:
        def __init__(self, name):
            self.name = name

    class DummyBoard:
        def list_lists(self, state):
            assert state == "open"
            return [DummyList("February 2026"), DummyList("Backlog")]

    class DummyTrelloSync:
        def __init__(self, api_key=None, token=None, board_id=None, request_delay_seconds=0):
            self.api_key = api_key
            self.token = token
            self.board_id = board_id or "board"
            self.board = DummyBoard()

        def setup_board(self):
            return None

    monkeypatch.setattr("sociclaw.scripts.cli.TrelloSync", DummyTrelloSync)

    parser = build_parser()
    args = parser.parse_args(
        [
            "trello-normalize",
            "--api-key",
            "k",
            "--token",
            "t",
            "--board-id",
            "b",
        ]
    )
    rc = args.func(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["open_lists"] == ["February 2026", "Backlog"]


def test_cli_trello_normalize_error(monkeypatch, capsys):
    class DummyTrelloSync:
        def __init__(self, *args, **kwargs):
            raise ValueError("missing trello creds")

    monkeypatch.setattr("sociclaw.scripts.cli.TrelloSync", DummyTrelloSync)

    parser = build_parser()
    args = parser.parse_args(["trello-normalize"])
    rc = args.func(args)
    assert rc == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "missing trello creds" in payload["error"]
