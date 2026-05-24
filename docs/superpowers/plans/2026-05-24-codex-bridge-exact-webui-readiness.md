# Codex Bridge Exact WebUI Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `codex_bridge_exact` operationally verifiable for the WebUI pipeline, so LDR runs its normal WebUI/API research flow while Codex supplies only the LLM responses.

**Architecture:** Keep the original LDR route, queue, settings snapshot, `AdvancedSearchSystem`, strategies, citation handling, and `IntegratedReportGenerator` unchanged for research execution. Add the missing readiness layer around the existing Codex bridge provider: active skill installation checks, WebUI model discovery, no-hang diagnostics, real pipeline tests, responder readiness, and quality benchmarks.

**Tech Stack:** Python, pytest, Flask route helpers, LangChain chat models, LDR provider auto-discovery, Codex skill files, PowerShell validation commands.

---

## Current Findings

- The checked-in skill exists at `W:/projects/local-deep-research/codex-skills/local-deep-research-codex/SKILL.md`, but diagnostics report it is not installed under the active Codex skills directory.
- `codex_like` cannot meet exact WebUI parity because Codex controls orchestration and synthesis instead of LDR's WebUI worker path.
- `ldr_exact` preserves the WebUI/API pipeline but uses an LDR-configured provider, not Codex.
- `codex_bridge_exact` is the only design that can meet the target, but it is not yet operationally ready in this environment because the bridge is disabled, no responder readiness is verified, WebUI model listing is incomplete, diagnostics still rely on slow MCP/config probes, and the existing integration test uses fake search/report classes.
- The parity reference currently says `/research/api/start`; the observed browser route posts to `/api/start_research`.

## File Structure

- Modify `W:/projects/local-deep-research/codex-skills/local-deep-research-codex/references/webui-pipeline-parity.md` to correct the endpoint and add the remaining readiness gates.
- Modify `W:/projects/local-deep-research/src/local_deep_research/llm/providers/implementations/codex_bridge.py` to expose WebUI-safe model listing and optional responder heartbeat checks.
- Modify `W:/projects/local-deep-research/src/local_deep_research/web/routes/settings_routes.py` to safely fetch models from no-auth discovered providers.
- Modify `W:/projects/local-deep-research/codex-skills/local-deep-research-codex/scripts/check_ldr_access.py` to prefer direct API probes and make slow MCP probes opt-in.
- Modify `W:/projects/local-deep-research/codex-skills/local-deep-research-codex/scripts/respond_to_codex_bridge.py` to write a responder heartbeat and expose a readiness check.
- Modify `W:/projects/local-deep-research/codex-skills/local-deep-research-codex/scripts/compare_webui_codex_quality.py` to emit pass/fail thresholds for completed runs.
- Create `W:/projects/local-deep-research/tests/web/test_settings_available_models_helpers.py` for WebUI model discovery helper tests.
- Create `W:/projects/local-deep-research/tests/integration/test_codex_bridge_real_pipeline.py` for a real LDR API pipeline bridge test with a deterministic retriever.
- Create or extend tests under `W:/projects/local-deep-research/tests/codex_skill/` and `W:/projects/local-deep-research/tests/llm/providers/`.

---

### Task 1: Correct Parity Documentation And Installation Gate

**Files:**
- Modify: `W:/projects/local-deep-research/codex-skills/local-deep-research-codex/references/webui-pipeline-parity.md`
- Modify: `W:/projects/local-deep-research/codex-skills/local-deep-research-codex/references/install-and-use.md`
- Verify: `W:/projects/local-deep-research/codex-skills/local-deep-research-codex/scripts/install_codex_skill.py`

- [ ] **Step 1: Update the call graph endpoint**

Replace the call graph block in `webui-pipeline-parity.md` with:

```text
research.html / research.js
  -> POST /api/start_research
  -> research_routes.start_research()
  -> start_research_process()
  -> research_service.run_research_process()
  -> get_llm() + get_search()
  -> AdvancedSearchSystem(strategy=...)
  -> strategy.analyze_topic()
  -> question generation
  -> iterative searches
  -> filtering and citation synthesis
  -> quick mode: save formatted findings
  -> detailed/report mode: IntegratedReportGenerator.generate_report()
  -> section structure
  -> subsection re-search
  -> report formatting
  -> history, sources, metadata, progress, errors, exports
```

