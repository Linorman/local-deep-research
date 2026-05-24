#!/usr/bin/env python3
"""Prepare a harness-readable Codex/LDR research request."""

from __future__ import annotations

import argparse
import json
import re
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from new_research_packet import build_packet


VALID_MODES = {"quick", "detailed", "report"}
VALID_OUTPUT_FORMATS = {"markdown", "json", "bullets", "brief"}
VALID_SUBAGENT_POLICIES = {"auto", "never", "when-authorized", "force"}
VALID_EXECUTION_MODES = {"codex_like", "ldr_exact", "codex_bridge_exact"}


@dataclass
class HarnessConfig:
    query: str
    mode: str = "report"
    engine: str | None = None
    engines: list[str] | None = None
    strategy: str | None = None
    iterations: int | None = None
    questions_per_iteration: int | None = None
    max_results: int | None = None
    output_language: str = "zh-CN"
    output_format: str = "markdown"
    audience: str | None = None
    collection: str | None = None
    use_subagents: str = "when-authorized"
    exact_webui: bool = False
    allow_ldr_generation: bool = False
    codex_bridge: bool = False
    execution_mode: str = "codex_like"
    create_research_packet: bool = True
    source_ledger: bool = True
    claim_table: bool = True


def extract_directives(text: str) -> tuple[dict[str, str], str]:
    directives: dict[str, str] = {}

    def collect(match: re.Match[str]) -> str:
        body = match.group(1)
        for token in shlex.split(body):
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            directives[normalize_key(key)] = value.strip()
        return ""

    text = re.sub(r"\[ldr-codex\s+([^\]]+)\]", collect, text, flags=re.I)
    text = re.sub(r"\[harness\s+([^\]]+)\]", collect, text, flags=re.I)

    for match in re.finditer(
        r"(?:^|\s)(mode|engine|engines|strategy|iterations|questions_per_iteration|questions|max_results|language|lang|format|audience|collection|subagents|exact_webui|allow_ldr_generation|codex_bridge|execution_mode)\s*[:=]\s*([^\n;,]+)",
        text,
        flags=re.I,
    ):
        directives[normalize_key(match.group(1))] = match.group(2).strip()

    return directives, text.strip()


def normalize_key(key: str) -> str:
    key = key.strip().lower().replace("-", "_")
    aliases = {
        "lang": "output_language",
        "language": "output_language",
        "format": "output_format",
        "questions": "questions_per_iteration",
        "subagents": "use_subagents",
        "search_engine": "engine",
        "search_engines": "engines",
    }
    return aliases.get(key, key)


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "是", "允许"}


def parse_int(value: str | None, lower: int, upper: int) -> int | None:
    if value is None or value == "":
        return None
    number = int(value)
    return max(lower, min(upper, number))


def infer_from_prompt(prompt: str) -> dict[str, Any]:
    lower = prompt.lower()
    inferred: dict[str, Any] = {}

    if any(word in lower for word in ["quick", "快速", "简短", "概要"]):
        inferred["mode"] = "quick"
    if any(word in lower for word in ["detailed", "详细", "深度", "分析"]):
        inferred["mode"] = "detailed"
    if any(word in lower for word in ["report", "报告", "综述", "full report"]):
        inferred["mode"] = "report"

    engine_terms = {
        "arxiv": "arxiv",
        "pubmed": "pubmed",
        "semantic scholar": "semantic_scholar",
        "semantic_scholar": "semantic_scholar",
        "wikipedia": "wikipedia",
        "github": "github",
        "searxng": "searxng",
        "openalex": "openalex",
    }
    engines = []
    for phrase, engine in engine_terms.items():
        if phrase in lower and engine not in engines:
            engines.append(engine)
    if len(engines) == 1:
        inferred["engine"] = engines[0]
    elif engines:
        inferred["engines"] = engines

    if any(word in lower for word in ["中文", "chinese", "zh-cn", "zh_cn"]):
        inferred["output_language"] = "zh-CN"
    elif any(word in lower for word in ["english", "英文", "en-us", "en_us"]):
        inferred["output_language"] = "en-US"

    if "json" in lower:
        inferred["output_format"] = "json"
    elif any(word in lower for word in ["bullet", "要点", "列表"]):
        inferred["output_format"] = "bullets"

    if any(word in lower for word in ["官方webui", "exact webui", "完全一致", "原生webui"]):
        inferred["exact_webui"] = True
        inferred["allow_ldr_generation"] = True

    if any(word in lower for word in ["codex bridge", "codex_bridge", "bridge exact"]):
        inferred["exact_webui"] = True
        inferred["codex_bridge"] = True

    if any(word in lower for word in ["subagent", "子代理", "并行", "parallel"]):
        inferred["use_subagents"] = "when-authorized"

    return inferred


