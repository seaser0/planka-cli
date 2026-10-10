"""Shared fixtures: a fake Planka API so commands run end-to-end via main()."""
import sys

import pytest

from planka import cli

BOARD_ID = "100"
BACKLOG_ID = "200"
DONE_ID = "201"

PROJECTS = {"items": [], "included": {"boards": [{"id": BOARD_ID, "name": "Autobots"}]}}

BOARD = {
    "item": {"id": BOARD_ID, "name": "Autobots"},
    "included": {
        "lists": [{"id": BACKLOG_ID, "name": "Backlog"}, {"id": DONE_ID, "name": "Done"}],
        "cards": [
            {"id": "301", "name": "Immich PSD export", "listId": BACKLOG_ID, "type": "project",
             "description": "## To do\n- [ ] export\n- [ ] rescan"},
            {"id": "302", "name": "Immich upgrade", "listId": DONE_ID, "type": "project"},
            {"id": "303", "name": "Paperless restart", "listId": BACKLOG_ID, "type": "story"},
        ],
        "labels": [{"id": "401", "name": "homelab", "color": "wet-moss"}],
        "cardLabels": [{"cardId": "301", "labelId": "401"}],
    },
}


def raw_card(card_id, **over):
    """A raw API card item with the ~18 fields Planka really returns."""
    item = {
        "id": card_id, "name": "zz-test", "description": None, "type": "project",
        "boardId": BOARD_ID, "listId": BACKLOG_ID, "creatorUserId": "9", "position": 65536,
        "dueDate": None, "isDueCompleted": None, "stopwatch": None, "commentsTotal": 0,
        "isClosed": False, "coverAttachmentId": None, "prevListId": None,
        "createdAt": "2026-10-10T02:47:08.179Z", "updatedAt": None,
        "listChangedAt": "2026-10-10T02:47:08.126Z",
    }
    item.update(over)
    return {"item": item}


class FakeClient:
    def __init__(self):
        self.calls = []
        self.routes = {
            "/api/projects": PROJECTS,
            f"/api/boards/{BOARD_ID}": BOARD,
            "/api/cards/301": {
                "item": BOARD["included"]["cards"][0],
                "included": {"cardLabels": [{"labelId": "401"}],
                             "cardMemberships": [{"userId": "9"}],
                             "users": [{"id": "9", "name": "seaser"}]},
            },
            "/api/cards/301/comments": {"items": [
                {"id": "c2", "createdAt": "2026-10-10", "text": "B" * 300},
                {"id": "c1", "createdAt": "2026-10-09", "text": "first"},
            ]},
        }

    def get(self, endpoint):
        self.calls.append(("GET", endpoint, None))
        return self.routes[endpoint]

    def post(self, endpoint, data):
        self.calls.append(("POST", endpoint, data))
        return raw_card("999", name=data.get("name", "x"))

    def patch(self, endpoint, data):
        self.calls.append(("PATCH", endpoint, data))
        return raw_card(endpoint.rsplit("/", 1)[-1], **data)

    def delete(self, endpoint):
        self.calls.append(("DELETE", endpoint, None))
        return {}


@pytest.fixture
def fake(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(cli, "PlankaClient", lambda: client)
    return client


@pytest.fixture
def run(fake, monkeypatch, capsys):
    """run("cards", "get", "Autobots", "301") -> captured stdout."""
    def _run(*argv):
        monkeypatch.setattr(sys, "argv", ["planka", *argv])
        cli.main()
        return capsys.readouterr().out
    return _run
