"""Instagram export ZIP generation (synthetic) and safe parsing.

Never touches user originals; synthetic ZIPs are written under
backend/.runtime/<run-id>/ and retained (no automatic cleanup).
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from .config import MAX_UNCOMPRESSED_BYTES, MAX_ZIP_ENTRIES

FOLLOWERS_PATH = "connections/followers_and_following/followers_1.json"
FOLLOWING_PATH = "connections/followers_and_following/following.json"


class ExportError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _string_list(records):
    return [
        {"title": "", "media_list_data": [], "string_list_data": [
            {"href": "", "value": r["username"], "timestamp": r.get("timestamp", 0)}]}
        for r in records
    ]


def write_synthetic_pair(case: dict, outdir: Path):
    """Write a deterministic synthetic old/current export ZIP pair."""
    outdir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for side in ("old", "current"):
        zpath = outdir / f"{side}_export.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(FOLLOWERS_PATH, json.dumps(_string_list(case[f"{side}_followers"]), ensure_ascii=False))
            z.writestr(FOLLOWING_PATH, json.dumps(
                {"relationships_following": _string_list(case.get(f"{side}_following") or [])}, ensure_ascii=False))
            z.writestr("SYNTHETIC_NOTICE.txt", "Synthetic TrendPilot test data. Fictitious handles only.")
        paths[side] = zpath
    return paths


def _read_json_member(z: zipfile.ZipFile, name: str):
    try:
        return json.loads(z.read(name).decode("utf-8"))
    except KeyError:
        raise ExportError("UNSUPPORTED_EXPORT", f"Export is missing {name}.")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ExportError("INVALID_ZIP", f"{name} is not valid UTF-8 JSON.")


def _flatten(node):
    if isinstance(node, dict):
        for key in ("relationships_following", "relationships_followers"):
            if key in node:
                return _flatten(node[key])
        node = [node]
    out = []
    for entry in node or []:
        for s in (entry.get("string_list_data") or []):
            value = s.get("value")
            if not isinstance(value, str) or not value:
                continue
            ts = s.get("timestamp")
            out.append({"username": value, "timestamp": ts if isinstance(ts, int) else 0})
    return out


def parse_export(path: Path) -> dict:
    """Parse one export ZIP with archive-safety checks."""
    if not zipfile.is_zipfile(path):
        raise ExportError("INVALID_ZIP", "Uploaded file is not a valid ZIP archive.")
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        if len(infos) > MAX_ZIP_ENTRIES:
            raise ExportError("ZIP_LIMIT_EXCEEDED", "Archive has too many entries.")
        total = 0
        for info in infos:
            name = info.filename
            if name.startswith("/") or ".." in Path(name).parts:
                raise ExportError("INVALID_ZIP", "Archive contains an unsafe member path.")
            total += info.file_size
            if total > MAX_UNCOMPRESSED_BYTES:
                raise ExportError("ZIP_LIMIT_EXCEEDED", "Archive uncompressed size limit exceeded.")
        names = set(z.namelist())
        fpath = FOLLOWERS_PATH if FOLLOWERS_PATH in names else next(
            (n for n in names if n.endswith("followers_1.json")), None)
        if fpath is None:
            raise ExportError("UNSUPPORTED_EXPORT", "Not a recognised Instagram follower export.")
        followers = _flatten(_read_json_member(z, fpath))
        gpath = FOLLOWING_PATH if FOLLOWING_PATH in names else next(
            (n for n in names if n.endswith("following.json")), None)
        following = _flatten(_read_json_member(z, gpath)) if gpath else []
    if not followers:
        raise ExportError("UNSUPPORTED_EXPORT", "Export contains no follower records.")
    return {"followers": followers, "following": following}


def minimize(records):
    """Only username + timestamp leave this process toward Daytona."""
    return [{"username": r["username"], "timestamp": int(r.get("timestamp") or 0)} for r in records]
