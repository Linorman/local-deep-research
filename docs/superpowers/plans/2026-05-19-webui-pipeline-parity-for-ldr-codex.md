# WebUI Pipeline Parity For LDR Codex

**For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to execute this plan task-by-task.

## Goal

Make the `local-deep-research-codex` skill clearly distinguish three execution levels and add the missing machinery for the highest level:

1. **WebUI-like Codex mode:** Codex orchestrates research using LDR raw retrieval and writes the report itself.
2. **Exact LDR provider-backed mode:** Codex delegates generation to LDR's existing `quick_research`, `detailed_research`, or `generate_report` APIs, using the model provider configured inside LDR.
3. **Exact LDR pipeline with Codex as model:** LDR's own `AdvancedSearchSystem`, strategies, citation handling, and `IntegratedReportGenerator` run unchanged, while every LLM call is answered by Codex through an explicit bridge.

Current state supports level 1 as an approximation and documents level 2 as the route to exact WebUI output. It does not yet support level 3, and level 1 cannot guarantee WebUI-equivalent quality even when both sides use GPT-5.5.

## WebUI Pipeline Facts To Preserve

The exact WebUI path is:

1. Browser form collects query, mode, provider, model, search engine, strategy, iterations, and questions per iteration.
2. `/research/api/start` delegates to `/api/start_research`.
3. `research_routes.start_research()` validates inputs, captures a full settings snapshot, writes `ResearchHistory`, handles queue/concurrency, and starts a worker thread.
4. `research_service.run_research_process()` builds `get_llm()`, `get_search()`, and `AdvancedSearchSystem`.
5. `AdvancedSearchSystem.analyze_topic()` dispatches the selected strategy.
6. Strategies generate LLM questions, run searches, filter/rank results, synthesize findings, and track citations/sources.
7. Quick mode stores formatted findings directly.
8. Detailed mode calls `IntegratedReportGenerator.generate_report()`, which asks the LLM for report structure and re-runs focused subsection research before formatting the final report.
9. The WebUI persists report content, metadata, progress events, source ledgers, errors, metrics, and optional exports.

## Architecture

Use a strict mode boundary:

- `codex_like`: current raw-search-plus-Codex synthesis workflow. It is useful, but never described as exact.
- `ldr_exact`: use existing LDR generation APIs with LDR's configured provider and model. This is the immediate production path for WebUI parity.
- `codex_bridge_exact`: experimental provider path where LDR treats Codex as a LangChain chat model through a queue/IPC bridge. This is required if "Codex GPT-5.5" must drive the exact WebUI pipeline.

The bridge must not pretend Codex is an OpenAI-compatible endpoint. It must be explicitly enabled, observable, timeout-bounded, and disabled by default.

Add sub-agents as a Codex-side context management layer, not as a parity mechanism. Sub-agents can help split large evidence sets, independent section research, source audit, and benchmark review. They do not replace the WebUI pipeline, and they must not fragment canonical state such as citation ids, source ledger ordering, settings snapshots, or final report ownership.

Mode rules:

- `codex_like`: sub-agents are allowed for parallel retrieval, evidence extraction, contradiction checks, and section-level drafts.
- `ldr_exact`: sub-agents are not part of the LDR run; use them only before the run for code/config inspection or after the run for report QA.
- `codex_bridge_exact`: the bridge coordinator owns the one-request-to-one-response contract. Sub-agents may inspect large source packets or audit responses, but they should not answer bridge prompts unless the benchmark harness explicitly validates that this does not degrade parity.

## Tasks

- [x] Add a parity matrix document.

  Create `codex-skills/local-deep-research-codex/references/webui-pipeline-parity.md`.

  Include:

  - WebUI call graph from browser submit to report persistence.
  - Table comparing `codex_like`, `ldr_exact`, and `codex_bridge_exact`.
  - Explicit non-equivalence list for queue state, DB history, Socket.IO events, provider prompts, source ordering, citation offsets, token accounting, and exports.
  - User-facing decision rule:

    ```text
    If exact WebUI result shape matters, use ldr_exact.
    If exact WebUI internals plus Codex-as-model matters, use codex_bridge_exact after bridge validation.
    If no LDR model provider is available, use codex_like and label the result as approximate.
    ```

