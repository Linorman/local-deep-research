# Install And Use

This reference gives copy-pasteable setup commands for using Local Deep Research (LDR) with Codex as the generation layer.

## Components

- Codex: runs this skill and performs planning, synthesis, and report writing.
- This skill: stored in the repository at `codex-skills/local-deep-research-codex`, then installed into Codex's skills directory.
- LDR Python package: provides `ldr-mcp`, `ldr-web`, search engines, local collections, and optional WebUI/API generation.
- LDR MCP server: preferred interface for Codex-led retrieval; STDIO only and must run on the host.
- LDR WebUI: optional, useful for configuring settings, accounts, collections, and exact WebUI runs.
- Search backends: examples include Wikipedia, arXiv, PubMed, Semantic Scholar, GitHub, and SearXNG.
- LDR model provider: optional for Codex generation mode; required only for official WebUI/API generation tools.

## Install LDR From PyPI

Use this when you want a normal deployment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install "local-deep-research[mcp]"
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install "local-deep-research[mcp]"
```

Verify:

```bash
ldr-mcp
```

`ldr-mcp` uses STDIO and may appear idle. Stop it with `Ctrl+C`.

## Install LDR From This Source Repository

Use this when working from a checkout of the LDR repository.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[mcp]"
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[mcp]"
```

For development with the repository's PDM workflow:

```bash
pip install pdm
pdm install
```

## Optional Search Backend: SearXNG

SearXNG is useful for broad web search without a paid search API.

```bash
docker run -d -p 8080:8080 --name searxng searxng/searxng
```

Then configure LDR's SearXNG instance URL in WebUI settings or via environment variables appropriate for your deployment.

## Optional WebUI

Start the WebUI when you want to configure settings, create users, manage collections, or compare against exact LDR behavior.

```bash
ldr-web
```

Alternative:

```bash
python -m local_deep_research.web.app
```

Open `http://localhost:5000`.

Important: WebUI research requires an LDR model provider and model setting. Codex generation mode does not require LDR-side generation, but it does need LDR retrieval access through MCP or importable Python code.

## Install This Skill Into Codex

From the LDR repository root:

```bash
python codex-skills/local-deep-research-codex/scripts/install_codex_skill.py --force
```

Restart the Codex session after installing so the skill metadata is discovered.

## Configure Codex To Reach LDR

Preferred path: add an MCP server named `local-deep-research` with command `ldr-mcp` in the Codex environment's MCP configuration UI or file.

Minimum MCP server definition:

```json
{
  "mcpServers": {
    "local-deep-research": {
      "command": "ldr-mcp"
    }
  }
}
```

If your Codex environment does not expose MCP tools, keep the repository environment importable and let Codex use the bundled diagnostic and local Python entry points where possible.

## Diagnostics

From the repository root:

```bash
python codex-skills/local-deep-research-codex/scripts/check_ldr_access.py --repo . --pretty
```

Useful fields:

- `ok`: true when MCP import or no-LLM discovery appears reachable.
- `availability.mcp_entrypoint_available`: `ldr-mcp` is on PATH.
- `availability.no_llm_discovery_available`: LDR can list engines and strategies without generation.
- `package_import.error`: usually shows missing Python dependencies.

If `loguru` or another dependency is missing, activate the environment where LDR was installed or reinstall LDR with MCP extras.

## Research Packet Helper

For long research:

```bash
python codex-skills/local-deep-research-codex/scripts/new_research_packet.py --query "Your research question" --mode report --output ldr-codex-packet.md
```

The packet is working context for Codex. Do not commit it unless it is meant to be a deliverable.

## Harness Preparation

Use this when an external runner should prepare parameters before invoking Codex.

```bash
python codex-skills/local-deep-research-codex/scripts/prepare_harness_run.py \
  --prompt "[ldr-codex mode=report engine=arxiv iterations=3 language=zh-CN] 研究多智能体科研工作流" \
  --output harness-request.json
```

