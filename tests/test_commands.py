"""Commands end-to-end through main() against a fake API."""
import json

import pytest
from conftest import BACKLOG_ID


def test_help_runs_without_api(monkeypatch, capsys):
    import sys

    from planka import cli
    monkeypatch.setattr(sys, "argv", ["planka", "--help"])
    with pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code == 0
    assert "cards" in capsys.readouterr().out


def test_cards_create_jq_id(run, fake):  # issue #22
    assert run("cards", "create", "Autobots", "Backlog", "new card", "-o", "json", "--jq", ".id").strip() == '"999"'
    assert ("POST", f"/api/lists/{BACKLOG_ID}/cards",
            {"name": "new card", "type": "project", "position": 65536}) in fake.calls


def test_cards_update_returns_object(run):  # issue #22
    out = json.loads(run("cards", "update", "Autobots", "301", "--name", "renamed", "-o", "json"))
    assert isinstance(out, dict) and out["name"] == "renamed"


def test_cards_update_table_is_key_value(run):  # issue #24
    out = run("cards", "update", "Autobots", "301", "--description", "hello")
    lines = [line for line in out.splitlines() if "│" in line]
    assert any("name" in line and "zz-test" in line for line in lines)  # one row per field
    assert any("description" in line and "hello" in line for line in lines)
    assert "coverAttachmentId" not in out  # null fields skipped
    assert "…" not in out


def test_cards_get_json_keeps_array_shape(run):
    out = json.loads(run("cards", "get", "Autobots", "301", "-o", "json"))
    assert isinstance(out, list) and out[0]["labels"] == "homelab" and out[0]["members"] == "seaser"


def test_cards_get_jq_index(run):
    assert run("cards", "get", "Autobots", "PSD", "--jq", ".[0].list").strip() == "Backlog"


def test_cards_get_table_keeps_line_breaks(run):  # issue #24
    out = run("cards", "get", "Autobots", "301")
    assert "- [ ] export" in out and "- [ ] rescan" in out


def test_cards_comments_json_not_truncated(run):  # issue #20
    out = json.loads(run("cards", "comments", "Autobots", "301", "-o", "json"))
    assert [c["id"] for c in out] == ["c1", "c2"]  # sorted by createdAt
    assert len(out[1]["text"]) == 300


def test_cards_list_carries_labels(run):  # issue #6/#7
    out = json.loads(run("cards", "list", "Autobots", "Backlog", "-o", "json"))
    assert {c["id"] for c in out} == {"301", "303"}
    assert next(c for c in out if c["id"] == "301")["labels"][0]["name"] == "homelab"


def test_ambiguous_partial_match_refuses(run):  # issue #4
    with pytest.raises(SystemExit, match="Ambiguous match: 2 cards"):
        run("cards", "get", "Autobots", "Immich")


def test_in_scope_disambiguates(run):
    out = run("cards", "update", "Autobots", "Immich", "--in", "Done", "--name", "x", "-o", "json", "--jq", ".id")
    assert out.strip() == '"302"'


def test_unknown_board_exits(run):
    with pytest.raises(SystemExit, match="Board not found"):
        run("cards", "list", "Nope", "Backlog")
