import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "codex-skills"
    / "local-deep-research-codex"
    / "scripts"
    / "split_research_packet_for_subagents.py"
)


PACKET = """# LDR Codex Research Packet

## Objective

Assess parity.

## Source Ledger

| Source ID | Engine | Title | URL or local ID | Date | Why it matters | Credibility / limitation |
| --- | --- | --- | --- | --- | --- | --- |
| S01 | web | Alpha | https://example.com/a | 2026 | A | ok |
| S02 | web | Beta | https://example.com/b | 2026 | B | ok |

## Claim Table

| Claim | Source IDs | Confidence | Limitation |
| --- | --- | --- | --- |
| Claim A | S01 | high | none |
"""


def load_splitter():
    spec = importlib.util.spec_from_file_location(
        "split_research_packet_for_subagents", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_packet(tmp_path):
    packet = tmp_path / "packet.md"
    packet.write_text(PACKET, encoding="utf-8")
    return packet


def test_codex_like_produces_retrieval_evidence_and_section_packets(tmp_path):
    module = load_splitter()
    packet = write_packet(tmp_path)

    manifest = module.split_packet(
        packet,
        mode="codex_like",
        output_dir=tmp_path / "out",
        max_sources_per_packet=1,
    )

    roles = {task["role"] for task in manifest["tasks"]}
    assert {"retrieval_worker", "evidence_auditor", "section_worker"} <= roles
    assert manifest["source_ids"] == ["S01", "S02"]


def test_ldr_exact_refuses_active_run_and_allows_post_run_qa(tmp_path):
    module = load_splitter()
    packet = write_packet(tmp_path)

    with pytest.raises(ValueError, match="ldr_exact"):
        module.split_packet(packet, mode="ldr_exact", output_dir=tmp_path / "active")

    manifest = module.split_packet(
        packet,
        mode="ldr_exact",
        output_dir=tmp_path / "qa",
        stage="post_run_qa",
    )

    assert {task["role"] for task in manifest["tasks"]} == {"benchmark_reviewer"}


def test_codex_bridge_exact_emits_audit_packets_only(tmp_path):
    module = load_splitter()
    packet = write_packet(tmp_path)

    manifest = module.split_packet(
        packet,
        mode="codex_bridge_exact",
        output_dir=tmp_path / "bridge",
    )

    roles = {task["role"] for task in manifest["tasks"]}
    assert roles == {"evidence_auditor"}
    assert all("bridge prompt" not in Path(task["path"]).read_text(encoding="utf-8").lower() for task in manifest["tasks"])