def apply_value(config: HarnessConfig, key: str, value: Any) -> None:
    if not hasattr(config, key):
        return
    if key in {
        "exact_webui",
        "allow_ldr_generation",
        "codex_bridge",
        "create_research_packet",
        "source_ledger",
        "claim_table",
    }:
        setattr(config, key, parse_bool(value))
    elif key in {"iterations"}:
        setattr(config, key, parse_int(str(value), 1, 10))
    elif key in {"questions_per_iteration"}:
        setattr(config, key, parse_int(str(value), 1, 8))
    elif key in {"max_results"}:
        setattr(config, key, parse_int(str(value), 1, 100))
    elif key == "engines":
        engines = [part.strip() for part in str(value).split(",") if part.strip()]
        setattr(config, key, engines or None)
    elif key == "mode":
        mode = str(value).strip().lower()
        if mode in {"full", "full_report"}:
            mode = "report"
        if mode in VALID_MODES:
            setattr(config, key, mode)
    elif key == "output_format":
        fmt = str(value).strip().lower()
        if fmt in VALID_OUTPUT_FORMATS:
            setattr(config, key, fmt)
    elif key == "use_subagents":
        policy = str(value).strip().lower().replace("_", "-")
        if policy in {"true", "yes", "on"}:
            policy = "when-authorized"
        if policy in {"false", "no", "off"}:
            policy = "never"
        if policy in VALID_SUBAGENT_POLICIES:
            setattr(config, key, policy)
    elif key == "execution_mode":
        mode = str(value).strip().lower().replace("-", "_")
        if mode in VALID_EXECUTION_MODES:
            setattr(config, key, mode)
    else:
        setattr(config, key, str(value).strip() or None)


def mode_defaults(mode: str) -> dict[str, int]:
    if mode == "quick":
        return {"iterations": 1, "questions_per_iteration": 3, "max_results": 8}
    if mode == "detailed":
        return {"iterations": 3, "questions_per_iteration": 4, "max_results": 10}
    return {"iterations": 5, "questions_per_iteration": 4, "max_results": 10}


def resolve_execution_mode(config: HarnessConfig) -> str:
    if config.codex_bridge:
        if not config.exact_webui:
            config.exact_webui = True
        return "codex_bridge_exact"
    if config.exact_webui and config.allow_ldr_generation:
        return "ldr_exact"
    if config.exact_webui:
        raise ValueError(
            "exact_webui=true requires allow_ldr_generation=true or codex_bridge=true"
        )
    return "codex_like"


def finalize_config(config: HarnessConfig) -> HarnessConfig:
    defaults = mode_defaults(config.mode)
    if config.iterations is None:
        config.iterations = defaults["iterations"]
    if config.questions_per_iteration is None:
        config.questions_per_iteration = defaults["questions_per_iteration"]
    if config.max_results is None:
        config.max_results = defaults["max_results"]
    config.execution_mode = resolve_execution_mode(config)
    return config


def build_codex_prompt(config: HarnessConfig) -> str:
    engines = ", ".join(config.engines or ([config.engine] if config.engine else []))
    engines = engines or "discover from LDR"
    if config.execution_mode == "ldr_exact":
        generation = "Exact LDR WebUI/API generation is allowed for this run."
        provenance = "Final output must disclose which parts were generated by LDR provider-backed tools and which parts were generated or compared by Codex."
        workflow = "Use LDR provider-backed tools for the research generation path."
    elif config.execution_mode == "codex_bridge_exact":
        generation = "Codex bridge exact mode is selected; use the explicit bridge contract and do not emulate an OpenAI endpoint."
        provenance = "Final output must disclose that LDR pipeline prompts were answered through the Codex bridge."
        workflow = "Use the exact LDR pipeline with bridge-visible request and response files."
    else:
        generation = "Do not call LDR provider-backed generation tools unless the user explicitly confirms during the run."
        provenance = "Final output must disclose that Codex generated the synthesis using LDR retrieval where available. Do not claim exact WebUI parity."
        workflow = "Follow the skill's WebUI-like Codex workflow."

    return f"""Use local-deep-research-codex in {config.execution_mode} {config.mode} mode.

Research question:
{config.query}

Harness parameters:
- Engines: {engines}
- Strategy: {config.strategy or "discover from LDR"}
- Iterations: {config.iterations}
- Questions per iteration: {config.questions_per_iteration}
- Max results per search: {config.max_results}
- Output language: {config.output_language}
- Output format: {config.output_format}
- Audience: {config.audience or "general expert reader"}
- Collection: {config.collection or "none specified"}
- Subagent policy: {config.use_subagents}
- Exact WebUI requested: {config.exact_webui}
- Execution mode: {config.execution_mode}

{workflow} Maintain a source ledger, claim table, current-knowledge notes, and open gaps. {generation} {provenance}"""


def build_environment(config: HarnessConfig) -> dict[str, str]:
    env: dict[str, str] = {}
    if config.engine:
        env["LDR_SEARCH_TOOL"] = config.engine
    if config.iterations is not None:
        env["LDR_SEARCH_ITERATIONS"] = str(config.iterations)
    if config.questions_per_iteration is not None:
        env["LDR_SEARCH_QUESTIONS_PER_ITERATION"] = str(config.questions_per_iteration)
    if config.strategy:
        env["LDR_SEARCH_SEARCH_STRATEGY"] = config.strategy
    return env