- [ ] **Step 2: Add a readiness gate section**

Append this section to `webui-pipeline-parity.md`:

```markdown
## Codex Bridge Exact Readiness Gates

`codex_bridge_exact` can be treated as available only when all gates pass:

1. The active Codex skill exists at `$CODEX_HOME/skills/local-deep-research-codex/SKILL.md`.
2. `LDR_ENABLE_CODEX_BRIDGE=1` is set before LDR provider discovery runs.
3. `LDR_CODEX_BRIDGE_DIR` points at a writable bridge directory.
4. A Codex bridge responder is ready and writes a fresh heartbeat for the same bridge directory.
5. WebUI `/api/available-models` exposes provider `codex_bridge` and model `gpt-5.5`.
6. A real LDR API pipeline test passes with `AdvancedSearchSystem` and `IntegratedReportGenerator`.
7. A quality comparison report has been generated for the chosen benchmark topics.

If any gate fails, use `ldr_exact` for exact LDR behavior or `codex_like` with an approximate label.
```

- [ ] **Step 3: Add the install command to the runbook**

Ensure `install-and-use.md` contains this exact PowerShell command:

```powershell
.venv\Scripts\python.exe codex-skills\local-deep-research-codex\scripts\install_codex_skill.py --force
```

Add this sentence immediately after the command:

```text
Restart the Codex session after installing so the active skill index is refreshed.
```

- [ ] **Step 4: Verify installation locally**

Run:

```powershell
.venv\Scripts\python.exe codex-skills\local-deep-research-codex\scripts\install_codex_skill.py --force
.venv\Scripts\python.exe codex-skills\local-deep-research-codex\scripts\check_ldr_access.py --repo . --pretty --probe-timeout 20
```

Expected:

```text
"active_skill_installed": true
```

- [ ] **Step 5: Commit**

```powershell
git add codex-skills/local-deep-research-codex/references/webui-pipeline-parity.md codex-skills/local-deep-research-codex/references/install-and-use.md
git commit -m "docs: clarify codex bridge exact readiness gates"
```

---

### Task 2: Expose Codex Bridge Models To WebUI

**Files:**
- Modify: `W:/projects/local-deep-research/src/local_deep_research/llm/providers/implementations/codex_bridge.py`
- Modify: `W:/projects/local-deep-research/tests/llm/providers/test_codex_bridge.py`

- [ ] **Step 1: Write the failing provider model listing test**

Append this test to `tests/llm/providers/test_codex_bridge.py`:

```python
def test_provider_lists_configured_codex_models(monkeypatch):
    module = load_codex_bridge_module()
    monkeypatch.setenv("LDR_ENABLE_CODEX_BRIDGE", "1")
    monkeypatch.setenv("LDR_CODEX_BRIDGE_MODELS", "gpt-5.5,gpt-5.4")

    assert module.CodexBridgeProvider.api_key_setting is None

    models = module.CodexBridgeProvider.list_models_for_api()

    assert models == [
        {"value": "gpt-5.5", "label": "GPT-5.5 (Codex Bridge)"},
        {"value": "gpt-5.4", "label": "GPT-5.4 (Codex Bridge)"},
    ]
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\llm\providers tests\llm\providers\test_codex_bridge.py::test_provider_lists_configured_codex_models
```

Expected:

```text
FAILED ... AttributeError: type object 'CodexBridgeProvider' has no attribute 'api_key_setting'
```

- [ ] **Step 3: Implement the provider model listing**

Inside `class CodexBridgeProvider`, add these members:

```python
    api_key_setting = None
    url_setting = None

    @classmethod
    def list_models_for_api(cls, api_key=None, base_url=None):
        raw_models = os.environ.get("LDR_CODEX_BRIDGE_MODELS", "gpt-5.5")
        models = [model.strip() for model in raw_models.split(",") if model.strip()]
        return [
            {
                "value": model,
                "label": f"{model.upper()} (Codex Bridge)",
            }
            for model in models
        ]
```

