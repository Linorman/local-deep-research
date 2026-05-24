#!/usr/bin/env python3
"""Helper for manually responding to Codex bridge request files."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RESPONSE_CONTRACTS = {
    "report_structure": (
        "Return only the report outline requested by LDR. Preserve required "
        "STRUCTURE/END_STRUCTURE markers if the prompt asks for them."
    ),
    "search_question_generation": (
        "Return search questions only, one per line. Use the exact line prefix "
        "requested by the prompt, typically 'Q:'. Do not add commentary."
    ),
    "citation_synthesis": (
        "Return only the source-grounded synthesis requested by LDR. Preserve "
        "citation markers and do not invent unsupported claims."
    ),
    "pubmed_query_transform": (
        "Return only the PubMed query string. Do not add explanations, bullets, "
        "markdown fences, or labels."
    ),
    "historical_query_classifier": (
        "Return exactly 'yes' or 'no' in lowercase, with no punctuation or "
        "explanation."
    ),
    "fact_check": (
        "Return only the factual consistency analysis requested by LDR, grounded "
        "in the supplied sources."
    ),
    "relevance_filter": (
        "Return only the relevance indices or labels in the exact format requested "
        "by the prompt."
    ),
    "general_llm": (
        "Return only the content that should be written to the bridge response."
    ),
}


def bridge_paths(bridge_dir: str | Path) -> tuple[Path, Path]:
    root = Path(bridge_dir).expanduser()
    return root / "requests", root / "responses"


def list_requests(bridge_dir: str | Path) -> list[Path]:
    requests_dir, responses_dir = bridge_paths(bridge_dir)
    if not requests_dir.exists():
        return []
    pending: list[Path] = []
    for request in sorted(requests_dir.glob("*.json")):
        if not (responses_dir / request.name).exists():
            pending.append(request)
    return pending


def load_request(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not payload.get("id"):
        raise ValueError("bridge request is missing id")
    if not isinstance(payload.get("messages"), list):
        raise ValueError("bridge request is missing messages list")
    return payload


def request_prompt_text(request: dict[str, Any]) -> str:
    chunks: list[str] = []
    for message in request.get("messages", []):
        content = message.get("content", "")
        if isinstance(content, str):
            chunks.append(content)
        else:
            chunks.append(json.dumps(content, ensure_ascii=False))
    return "\n".join(chunks)


def classify_request(request: dict[str, Any]) -> str:
    text = request_prompt_text(request).lower()
    if "optimized pubmed search query" in text or "pubmed search query" in text:
        return "pubmed_query_transform"
    if "answer only" in text and "yes" in text and "historical" in text:
        return "historical_query_classifier"
    if (
        "determine the most appropriate report structure" in text
        or "return a table of contents structure" in text
        or ("structure" in text and "end_structure" in text)
    ):
        return "report_structure"
    if (
        "high-quality internet search questions" in text
        or "one question per line" in text
        or "format: one question per line" in text
    ):
        return "search_question_generation"
    if (
        "using the previous knowledge and new sources" in text
        or "citation" in text
        and "source" in text
        and "synthesis" in text
    ):
        return "citation_synthesis"
    if "factual consistency" in text or "fact check" in text:
        return "fact_check"
    if "relevant indices" in text or "return the indices" in text:
        return "relevance_filter"
    return "general_llm"


def response_contract(kind: str) -> str:
    return RESPONSE_CONTRACTS.get(kind, RESPONSE_CONTRACTS["general_llm"])


def validate_response_for_kind(kind: str, content: str) -> list[str]:
    stripped = content.strip()
    warnings: list[str] = []
    if not stripped:
        return ["response is empty"]

    if kind == "historical_query_classifier":
        if stripped.lower() not in {"yes", "no"} or stripped != stripped.lower():
            warnings.append("historical classifier must be exactly 'yes' or 'no'")
    elif kind == "search_question_generation":
        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        if not any(line.startswith("Q:") for line in lines):
            warnings.append("search question generation should include 'Q:' lines")
    elif kind == "report_structure":
        upper = stripped.upper()
        if "STRUCTURE" in upper and "END_STRUCTURE" not in upper:
            warnings.append("report structure has STRUCTURE without END_STRUCTURE")
    elif kind == "pubmed_query_transform":
        if "\n" in stripped:
            warnings.append("PubMed query transform should be a single query string")
        lowered = stripped.lower()
        if lowered.startswith(("here", "sure", "the query", "pubmed query")):
            warnings.append("PubMed query transform should not include explanation text")
    return warnings


def append_manifest(
    manifest_output: str | Path,
    *,
    request: dict[str, Any],
    request_path: str | Path | None,
    response_path: str | Path,
    kind: str,
    warnings: list[str] | None = None,
) -> None:
    manifest_path = Path(manifest_output)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "request_id": request["id"],
        "kind": kind,
        "model": request.get("model"),
        "request_path": str(request_path) if request_path else None,
        "response_path": str(response_path),
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "validation_warnings": warnings or [],
    }
    with manifest_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def format_prompt(request: dict[str, Any]) -> str:
    kind = classify_request(request)
    lines = [
        "Answer this Local Deep Research Codex bridge request.",
        f"Request id: {request['id']}",
        f"Model: {request.get('model', 'unspecified')}",
        f"Detected request kind: {kind}",
        f"Response contract: {response_contract(kind)}",
        "",
        "Messages:",
    ]
    for message in request.get("messages", []):
        role = message.get("role", "user")
        content = message.get("content", "")
        lines.append(f"\n[{role}]\n{content}")
    lines.extend(
        [
            "",
            "Return only the content that should be written to the bridge response.",
        ]
    )
    return "\n".join(lines)


def write_response(
    bridge_dir: str | Path,
    request_id: str,
    content: str,
    usage: dict[str, Any] | None = None,
    *,
    request: dict[str, Any] | None = None,
    request_path: str | Path | None = None,
    manifest_output: str | Path | None = None,
    validation_warnings: list[str] | None = None,
) -> Path:
    _, responses_dir = bridge_paths(bridge_dir)
    responses_dir.mkdir(parents=True, exist_ok=True)
    response_path = responses_dir / f"{request_id}.json"
    payload = {
        "id": request_id,
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "content": content,
        "usage": usage or {"input_tokens": 0, "output_tokens": 0},
    }
    response_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    if request is not None and manifest_output is not None:
        append_manifest(
            manifest_output,
            request=request,
            request_path=request_path,
            response_path=response_path,
            kind=classify_request(request),
            warnings=validation_warnings,
        )
    return response_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Format or write responses for Codex bridge request files.",
    )
    parser.add_argument("--bridge-dir", required=True)
    parser.add_argument("--request-id", help="Request id to format/respond to.")
    parser.add_argument("--list", action="store_true", help="List pending request files.")
    parser.add_argument("--print-prompt", action="store_true")
    parser.add_argument("--classify", action="store_true")
    parser.add_argument("--response-file", help="File containing response content.")
    parser.add_argument("--response-stdin", action="store_true")
    parser.add_argument("--response-text", help="Response content passed as an argument.")
    parser.add_argument("--validate-response", action="store_true")
    parser.add_argument("--strict-validation", action="store_true")
    parser.add_argument("--manifest-output", help="Append request/response metadata as JSONL.")
    args = parser.parse_args()

    pending = list_requests(args.bridge_dir)
    if args.list:
        for path in pending:
            print(path)  # noqa: T201
        return 0

    request_path: Path | None = None
    if args.request_id:
        request_path = bridge_paths(args.bridge_dir)[0] / f"{args.request_id}.json"
    elif pending:
        request_path = pending[0]
    if request_path is None:
        parser.error("no pending request found; pass --request-id or --list")

    request = load_request(request_path)
    kind = classify_request(request)
    if args.classify:
        print(kind)  # noqa: T201
    if args.print_prompt:
        print(format_prompt(request))  # noqa: T201

    response_content: str | None = None
    if args.response_file:
        response_content = Path(args.response_file).read_text(encoding="utf-8")
    elif args.response_stdin:
        response_content = sys.stdin.read()
    elif args.response_text is not None:
        response_content = args.response_text

    if response_content is not None:
        response_content = response_content.strip()
        validation_warnings: list[str] = []
        if args.validate_response or args.strict_validation:
            validation_warnings = validate_response_for_kind(kind, response_content)
            for warning in validation_warnings:
                print(f"validation warning: {warning}", file=sys.stderr)  # noqa: T201
            if validation_warnings and args.strict_validation:
                return 3
        path = write_response(
            args.bridge_dir,
            request["id"],
            response_content,
            request=request,
            request_path=request_path,
            manifest_output=args.manifest_output,
            validation_warnings=validation_warnings,
        )
        print(path)  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
