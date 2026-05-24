#!/usr/bin/env python3
"""Diagnose Local Deep Research access for Codex-led workflows."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


ENTRYPOINTS = ("ldr-mcp", "ldr-web")
MCP_TOOL_NAMES = (
    "list_search_engines",
    "list_strategies",
    "get_configuration",
    "search",
    "quick_research",
    "detailed_research",
    "generate_report",
    "analyze_documents",
)
DEFAULT_TIMEOUT_SECONDS = 12.0

IMPORT_CODE = """
import json
import local_deep_research
print(json.dumps({
    "module_file": getattr(local_deep_research, "__file__", None),
    "version": getattr(local_deep_research, "__version__", None),
}))
"""

MCP_IMPORT_CODE = """
import json
import local_deep_research.mcp.server as server
tool_names = __TOOL_NAMES__
print(json.dumps({
    "module_file": getattr(server, "__file__", None),
    "tools_present": [name for name in tool_names if hasattr(server, name)],
}))
"""

CONFIGURATION_CODE = """
import json
from local_deep_research.mcp.server import get_configuration
result = get_configuration()
print(json.dumps({"result_type": type(result).__name__}))
"""


def exception_payload(exc: BaseException) -> dict[str, str]:
    return {"type": type(exc).__name__, "message": str(exc)}


def safe_call(fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        payload = fn()
    except Exception as exc:  # noqa: BLE001 - diagnostics must keep going.
        return {"ok": False, "error": exception_payload(exc)}
    return {"ok": True, **payload}


def _repo_env(repo: Path) -> dict[str, str]:
    env = os.environ.copy()
    src = str(repo / "src")
    old_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src if not old_pythonpath else f"{src}{os.pathsep}{old_pythonpath}"
    return env


def run_python_probe(
    name: str,
    executable: Path,
    code: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "executable": str(executable),
        "ok": False,
        "timed_out": False,
    }
    try:
        completed = subprocess.run(
            [str(executable), "-c", code],
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        payload.update(
            {
                "timed_out": True,
                "timeout_seconds": timeout_seconds,
                "error": {
                    "type": "TimeoutExpired",
                    "message": f"probe timed out after {exc.timeout} seconds",
                },
            }
        )
        return payload
    except OSError as exc:
        payload["error"] = exception_payload(exc)
        return payload

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    payload.update(
        {
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "ok": completed.returncode == 0,
        }
    )
    if stdout:
        try:
            payload["json"] = json.loads(stdout.splitlines()[-1])
        except json.JSONDecodeError:
            pass
    return payload


def repo_venv_python(repo: Path) -> Path | None:
    candidates = [
        repo / ".venv" / "Scripts" / "python.exe",
        repo / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def probe_active_skill_install() -> dict[str, Any]:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    skill_dir = codex_home / "skills" / "local-deep-research-codex"
    installed = (skill_dir / "SKILL.md").exists()
    return {
        "codex_home": str(codex_home),
        "active_skill_path": str(skill_dir),
        "active_skill_installed": installed,
    }


def probe_codex_bridge() -> dict[str, Any]:
    enabled = os.environ.get("LDR_ENABLE_CODEX_BRIDGE") == "1"
    bridge_dir = os.environ.get("LDR_CODEX_BRIDGE_DIR")
    return {
        "available": enabled and bool(bridge_dir),
        "enabled": enabled,
        "bridge_dir": bridge_dir,
    }


def summarize_probe_results(results: dict[str, Any]) -> dict[str, Any]:
    default_import = results.get("default_python_import", {})
    repo_venv_import = results.get("repo_venv_python_import", {})
    mcp_import = results.get("mcp_import", {})
    configuration = results.get("configuration", {})
    web_entrypoint = results.get("web_entrypoint", {})
    active_skill = results.get("active_skill_install", {})
    codex_bridge = results.get("codex_bridge", {})

    mcp_ok = bool(mcp_import.get("ok"))
    configuration_ok = bool(configuration.get("ok"))
    web_ok = bool(web_entrypoint.get("ok"))
    exact_ldr_mode_available = bool(mcp_ok or configuration_ok or web_ok)
    codex_bridge_mode_available = bool(codex_bridge.get("available"))
    return {
        "default_python_ok": bool(default_import.get("ok")),
        "repo_venv_python_ok": bool(repo_venv_import.get("ok")),
        "mcp_import_ok": mcp_ok,
        "mcp_import_timed_out": bool(mcp_import.get("timed_out")),
        "configuration_ok": configuration_ok,
        "web_entrypoint_ok": web_ok,
        "active_skill_installed": bool(active_skill.get("active_skill_installed")),
        "exact_ldr_mode_available": exact_ldr_mode_available,
        "codex_bridge_mode_available": codex_bridge_mode_available,
    }


def names_from(value: Any) -> list[str] | str:
    if isinstance(value, dict):
        return sorted(str(key) for key in value.keys())
    if isinstance(value, (list, tuple, set)):
        names: list[str] = []
        for item in value:
            if isinstance(item, dict) and "name" in item:
                names.append(str(item["name"]))
            else:
                names.append(str(getattr(item, "name", item)))
        return sorted(names)
    return type(value).__name__


def configure_repo_import(repo: Path) -> dict[str, Any]:
    src = repo / "src"
    package_dir = src / "local_deep_research"
    added = False
    if package_dir.exists():
        src_text = str(src)
        if src_text not in sys.path:
            sys.path.insert(0, src_text)
            added = True
    return {
        "repo": str(repo),
        "src": str(src),
        "package_dir_exists": package_dir.exists(),
        "added_src_to_sys_path": added,
    }


def probe_module_spec() -> dict[str, Any]:
    spec = importlib.util.find_spec("local_deep_research")
    return {
        "found": spec is not None,
        "origin": getattr(spec, "origin", None) if spec else None,
    }


def probe_package_import() -> dict[str, Any]:
    module = importlib.import_module("local_deep_research")
    return {
        "module_file": getattr(module, "__file__", None),
        "version": getattr(module, "__version__", None),
    }


def probe_discovery() -> dict[str, Any]:
    from local_deep_research.api.settings_utils import create_settings_snapshot
    from local_deep_research.search_system_factory import get_available_strategies
    from local_deep_research.web_search_engines.search_engines_config import (
        search_config,
    )

    settings = create_settings_snapshot()
    engines = search_config(settings_snapshot=settings)
    strategies = get_available_strategies(show_all=True)
    return {
        "engines": names_from(engines),
        "strategies": names_from(strategies),
    }


def probe_mcp_import() -> dict[str, Any]:
    server = importlib.import_module("local_deep_research.mcp.server")
    return {
        "module_file": getattr(server, "__file__", None),
        "tools_present": [name for name in MCP_TOOL_NAMES if hasattr(server, name)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check which Local Deep Research interfaces are reachable.",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the Local Deep Research repository. Defaults to the current directory.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    parser.add_argument(
        "--fail-on-unavailable",
        action="store_true",
        help="Exit with status 1 when no LDR interface appears reachable.",
    )
    parser.add_argument(
        "--probe-timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Seconds before each subprocess probe is reported as timed out.",
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    import_setup = configure_repo_import(repo)

    executables = {name: shutil.which(name) for name in ENTRYPOINTS}
    env = _repo_env(repo)
    module_spec = safe_call(probe_module_spec)

    default_python_import = run_python_probe(
        "default_python_import",
        Path(sys.executable),
        IMPORT_CODE,
        timeout_seconds=args.probe_timeout,
        cwd=repo,
        env=env,
    )
    repo_venv = repo_venv_python(repo)
    probe_python = repo_venv or Path(sys.executable)
    if repo_venv:
        repo_venv_python_import = run_python_probe(
            "repo_venv_python_import",
            repo_venv,
            IMPORT_CODE,
            timeout_seconds=args.probe_timeout,
            cwd=repo,
            env=env,
        )
    else:
        repo_venv_python_import = {
            "name": "repo_venv_python_import",
            "ok": False,
            "timed_out": False,
            "error": {"type": "FileNotFoundError", "message": "repo .venv python not found"},
        }
    mcp_import = run_python_probe(
        "mcp_import",
        probe_python,
        MCP_IMPORT_CODE.replace("__TOOL_NAMES__", repr(MCP_TOOL_NAMES)),
        timeout_seconds=args.probe_timeout,
        cwd=repo,
        env=env,
    )
    configuration = run_python_probe(
        "configuration",
        probe_python,
        CONFIGURATION_CODE,
        timeout_seconds=args.probe_timeout,
        cwd=repo,
        env=env,
    )

    active_skill_install = probe_active_skill_install()
    codex_bridge = probe_codex_bridge()
    web_entrypoint = {
        "ok": bool(executables.get("ldr-web")),
        "path": executables.get("ldr-web"),
    }

    probe_results = {
        "default_python_import": default_python_import,
        "repo_venv_python_import": repo_venv_python_import,
        "mcp_import": mcp_import,
        "configuration": configuration,
        "web_entrypoint": web_entrypoint,
        "active_skill_install": active_skill_install,
        "codex_bridge": codex_bridge,
    }
    summary = summarize_probe_results(probe_results)
    package_import = (
        repo_venv_python_import
        if repo_venv_python_import.get("ok")
        else default_python_import
    )
    discovery = configuration

    availability = {
        "package_importable": bool(package_import.get("ok")),
        "mcp_entrypoint_available": bool(executables.get("ldr-mcp")),
        "mcp_importable": bool(mcp_import.get("ok")),
        "no_llm_discovery_available": bool(discovery.get("ok")),
        "web_entrypoint_available": bool(executables.get("ldr-web")),
        "exact_ldr_mode_available": summary["exact_ldr_mode_available"],
        "codex_bridge_mode_available": summary["codex_bridge_mode_available"],
    }
    ok = bool(
        availability["mcp_entrypoint_available"]
        or availability["mcp_importable"]
        or availability["no_llm_discovery_available"]
    )

    payload: dict[str, Any] = {
        "ok": ok,
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "platform": platform.platform(),
        },
        "import_setup": import_setup,
        "availability": availability,
        "entrypoints": executables,
        "summary": summary,
        "probes": probe_results,
        "module_spec": module_spec,
        "package_import": package_import,
        "no_llm_discovery": discovery,
        "mcp_import": mcp_import,
    }

    indent = 2 if args.pretty else None
    print(json.dumps(payload, indent=indent, sort_keys=True))  # noqa: T201
    if args.fail_on_unavailable and not ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
