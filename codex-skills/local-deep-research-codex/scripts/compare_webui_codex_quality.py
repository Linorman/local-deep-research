#!/usr/bin/env python3
"""Compare completed WebUI/Codex research outputs with lightweight metrics."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SOURCE_RE = re.compile(r"https?://[^\s)\]>]+")
CITATION_RE = re.compile(r"\[(\d+|S\d+)\]")


def read_output(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def extract_sources(text: str) -> set[str]:
    return {match.rstrip(".,;") for match in SOURCE_RE.findall(text)}


def extract_citations(text: str) -> set[str]:
    return set(CITATION_RE.findall(text))


def score_overlap(candidate: set[str], reference: set[str]) -> float:
    if not reference:
        return 0.0 if candidate else 1.0
    return round(len(candidate & reference) / len(reference), 4)


def section_coverage(candidate: str, reference: str) -> float:
    reference_headings = {
        line.strip().lower()
        for line in reference.splitlines()
        if line.lstrip().startswith("#")
    }
    candidate_headings = {
        line.strip().lower()
        for line in candidate.splitlines()
        if line.lstrip().startswith("#")
    }
    if not reference_headings:
        return 0.0 if not candidate_headings else 1.0
    return round(len(reference_headings & candidate_headings) / len(reference_headings), 4)


def compare(topic: str, mode: str, candidate: str, reference: str) -> dict[str, Any]:
    candidate_sources = extract_sources(candidate)
    reference_sources = extract_sources(reference)
    candidate_citations = extract_citations(candidate)
    unsupported_claim_count = max(0, candidate.count("\n- ") - len(candidate_citations))
    return {
        "topic": topic,
        "mode": mode,
        "source_count": len(candidate_sources),
        "source_overlap_with_webui": score_overlap(candidate_sources, reference_sources),
        "citation_support_score": 1.0 if candidate_citations else 0.0,
        "section_coverage_score": section_coverage(candidate, reference),
        "unsupported_claim_count": unsupported_claim_count,
        "grader_summary": "Lightweight structural comparison; use human or LLM grading for factual parity.",
    }


def markdown_summary(metrics: list[dict[str, Any]]) -> str:
    lines = [
        "# WebUI/Codex Quality Comparison",
        "",
        "| Topic | Mode | Sources | Source overlap | Citation score | Section score | Unsupported claims |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in metrics:
        lines.append(
            "| {topic} | {mode} | {source_count} | {source_overlap_with_webui} | {citation_support_score} | {section_coverage_score} | {unsupported_claim_count} |".format(
                **row
            )
        )
    return "\n".join(lines) + "\n"


def parse_mode_output(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected MODE=PATH")
    mode, path = value.split("=", 1)
    return mode.strip(), Path(path).expanduser()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare completed ldr_exact, codex_bridge_exact, and codex_like outputs.",
    )
    parser.add_argument("--topic", required=True)
    parser.add_argument("--webui-output", required=True, help="Reference ldr_exact output file.")
    parser.add_argument(
        "--mode-output",
        action="append",
        type=parse_mode_output,
        default=[],
        help="Candidate output as MODE=PATH. Repeat for multiple modes.",
    )
    parser.add_argument("--json-output")
    parser.add_argument("--markdown-output")
    args = parser.parse_args()

    reference = read_output(args.webui_output)
    metrics = [
        compare(args.topic, mode, read_output(path), reference)
        for mode, path in args.mode_output
    ]

    text = json.dumps(metrics, indent=2, ensure_ascii=False, sort_keys=True)
    if args.json_output:
        Path(args.json_output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)  # noqa: T201
    if args.markdown_output:
        Path(args.markdown_output).write_text(markdown_summary(metrics), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
