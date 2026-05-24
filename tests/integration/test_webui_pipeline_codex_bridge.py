import importlib.util
import json
import sys
import threading
import time
import types
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage


ROOT = Path(__file__).resolve().parents[2]
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


def bridge_responder(bridge_dir: Path, responses: list[str], stop: threading.Event):
    requests_dir = bridge_dir / "requests"
    responses_dir = bridge_dir / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    while not stop.is_set() and responses:
        for request_path in sorted(requests_dir.glob("*.json")):
            if request_path.name in seen:
                continue
            seen.add(request_path.name)
            payload = json.loads(request_path.read_text(encoding="utf-8"))
            content = responses.pop(0)
            (responses_dir / request_path.name).write_text(
                json.dumps({"id": payload["id"], "content": content}),
                encoding="utf-8",
            )
        time.sleep(0.005)


class FakeAdvancedSearchSystem:
    def __init__(self, llm):
        self.llm = llm
        self.all_links_of_system = []
        self.analyze_topic_called = False

    def analyze_topic(self, query):
        self.analyze_topic_called = True
        questions = self.llm.invoke([HumanMessage(content=f"questions for {query}")])
        synthesis = self.llm.invoke([HumanMessage(content="citation synthesis")])
        self.all_links_of_system.append(
            {"title": "Source A", "url": "https://example.com/a"}
        )
        return {
            "query": query,
            "current_knowledge": synthesis.content,
            "questions_by_iteration": [[questions.content]],
            "search_system": self,
            "all_links_of_system": self.all_links_of_system,
        }


class FakeIntegratedReportGenerator:
    def __init__(self, search_system):
        self.search_system = search_system
        self.generate_report_called = False

    def generate_report(self, results, query, progress_callback=None):
        self.generate_report_called = True
        structure = self.search_system.llm.invoke(
            [HumanMessage(content="report structure")]
        )
        section = self.search_system.llm.invoke([HumanMessage(content="section body")])
        return (
            "# Report\n\n"
            f"{structure.content}\n\n"
            f"{section.content}\n\n"
            "Sources\n\n[1] https://example.com/a"
        )


def test_bridge_supports_exact_pipeline_request_sequence(tmp_path):
    module = load_codex_bridge_module()
    bridge_dir = tmp_path / "bridge"
    pending_responses = [
        "Q: focused question",
        "Synthesized current knowledge [1]",
        "STRUCTURE\n1. Findings",
        "Detailed section content [1]",
    ]
    stop = threading.Event()
    thread = threading.Thread(
        target=bridge_responder,
        args=(bridge_dir, pending_responses, stop),
        daemon=True,
    )
    thread.start()

    try:
        llm = module.CodexBridgeChatModel(
            bridge_dir=str(bridge_dir),
            model="gpt-5.5",
            timeout_seconds=2,
            poll_interval_seconds=0.01,
        )
        search_system = FakeAdvancedSearchSystem(llm)
        results = search_system.analyze_topic("Assess parity")
        report_generator = FakeIntegratedReportGenerator(search_system)
        final_report = report_generator.generate_report(results, "Assess parity")
    finally:
        stop.set()
        thread.join(timeout=1)

    assert search_system.analyze_topic_called is True
    assert report_generator.generate_report_called is True
    assert search_system.all_links_of_system == [
        {"title": "Source A", "url": "https://example.com/a"}
    ]
    assert "# Report" in final_report
    assert "STRUCTURE" in final_report
    assert "[1] https://example.com/a" in final_report