- [x] Update the skill entrypoint to require mode declaration.

  Modify `codex-skills/local-deep-research-codex/SKILL.md`.

  Add a mandatory startup step:

  ```text
  Before research begins, state the selected execution mode:
  - codex_like
  - ldr_exact
  - codex_bridge_exact

  If the user asks for exact WebUI parity and no exact mode is available, stop and report the missing requirement instead of silently falling back.
  ```

  Link the new parity document from the references section.

- [x] Add sub-agent context orchestration guidance.

  Create `codex-skills/local-deep-research-codex/references/subagent-context-orchestration.md`.

  Document:

  - Sub-agents solve context pressure and parallel review; they do not make approximate mode exact.
  - The main Codex coordinator owns final decisions, final report text, canonical citation numbering, source deduplication, and mode labeling.
  - Recommended roles:

    ```text
    pipeline_mapper: inspect code paths and strategy-specific prompts.
    retrieval_worker: run or summarize independent raw-search packets.
    evidence_auditor: verify that claims are supported by source ledger entries.
    section_worker: draft a bounded report subsection from a supplied evidence packet.
    benchmark_reviewer: compare two completed outputs against the parity rubric.
    ```

  - Merge contract:

    ```text
    Every sub-agent output must include:
    - task id
    - input packet id
    - sources touched
    - claims supported
    - unresolved gaps
    - confidence notes
    - no mutation of canonical citation ids
    ```

  - Failure modes to guard against: duplicated sources, inconsistent citation ids, hidden assumptions, unsupported claims, and section drift from the original research question.

- [x] Add optional sub-agent packet splitting for Codex-like mode.

  Create `codex-skills/local-deep-research-codex/scripts/split_research_packet_for_subagents.py`.

  Inputs:

  ```powershell
  .venv\Scripts\python.exe codex-skills\local-deep-research-codex\scripts\split_research_packet_for_subagents.py `
    --packet research_packet.md `
    --mode codex_like `
    --output-dir packets\subagents `
    --max-sources-per-packet 8
  ```

  Outputs:

  ```text
  packets/subagents/001-retrieval-worker.md
  packets/subagents/002-evidence-auditor.md
  packets/subagents/003-section-worker.md
  packets/subagents/manifest.json
  ```

  Rules:

  - Refuse to split `ldr_exact` runs except for post-run QA packets.
  - For `codex_bridge_exact`, emit audit packets only; do not emit bridge-answering packets by default.
  - Keep each packet self-contained with objective, allowed sources, required output schema, and merge constraints.
  - Preserve the main packet as the only canonical source ledger.

- [x] Add tests for sub-agent packet splitting.

  Create `tests/codex_skill/test_split_research_packet_for_subagents.py`.

  Cover:

  - `codex_like` produces retrieval, evidence, and section packets.
  - `ldr_exact` refuses active-run splitting and allows post-run QA mode.
  - `codex_bridge_exact` emits audit packets only.
  - Manifest source ids match the original packet and do not renumber citations.

  Verification command:

  ```powershell
  .venv\Scripts\python.exe -m pytest tests/codex_skill/test_split_research_packet_for_subagents.py
  ```

- [x] Harden diagnostics so the skill can prove whether exact modes are available.

  Modify `codex-skills/local-deep-research-codex/scripts/check_ldr_access.py`.

  Add probes with per-probe subprocess timeouts:

  - Default Python import of `local_deep_research`.
  - Repo `.venv/Scripts/python.exe` import of `local_deep_research`.
  - `local_deep_research.mcp.server` import.
  - `get_configuration` availability.
  - Web entrypoint availability.
  - Active skill install check under `$CODEX_HOME/skills/local-deep-research-codex`.

  Expected JSON fields:

  ```json
  {
    "default_python_ok": true,
    "repo_venv_python_ok": true,
    "mcp_import_ok": true,
    "mcp_import_timed_out": false,
    "web_entrypoint_ok": true,
    "active_skill_installed": true,
    "exact_ldr_mode_available": true,
    "codex_bridge_mode_available": false
  }
  ```

