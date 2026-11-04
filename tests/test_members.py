"""users set-password and board members, against a recording fake client."""
import io
from types import SimpleNamespace

import pytest

from planka import cli

USER = {"id": "9", "name": "Wheeljack", "email": "wheeljack@autobots.ai"}
BOARD = {"included": {"users": [USER], "boardMemberships": [{"userId": "9", "role": "editor", "canComment": None}]}}


class Client:
    def __init__(self):
        self.calls = []

    def patch(self, endpoint, data):
        self.calls.append(("patch", endpoint, data))

    def post(self, endpoint, data):
        self.calls.append(("post", endpoint, data))


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(cli, "resolve_user", lambda c, ref: USER)
    monkeypatch.setattr(cli, "resolve_board_id", lambda c, ref: "100")
    monkeypatch.setattr(cli, "get_board_data", lambda c, b: BOARD)
    return Client()


def test_set_password_reads_stdin(client, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("s3cret\n"))
    cli.users_set_password(client, SimpleNamespace(user="Wheeljack"))
    assert client.calls == [("patch", "/api/users/9/password", {"password": "s3cret"})]
    assert "s3cret" not in capsys.readouterr().out


def test_set_password_rejects_empty(client, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("\n"))
    with pytest.raises(SystemExit):
        cli.users_set_password(client, SimpleNamespace(user="Wheeljack"))
    assert client.calls == []


def test_add_member_editor(client):
    cli.boards_add_member(client, SimpleNamespace(board="Autobots", user="Wheeljack", role="editor"))
    assert client.calls == [("post", "/api/boards/100/board-memberships", {"userId": "9", "role": "editor"})]


def test_add_member_viewer_can_comment(client):
    cli.boards_add_member(client, SimpleNamespace(board="Autobots", user="Wheeljack", role="viewer"))
    assert client.calls[0][2]["canComment"] is True


def test_members_lists_names(client, monkeypatch):
    seen = []
    monkeypatch.setattr(cli, "output", lambda rows, args: seen.extend(rows))
    cli.boards_members(client, SimpleNamespace(board="Autobots"))
    assert seen[0]["user"] == "Wheeljack" and seen[0]["role"] == "editor"
