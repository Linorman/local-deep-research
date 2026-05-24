# Codex-Only Bridge Exact Workflow

Use this reference when the user wants `codex_bridge_exact`: LDR runs its normal research/report pipeline and writes every LLM prompt to a local bridge queue; Codex reads those requests and writes responses.

## What This Mode Guarantees

- LDR owns the research pipeline: `generate_report`, strategy setup, search iteration, source handling, citation synthesis, and report generation.
- Codex owns every model response through the explicit file bridge.
- No LDR provider API key is required for generation.
- The run is auditable through request JSON files, response JSON files, `request_manifest.jsonl`, `status.json`, and `ldr_process.log`.

This mode is closer to WebUI/API behavior than `codex_like` because LDR still controls its internal prompt sequence. It is not a hidden WebUI session: WebUI queue records, Socket.IO timing, browser state, and DB history are not reproduced unless the user separately runs the WebUI path.

## Start A Run

From the repository copy of the skill:

```bash
/opt/miniforge3/envs/ldr-codex/bin/python \
  codex-skills/local-deep-research-codex/scripts/run_codex_bridge_exact.py \
  --query-file prompt.txt \
  --run-dir ./ldr_codex_runs/protein_pocket \
  --model gpt-5.5 \
  --search-tool auto \
  --iterations 5 \
  --questions-per-iteration 4 \
  --timeout-seconds 1200 \
  --current-date 2026-05-20 \
  --background
```

The runner writes:

- `<run_dir>/codex_bridge/requests/*.json`
- `<run_dir>/codex_bridge/responses/*.json`
- `<run_dir>/run_config.json`
- `<run_dir>/settings_overrides.json`
- `<run_dir>/settings_snapshot.json`
- `<run_dir>/status.json`
- `<run_dir>/progress.jsonl`
- `<run_dir>/ldr_process.log`
- `<run_dir>/final_report.md`

The required settings are passed through `create_settings_snapshot(overrides=...)` and include:

```text
llm.provider = codex_bridge
llm.model = gpt-5.5
llm.codex_bridge.bridge_dir = <run_dir>/codex_bridge
llm.codex_bridge.timeout_seconds = 1200
search.tool = auto
search.iterations = 5
search.questions_per_iteration = 4
api.allow_file_output = true
```

## Response Loop

List pending requests:

```bash
python codex-skills/local-deep-research-codex/scripts/respond_to_codex_bridge.py \
  --bridge-dir ./ldr_codex_runs/protein_pocket/codex_bridge \
  --list
```

Print the next prompt:

```bash
python codex-skills/local-deep-research-codex/scripts/respond_to_codex_bridge.py \
  --bridge-dir ./ldr_codex_runs/protein_pocket/codex_bridge \
  --request-id <id> \
  --print-prompt
```

Answer with the active Codex model, then write the response:

```bash
python codex-skills/local-deep-research-codex/scripts/respond_to_codex_bridge.py \
  --bridge-dir ./ldr_codex_runs/protein_pocket/codex_bridge \
  --request-id <id> \
  --response-stdin \
  --validate-response \
  --manifest-output ./ldr_codex_runs/protein_pocket/request_manifest.jsonl
```

Repeat until:

```bash
cat ./ldr_codex_runs/protein_pocket/status.json
```

shows `completed` or `failed`.

## Internal Request Contracts

The responder helper classifies common LDR bridge requests and prints a response contract. Follow it exactly.

| Kind | Expected response |
| --- | --- |
| `historical_query_classifier` | exactly `yes` or `no` |
| `pubmed_query_transform` | one PubMed query string only |
| `search_question_generation` | search questions only, normally `Q:` lines |
| `report_structure` | only the requested outline or structure markers |
| `citation_synthesis` | source-grounded synthesis with citation markers |
| `fact_check` | factual consistency analysis grounded in supplied sources |
| `relevance_filter` | only requested indices or labels |

Most quality failures in this mode come from violating these small internal contracts. For example, adding prose around a PubMed query can poison downstream retrieval, and answering a classifier with a sentence instead of `yes`/`no` can route LDR incorrectly.

## Engine Selection

For broad web tasks, `search.tool=auto` can match the WebUI default. For scholarly biomedical work, explicit engines are often more reliable:

```text
semantic_scholar
pubmed
arxiv
wikipedia
```

Use `auto` when the user requires WebUI-like defaults or the local LDR auto engine has been smoke-tested. If search quality looks unrelated, inspect recent bridge requests before blaming retrieval; the query-transform response may be malformed.

## Failure Triage

If the run hangs:

1. Check `status.json` for the phase.
2. Check pending files under `<run_dir>/codex_bridge/requests`.
3. Check whether a matching response file exists under `<run_dir>/codex_bridge/responses`.
4. Check `ldr_process.log` for Python exceptions.
5. If the error is `api.allow_file_output`, confirm `settings_overrides.json` contains `"api.allow_file_output": true`.

If the final report is low quality:

1. Audit `request_manifest.jsonl` for request kinds.
2. Re-open the prompt for malformed responses.
3. Check whether source URLs in the report match the research topic.
4. Prefer an explicit scholarly search engine for the next run.