- [ ] **Step 4: Run the focused provider tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\llm\providers tests\llm\providers\test_codex_bridge.py
```

Expected:

```text
5 passed
```

- [ ] **Step 5: Commit**

```powershell
git add src/local_deep_research/llm/providers/implementations/codex_bridge.py tests/llm/providers/test_codex_bridge.py
git commit -m "feat: expose codex bridge models to webui"
```

---

### Task 3: Make WebUI Discovered Provider Model Fetching No-Auth Safe

**Files:**
- Modify: `W:/projects/local-deep-research/src/local_deep_research/web/routes/settings_routes.py`
- Create: `W:/projects/local-deep-research/tests/web/test_settings_available_models_helpers.py`

- [ ] **Step 1: Write the failing helper test**

Create `tests/web/test_settings_available_models_helpers.py`:

```python
from types import SimpleNamespace

from local_deep_research.web.routes import settings_routes


class NoAuthProvider:
    api_key_setting = None
    url_setting = None

    @classmethod
    def list_models_for_api(cls, api_key=None, base_url=None):
        assert api_key is None
        assert base_url is None
        return [{"value": "gpt-5.5", "label": "GPT-5.5 (Codex Bridge)"}]


def test_fetch_discovered_provider_models_supports_no_auth_provider():
    provider_info = SimpleNamespace(
        provider_name="Codex Bridge",
        provider_class=NoAuthProvider,
    )

    models = settings_routes._fetch_discovered_provider_models(
        provider_key="CODEX_BRIDGE",
        provider_info=provider_info,
        get_setting=lambda key, default="": default,
    )

    assert models == [
        {
            "value": "gpt-5.5",
            "label": "GPT-5.5 (Codex Bridge)",
            "provider": "CODEX_BRIDGE",
        }
    ]
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 tests\web\test_settings_available_models_helpers.py
```

Expected:

```text
FAILED ... AttributeError: module ... has no attribute '_fetch_discovered_provider_models'
```

- [ ] **Step 3: Add the helper**

Add this function above `api_get_available_models()` in `settings_routes.py`:

```python
def _fetch_discovered_provider_models(provider_key, provider_info, get_setting):
    provider_models = []
    provider_class = provider_info.provider_class

    api_key_setting = getattr(provider_class, "api_key_setting", None)
    api_key = get_setting(api_key_setting, "") if api_key_setting else None

    provider_base_url = None
    url_setting = getattr(provider_class, "url_setting", None)
    if url_setting:
        provider_base_url = get_setting(url_setting, "")

    models = provider_class.list_models_for_api(api_key, provider_base_url)
    for model in models:
        provider_models.append(
            {
                "value": model["value"],
                "label": model["label"],
                "provider": provider_key,
            }
        )
    return provider_models
```

- [ ] **Step 4: Replace the duplicated route block**

In the auto-discovery loop in `api_get_available_models()`, replace the inline `api_key`, `provider_base_url`, `list_models_for_api`, and formatting code with:

```python
                provider_models = _fetch_discovered_provider_models(
                    provider_key=provider_key,
                    provider_info=provider_info,
                    get_setting=_get_setting_from_session,
                )
```

- [ ] **Step 5: Run the helper test and focused Codex bridge test**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 tests\web\test_settings_available_models_helpers.py
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\llm\providers tests\llm\providers\test_codex_bridge.py
```

Expected:

```text
1 passed
5 passed
```

- [ ] **Step 6: Commit**

```powershell
git add src/local_deep_research/web/routes/settings_routes.py tests/web/test_settings_available_models_helpers.py
git commit -m "fix: support no-auth discovered provider models"
```

---

### Task 4: Make Diagnostics Prefer Direct LDR API Probes

**Files:**
- Modify: `W:/projects/local-deep-research/codex-skills/local-deep-research-codex/scripts/check_ldr_access.py`
- Modify: `W:/projects/local-deep-research/tests/codex_skill/test_check_ldr_access.py`

- [ ] **Step 1: Write the failing direct API summary test**

Append this test to `tests/codex_skill/test_check_ldr_access.py`:

```python
def test_summary_marks_exact_mode_available_from_direct_api():
    module = load_check_ldr_access()
    summary = module.summarize_probe_results(
        {
            "default_python_import": {"ok": True},
            "repo_venv_python_import": {"ok": True},
            "direct_api": {"ok": True},
            "discovery": {"ok": True},
            "mcp_import": {"ok": False, "timed_out": True},
            "configuration": {"ok": False, "timed_out": True},
            "web_entrypoint": {"ok": False},
            "active_skill_install": {"active_skill_installed": True},
            "codex_bridge": {"available": False},
        }
    )

    assert summary["direct_api_ok"] is True
    assert summary["exact_ldr_mode_available"] is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\codex_skill tests\codex_skill\test_check_ldr_access.py::test_summary_marks_exact_mode_available_from_direct_api
```

Expected:

```text
FAILED ... KeyError: 'direct_api_ok'
```

- [ ] **Step 3: Add direct API and discovery probes**

Add these constants below `CONFIGURATION_CODE`:

```python
DIRECT_API_CODE = """
import json
from local_deep_research.api import research_functions
tool_names = ["quick_summary", "detailed_research", "generate_report"]
print(json.dumps({
    "module_file": getattr(research_functions, "__file__", None),
    "functions_present": [
        name for name in tool_names if hasattr(research_functions, name)
    ],
}))
"""

DISCOVERY_CODE = """
import json
from local_deep_research.api.settings_utils import create_settings_snapshot
from local_deep_research.search_system_factory import get_available_strategies
from local_deep_research.web_search_engines.search_engines_config import search_config
settings = create_settings_snapshot()
engines = search_config(settings_snapshot=settings)
strategies = get_available_strategies(show_all=True)
print(json.dumps({
    "engine_count": len(engines),
    "strategy_count": len(strategies),
}))
"""
```

- [ ] **Step 4: Add an opt-in MCP flag**

Add this argparse option:

```python
    parser.add_argument(
        "--include-mcp",
        action="store_true",
        help="Run slower MCP import and configuration probes. Direct API probes run by default.",
    )
```

- [ ] **Step 5: Run direct probes by default and MCP probes only when requested**

In `main()`, create these probes before MCP probes:

```python
    direct_api = run_python_probe(
        "direct_api",
        probe_python,
        DIRECT_API_CODE,
        timeout_seconds=args.probe_timeout,
        cwd=repo,
        env=env,
    )
    discovery = run_python_probe(
        "discovery",
        probe_python,
        DISCOVERY_CODE,
        timeout_seconds=args.probe_timeout,
        cwd=repo,
        env=env,
    )
```

Replace unconditional MCP probe calls with:

```python
    if args.include_mcp:
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
    else:
        mcp_import = {"name": "mcp_import", "ok": False, "timed_out": False, "skipped": True}
        configuration = {"name": "configuration", "ok": False, "timed_out": False, "skipped": True}
```

- [ ] **Step 6: Update summary and availability**

In `summarize_probe_results()`, add:

```python
    direct_api = results.get("direct_api", {})
    discovery = results.get("discovery", {})
    direct_api_ok = bool(direct_api.get("ok"))
    discovery_ok = bool(discovery.get("ok"))
```

Set exact availability with:

```python
    exact_ldr_mode_available = bool(direct_api_ok and discovery_ok)
```

Return these fields:

```python
        "direct_api_ok": direct_api_ok,
        "discovery_ok": discovery_ok,
```

In `availability`, set:

```python
        "direct_api_available": summary["direct_api_ok"],
        "discovery_available": summary["discovery_ok"],
        "exact_ldr_mode_available": summary["exact_ldr_mode_available"],
```

- [ ] **Step 7: Run diagnostics tests and the command**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\codex_skill tests\codex_skill\test_check_ldr_access.py
.venv\Scripts\python.exe codex-skills\local-deep-research-codex\scripts\check_ldr_access.py --repo . --pretty --probe-timeout 20
```

Expected:

```text
4 passed
"direct_api_ok": true
"discovery_ok": true
```

- [ ] **Step 8: Commit**

```powershell
git add codex-skills/local-deep-research-codex/scripts/check_ldr_access.py tests/codex_skill/test_check_ldr_access.py
git commit -m "fix: use direct api probes for ldr diagnostics"
```

---

### Task 5: Add Responder Heartbeat And Availability Gate

**Files:**
- Modify: `W:/projects/local-deep-research/src/local_deep_research/llm/providers/implementations/codex_bridge.py`
- Modify: `W:/projects/local-deep-research/codex-skills/local-deep-research-codex/scripts/respond_to_codex_bridge.py`
- Modify: `W:/projects/local-deep-research/tests/llm/providers/test_codex_bridge.py`

- [ ] **Step 1: Write the heartbeat availability tests**

Append these tests to `tests/llm/providers/test_codex_bridge.py`:

```python
def test_bridge_responder_heartbeat_is_required_when_configured(tmp_path, monkeypatch):
    module = load_codex_bridge_module()
    monkeypatch.setenv("LDR_ENABLE_CODEX_BRIDGE", "1")
    monkeypatch.setenv("LDR_CODEX_BRIDGE_DIR", str(tmp_path))
    monkeypatch.setenv("LDR_CODEX_BRIDGE_REQUIRE_RESPONDER", "1")

    assert module.CodexBridgeProvider.is_available() is False


