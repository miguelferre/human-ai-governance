# ADR-009: MCP server (use it from Claude or an IDE)

- **Status:** Accepted
- **Date:** 2026-07-08

## Context

The reviewer is a CLI. To use it you clone the repo, install it, write a dossier and run
`review`. That is fine for a bench, but it is friction for the person we most want to reach:
someone in governance, quality or compliance who lives inside an assistant (Claude) or an IDE
and wants to audit *their own* system without adopting a Python project. The Model Context
Protocol is the way to expose the tool to those clients. It also doubles as a distribution
surface (`uvx --from git+...`, the official MCP registry) that needs no PyPI release to work.

## Decision

A single module `mcp_server.py` and a second console script `interaction-review-mcp` (stdio),
built on the official `mcp` SDK (`FastMCP`). It is a **thin wrapper**: every tool reuses the
existing programmatic entry points (`approaches.REGISTRY`, `router.route`, `ingest.build_dossier`,
`report.*`, `regulatory`, `guidelines.loader`) and duplicates no CLI logic. The only refactor to
existing code was extracting `ingest.build_dossier` (operates on template *text*) out of
`ingest_templates` (reads files), because an MCP client has content, not file paths.

Six tools: `review_dossier` (the only LLM one, unless `approach='b0'`), `ingest_templates`,
`validate_dossier`, `regulatory_crosswalk`, `render_report`, `get_template`. Three resources
(`template://{kind}`, `guidelines://{corpus}`, `example://dossier`) and two prompts
(`audit_my_system`, `review_from_files`). Tools mirror the resources because client support for
resources is still uneven.

Key choices:

- **`mcp` is a core dependency, not an extra.** The target is the one-liner
  `uvx --from git+... interaction-review-mcp`; an extra would force the clumsier
  `uvx --from "interaction-review[mcp] @ git+..."`. The transitive cost (starlette/uvicorn) is
  acceptable. Contrast with `inspect-ai`, which *is* an extra (ADR-010): product deps in core,
  harness deps in extras.
- **Stateless by design.** No tool depends on a previous call: `review_dossier` returns the report
  **and** the structured findings in one shot, and `render_report` re-renders already-generated
  findings (md->html, add crosswalk) for free. This is not only cleaner; the MCP spec dated
  2026-07-28 makes the protocol stateless and deprecates Sampling/Roots/Logging, so a stateless
  server migrates to SDK v2 (`FastMCP` -> `MCPServer`) mechanically. Hence the pin `mcp>=1.28,<2`.
- **Credentials via the client's `env` block.** The server inherits `ANTHROPIC_API_KEY` (or
  `LLM_BACKEND=ollama` for a fully local run) from the process environment. Nothing loads a `.env`
  (the project never did). `LLMNotConfigured` propagates as an actionable message naming both fixes.
- **No MCP Sampling.** It would be the way to run without the client shipping a key, but the
  2026-07-28 spec deprecates it. The door is left open in the code for a future
  bring-your-own-endpoint mode, not for classic Sampling.
- **LLM tools are async and run the blocking pipeline in a worker thread**
  (`anyio.to_thread.run_sync`) so the server keeps answering pings during a p3 review (minutes).

## Consequences

- Anyone on Claude Desktop, Claude Code or an MCP-capable IDE can audit their system with no clone
  and no Python project, inline dossier or file path. The inline dossier is typed as the Pydantic
  `Dossier`, so the SDK advertises the real schema and validates it (self-documenting, free
  `validate_dossier`).
- **Startup stays light:** `llm.py` already defers the `anthropic` import, and the server does not
  import `pypdf` at module load. Verified by the offline tests, which run the full protocol
  in-memory (`create_connected_server_and_client_session`) with the LLM monkeypatched.
- **Distribution artifacts ship in the repo** (`server.json` for the official registry, README
  config blocks). Publishing to PyPI / submitting to the registry is a manual step, out of scope.
- **Risk:** a client's default tool timeout can be shorter than a p3 review. Mitigated by the async
  design and documented in the README (`MCP_TIMEOUT`, and `b1`/`b0` as faster/free alternatives).
- **Follow-up:** migrate to SDK v2 when it stabilizes; the stateless design keeps this mechanical.
