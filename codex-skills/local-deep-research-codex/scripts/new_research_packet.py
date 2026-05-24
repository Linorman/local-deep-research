#!/usr/bin/env python3
"""Create a WebUI-like Codex research packet template."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


MODES = ("quick", "detailed", "report")


def default_budget(mode: str) -> tuple[int, str, str]:
    if mode == "quick":
        return 1, "2-4", "3-6"
    if mode == "detailed":
        return 3, "4-8", "8-18"
    return 5, "6-12", "15-35"


def build_packet(query: str, mode: str, engine: str | None, strategy: str | None) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    iterations, subquestions, searches = default_budget(mode)
    engine_text = engine or "discover with list_search_engines"
    strategy_text = strategy or "discover with list_strategies"
    return f"""# LDR Codex Research Packet

Created: {now}
Mode: {mode}

## Objective

{query}

## Configuration

- LDR access:
- Selected engines: {engine_text}
- Strategy vocabulary: {strategy_text}
- Iteration budget: {iterations}
- Subquestion target: {subquestions}
- Search target: {searches}
- Date/time assumptions:
- Privacy constraints:

## Plan

| ID | Subquestion | Search terms | Engine | Status |
| --- | --- | --- | --- | --- |
| Q1 |  |  |  | pending |

## Source Ledger

| Source ID | Engine | Title | URL or local ID | Date | Why it matters | Credibility / limitation |
| --- | --- | --- | --- | --- | --- | --- |
| S01 |  |  |  |  |  |  |

## Iteration Notes

### Iteration 1

- Searches run:
- New sources:
- New claims:
- Conflicts:
- Gaps:

## Claim Table

| Claim | Source IDs | Confidence | Limitation |
| --- | --- | --- | --- |
|  |  |  |  |

## Current Knowledge

-

## Open Gaps

-

## Final Output Checklist

- [ ] Every major claim has source IDs.
- [ ] Evidence and inference are separated.
- [ ] Conflicts or weak coverage are disclosed.
- [ ] Final answer states that Codex generated the synthesis using LDR retrieval.
- [ ] Source list is included.
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a working research packet for WebUI-like Codex LDR research.",
    )
    parser.add_argument("--query", required=True, help="Research question.")
    parser.add_argument(
        "--mode",
        choices=MODES,
        default="report",
        help="Research mode budget to prefill.",
    )
    parser.add_argument("--engine", help="Preferred LDR search engine.")
    parser.add_argument("--strategy", help="Preferred LDR strategy vocabulary.")
    parser.add_argument(
        "--output",
        required=True,
        help="Output markdown path. Use a scratch path unless this packet is a deliverable.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing output file.",
    )
    args = parser.parse_args()

    output = Path(args.output).expanduser()
    if output.exists() and not args.force:
        parser.error(f"output already exists: {output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        build_packet(args.query, args.mode, args.engine, args.strategy),
        encoding="utf-8",
    )
    print(str(output.resolve()))  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
