#!/usr/bin/env python3
"""Run the LDR generate_report pipeline with Codex bridge as the LLM."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_INSTRUCTIONS = (
    "Write the final report in Simplified Chinese. Use this structure: title, "
    "executive summary, concept boundaries, research timeline and key papers, "
    "main technical route comparison table, recent 2023-2026 progress, core "
    "bottlenecks, research questions worth pursuing, and reference list. Every "
    "important conclusion must be traceable to cited sources."
)

SECRET_KEYS = {"api_key", "apikey", "authorization", "password", "secret", "token"}


@dataclass
class RunConfig:
    query: str
    run_dir: Path
    model: str = "gpt-5.5"
    search_tool: str = "auto"
    strategy: str = "source-based"
    iterations: int = 5
    questions_per_iteration: int = 4
    timeout_seconds: int = 1200
    poll_interval_seconds: float = 0.5
    max_prompt_chars: int = 200_000
    searches_per_section: int = 2
    output_file: Path | None = None
    output_language: str = "zh-CN"
    output_instructions: str = DEFAULT_OUTPUT_INSTRUCTIONS
    allow_file_output: bool = True
    search_original_query: bool = True
    current_date: str | None = None

    def __post_init__(self) -> None:
        self.run_dir = Path(self.run_dir).expanduser().resolve()
        if self.output_file is not None:
            output_file = Path(self.output_file).expanduser()
            if not output_file.is_absolute():
                output_file = self.run_dir / output_file
            self.output_file = output_file.resolve()
        self.strategy = normalize_strategy(self.strategy)

    @property
    def bridge_dir(self) -> Path:
        return self.run_dir / "codex_bridge"

    @property
    def query_file(self) -> Path:
        return self.run_dir / "query.txt"

    @property
    def output_path(self) -> Path:
        return self.output_file or (self.run_dir / "final_report.md")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["run_dir"] = str(self.run_dir)
        data["bridge_dir"] = str(self.bridge_dir)
        data["query_file"] = str(self.query_file)
        data["output_file"] = str(self.output_path)
        return data


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_strategy(strategy: str) -> str:
    return strategy.replace("_", "-")


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in SECRET_KEYS or any(secret in lowered for secret in SECRET_KEYS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(redact_secrets(data), indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def write_status(config: RunConfig, phase: str, **extra: Any) -> None:
    payload = {
        "phase": phase,
        "updated_at": utc_now(),
        "run_dir": str(config.run_dir),
        "bridge_dir": str(config.bridge_dir),
        "output_file": str(config.output_path),
        **extra,
    }
    write_json(config.run_dir / "status.json", payload)


def build_settings_overrides(config: RunConfig) -> dict[str, Any]:
    overrides: dict[str, Any] = {
        "llm.provider": "codex_bridge",
        "llm.model": config.model,
        "llm.codex_bridge.bridge_dir": str(config.bridge_dir),
        "llm.codex_bridge.timeout_seconds": config.timeout_seconds,
        "llm.codex_bridge.poll_interval_seconds": config.poll_interval_seconds,
        "llm.codex_bridge.max_prompt_chars": config.max_prompt_chars,
        "search.tool": config.search_tool,
        "search.iterations": config.iterations,
        "search.questions_per_iteration": config.questions_per_iteration,
        "search.questions": config.questions_per_iteration,
        "search.search_strategy": config.strategy,
        "api.allow_file_output": config.allow_file_output,
        "general.output_language": config.output_language,
        "general.output_instructions": config.output_instructions,
        "programmatic_mode": True,
        "rate_limiting.llm_enabled": False,
    }
    if config.current_date:
        overrides["general.current_date"] = config.current_date
    return overrides


def prepare_run_dir(config: RunConfig) -> None:
    (config.bridge_dir / "requests").mkdir(parents=True, exist_ok=True)
    (config.bridge_dir / "responses").mkdir(parents=True, exist_ok=True)
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    config.query_file.write_text(config.query, encoding="utf-8")
    write_json(config.run_dir / "run_config.json", config.to_dict())
    write_status(config, "starting")


def build_child_command(config: RunConfig) -> list[str]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--execute",
        "--query-file",
        str(config.query_file),
        "--run-dir",
        str(config.run_dir),
        "--model",
        config.model,
        "--search-tool",
        config.search_tool,
        "--strategy",
        config.strategy,
        "--iterations",
        str(config.iterations),
        "--questions-per-iteration",
        str(config.questions_per_iteration),
        "--timeout-seconds",
        str(config.timeout_seconds),
        "--poll-interval-seconds",
        str(config.poll_interval_seconds),
        "--max-prompt-chars",
        str(config.max_prompt_chars),
        "--searches-per-section",
        str(config.searches_per_section),
        "--output-file",
        str(config.output_path),
        "--output-language",
        config.output_language,
    ]
    if config.current_date:
        command.extend(["--current-date", config.current_date])
    if not config.allow_file_output:
        command.append("--no-allow-file-output")
    if not config.search_original_query:
        command.append("--no-search-original-query")
    return command


def ensure_repo_src_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    src_dir = repo_root / "src"
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))


def progress_callback(config: RunConfig):
    progress_path = config.run_dir / "progress.jsonl"

    def _callback(phase: str, progress: int, metadata: dict[str, Any] | None = None) -> None:
        entry = {
            "phase": phase,
            "progress": progress,
            "metadata": metadata or {},
            "timestamp": utc_now(),
        }
        with progress_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(redact_secrets(entry), ensure_ascii=False) + "\n")

    return _callback


def execute_run(config: RunConfig) -> int:
    prepare_run_dir(config)
    os.environ["LDR_ENABLE_CODEX_BRIDGE"] = "1"
    os.environ["LDR_CODEX_BRIDGE_DIR"] = str(config.bridge_dir)
    os.environ.setdefault("MPLCONFIGDIR", str(config.run_dir / ".mplconfig"))
    ensure_repo_src_on_path()

    try:
        from local_deep_research.api.research_functions import generate_report
        from local_deep_research.api.settings_utils import create_settings_snapshot

        settings_overrides = build_settings_overrides(config)
        settings_snapshot = create_settings_snapshot(overrides=settings_overrides)
        write_json(config.run_dir / "settings_overrides.json", settings_overrides)
        write_json(config.run_dir / "settings_snapshot.json", settings_snapshot)
        write_status(config, "running_generate_report")

        result = generate_report(
            config.query,
            output_file=str(config.output_path),
            progress_callback=progress_callback(config),
            searches_per_section=config.searches_per_section,
            search_tool=config.search_tool,
            search_strategy=config.strategy,
            iterations=config.iterations,
            questions_per_iteration=config.questions_per_iteration,
            search_original_query=config.search_original_query,
            settings_snapshot=settings_snapshot,
        )
        if isinstance(result, dict) and result.get("content") and not config.output_path.exists():
            config.output_path.write_text(result["content"], encoding="utf-8")
        write_json(config.run_dir / "ldr_result.json", result)
        write_status(
            config,
            "completed",
            result_keys=sorted(result.keys()) if isinstance(result, dict) else [],
        )
        return 0
    except Exception as exc:  # pragma: no cover - exercised in live smoke runs.
        write_status(
            config,
            "failed",
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return 1


def start_background(config: RunConfig) -> int:
    prepare_run_dir(config)
    command = build_child_command(config)
    log_path = config.run_dir / "ldr_process.log"
    with log_path.open("ab") as log_file:
        process = subprocess.Popen(
            command,
            cwd=str(Path.cwd()),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )
    (config.run_dir / "ldr_process.pid").write_text(str(process.pid), encoding="utf-8")
    write_status(
        config,
        "background_started",
        pid=process.pid,
        log_file=str(log_path),
        command=command,
    )
    print(json.dumps({"pid": process.pid, "run_dir": str(config.run_dir)}, ensure_ascii=False))  # noqa: T201
    return 0


def read_query(args: argparse.Namespace) -> str:
    if args.query_file:
        return Path(args.query_file).read_text(encoding="utf-8").strip()
    if args.query:
        return args.query.strip()
    raise SystemExit("--query or --query-file is required")


def config_from_args(args: argparse.Namespace) -> RunConfig:
    return RunConfig(
        query=read_query(args),
        run_dir=Path(args.run_dir),
        model=args.model,
        search_tool=args.search_tool,
        strategy=args.strategy,
        iterations=args.iterations,
        questions_per_iteration=args.questions_per_iteration,
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        max_prompt_chars=args.max_prompt_chars,
        searches_per_section=args.searches_per_section,
        output_file=Path(args.output_file) if args.output_file else None,
        output_language=args.output_language,
        output_instructions=args.output_instructions,
        allow_file_output=args.allow_file_output,
        search_original_query=args.search_original_query,
        current_date=args.current_date,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run LDR generate_report through codex_bridge exact mode.",
    )
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--query")
    query_group.add_argument("--query-file")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--search-tool", default="auto")
    parser.add_argument("--strategy", default="source-based")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--questions-per-iteration", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument("--poll-interval-seconds", type=float, default=0.5)
    parser.add_argument("--max-prompt-chars", type=int, default=200_000)
    parser.add_argument("--searches-per-section", type=int, default=2)
    parser.add_argument("--output-file")
    parser.add_argument("--output-language", default="zh-CN")
    parser.add_argument("--output-instructions", default=DEFAULT_OUTPUT_INSTRUCTIONS)
    parser.add_argument("--current-date")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--execute", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--no-allow-file-output",
        dest="allow_file_output",
        action="store_false",
    )
    parser.add_argument(
        "--no-search-original-query",
        dest="search_original_query",
        action="store_false",
    )
    parser.set_defaults(allow_file_output=True, search_original_query=True)
    args = parser.parse_args()

    config = config_from_args(args)
    if args.background and not args.execute:
        return start_background(config)
    return execute_run(config)


if __name__ == "__main__":
    raise SystemExit(main())
