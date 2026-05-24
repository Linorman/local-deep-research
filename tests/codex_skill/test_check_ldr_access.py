import importlib.util
import subprocess
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "codex-skills"
    / "local-deep-research-codex"
    / "scripts"
    / "check_ldr_access.py"
)


def load_check_ldr_access():
    spec = importlib.util.spec_from_file_location("check_ldr_access", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_subprocess_probe_reports_timeout(monkeypatch):
    module = load_check_ldr_access()

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = module.run_python_probe(
        "timeout_probe",
        Path("python"),
        "print('never')",
        timeout_seconds=0.01,
    )

    assert result["ok"] is False
    assert result["timed_out"] is True
    assert result["name"] == "timeout_probe"


def test_active_skill_install_detection(tmp_path, monkeypatch):
    module = load_check_ldr_access()
    skill_dir = tmp_path / "skills" / "local-deep-research-codex"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))

    result = module.probe_active_skill_install()

    assert result["active_skill_installed"] is True
    assert result["active_skill_path"] == str(skill_dir)


def test_summary_marks_exact_mode_unavailable():
    module = load_check_ldr_access()
    summary = module.summarize_probe_results(
        {
            "default_python_import": {"ok": False},
            "repo_venv_python_import": {"ok": False},
            "mcp_import": {"ok": False, "timed_out": False},
            "configuration": {"ok": False},
            "web_entrypoint": {"ok": False},
            "active_skill_install": {"active_skill_installed": False},
            "codex_bridge": {"available": False},
        }
    )

    assert summary["exact_ldr_mode_available"] is False
    assert summary["codex_bridge_mode_available"] is False