def test_bridge_responder_heartbeat_makes_provider_available(tmp_path, monkeypatch):
    module = load_codex_bridge_module()
    heartbeat = tmp_path / "responder.json"
    heartbeat.write_text(
        '{"status":"ready","model":"gpt-5.5","updated_at_epoch":9999999999}',
        encoding="utf-8",
    )
    monkeypatch.setenv("LDR_ENABLE_CODEX_BRIDGE", "1")
    monkeypatch.setenv("LDR_CODEX_BRIDGE_DIR", str(tmp_path))
    monkeypatch.setenv("LDR_CODEX_BRIDGE_REQUIRE_RESPONDER", "1")

    assert module.CodexBridgeProvider.is_available() is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\llm\providers tests\llm\providers\test_codex_bridge.py::test_bridge_responder_heartbeat_is_required_when_configured tests\llm\providers\test_codex_bridge.py::test_bridge_responder_heartbeat_makes_provider_available
```

Expected:

```text
FAILED ... assert True is False
```

- [ ] **Step 3: Add heartbeat helpers**

Add these functions near `redact_secrets()` in `codex_bridge.py`:

```python
def responder_heartbeat_path(bridge_dir: str | Path) -> Path:
    return Path(bridge_dir).expanduser() / "responder.json"


def responder_heartbeat_is_fresh(bridge_dir: str | Path, max_age_seconds: int = 120) -> bool:
    path = responder_heartbeat_path(bridge_dir)
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if payload.get("status") != "ready":
        return False
    updated_at_epoch = payload.get("updated_at_epoch")
    if not isinstance(updated_at_epoch, (int, float)):
        return False
    return (time.time() - float(updated_at_epoch)) <= max_age_seconds
```

- [ ] **Step 4: Gate provider availability when required**

Replace `CodexBridgeProvider.is_available()` with:

```python
    @classmethod
    def is_available(cls, settings_snapshot=None) -> bool:
        if not cls.is_discoverable():
            return False
        if os.environ.get("LDR_CODEX_BRIDGE_REQUIRE_RESPONDER") != "1":
            return True
        bridge_dir = (
            _setting_value(settings_snapshot, "llm.codex_bridge.bridge_dir")
            or os.environ.get("LDR_CODEX_BRIDGE_DIR")
            or ".codex_bridge"
        )
        return responder_heartbeat_is_fresh(bridge_dir)
```

- [ ] **Step 5: Add heartbeat writing to the responder helper**

In `respond_to_codex_bridge.py`, add:

```python
def write_heartbeat(bridge_dir: Path, model: str) -> Path:
    path = bridge_dir / "responder.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "ready",
        "model": model,
        "updated_at_epoch": time.time(),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
```

Add CLI options:

```python
parser.add_argument("--heartbeat", action="store_true", help="Write responder readiness heartbeat and exit.")
parser.add_argument("--model", default="gpt-5.5", help="Codex model name recorded in heartbeat.")
```

After parsing args, add:

```python
if args.heartbeat:
    path = write_heartbeat(Path(args.bridge_dir), args.model)
    print(json.dumps({"ok": True, "heartbeat": str(path)}, indent=2))
    return 0
```

- [ ] **Step 6: Run focused tests and heartbeat command**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\llm\providers tests\llm\providers\test_codex_bridge.py
.venv\Scripts\python.exe codex-skills\local-deep-research-codex\scripts\respond_to_codex_bridge.py --bridge-dir .codex_bridge --heartbeat --model gpt-5.5
```

