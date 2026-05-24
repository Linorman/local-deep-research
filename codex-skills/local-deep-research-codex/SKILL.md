---
name: local-deep-research-codex
description: Use when users want Local Deep Research work without LLM API keys, want Codex quota or Codex capabilities to replace LDR-side generation, request Codex-as-model research, ask for WebUI-like reports using LDR retrieval, or need compliant Codex/LDR integration boundaries.
---

# Local Deep Research With Codex

Use this skill to make Codex the research orchestrator and Local Deep Research (LDR) the retrieval substrate.

## Operating Model

- Use LDR for retrieval, discovery, configured local document access, strategy metadata, and source collection.
- Use Codex for decomposition, follow-up question design, evidence comparison, source conflict analysis, synthesis, and report writing.
- When the user asks for WebUI-like results with Codex as the generator, emulate WebUI phases: setup, planning, iterative retrieval, current-knowledge updates, report generation, source formatting, and limitations.
- Prefer no-LLM LDR operations before any LDR operation that calls its configured model provider.
- Treat raw local document retrieval as available only when LDR exposes the collection as a search engine or retrievable collection.
- Do not claim Codex is an OpenAI-compatible model endpoint or a drop-in `BaseChatModel`.
- Keep generated text attribution clear: Codex-generated synthesis is not the same as LDR provider-generated output.

## Start Every Task

1. Identify the user intent: fast fact check, deep research, report, local document analysis, strategy comparison, setup help, or provider replacement question.
   - If the task arrives from a harness payload, honor the harness parameters and `codex_prompt` before inferring defaults.
2. Declare the execution mode before research begins:
   - `codex_like`
   - `ldr_exact`
   - `codex_bridge_exact`
   If the user asks for exact WebUI parity and no exact mode is available, stop and report the missing requirement instead of silently falling back.
3. Check available LDR access in this order:
   - Installed MCP tools or app-provided LDR tools.
   - Local `ldr-mcp`, `python -m local_deep_research.mcp`, or Python API from the project environment.
   - Repository documentation when tools are not runnable.
   - If using the project copy of this skill and LDR availability is unclear, run `python codex-skills/local-deep-research-codex/scripts/check_ldr_access.py --repo . --pretty`.
4. Prefer discovery calls before research calls:
   - `list_search_engines`
   - `list_strategies`
   - `get_configuration`
5. Pick retrieval tools that do not require an LDR LLM provider whenever possible.
6. Run retrieval in small rounds, inspect sources, then decide the next round.

## WebUI-Like Codex Mode

Use this mode when the user wants results similar to official WebUI research while using Codex for generation.

1. Select a mode: quick summary, detailed research, or full report.
2. Create a research packet with objective, assumptions, chosen engines, subquestions, source ledger, claim table, gaps, and current knowledge. For long work, use `scripts/new_research_packet.py`.
3. Run LDR discovery and raw search by iteration, using WebUI settings when available.
4. After each iteration, compress raw results into current knowledge with source IDs and open gaps; keep enough detail to audit every final claim.
5. Use subagents only when the current runtime allows them and the user has authorized delegation or parallel agent work. Split by independent subquestion, engine family, or source type; reconcile conflicts locally before final synthesis.
6. Produce a WebUI-style final answer: title, scope, method, executive summary, detailed findings, source-backed evidence, limitations, and source list.

## Harness Mode

Use harness mode when an external runner needs deterministic setup before handing work to Codex.

- Accept parameters from a prepared JSON payload or from prompt directives such as `[ldr-codex mode=report engine=arxiv iterations=3 language=zh-CN]`.
- Explicit harness parameters override natural-language inference; natural-language inference overrides mode defaults.
- Use `scripts/prepare_harness_run.py` to convert prompt text into JSON containing normalized parameters, suggested LDR environment variables, and the Codex prompt to execute.
- Treat `allow_ldr_generation=false` as a hard boundary: do not call LDR provider-backed generation tools.
- Treat `exact_webui=true` as requiring official LDR WebUI/API generation and therefore a configured LDR model provider.

## Codex Bridge Exact Mode

Use `codex_bridge_exact` when the user wants the LDR/WebUI research pipeline and prompts, but wants every LLM call answered by the active Codex session.

This is the Codex-only exact path. Do not route through the WebUI, do not require an LDR API key, and do not fall back to `codex_like` unless the bridge fails and the user approves the downgrade.

1. Start LDR through `scripts/run_codex_bridge_exact.py`, preferably with `--background` for long runs. The runner must create `<run_dir>/codex_bridge/requests`, `<run_dir>/codex_bridge/responses`, `run_config.json`, `settings_overrides.json`, `settings_snapshot.json`, `status.json`, and `final_report.md`.
2. Ensure the settings snapshot contains:
   - `llm.provider = codex_bridge`
   - `llm.model = gpt-5.5` unless the user selects another Codex model
   - `llm.codex_bridge.bridge_dir = <run_dir>/codex_bridge`
   - `llm.codex_bridge.timeout_seconds = 1200` for deep research unless the user chooses another timeout
   - `search.tool`, `search.iterations`, and `search.questions_per_iteration` from the user request
   - `api.allow_file_output = true`
