import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = (
    Path(__file__).resolve().parents[2]
    / "codex-skills"
    / "local-deep-research-codex"
    / "scripts"
)


@pytest.fixture(autouse=True)
def reset_all_singletons():
    yield


def load_responder():
    spec = importlib.util.spec_from_file_location(
        "respond_to_codex_bridge",
        SCRIPT_DIR / "respond_to_codex_bridge.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def request_with(content):
    return {
        "id": "request-1",
        "model": "gpt-5.5",
        "messages": [{"role": "user", "content": content}],
    }


def test_classifies_report_structure_request():
    module = load_responder()
    request = request_with(
        "Determine the most appropriate report structure. "
        "Return a table of contents structure."
    )

    assert module.classify_request(request) == "report_structure"


def test_print_prompt_includes_detected_contract_for_pubmed_query():
    module = load_responder()
    request = request_with("Create an optimized PubMed search query for protein pockets.")

    prompt = module.format_prompt(request)

    assert "Detected request kind: pubmed_query_transform" in prompt
    assert "Return only the PubMed query string" in prompt


def test_validates_binary_historical_classifier():
    module = load_responder()

    assert module.validate_response_for_kind("historical_query_classifier", "yes") == []
    assert module.validate_response_for_kind("historical_query_classifier", "maybe")


def test_validates_search_question_generation_format():
    module = load_responder()

    assert module.validate_response_for_kind(
        "search_question_generation", "Q: protein pocket detection 2024 review"
    ) == []
    assert module.validate_response_for_kind(
        "search_question_generation", "protein pocket detection 2024 review"
    )


def test_write_response_can_append_manifest(tmp_path):
    module = load_responder()
    bridge_dir = tmp_path / "codex_bridge"
    request_dir = bridge_dir / "requests"
    request_dir.mkdir(parents=True)
    request = request_with("Answer ONLY \"yes\" if this is a historical query.")
    request_path = request_dir / "request-1.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    manifest = tmp_path / "request_manifest.jsonl"

    response_path = module.write_response(
        bridge_dir,
        "request-1",
        "yes",
        request=request,
        request_path=request_path,
        manifest_output=manifest,
    )

    assert response_path.exists()
    entry = json.loads(manifest.read_text(encoding="utf-8").strip())
    assert entry["request_id"] == "request-1"
    assert entry["kind"] == "historical_query_classifier"
    assert entry["response_path"] == str(response_path)