- [x] Add tests for diagnostics.

  Create `tests/codex_skill/test_check_ldr_access.py`.

  Cover:

  - Missing dependency reports `exact_ldr_mode_available=false`.
  - Hanging probe is terminated and reported as `*_timed_out=true`.
  - Installed skill path detection works when `CODEX_HOME` is pointed at a temp directory.

  Verification command:

  ```powershell
  .venv\Scripts\python.exe -m pytest tests/codex_skill/test_check_ldr_access.py
  ```

- [x] Make harness mode semantics explicit.

  Modify `codex-skills/local-deep-research-codex/scripts/prepare_harness_run.py`.

  Add an `execution_mode` field with values:

  - `codex_like`
  - `ldr_exact`
  - `codex_bridge_exact`

  Rules:

  - `exact_webui=true` and `allow_ldr_generation=true` maps to `ldr_exact`.
  - `exact_webui=true` and `codex_bridge=true` maps to `codex_bridge_exact`.
  - `exact_webui=true` without either exact backend returns a validation error.
  - Default remains `codex_like`.

  The generated Codex prompt must say which mode is selected and which tools are allowed.

- [x] Add tests for harness mode routing.

  Create `tests/codex_skill/test_prepare_harness_run.py`.

  Assertions:

  - `exact_webui=true` without generation or bridge fails.
  - `allow_ldr_generation=true` selects `ldr_exact`.
  - `codex_bridge=true` selects `codex_bridge_exact`.
  - Default selects `codex_like` and forbids claims of exact WebUI parity.

  Verification command:

  ```powershell
  .venv\Scripts\python.exe -m pytest tests/codex_skill/test_prepare_harness_run.py
  ```

- [x] Add an LDR provider for explicit Codex bridge mode.

  Create `src/local_deep_research/llm/providers/implementations/codex_bridge.py`.

  Implement a LangChain-compatible chat model provider with this behavior:

  - Accepts `bridge_dir`, `timeout_seconds`, `poll_interval_seconds`, and `max_prompt_chars`.
  - Serializes each invocation into a JSON request file.
  - Waits for a JSON response file with the same request id.
  - Returns an `AIMessage` with the response content.
  - Raises a clear timeout exception with the request id and bridge path.
  - Records request metadata without writing API keys or secrets.

  Request shape:

  ```json
  {
    "id": "uuid",
    "created_at": "2026-05-19T00:00:00Z",
    "messages": [
      {"role": "system", "content": "..."},
      {"role": "user", "content": "..."}
    ],
    "model": "gpt-5.5",
    "temperature": 0.2,
    "metadata": {
      "research_id": "...",
      "phase": "question_generation"
    }
  }
  ```

  Response shape:

  ```json
  {
    "id": "same uuid",
    "completed_at": "2026-05-19T00:00:10Z",
    "content": "...",
    "usage": {
      "input_tokens": 0,
      "output_tokens": 0
    }
  }
  ```

- [x] Register the Codex bridge provider behind an explicit feature flag.

  Modify provider discovery/config files under `src/local_deep_research/llm/providers/`.

  Requirements:

  - Provider name is `codex_bridge`.
  - It is unavailable unless `LDR_ENABLE_CODEX_BRIDGE=1`.
  - It does not appear as a default provider.
  - Error message says the bridge is experimental and requires a responder process.
  - Existing providers remain unchanged.

- [x] Add a Codex bridge responder script for manual/harness use.

  Create `codex-skills/local-deep-research-codex/scripts/respond_to_codex_bridge.py`.

  Purpose:

  - Poll `bridge_dir/requests/*.json`.
  - Present the next request content to Codex in a bounded prompt.
  - Write `bridge_dir/responses/<id>.json` after Codex generates the answer.

  Since a normal repository script cannot directly call this Codex session, implement it as a helper that validates queue files, formats the request into a prompt, and writes responses from stdin or an explicitly supplied response file. The skill instructions will drive Codex to use it.

