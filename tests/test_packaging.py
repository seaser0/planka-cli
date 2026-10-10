"""Version single-sourcing: pyproject and uv.lock must agree (the 4.6.0 drift)."""
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_lock_version_matches_pyproject():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    locked = next(p["version"] for p in lock["package"] if p["name"] == "planka-cli")
    assert locked == version
