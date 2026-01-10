#!/usr/bin/env python3
"""Prepare SWE-agent batch instances from a Loc-Bench JSONL dataset."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def load_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_num, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_num} of {path}") from exc


def build_repo_path(repo_root: Path, repo_slug: str) -> Path:
    return repo_root / repo_slug.replace("/", "_")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Loc-Bench JSONL into SWE-agent instances.jsonl.",
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to Loc-Bench JSONL (e.g., data/Loc-Bench_V1_dataset.jsonl).",
    )
    parser.add_argument(
        "--repo-root",
        required=True,
        help="Root directory holding local repo mirrors (e.g., locbench_repos).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output instances.jsonl path.",
    )
    parser.add_argument(
        "--image-name",
        default="",
        help=(
            "Docker image name for instances. Leave empty for local deployment. "
            "Set to e.g. python:3.11 for docker runs."
        ),
    )
    parser.add_argument(
        "--filter",
        default=None,
        help="Optional regex filter on instance_id.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of instances to emit.",
    )
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Skip instances whose repo folder is missing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_path = Path(args.dataset)
    repo_root = Path(args.repo_root)
    output_path = Path(args.output)

    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}", file=sys.stderr)
        return 2
    if not repo_root.exists():
        print(f"Repo root not found: {repo_root}", file=sys.stderr)
        return 2

    regex = re.compile(args.filter) if args.filter else None
    missing_repos: list[str] = []
    count = 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out_handle:
        for record in load_jsonl(dataset_path):
            instance_id = record.get("instance_id")
            if not instance_id:
                continue
            if regex and not regex.search(instance_id):
                continue

            repo_slug = record.get("repo")
            if not repo_slug:
                continue
            repo_path = build_repo_path(repo_root, repo_slug)
            if not repo_path.exists():
                if args.skip_missing:
                    continue
                missing_repos.append(repo_slug)
                continue

            base_commit = record.get("base_commit") or "HEAD"
            problem_statement = record.get("problem_statement") or ""

            instance = {
                "image_name": args.image_name,
                "problem_statement": problem_statement,
                "instance_id": instance_id,
                "repo_name": str(repo_path),
                "base_commit": base_commit,
                "extra_fields": {
                    "repo_slug": repo_slug,
                    "repo_path": str(repo_path),
                    "base_commit": base_commit,
                },
            }
            out_handle.write(json.dumps(instance, ensure_ascii=True) + "\n")
            count += 1
            if args.limit and count >= args.limit:
                break

    if missing_repos:
        missing_preview = ", ".join(missing_repos[:10])
        msg = f"Missing {len(missing_repos)} repos (first 10: {missing_preview})"
        if args.skip_missing:
            print(f"Warning: {msg}", file=sys.stderr)
        else:
            print(msg, file=sys.stderr)
            return 3

    print(f"Wrote {count} instances to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