- [x] Add bridge unit tests.

  Create `tests/llm/providers/test_codex_bridge.py`.

  Cover:

  - Request file creation.
  - Response file parsing.
  - Timeout behavior.
  - Secret redaction in persisted metadata.
  - Feature flag required for registration.

  Verification command:

  ```powershell
  .venv\Scripts\python.exe -m pytest tests/llm/providers/test_codex_bridge.py
  ```

- [x] Add an exact-pipeline integration test with fake search and fake bridge responses.

  Create `tests/integration/test_webui_pipeline_codex_bridge.py`.

  Use deterministic fake responses for:

  - Initial question generation.
  - Follow-up question generation.
  - Cross-engine filtering.
  - Citation synthesis.
  - Report structure.
  - Section and subsection generation.

  Assert:

  - `AdvancedSearchSystem.analyze_topic()` is the code path used.
  - `IntegratedReportGenerator.generate_report()` is called in detailed mode.
  - `all_links_of_system` is preserved.
  - Final report contains expected section headings and numbered source references.

- [x] Add a quality comparison harness.

  Create `codex-skills/local-deep-research-codex/scripts/compare_webui_codex_quality.py`.

  It should run the same benchmark topics through:

  - `ldr_exact` with LDR provider set to GPT-5.5.
  - `codex_bridge_exact` with Codex set to GPT-5.5.
  - `codex_like`.

  Output JSON metrics:

  ```json
  {
    "topic": "...",
    "mode": "codex_bridge_exact",
    "source_count": 24,
    "source_overlap_with_webui": 0.72,
    "citation_support_score": 0.86,
    "section_coverage_score": 0.91,
    "unsupported_claim_count": 2,
    "grader_summary": "..."
  }
  ```

  Add a Markdown summary writer for human review.

- [x] Document quality expectations.

  Update `codex-skills/local-deep-research-codex/references/webui-like-codex-workflow.md`.

  Add:

  - Same model id is not enough for equivalent output.
  - Prompt templates, truncation, source filtering, citation code, report section re-search, temperature, and tool ordering all affect quality.
  - `codex_like` may produce comparable prose but must be labeled as approximate.
  - Only `ldr_exact` or `codex_bridge_exact` should be called WebUI-pipeline parity.

- [x] Run focused validation.

  Commands:

  ```powershell
  .venv\Scripts\python.exe -m pytest -o timeout_method=thread -o timeout=180 --confcutdir=tests/codex_skill tests/codex_skill
  .venv\Scripts\python.exe -m pytest -o timeout_method=thread -o timeout=180 --confcutdir=tests/llm/providers tests/llm/providers/test_codex_bridge.py
  .venv\Scripts\python.exe -m pytest -o timeout_method=thread -o timeout=180 --confcutdir=tests/integration tests/integration/test_webui_pipeline_codex_bridge.py
  .venv\Scripts\python.exe codex-skills\local-deep-research-codex\scripts\check_ldr_access.py --repo . --pretty
  .venv\Scripts\python.exe codex-skills\local-deep-research-codex\scripts\prepare_harness_run.py --help
  ```

  Completion criteria:

  - Tests pass.
  - Diagnostics do not hang.
  - Skill docs no longer imply WebUI-like mode is exact.
  - Exact mode refuses to run unless LDR generation or Codex bridge is available.
  - Benchmark report clearly states whether Codex GPT-5.5 reaches WebUI GPT-5.5 parity on the tested topics.

## Expected Outcome

After this plan is implemented:

- Users can run approximate Codex-led research honestly.
- Users can invoke exact WebUI behavior through LDR's provider-backed API when LDR has GPT-5.5 configured.
- Users can experimentally run the exact LDR pipeline with Codex GPT-5.5 as the model through a visible, opt-in bridge.
- The repository will have tests and diagnostics proving which mode is available instead of relying on assumptions.