Expected:

```text
7 passed
"ok": true
```

- [ ] **Step 7: Commit**

```powershell
git add src/local_deep_research/llm/providers/implementations/codex_bridge.py codex-skills/local-deep-research-codex/scripts/respond_to_codex_bridge.py tests/llm/providers/test_codex_bridge.py
git commit -m "feat: add codex bridge responder readiness gate"
```

---

### Task 6: Replace Fake Pipeline Test With Real LDR API Pipeline Test

**Files:**
- Create: `W:/projects/local-deep-research/tests/integration/test_codex_bridge_real_pipeline.py`
- Keep: `W:/projects/local-deep-research/tests/integration/test_webui_pipeline_codex_bridge.py`

- [ ] **Step 1: Create a deterministic real pipeline test**

Create `tests/integration/test_codex_bridge_real_pipeline.py`:

```python
import json
import threading
import time
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever


class StaticRetriever(BaseRetriever):
    def _get_relevant_documents(self, query, *, run_manager=None):
        return [
            Document(
                page_content=(
                    "Codex Bridge lets LDR keep its own search and report pipeline "
                    "while a Codex responder supplies LLM text."
                ),
                metadata={
                    "title": "Codex Bridge Design Note",
                    "source": "https://example.test/codex-bridge",
                },
            )
        ]


def bridge_responder(bridge_dir: Path, stop: threading.Event):
    requests_dir = bridge_dir / "requests"
    responses_dir = bridge_dir / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    seen = set()
    while not stop.is_set():
        for request_path in sorted(requests_dir.glob("*.json")):
            if request_path.name in seen:
                continue
            seen.add(request_path.name)
            payload = json.loads(request_path.read_text(encoding="utf-8"))
            prompt = "\n".join(message["content"] for message in payload["messages"])
            if "Generate" in prompt and "search questions" in prompt:
                content = "Q: Codex bridge exact WebUI parity evidence"
            elif "report structure" in prompt.lower() or "structure" in prompt.lower():
                content = "# Executive Summary\n# Findings\n# Sources"
            else:
                content = (
                    "The bridge run used LDR search and report generation while Codex "
                    "answered the LLM call [1]."
                )
            (responses_dir / request_path.name).write_text(
                json.dumps({"id": payload["id"], "content": content}),
                encoding="utf-8",
            )
        time.sleep(0.01)
```

Append the test:

```python
def test_codex_bridge_runs_real_generate_report_pipeline(tmp_path, monkeypatch):
    monkeypatch.setenv("LDR_ENABLE_CODEX_BRIDGE", "1")
    monkeypatch.setenv("LDR_CODEX_BRIDGE_DIR", str(tmp_path / "bridge"))

    from local_deep_research.api.research_functions import generate_report
    from local_deep_research.api.settings_utils import create_settings_snapshot

    stop = threading.Event()
    thread = threading.Thread(
        target=bridge_responder,
        args=(tmp_path / "bridge", stop),
        daemon=True,
    )
    thread.start()

    try:
        settings_snapshot = create_settings_snapshot(
            overrides={
                "llm.provider": {"value": "codex_bridge"},
                "llm.model": {"value": "gpt-5.5"},
                "search.tool": {"value": "static_bridge"},
            }
        )
        result = generate_report(
            "Can Codex Bridge reproduce the WebUI pipeline?",
            retrievers={"static_bridge": StaticRetriever()},
            provider="codex_bridge",
            model_name="gpt-5.5",
            search_tool="static_bridge",
            search_strategy="source-based",
            iterations=1,
            questions_per_iteration=1,
            searches_per_section=1,
            settings_snapshot=settings_snapshot,
        )
    finally:
        stop.set()
        thread.join(timeout=1)

    content = result["content"] if isinstance(result, dict) else str(result)
    assert "Codex" in content
    assert "Sources" in content
    assert "https://example.test/codex-bridge" in content
```