3. While LDR is running, repeatedly inspect pending requests:
   - `python scripts/respond_to_codex_bridge.py --bridge-dir <run_dir>/codex_bridge --list`
   - `python scripts/respond_to_codex_bridge.py --bridge-dir <run_dir>/codex_bridge --request-id <id> --print-prompt`
4. Answer the printed prompt with Codex, respecting the detected request kind and response contract. Internal requests may require exact formats such as `yes`/`no`, one PubMed query string, `Q:` search questions, or report-structure markers.
5. Write the response with validation and manifest logging:
   - `python scripts/respond_to_codex_bridge.py --bridge-dir <run_dir>/codex_bridge --request-id <id> --response-stdin --validate-response --manifest-output <run_dir>/request_manifest.jsonl`
6. Continue until `status.json` reaches `completed` or `failed`. If it fails, inspect `ldr_process.log`, `status.json`, and `request_manifest.jsonl` before proposing a fix.

For biomedical or scholarly topics, prefer explicit engines such as `semantic_scholar`, `pubmed`, `arxiv`, or a configured metasearch engine when available. Use bare `auto` only when the user requires it or the local LDR configuration has been validated, because poor query-transform responses can make `auto` pick irrelevant engines.

## Tool Selection

- Use LDR `search` for raw search results without LLM processing.
- Use LDR search engines such as `arxiv`, `pubmed`, `wikipedia`, `semantic_scholar`, `github`, or `searxng` based on the user's domain and local configuration.
- Use local document collection workflows only when the user asks about local/private material or a collection is clearly relevant.
- Use `quick_research`, `detailed_research`, `generate_report`, or LDR-side document summarization only after confirming the user accepts that those paths require an LDR model provider.
- If an engine requires a missing API key, switch to a no-key engine when it can satisfy the task; otherwise report the missing setting.

## Research Workflow

1. Restate the research question as a working objective.
2. Break it into 2-6 focused subquestions.
3. Choose search engines and search terms for each subquestion.
4. Retrieve sources with LDR.
5. Track claims, source URLs, dates when relevant, and conflicts.
6. Iterate until the evidence is sufficient or the remaining uncertainty is clear.
7. Produce the final answer with citations, confidence notes, and unresolved gaps.

## When More Detail Is Needed

- Read `references/ldr-interfaces.md` for exact LDR commands, APIs, settings, and MCP boundaries.
- Read `references/research-workflows.md` for task-specific workflows.
- Read `references/webui-like-codex-workflow.md` when the user asks for WebUI-like results with Codex as the generator.
- Read `references/webui-pipeline-parity.md` when the user asks whether Codex can reproduce the WebUI pipeline.
- Read `references/codex-only-bridge-workflow.md` when the user asks for `codex_bridge_exact`, exact LDR pipeline behavior with Codex-only generation, or a long bridge run.
- Read `references/subagent-context-orchestration.md` when a long Codex-led run needs sub-agent packet splitting or review.
- Read `references/harness-integration.md` when an external runner, benchmark harness, or script should prepare Codex/LDR research parameters.
- Read `references/install-and-use.md` for installing LDR, starting MCP/WebUI, installing this skill, diagnostics, and example prompts.
- Read `references/codex-bridge-experimental.md` when the user asks for transparent provider replacement or a Codex `BaseChatModel` bridge.
- Use `scripts/check_ldr_access.py` from the project copy when a deterministic environment diagnostic is needed.
- Use `scripts/install_codex_skill.py --force` from the project copy to sync this skill into the active Codex skills directory.
- Use `scripts/new_research_packet.py` when a long research task needs a persistent context template.
- Use `scripts/prepare_harness_run.py` when a harness needs normalized parameters and a ready-to-send Codex prompt.
- Use `scripts/run_codex_bridge_exact.py` to start the Codex-only exact LDR report pipeline.
- Use `scripts/respond_to_codex_bridge.py` to inspect, classify, validate, and write bridge responses.
- Use `scripts/split_research_packet_for_subagents.py` when authorized sub-agents need bounded packet files.

## Compliance Boundaries

- Do not scrape Codex credentials.
- Do not call undocumented Codex inference endpoints.
- Do not build or recommend a fake OpenAI-compatible Codex endpoint.
- Do not send private local documents to external services unless the user explicitly requests that and the selected tool requires it.
- Treat any Codex bridge/provider as experimental and explicit, never as the default workflow.
