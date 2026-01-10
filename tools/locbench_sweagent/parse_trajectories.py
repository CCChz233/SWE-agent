#!/usr/bin/env python3
"""Parse SWE-agent trajectories into Loc-Bench loc_outputs.jsonl format."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

JSON_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    data = []
    with path.open("r", encoding="utf-8") as handle:
        for line_num, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_num} of {path}") from exc
    return data


def normalize_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = [value]
    result: list[str] = []
    seen = set()
    for item in items:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def extract_json_payload(text: str) -> tuple[dict[str, Any] | None, str | None]:
    if not text:
        return None, None

    candidates: list[str] = []
    for match in JSON_CODE_BLOCK_RE.finditer(text):
        candidate = match.group(1).strip()
        if candidate:
            candidates.append(candidate)

    if not candidates:
        candidates.append(text.strip())

    for candidate in candidates:
        payload = _try_load_json(candidate)
        if payload is not None:
            return payload, candidate

    for candidate in _iter_json_substrings(text):
        payload = _try_load_json(candidate)
        if payload is not None:
            return payload, candidate

    return None, None


def _try_load_json(candidate: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _iter_json_substrings(text: str):
    starts = [i for i, ch in enumerate(text) if ch == "{"]
    for start in starts:
        depth = 0
        for idx in range(start, len(text)):
            char = text[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    yield text[start : idx + 1]
                    break


def entities_to_modules(found_entities: list[str]) -> list[str]:
    modules: list[str] = []
    seen = set()
    for entity in found_entities:
        if ":" not in entity:
            continue
        file_path, name = entity.split(":", 1)
        module_name = name.split(".")[0]
        module_id = f"{file_path}:{module_name}" if module_name else file_path
        if module_id in seen:
            continue
        seen.add(module_id)
        modules.append(module_id)
    return modules


def build_meta(record: dict[str, Any]) -> dict[str, Any]:
    meta = {}
    for key in ("repo", "base_commit", "problem_statement", "patch", "test_patch"):
        if key in record:
            meta[key] = record[key]
    return meta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert SWE-agent trajectories to Loc-Bench localization outputs.",
    )
    parser.add_argument(
        "--traj-dir",
        required=True,
        help="Directory containing .traj files (output_dir from sweagent run-batch).",
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to Loc-Bench JSONL (for meta_data fields).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output loc_outputs.jsonl path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    traj_dir = Path(args.traj_dir)
    dataset_path = Path(args.dataset)
    output_path = Path(args.output)

    if not traj_dir.exists():
        print(f"Trajectory directory not found: {traj_dir}", file=sys.stderr)
        return 2
    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}", file=sys.stderr)
        return 2

    bench_data = {item.get("instance_id"): item for item in load_jsonl(dataset_path)}
    traj_files = sorted(traj_dir.rglob("*.traj"))
    if not traj_files:
        print(f"No .traj files found under {traj_dir}", file=sys.stderr)
        return 3

    output_path.parent.mkdir(parents=True, exist_ok=True)
    missing_payload = 0

    with output_path.open("w", encoding="utf-8") as out_handle:
        for traj_path in traj_files:
            instance_id = traj_path.stem
            if instance_id not in bench_data:
                continue
            try:
                traj_data = json.loads(traj_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON: {traj_path}", file=sys.stderr)
                continue

            trajectory = traj_data.get("trajectory", [])
            payload = None
            raw_response = None
            for step in reversed(trajectory):
                response = step.get("response") or ""
                parsed, _ = extract_json_payload(response)
                if parsed is not None:
                    payload = parsed
                    raw_response = response
                    break

            if payload is None:
                missing_payload += 1
                raw_response = trajectory[-1].get("response") if trajectory else ""
                payload = {}

            found_files = normalize_list(payload.get("found_files"))
            found_entities = normalize_list(payload.get("found_entities"))
            if not found_files and found_entities:
                found_files = normalize_list([item.split(":", 1)[0] for item in found_entities if ":" in item])
            found_modules = normalize_list(payload.get("found_modules"))
            if not found_modules and found_entities:
                found_modules = entities_to_modules(found_entities)

            output_record = {
                "instance_id": instance_id,
                "found_files": found_files,
                "found_modules": found_modules,
                "found_entities": found_entities,
                "raw_output_loc": [raw_response] if raw_response else [],
                "meta_data": build_meta(bench_data[instance_id]),
            }
            out_handle.write(json.dumps(output_record, ensure_ascii=True) + "\n")

    if missing_payload:
        print(f"Warning: {missing_payload} instances had no JSON payload.", file=sys.stderr)

    print(f"Wrote loc outputs to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
