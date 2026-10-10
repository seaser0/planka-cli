"""Pure helpers: jq semantics and table rendering."""
from planka import cli


def test_apply_jq_no_filter_passthrough():
    assert cli.apply_jq([1, 2], None) == [1, 2]


def test_apply_jq_single_result_unwraps():  # issue #16
    assert cli.apply_jq([{"id": "1"}], ".[0].id") == "1"


def test_apply_jq_multiple_results_stay_list():
    assert cli.apply_jq([{"id": "1"}, {"id": "2"}], ".[].id") == ["1", "2"]


def test_fmt_cell_label_list_joins_names():  # issue #6/#7
    assert cli._fmt_cell([{"name": "a"}, {"name": "b"}]) == "a, b"


def test_fmt_cell_flattens_and_truncates():
    out = cli._fmt_cell("x\n" + "y" * 200, width=10)
    assert "\n" not in out and len(out) == 10 and out.endswith("…")


def test_to_table_scalar_does_not_crash(capsys):  # issue #16
    cli.to_table("1882472739193751390")
    assert "1882472739193751390" in capsys.readouterr().out


def test_to_table_list_of_scalars(capsys):
    cli.to_table(["a", "b"])
    assert capsys.readouterr().out.split() == ["a", "b"]


def test_to_table_empty(capsys):
    cli.to_table([])
    assert "No data" in capsys.readouterr().out


def test_kv_table_skips_empty_and_keeps_markup(capsys):  # issue #24
    cli.to_table({"name": "n", "dueDate": None, "description": "- [ ] todo\n- [x] done", "labels": []})
    out = capsys.readouterr().out
    assert "dueDate" not in out and "labels" not in out
    assert "[ ] todo" in out and "[x] done" in out  # not swallowed as rich markup
