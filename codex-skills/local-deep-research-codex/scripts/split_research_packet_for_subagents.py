#!/usr/bin/env python3
"""Split an LDR Codex research packet into bounded sub-agent work packets."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


VALID_MODES = {"codex_like", "ldr_exact", "codex_bridge_exact"}
VALID_STAGES = {"active", "post_run_qa"}


def parse_source_ids(packet_text: str) -> list[str]:
    ids: list[str] = []
    for line in packet_text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells:
            continue
        source_id = cells[0]
        if re.fullmatch(r"S\d+", source_id) and source_id not in ids:
            ids.append(source_id)
    return ids


def parse_objective(packet_text: str) -> str:
    match = re.search(
        r"## Objective\s*(?P<body>.*?)(?:\n## |\Z)",
        packet_text,
        flags=re.S,
    )
    if not match:
        return "Review the supplied research packet."
    body = match.group("body").strip()
    return body or "Review the supplied research packet."


def chunks(values: list[str], size: int) -> list[list[str]]:
    size = max(1, size)
    return [values[index : index + size] for index in range(0, len(values), size)]


def packet_body(
    *,
    role: str,
    task_id: str,
    objective: str,
    source_ids: list[str],
    mode: str,
    stage: str,
) -> str:
    allowed = ", ".join(source_ids) if source_ids else "none assigned"
    return f"""# Sub-Agent Packet: {task_id}

Role: {role}
Mode: {mode}
Stage: {stage}

## Objective

{objective}

## Allowed Sources

{allowed}

## Required Output Schema

- task id: {task_id}
- input packet id: main
- sources touched:
- claims supported:
- unresolved gaps:
- confidence notes:
- canonical citation ids changed: no

## Merge Constraints

- Do not renumber source ids or citation ids.
- Do not mutate the main source ledger.
- Separate evidence from inference.
- Report unsupported claims explicitly.
"""


def write_task(
    output_dir: Path,
    *,
    index: int,
    role: str,
    objective: str,
    source_ids: list[str],
    mode: str,
    stage: str,
) -> dict[str, Any]:
    task_id = f"{index:03d}-{role.replace('_', '-')}"
    path = output_dir / f"{task_id}.md"
    path.write_text(
        packet_body(
            role=role,
            task_id=task_id,
            objective=objective,
            source_ids=source_ids,
            mode=mode,
            stage=stage,
        ),
        encoding="utf-8",
    )
    return {
        "task_id": task_id,
        "role": role,
        "path": str(path),
        "source_ids": source_ids,
    }


def build_tasks(
    *,
    mode: str,
    stage: str,
    objective: str,
    source_ids: list[str],
    output_dir: Path,
    max_sources_per_packet: int,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    index = 1

    if mode == "ldr_exact":
        if stage != "post_run_qa":
            raise ValueError(
                "ldr_exact runs should not be split during active execution; use stage=post_run_qa for QA packets."
            )
        return [
            write_task(
                output_dir,
                index=index,
                role="benchmark_reviewer",
                objective=objective,
                source_ids=source_ids,
                mode=mode,
                stage=stage,
            )
        ]

    if mode == "codex_bridge_exact":
        for source_chunk in chunks(source_ids, max_sources_per_packet) or [[]]:
            tasks.append(
                write_task(
                    output_dir,
                    index=index,
                    role="evidence_auditor",
                    objective=objective,
                    source_ids=source_chunk,
                    mode=mode,
                    stage=stage,
                )
            )
            index += 1
        return tasks

    roles = ["retrieval_worker", "evidence_auditor", "section_worker"]
    for role in roles:
        for source_chunk in chunks(source_ids, max_sources_per_packet) or [[]]:
            tasks.append(
                write_task(
                    output_dir,
                    index=index,
                    role=role,
                    objective=objective,
                    source_ids=source_chunk,
                    mode=mode,
                    stage=stage,
                )
            )
            index += 1
    return tasks


def split_packet(
    packet: str | Path,
    *,
    mode: str,
    output_dir: str | Path,
    max_sources_per_packet: int = 8,
    stage: str = "active",
) -> dict[str, Any]:
    mode = mode.strip().lower().replace("-", "_")
    stage = stage.strip().lower().replace("-", "_")
    if mode not in VALID_MODES:
        raise ValueError(f"mode must be one of: {sorted(VALID_MODES)}")
    if stage not in VALID_STAGES:
        raise ValueError(f"stage must be one of: {sorted(VALID_STAGES)}")

    packet_path = Path(packet).expanduser()
    packet_text = packet_path.read_text(encoding="utf-8")
    source_ids = parse_source_ids(packet_text)
    objective = parse_objective(packet_text)

    output_path = Path(output_dir).expanduser()
    output_path.mkdir(parents=True, exist_ok=True)
    tasks = build_tasks(
        mode=mode,
        stage=stage,
        objective=objective,
        source_ids=source_ids,
        output_dir=output_path,
        max_sources_per_packet=max_sources_per_packet,
    )
    manifest = {
        "packet": str(packet_path.resolve()),
        "mode": mode,
        "stage": stage,
        "source_ids": source_ids,
        "tasks": tasks,
    }
    manifest_path = output_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split an LDR Codex research packet into bounded sub-agent packets.",
    )
    parser.add_argument("--packet", required=True, help="Input research packet markdown.")
    parser.add_argument("--mode", required=True, choices=sorted(VALID_MODES))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-sources-per-packet", type=int, default=8)
    parser.add_argument("--stage", choices=sorted(VALID_STAGES), default="active")
    args = parser.parse_args()

    try:
        manifest = split_packet(
            args.packet,
            mode=args.mode,
            output_dir=args.output_dir,
            max_sources_per_packet=args.max_sources_per_packet,
            stage=args.stage,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(manifest, indent=2, sort_keys=True))  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
