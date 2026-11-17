#!/usr/bin/env python3
"""Persist observed L2 Update fingerprints, never publication approval."""
import argparse
import json
from pathlib import Path

from compare_nc_capture import load_capture, compare


def update_registry(current, previous):
    previous_records = previous.get("records", {})
    if previous.get("schemaVersion", 1) != 1:
        raise ValueError("Unsupported registry schema")
    if not isinstance(previous_records, dict):
        raise ValueError("Invalid registry records")
    for key, item in previous_records.items():
        if not isinstance(item, dict) or not isinstance(item.get("contentHash"), str):
            raise ValueError(f"Invalid prior record: {key}")
    changes = compare(current, previous_records)
    merged = dict(previous_records)  # keep IDs outside the current 18-item window
    for item in current.values():
        merged[item["id"]] = {key: value for key, value in item.items() if key != "status"}
    return {"schemaVersion": 1, "board": "l2update", "records": merged}, changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("--previous", type=Path, help="Existing persistent registry, if any")
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    previous = json.loads(args.previous.read_text(encoding="utf-8")) if args.previous and args.previous.exists() else {}
    registry, changes = update_registry(load_capture(args.capture), previous)
    report = {
        "board": "l2update",
        "baseline": not bool(previous),
        "records": changes,
        "counts": {status: sum(x["status"] == status for x in changes) for status in ("new", "changed", "unchanged")},
        "warning": "Observed source changes only; NOT reviewed, translated or published.",
    }
    for path, data in ((args.registry, registry), (args.report, report)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Editorial source changes:", report["counts"])


if __name__ == "__main__":
    main()
