# Harness Integration

Use this reference when an external harness prepares or launches Codex/LDR research.

## Contract

`scripts/prepare_harness_run.py` is the stable harness entry point. It does not call Codex and does not call undocumented Codex APIs. It normalizes user intent into a JSON payload that a harness can pass to Codex through whatever supported Codex interface it controls.

Inputs:

- Natural-language prompt via `--prompt` or `--prompt-file`.
- Optional explicit overrides such as `--mode`, `--engine`, `--strategy`, `--iterations`, `--output-language`.
- Optional inline prompt directive: `[ldr-codex key=value ...]`.

Outputs:

- `parameters`: normalized request configuration.
- `ldr_environment`: safe LDR environment variables for search mode.
- `codex_prompt`: ready-to-send prompt for Codex.
- `recommended_tools`: tools to prefer in Codex-generation mode.
- `provider_backed_tools`: tools that require LDR-side generation.
- Optional sidecar files: `--env-output`, `--codex-prompt-output`, and `--packet-output`.
- Convenience sidecar directory: `--sidecar-dir DIR` writes `request.json`, `ldr.env`, `prompt.txt`, and `packet.md` unless explicit output paths override those names.

## Precedence

1. Explicit CLI arguments.
2. Inline prompt directives.
3. Natural-language inference.
4. Mode defaults.

The harness should log the final `parameters` object so the run is reproducible.

## Prompt Directives

Supported directive forms:

```text
[ldr-codex mode=report engine=arxiv iterations=3 language=zh-CN]
[harness mode=detailed engines=pubmed,semantic_scholar max_results=8]
```

Supported keys:

- `mode`: `quick`, `detailed`, `report`
- `engine`: one engine
- `engines`: comma-separated engine list
- `strategy`: LDR strategy vocabulary such as `source-based`
- `iterations`: 1-10
- `questions` or `questions_per_iteration`: 1-8
- `max_results`: 1-100
- `language` or `lang`: output language, for example `zh-CN` or `en-US`
- `format`: `markdown`, `json`, `bullets`, `brief`
- `audience`: intended reader
- `collection`: local collection/search engine identifier
- `subagents`: `auto`, `never`, `when-authorized`, `force`
- `exact_webui`: `true` or `false`
- `allow_ldr_generation`: `true` or `false`

## Harness Algorithm

1. Call `prepare_harness_run.py` with the user's prompt and any harness-level overrides.
2. Optionally set variables from `ldr_environment` before starting `ldr-mcp`.
3. Ensure Codex has access to the installed `local-deep-research-codex` skill.
4. Send `codex_prompt` to Codex.
5. If `parameters.create_research_packet` is true and the run is long, pass `--packet-output` so the helper creates a packet and includes its path in `codex_prompt`.
6. Store final `parameters`, diagnostics, and final report together for auditability.

## Generation Boundaries

- If `allow_ldr_generation` is false, Codex should use raw retrieval/discovery tools and generate the synthesis itself.
- If `exact_webui` is true, the harness must provide a configured LDR model provider because exact WebUI/API behavior is LDR-provider-backed.
- If `use_subagents` is `force`, the harness must ensure the Codex runtime actually supports subagents; otherwise downgrade to `when-authorized` and record the downgrade.

## Example

```bash
python codex-skills/local-deep-research-codex/scripts/prepare_harness_run.py \
  --prompt "[ldr-codex mode=report engines=arxiv,semantic_scholar iterations=4 language=zh-CN] 研究 AI 科研智能体的评估方法" \
  --output harness-request.json \
  --env-output ldr.env \
  --codex-prompt-output codex-prompt.txt \
  --packet-output ldr-codex-packet.md
```

For runners that prefer a single artifact directory:

```bash
python codex-skills/local-deep-research-codex/scripts/prepare_harness_run.py \
  --prompt "[ldr-codex mode=report engine=arxiv iterations=3 language=zh-CN] 研究多智能体科研工作流" \
  --sidecar-dir .ldr-codex/run-001
```

The harness can then send `codex_prompt` from `harness-request.json` to Codex and use `ldr_environment` when launching LDR MCP.