def write_env_file(path: str, env: dict[str, str]) -> None:
    lines = [f"{key}={value}" for key, value in sorted(env.items())]
    Path(path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a JSON request for a Codex harness using the local-deep-research-codex skill.",
    )
    parser.add_argument("--prompt", help="User prompt to parse.")
    parser.add_argument("--prompt-file", help="File containing the user prompt.")
    parser.add_argument("--query", help="Research query. Overrides prompt-derived query.")
    parser.add_argument("--mode", choices=sorted(VALID_MODES))
    parser.add_argument("--engine")
    parser.add_argument("--engines", help="Comma-separated engine list.")
    parser.add_argument("--strategy")
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--questions-per-iteration", type=int)
    parser.add_argument("--max-results", type=int)
    parser.add_argument("--output-language")
    parser.add_argument("--output-format", choices=sorted(VALID_OUTPUT_FORMATS))
    parser.add_argument("--audience")
    parser.add_argument("--collection")
    parser.add_argument("--use-subagents", choices=sorted(VALID_SUBAGENT_POLICIES))
    parser.add_argument("--exact-webui", action="store_true")
    parser.add_argument("--allow-ldr-generation", action="store_true")
    parser.add_argument("--codex-bridge", action="store_true")
    parser.add_argument("--no-research-packet", action="store_true")
    parser.add_argument(
        "--sidecar-dir",
        help=(
            "Directory for standard harness files. Defaults unset outputs to "
            "request.json, ldr.env, prompt.txt, and packet.md inside this directory."
        ),
    )
    parser.add_argument("--output", help="Write JSON to this path instead of stdout.")
    parser.add_argument("--env-output", help="Write suggested LDR environment variables to this file.")
    parser.add_argument("--codex-prompt-output", help="Write the prepared Codex prompt to this file.")
    parser.add_argument("--packet-output", help="Create a research packet markdown file at this path.")
    args = parser.parse_args()

    sidecar_dir = Path(args.sidecar_dir).expanduser() if args.sidecar_dir else None
    if sidecar_dir:
        sidecar_dir.mkdir(parents=True, exist_ok=True)
        if not args.output:
            args.output = str(sidecar_dir / "request.json")
        if not args.env_output:
            args.env_output = str(sidecar_dir / "ldr.env")
        if not args.codex_prompt_output:
            args.codex_prompt_output = str(sidecar_dir / "prompt.txt")
        if not args.packet_output and not args.no_research_packet:
            args.packet_output = str(sidecar_dir / "packet.md")

    prompt = args.prompt or ""
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    directives, cleaned_prompt = extract_directives(prompt)
    inferred = infer_from_prompt(cleaned_prompt)
    query = args.query or directives.pop("query", None) or cleaned_prompt
    if not query:
        parser.error("provide --query, --prompt, or --prompt-file")

    config = HarnessConfig(query=query)
    for source in (inferred, directives):
        for key, value in source.items():
            apply_value(config, key, value)

    explicit = {
        "mode": args.mode,
        "engine": args.engine,
        "engines": args.engines,
        "strategy": args.strategy,
        "iterations": args.iterations,
        "questions_per_iteration": args.questions_per_iteration,
        "max_results": args.max_results,
        "output_language": args.output_language,
        "output_format": args.output_format,
        "audience": args.audience,
        "collection": args.collection,
        "use_subagents": args.use_subagents,
        "exact_webui": args.exact_webui if args.exact_webui else None,
        "allow_ldr_generation": args.allow_ldr_generation
        if args.allow_ldr_generation
        else None,
        "codex_bridge": args.codex_bridge if args.codex_bridge else None,
        "create_research_packet": False if args.no_research_packet else None,
    }
    for key, value in explicit.items():
        if value is not None:
            apply_value(config, key, value)

    try:
        finalize_config(config)
    except ValueError as exc:
        parser.error(str(exc))

    env = build_environment(config)
    codex_prompt = build_codex_prompt(config)
    packet_path = None
    if args.packet_output and config.create_research_packet:
        packet_file = Path(args.packet_output).expanduser()
        packet_file.parent.mkdir(parents=True, exist_ok=True)
        packet_file.write_text(
            build_packet(config.query, config.mode, config.engine, config.strategy),
            encoding="utf-8",
        )
        packet_path = str(packet_file.resolve())
        codex_prompt += f"\n\nUse this research packet path if available: {packet_path}"

    if args.env_output:
        write_env_file(args.env_output, env)
    if args.codex_prompt_output:
        Path(args.codex_prompt_output).write_text(codex_prompt + "\n", encoding="utf-8")

    payload = {
        "skill": "local-deep-research-codex",
        "schema_version": 1,
        "parameters": asdict(config),
        "ldr_environment": env,
        "codex_prompt": codex_prompt,
        "research_packet_path": packet_path,
        "recommended_tools": [
            "check_ldr_access",
            "list_search_engines",
            "list_strategies",
            "get_configuration",
            "search",
        ],
        "provider_backed_tools": [
            "quick_research",
            "detailed_research",
            "generate_report",
            "analyze_documents",
        ],
    }

    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
