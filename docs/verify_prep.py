#!/usr/bin/env python3
"""Read-only preparation/ownership checks. Not an application or provider test.

Supports only the JSON Schema keywords actually used in this preparation contract.
No files are created, changed or deleted; mutation probes use in-memory copies.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))


def resolve(document: dict, ref: str) -> Any:
    require(ref.startswith("#/"), f"External reference unsupported: {ref}")
    node: Any = document
    for part in ref[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def validate(value: Any, schema: dict, document: dict, path: str = "$") -> None:
    if "$ref" in schema:
        validate(value, resolve(document, schema["$ref"]), document, path)
        return
    if "anyOf" in schema:
        for branch in schema["anyOf"]:
            try:
                validate(value, branch, document, path)
                return
            except ValueError:
                pass
        raise ValueError(f"{path}: no anyOf branch matched")
    predicates = {
        "null": lambda x: x is None,
        "object": lambda x: isinstance(x, dict),
        "array": lambda x: isinstance(x, list),
        "string": lambda x: isinstance(x, str),
        "boolean": lambda x: type(x) is bool,
        "integer": lambda x: type(x) is int,
        "number": lambda x: type(x) in (int, float) and math.isfinite(x),
    }
    types = schema.get("type")
    if types is not None:
        types = [types] if isinstance(types, str) else types
        require(any(predicates[t](value) for t in types), f"{path}: incorrect type")
    if "const" in schema:
        require(value == schema["const"], f"{path}: wrong const")
    if "enum" in schema:
        require(value in schema["enum"], f"{path}: wrong enum")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        require(set(schema.get("required", [])).issubset(value), f"{path}: missing required field")
        if schema.get("additionalProperties") is False:
            require(set(value).issubset(props), f"{path}: extra property")
        for key in value.keys() & props.keys():
            validate(value[key], props[key], document, f"{path}.{key}")
    if isinstance(value, list):
        require(len(value) >= schema.get("minItems", 0), f"{path}: too few items")
        require(len(value) <= schema.get("maxItems", float("inf")), f"{path}: too many items")
        for i, item in enumerate(value):
            validate(item, schema.get("items", {}), document, f"{path}[{i}]")
    if isinstance(value, str):
        require(len(value) >= schema.get("minLength", 0), f"{path}: too short")
        require(len(value) <= schema.get("maxLength", float("inf")), f"{path}: too long")
        if "pattern" in schema:
            require(re.search(schema["pattern"], value) is not None, f"{path}: pattern mismatch")
        if schema.get("format") == "date-time":
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            require(dt.tzinfo is not None, f"{path}: timezone missing")
    if type(value) in (int, float):
        require(value >= schema.get("minimum", -float("inf")), f"{path}: below minimum")
        require(value <= schema.get("maximum", float("inf")), f"{path}: above maximum")


def references(node: Any, document: dict) -> None:
    if isinstance(node, dict):
        if "$ref" in node:
            resolve(document, node["$ref"])
        for child in node.values():
            references(child, document)
    elif isinstance(node, list):
        for child in node:
            references(child, document)


def check_result(run: dict, document: dict, profile: dict, seed: dict) -> None:
    validate(run, document["components"]["schemas"]["Run"], document)
    result = run["result"]
    require(result is not None, "sample result missing")
    require(run["is_mock"] is True, "sample must be labeled mock")
    require(result["evidence_mode"] == "synthetic" and bool(result["sample_notice"]), "sample label missing")
    require(all(t["mode"] == "mock" for t in run["trace"]), "sample trace cannot be live")
    sources = result["sources"]
    source_ids = {s["id"] for s in sources}
    require(len(source_ids) == len(sources), "duplicate source IDs")
    for s in sources:
        require(s["source_mode"] == "synthetic" and s["url"] is None, "synthetic source misrepresented")
    for item in result["actions"] + result["opportunities"]:
        require(set(item["source_ids"]).issubset(source_ids), "unknown source reference")
    require(len(result["actions"]) == 3, "sample needs exactly three experiments")
    modes = {a["strategy_mode"] for a in result["actions"]}
    require("safe_bet" in modes and "growth_experiment" in modes, "sample must include safe bet and growth experiment")
    for action in result["actions"]:
        package = action["production_package"]
        require(package["script"]["hook"].strip() != "", "production script hook missing")
        require(len(package["shot_list"]) >= 1, "shot list missing")
        require([shot["order"] for shot in package["shot_list"]] == list(range(1, len(package["shot_list"]) + 1)), "shot order must be consecutive")
        require(all(shot["duration_sec"] > 0 for shot in package["shot_list"]), "invalid shot duration")
        require(package["publishing_package"]["title"].strip() != "", "publishing title missing")
        if action["strategy_mode"] == "growth_experiment":
            require(bool(action["weakness_target"]), "growth experiment must target one weakness")
    require(sum(a["production_minutes"] for a in result["actions"]) <= profile["weekly_minutes"], "production budget exceeded")
    require(all(a["baseline"] is None for a in result["actions"]), "sample baseline invented")
    f = result["followers"]
    require(f is not None, "sample followers missing")
    for key, expected in seed["expected"].items():
        require(f[key] == expected, f"seed/count mismatch: {key}")
    require(f["raw_missing_count"] == sum(f[k] for k in ("outside_window_count", "renamed_still_following_count", "relationship_absent_count", "unresolved_count", "explicitly_inactive_count")), "count partition mismatch")
    require(f["old_count"] == f["retained_count"] + f["raw_missing_count"], "old count mismatch")
    require(f["current_count"] == f["retained_count"] + f["raw_new_count"], "current count mismatch")
    require(f["export_count_delta"] == f["current_count"] - f["old_count"], "delta mismatch")
    require(len(f["audits"]) == f["raw_missing_count"] - f["outside_window_count"], "audit coverage incomplete")
    for audit in f["audits"]:
        if audit["status"] in ("confirmed_rename_still_current_follower", "username_change_not_ruled_out"):
            require(audit["relationship_absent"] is False, "ineligible audit promoted to absence")
        if audit["relationship_absent"]:
            require(bool(audit["active_evidence"]), "absence lacks active evidence")
    digest = hashlib.sha256((ROOT / "fixtures/report-sample.md").read_bytes()).hexdigest()
    require(result["artifacts"][0]["sha256"] == digest, "sample report hash mismatch")


def git(*args: str) -> str:
    process = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, encoding="utf-8", check=False)
    require(process.returncode == 0, f"git {' '.join(args)} failed: {process.stderr.strip()}")
    return process.stdout


def ownership(base: str, owner: str) -> None:
    prefix = "frontend/" if owner == "A" else "backend/"
    changed: set[str] = set()
    for args in (("diff", "--name-only", "--no-renames", base, "HEAD"), ("diff", "--name-only", "--no-renames"), ("diff", "--cached", "--name-only", "--no-renames"), ("ls-files", "--others", "--exclude-standard")):
        changed.update(git(*args).splitlines())
    forbidden = sorted(p for p in changed if not p.startswith(prefix))
    require(not forbidden, f"owner {owner} touched forbidden paths: {forbidden}")
    for args in (("diff", "--name-only", "--no-renames", "--diff-filter=D", base, "HEAD"), ("diff", "--name-only", "--no-renames", "--diff-filter=D"), ("diff", "--cached", "--name-only", "--no-renames", "--diff-filter=D")):
        require(not git(*args).strip(), "deletion is not authorized")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    parser.add_argument("--owner", choices=["A", "B"])
    args = parser.parse_args()
    checks: list[str] = []
    try:
        require(bool(args.base) == bool(args.owner), "use --base and --owner together")
        required = ["README.md", "AGENTS.md", "contracts/HTTP.md", "contracts/v1.openapi.json", "fixtures/run-sample.json", "fixtures/follower-case.json", "fixtures/profile-sample.json", "fixtures/report-sample.md", "docs/PROVIDERS_AND_TESTS.md", "handoff/SESSION_A.md", "handoff/SESSION_B.md", "handoff/INTEGRATION.md"]
        require(all((ROOT / p).is_file() for p in required), "required preparation file missing")
        checks.append("required_files")
        document = load("contracts/v1.openapi.json")
        require(document["info"]["version"] == "1.1.0", "contract version mismatch")
        references(document, document)
        checks.append("internal_schema_references")
        profile = load("fixtures/profile-sample.json")
        validate(profile, document["components"]["schemas"]["Profile"], document)
        checks.append("profile_schema_subset")
        sample, seed = load("fixtures/run-sample.json"), load("fixtures/follower-case.json")
        check_result(sample, document, profile, seed)
        checks.append("response_schema_counts_audits_sources_budget_hash")
        mutations = []
        bad = copy.deepcopy(sample); bad["status"] = "complete"; mutations.append(("invalid_status", bad))
        bad = copy.deepcopy(sample); bad["result"]["actions"][0]["source_ids"] = ["invented"]; mutations.append(("invented_source", bad))
        bad = copy.deepcopy(sample); bad["result"]["followers"]["relationship_absent_count"] = 4; mutations.append(("false_loss_count", bad))
        bad = copy.deepcopy(sample); bad["result"]["followers"]["audits"][0]["relationship_absent"] = True; mutations.append(("rename_as_loss", bad))
        bad = copy.deepcopy(sample); bad["trace"][0]["mode"] = "live"; mutations.append(("fake_live_trace", bad))
        bad = copy.deepcopy(sample); bad["result"]["actions"][0]["production_minutes"] = 1200; mutations.append(("over_budget", bad))
        bad = copy.deepcopy(sample); bad["result"]["actions"][2]["strategy_mode"] = "safe_bet"; mutations.append(("missing_growth_experiment", bad))
        bad = copy.deepcopy(sample); bad["result"]["actions"][2]["weakness_target"] = None; mutations.append(("growth_without_weakness", bad))
        bad = copy.deepcopy(sample); bad["result"]["actions"][0]["production_package"]["shot_list"][0]["order"] = 2; mutations.append(("bad_shot_order", bad))
        bad = copy.deepcopy(sample); bad["result"]["artifacts"][0]["sha256"] = "0" * 64; mutations.append(("wrong_artifact_hash", bad))
        for name, mutated in mutations:
            rejected = False
            try:
                check_result(mutated, document, profile, seed)
            except ValueError:
                rejected = True
            require(rejected, f"negative probe not detected: {name}")
            checks.append("reject_" + name)
        if args.base:
            ownership(args.base, args.owner)
            checks.append("branch_path_ownership_no_deletions")
        print(json.dumps({"ok": True, "scope": "preparation subset only; app/providers NOT TESTED", "checks": checks, "contract_sha256": hashlib.sha256((ROOT / "contracts/v1.openapi.json").read_bytes()).hexdigest()}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({"ok": False, "passed": checks, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