- [ ] **Step 2: Run the new integration test to verify current gaps**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\integration tests\integration\test_codex_bridge_real_pipeline.py
```

Expected before fixes:

```text
FAILED
```

The acceptable failure is provider discovery, bridge registration timing, or report formatting. A network-search failure is not acceptable because the registered retriever must keep the test offline.

- [ ] **Step 3: Make the test pass without replacing LDR pipeline classes**

Apply only minimal fixes required by the failure. Allowed fixes:

```text
1. Ensure `LDR_ENABLE_CODEX_BRIDGE=1` is set before provider discovery imports run in the test.
2. Pass `settings_snapshot` consistently into `generate_report()`.
3. Adjust deterministic bridge responses to satisfy existing parser expectations.
4. Keep actual `AdvancedSearchSystem` and `IntegratedReportGenerator` in use.
```

Disallowed fixes:

```text
1. Do not replace `AdvancedSearchSystem` with a fake class.
2. Do not replace `IntegratedReportGenerator` with a fake class.
3. Do not use a live web search engine.
```

- [ ] **Step 4: Run both integration tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\integration tests\integration\test_webui_pipeline_codex_bridge.py tests\integration\test_codex_bridge_real_pipeline.py
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```powershell
git add tests/integration/test_codex_bridge_real_pipeline.py
git commit -m "test: exercise codex bridge through real ldr pipeline"
```

---

### Task 7: Add Quality Thresholds For Completed Runs

**Files:**
- Modify: `W:/projects/local-deep-research/codex-skills/local-deep-research-codex/scripts/compare_webui_codex_quality.py`
- Create: `W:/projects/local-deep-research/tests/codex_skill/test_compare_webui_codex_quality.py`

- [ ] **Step 1: Write threshold tests**

Create `tests/codex_skill/test_compare_webui_codex_quality.py`:

```python
import importlib.util
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "codex-skills"
    / "local-deep-research-codex"
    / "scripts"
    / "compare_webui_codex_quality.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("compare_webui_codex_quality", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_evaluate_thresholds_marks_passing_candidate():
    module = load_module()
    result = module.evaluate_thresholds(
        {
            "source_overlap_with_webui": 0.8,
            "citation_support_score": 1.0,
            "section_coverage_score": 0.9,
            "unsupported_claim_count": 1,
        }
    )

    assert result["passes_quality_gate"] is True
    assert result["failed_thresholds"] == []


def test_evaluate_thresholds_reports_failed_fields():
    module = load_module()
    result = module.evaluate_thresholds(
        {
            "source_overlap_with_webui": 0.2,
            "citation_support_score": 0.0,
            "section_coverage_score": 0.4,
            "unsupported_claim_count": 9,
        }
    )

    assert result["passes_quality_gate"] is False
    assert result["failed_thresholds"] == [
        "source_overlap_with_webui",
        "citation_support_score",
        "section_coverage_score",
        "unsupported_claim_count",
    ]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\codex_skill tests\codex_skill\test_compare_webui_codex_quality.py
```

Expected:

```text
FAILED ... AttributeError: module ... has no attribute 'evaluate_thresholds'
```

- [ ] **Step 3: Add thresholds and evaluation**

Add this near the top of `compare_webui_codex_quality.py`:

```python
DEFAULT_THRESHOLDS = {
    "source_overlap_with_webui": 0.7,
    "citation_support_score": 0.85,
    "section_coverage_score": 0.8,
    "unsupported_claim_count": 3,
}
```

Add this function:

```python
def evaluate_thresholds(row: dict[str, Any], thresholds: dict[str, float] | None = None) -> dict[str, Any]:
    limits = thresholds or DEFAULT_THRESHOLDS
    failed = []
    for key in [
        "source_overlap_with_webui",
        "citation_support_score",
        "section_coverage_score",
    ]:
        if float(row.get(key, 0.0)) < float(limits[key]):
            failed.append(key)
    if int(row.get("unsupported_claim_count", 0)) > int(limits["unsupported_claim_count"]):
        failed.append("unsupported_claim_count")
    return {
        "passes_quality_gate": not failed,
        "failed_thresholds": failed,
    }
```

In `compare()`, merge the evaluation into the returned row:

```python
    row = {
        "topic": topic,
        "mode": mode,
        "source_count": len(candidate_sources),
        "source_overlap_with_webui": score_overlap(candidate_sources, reference_sources),
        "citation_support_score": 1.0 if candidate_citations else 0.0,
        "section_coverage_score": section_coverage(candidate, reference),
        "unsupported_claim_count": unsupported_claim_count,
        "grader_summary": "Lightweight structural comparison; use human or LLM grading for factual parity.",
    }
    row.update(evaluate_thresholds(row))
    return row
