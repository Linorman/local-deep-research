import json
import importlib.util
import sys
import types
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage, SystemMessage


ROOT = Path(__file__).resolve().parents[3]
PROVIDER_PATH = (
    ROOT
    / "src"
    / "local_deep_research"
    / "llm"
    / "providers"
    / "implementations"
    / "codex_bridge.py"
)
BASE_PATH = ROOT / "src" / "local_deep_research" / "llm" / "providers" / "base.py"


@pytest.fixture(autouse=True)
def reset_all_singletons():
    yield


def load_codex_bridge_module():
    for name, path in {
        "local_deep_research": ROOT / "src" / "local_deep_research",
        "local_deep_research.llm": ROOT / "src" / "local_deep_research" / "llm",
        "local_deep_research.llm.providers": ROOT
        / "src"
        / "local_deep_research"
        / "llm"
        / "providers",
        "local_deep_research.llm.providers.implementations": ROOT
        / "src"
        / "local_deep_research"
        / "llm"
        / "providers"
        / "implementations",
    }.items():
        package = types.ModuleType(name)
        package.__path__ = [str(path)]
        sys.modules.setdefault(name, package)

    base_spec = importlib.util.spec_from_file_location(
        "local_deep_research.llm.providers.base", BASE_PATH
    )
    base_module = importlib.util.module_from_spec(base_spec)
    assert base_spec.loader is not None
    sys.modules[base_spec.name] = base_module
    base_spec.loader.exec_module(base_module)

    spec = importlib.util.spec_from_file_location(
        "local_deep_research.llm.providers.implementations.codex_bridge",
        PROVIDER_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_request_file_creation_and_response_parsing(tmp_path):
    module = load_codex_bridge_module()

    model = module.CodexBridgeChatModel(
        bridge_dir=str(tmp_path),
        model="gpt-5.5",
        timeout_seconds=0.2,
        poll_interval_seconds=0.01,
    )

    requests_dir = tmp_path / "requests"
    responses_dir = tmp_path / "responses"
    responses_dir.mkdir(parents=True)

    request_id = model._write_request(
        [SystemMessage(content="system"), HumanMessage(content="hello")]
    )
    request_payload = json.loads(
        (requests_dir / f"{request_id}.json").read_text(encoding="utf-8")
    )
    assert request_payload["model"] == "gpt-5.5"
    assert request_payload["messages"][0]["role"] == "system"

    (responses_dir / f"{request_id}.json").write_text(
        json.dumps({"id": request_id, "content": "bridge response"}),
        encoding="utf-8",
    )

    content, usage = model._wait_for_response(request_id)

    assert content == "bridge response"
    assert usage == {}


def test_timeout_behavior(tmp_path):
    module = load_codex_bridge_module()

    model = module.CodexBridgeChatModel(
        bridge_dir=str(tmp_path),
        timeout_seconds=0.01,
        poll_interval_seconds=0.01,
    )

    with pytest.raises(module.CodexBridgeTimeout, match="Timed out waiting"):
        model._generate([HumanMessage(content="hello")])


def test_secret_redaction_in_request_metadata(tmp_path):
    module = load_codex_bridge_module()

    model = module.CodexBridgeChatModel(
        bridge_dir=str(tmp_path),
        metadata={
            "api_key": "secret",
            "nested": {"token": "secret-token", "safe": "visible"},
        },
    )

    request_id = model._write_request([HumanMessage(content="hello")])
    payload = json.loads(
        (tmp_path / "requests" / f"{request_id}.json").read_text(
            encoding="utf-8"
        )
    )

    assert payload["metadata"]["api_key"] == "[REDACTED]"
    assert payload["metadata"]["nested"]["token"] == "[REDACTED]"
    assert payload["metadata"]["nested"]["safe"] == "visible"


def test_feature_flag_required_for_provider_availability(monkeypatch):
    module = load_codex_bridge_module()

    monkeypatch.delenv("LDR_ENABLE_CODEX_BRIDGE", raising=False)
    assert module.CodexBridgeProvider.is_discoverable() is False
    assert module.CodexBridgeProvider.is_available() is False

    monkeypatch.setenv("LDR_ENABLE_CODEX_BRIDGE", "1")
    assert module.CodexBridgeProvider.is_discoverable() is True
    assert module.CodexBridgeProvider.is_available() is True
