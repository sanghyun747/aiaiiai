"""Synthetic ZIP round-trip and malformed/malicious archive rejection."""
import zipfile

import pytest
from app import exports


def test_synthetic_roundtrip(follower_case, tmp_path):
    paths = exports.write_synthetic_pair(follower_case, tmp_path)
    old = exports.parse_export(paths["old"])
    cur = exports.parse_export(paths["current"])
    assert len(old["followers"]) == follower_case["expected"]["old_count"]
    assert len(cur["followers"]) == follower_case["expected"]["current_count"]
    assert {r["username"] for r in cur["following"]} == {"tp_missing"}


def test_non_zip_rejected(tmp_path):
    bad = tmp_path / "not.zip"
    bad.write_bytes(b"this is not a zip file at all")
    with pytest.raises(exports.ExportError) as exc:
        exports.parse_export(bad)
    assert exc.value.code == "INVALID_ZIP"


def test_zip_without_follower_member_rejected(tmp_path):
    z = tmp_path / "wrong.zip"
    with zipfile.ZipFile(z, "w") as fh:
        fh.writestr("readme.txt", "hello")
    with pytest.raises(exports.ExportError) as exc:
        exports.parse_export(z)
    assert exc.value.code == "UNSUPPORTED_EXPORT"


def test_path_traversal_member_rejected(tmp_path):
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as fh:
        fh.writestr("../../etc/passwd", "root")
        fh.writestr(exports.FOLLOWERS_PATH, "[]")
    with pytest.raises(exports.ExportError) as exc:
        exports.parse_export(z)
    assert exc.value.code == "INVALID_ZIP"


def test_corrupt_json_member_rejected(tmp_path):
    z = tmp_path / "corrupt.zip"
    with zipfile.ZipFile(z, "w") as fh:
        fh.writestr(exports.FOLLOWERS_PATH, "{not json")
    with pytest.raises(exports.ExportError) as exc:
        exports.parse_export(z)
    assert exc.value.code == "INVALID_ZIP"


def test_minimize_drops_everything_but_handle_and_time():
    rows = exports.minimize([{"username": "a", "timestamp": 5, "email": "x@y.z", "href": "u"}])
    assert rows == [{"username": "a", "timestamp": 5}]