The script emits JSON with:

- `parameters`: normalized mode, engines, strategy, iterations, output language, subagent policy, and generation boundary flags.
- `ldr_environment`: environment variables a harness may set before starting `ldr-mcp`.
- `codex_prompt`: prompt text the harness can send to Codex.
- `recommended_tools`: LDR tools to prefer for Codex generation mode.
- `provider_backed_tools`: tools that require an LDR model provider unless explicitly allowed.
- `research_packet_path`: packet path when `--packet-output` is used.

Explicit CLI arguments override prompt directives:

```bash
python codex-skills/local-deep-research-codex/scripts/prepare_harness_run.py \
  --prompt "请用 PubMed 做详细中文综述" \
  --mode detailed \
  --engine pubmed \
  --iterations 2 \
  --questions-per-iteration 4
```

Write separate files for a simple harness:

```bash
python codex-skills/local-deep-research-codex/scripts/prepare_harness_run.py \
  --prompt "[ldr-codex mode=report engine=arxiv iterations=3 language=zh-CN] 研究多智能体科研工作流" \
  --output harness-request.json \
  --env-output ldr.env \
  --codex-prompt-output codex-prompt.txt \
  --packet-output ldr-codex-packet.md
```

Or let the helper create the standard sidecar files in one directory:

```bash
python codex-skills/local-deep-research-codex/scripts/prepare_harness_run.py \
  --prompt "[ldr-codex mode=report engine=arxiv iterations=3 language=zh-CN] 研究多智能体科研工作流" \
  --sidecar-dir .ldr-codex/run-001
```

This creates `request.json`, `ldr.env`, `prompt.txt`, and `packet.md`.

Supported prompt directive form:

```text
[ldr-codex mode=report engine=semantic_scholar strategy=source-based iterations=4 questions=4 max_results=10 language=zh-CN format=markdown subagents=when-authorized]
```

Use `exact_webui=true` only when the harness should run LDR WebUI/API generation with a configured LDR model provider.

## Example Prompts

Quick:

```text
Use local-deep-research-codex in WebUI-like quick mode. Use LDR raw search where available and let Codex write the answer with citations.
```

Detailed:

```text
Use local-deep-research-codex in WebUI-like detailed mode. Maintain a source ledger, iterate over gaps, and produce a structured Chinese analysis.
```

Full report:

```text
Use local-deep-research-codex in WebUI-like full report mode. Use Codex as the generator, LDR for retrieval, and include methodology, findings, limitations, and source list.
```

Exact WebUI comparison:

```text
Run an exact LDR WebUI/API-backed report and compare it with a Codex-generated WebUI-like report.
```

This last option requires a working LDR model provider because exact WebUI/API generation is LDR-provider-backed.

## Operating Modes

| Goal | Use | Requires LDR model provider |
| --- | --- | --- |
| Codex generation, LDR retrieval | MCP `search` and discovery; Codex synthesis | No |
| WebUI-like Codex report | Iterative raw retrieval plus Codex research packet | No |
| Exact WebUI output | WebUI/API `quick_summary`, `detailed_research`, or `generate_report` | Yes |
| Exact LDR pipeline with Codex generation | `scripts/run_codex_bridge_exact.py` plus bridge response loop | No LDR model provider; requires active Codex session |
| Local document Codex summary | Collection search engine retrieval plus Codex synthesis | No, if collection is exposed as raw search |
| LDR `analyze_documents` | LDR document summarization | Yes |

## Security And Compliance

- Do not expose `ldr-mcp` over the network; it is STDIO-only local tooling.
- Do not create a fake OpenAI-compatible Codex endpoint.
- Do not scrape Codex credentials or call undocumented Codex inference APIs.
- Treat Codex-generated synthesis and LDR-provider-generated output as different provenance.
- Do not send private local documents to external tools unless the user explicitly requests it.