```

- [ ] **Step 4: Include pass/fail in Markdown output**

Change the Markdown table header to:

```python
        "| Topic | Mode | Sources | Source overlap | Citation score | Section score | Unsupported claims | Pass | Failed thresholds |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
```

Change the row formatter to:

```python
        lines.append(
            "| {topic} | {mode} | {source_count} | {source_overlap_with_webui} | {citation_support_score} | {section_coverage_score} | {unsupported_claim_count} | {passes_quality_gate} | {failed} |".format(
                failed=", ".join(row.get("failed_thresholds", [])),
                **row,
            )
        )
```

- [ ] **Step 5: Run quality comparator tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\codex_skill tests\codex_skill\test_compare_webui_codex_quality.py
```

Expected:

```text
2 passed
```

- [ ] **Step 6: Commit**

```powershell
git add codex-skills/local-deep-research-codex/scripts/compare_webui_codex_quality.py tests/codex_skill/test_compare_webui_codex_quality.py
git commit -m "feat: add codex quality gate thresholds"
```

---

### Task 8: Final Readiness Validation

**Files:**
- Verify only.

- [ ] **Step 1: Run all focused validation commands**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\codex_skill tests\codex_skill
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\llm\providers tests\llm\providers\test_codex_bridge.py
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 tests\web\test_settings_available_models_helpers.py
.venv\Scripts\python.exe -m pytest -q -o timeout_method=thread -o timeout=180 --confcutdir=tests\integration tests\integration\test_webui_pipeline_codex_bridge.py tests\integration\test_codex_bridge_real_pipeline.py
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 2: Run the readiness diagnostic**

Run:

```powershell
$env:LDR_ENABLE_CODEX_BRIDGE='1'
$env:LDR_CODEX_BRIDGE_DIR=(Resolve-Path .codex_bridge).Path
$env:LDR_CODEX_BRIDGE_REQUIRE_RESPONDER='1'
.venv\Scripts\python.exe codex-skills\local-deep-research-codex\scripts\respond_to_codex_bridge.py --bridge-dir .codex_bridge --heartbeat --model gpt-5.5
.venv\Scripts\python.exe codex-skills\local-deep-research-codex\scripts\check_ldr_access.py --repo . --pretty --probe-timeout 20
```

Expected:

```text
"active_skill_installed": true
"direct_api_ok": true
"discovery_ok": true
"codex_bridge_mode_available": true
```

- [ ] **Step 3: Run a completed-output quality comparison**

After producing one WebUI/LDR exact report and one Codex bridge exact report for the same topic and settings, run:

```powershell
.venv\Scripts\python.exe codex-skills\local-deep-research-codex\scripts\compare_webui_codex_quality.py `
  --topic "Codex Bridge parity smoke test" `
  --webui-output outputs\webui-ldr-exact.md `
  --mode-output codex_bridge_exact=outputs\codex-bridge-exact.md `
  --mode-output codex_like=outputs\codex-like.md `
  --json-output outputs\quality.json `
  --markdown-output outputs\quality.md
```

Expected:

```text
outputs\quality.json exists
outputs\quality.md exists
codex_bridge_exact has "passes_quality_gate": true for the chosen smoke topic
```

- [ ] **Step 4: Commit validation-only changes if docs changed during validation**

If no files changed, do not create an empty commit. If validation updated docs or fixtures, run:

```powershell
git add <changed-doc-or-fixture-path>
git commit -m "docs: record codex bridge readiness validation"
```

---

## Completion Criteria

- The active Codex skill install check passes.
- WebUI model discovery can show `codex_bridge` with `gpt-5.5`.
- Diagnostics finish without MCP/config timeouts by default.
- Bridge availability can require and detect a responder heartbeat.
- A real LDR API pipeline test passes with `AdvancedSearchSystem` and `IntegratedReportGenerator`.
- The quality comparator reports pass/fail thresholds for same-topic completed runs.
- The final user-facing answer states `codex_like` is approximate, `ldr_exact` is exact LDR but not Codex-as-model, and `codex_bridge_exact` is the only candidate for exact WebUI internals with Codex model calls.
