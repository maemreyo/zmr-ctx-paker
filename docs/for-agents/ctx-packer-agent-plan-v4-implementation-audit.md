# ctx-packer Agent Plan v4 — Implementation Audit Report

_Date:_ 2026-03-25  
_Scope:_ Audit of `docs/for-agents/ctx-packer-agent-plan-v4.md` against the current repository state.

## Executive Summary

**Verdict: the plan is not fully implemented yet.**

The repository already contains a substantial portion of the planned work, especially around the MCP server. However, there are still several gaps between the implementation and the literal plan/spec:

- **Phase 1:** mostly implemented, but not fully aligned.
- **Phase 2:** partially implemented.
- **Phase 3:** core MCP functionality is largely present, but Week 11 documentation deliverables and some spec details are still incomplete.

### Phase Summary

| Phase | Status | Summary |
|---|---|---|
| Phase 1 — CLI & Agent Prompts | Partial | `search`, `--limit`, `--domain-filter` exist; global `--agent-mode` behavior and agent templates are not fully aligned with the plan. |
| Phase 2 — Agent-Native Formats | Partial | JSON/Markdown pack output exists, plus secret-scan cache; missing `secretlint` subprocess integration and full parity across formats/responses. |
| Phase 3 — MCP Server | Partial | MCP server, 4 tools, security guardrails, config, tests, and benchmarks exist; rate limiting differs from plan and documentation deliverables are incomplete. |

---

## 1) Detailed Checklist — Literal Plan Audit

## Phase 1 — Quick Wins: CLI & Agent Prompts

Plan source: `docs/for-agents/ctx-packer-agent-plan-v4.md:716-734`

| # | Plan item | Status | Evidence | Notes |
|---|---|---|---|---|
| 1.1 | Implement `ctx-packer search "<query>"` | Pass | `src/context_packer/cli/cli.py:189-291`, `src/context_packer/workflow/query.py:151-215` | Implemented as a first-class CLI command. |
| 1.2 | Add global `--agent-mode` flag (all commands) | Partial | `src/context_packer/cli/cli.py:88-107`, `src/context_packer/cli/cli.py:435-455`, `src/context_packer/cli/cli.py:560-597`, `src/context_packer/cli/cli.py:655-685` | Global flag exists, but `query`, `pack`, and `status` still emit human-readable output instead of fully clean NDJSON behavior. |
| 1.3 | Add `--limit` flag to `search` | Pass | `src/context_packer/cli/cli.py:201-208`, `src/context_packer/workflow/query.py:168-169` | Matches default and bounds from the plan. |
| 1.4 | Add `domain_filter` option to `search` | Pass | `src/context_packer/cli/cli.py:209-213`, `src/context_packer/workflow/query.py:195-210` | Implemented as `--domain-filter`. |
| 1.5 | Update `SKILL.md` template to teach `search` not `pack` | Partial | `src/context_packer/templates/claude/SKILL.md.tpl:16-19`, `src/context_packer/scripts/lib/commands.sh:12-18,27-34` | Template exists, but still points to `CTX_CMD_QUERY`, and canonical command export still defines `query` instead of `search`. |
| 1.6 | Update `.cursorrules` template | Fail | `src/context_packer/templates/cursor/ctx-packer.mdc.tpl:12-17,35`, `src/context_packer/scripts/lib/commands.sh:27-34` | No `.cursorrules` template was found; current Cursor rule template exists in `.mdc` form but still relies on `CTX_CMD_QUERY`. |
| 1.7 | Update `--help` output for agent-mode | Pass | `src/context_packer/cli/cli.py:98-101` | Help text is present. |
| 1.D | Deliverable: `ctx-packer search "query" --agent-mode` returns clean NDJSON | Partial | `src/context_packer/cli/cli.py:261-281`, `tests/unit/test_cli.py:427-446` | Search NDJSON exists, but tests only verify top-level `--agent-mode search ...`; the exact invocation form shown in the plan is not validated. |
| 1.A | Acceptance test for `search ... --agent-mode --limit 3` | Partial | `tests/unit/test_cli.py:427-446` | Behavior is covered in spirit, but not in the exact command shape from the plan. |

### Phase 1 verdict

**Status: Partial**  
Core search capabilities are present, but the agent UX/documentation layer is not fully converted from `query` to `search`, and `--agent-mode` is not consistently implemented across commands.

---

## Phase 2 — Agent-Native Formats

Plan source: `docs/for-agents/ctx-packer-agent-plan-v4.md:742-763`

| # | Plan item | Status | Evidence | Notes |
|---|---|---|---|---|
| 2.1 | Implement `--format json` for `pack` | Pass | `src/context_packer/cli/cli.py:491-496,534-538`, `src/context_packer/workflow/query.py:434-465`, `src/context_packer/output/json_formatter.py:9-15` | Implemented and tested. |
| 2.2 | Implement `--format md` for `pack` | Pass | `src/context_packer/cli/cli.py:491-496,534-538`, `src/context_packer/workflow/query.py:434-469`, `src/context_packer/output/md_formatter.py:29-76` | Implemented and includes data-boundary comments. |
| 2.3 | Implement CLI `--secrets-scan` | Partial | `src/context_packer/cli/cli.py:394-398`, `src/context_packer/cli/cli.py:515-518`, `src/context_packer/workflow/query.py:444-457` | Flag exists and works for JSON/MD payload building, but not for XML/ZIP pack paths. |
| 2.4 | Build secret scan cache (`secret_scan_cache.json`) | Pass | `src/context_packer/secret_scanner.py:29-33,42-65,78-81` | Implemented exactly with `mtime` + `inode` keyed persistence. |
| 2.5 | Integrate `secretlint` as Python subprocess with regex fallback | Fail | `src/context_packer/secret_scanner.py:14-20,58-66` | Current implementation is regex-only; no `secretlint` subprocess integration was found in repo code. |
| 2.6 | Add `index_health` object in all responses | Partial | `src/context_packer/workflow/query.py:390-401`, `src/context_packer/output/json_formatter.py:9-15`, `src/context_packer/output/md_formatter.py:29-76`, `src/context_packer/packer/xml_packer.py:114-138`, `src/context_packer/packer/zip_packer.py:153-167` | Present in JSON metadata and MCP/search responses, but not rendered in Markdown/XML/ZIP output. |
| 2.D | Deliverable: `ctx-packer pack --format json --secrets-scan` produces clean, parseable JSON | Partial | `src/context_packer/workflow/query.py:462-472`, `src/context_packer/cli/cli.py:581-597` | JSON payload is produced, but written to a file rather than emitted as parseable stdout as implied by the acceptance test. |
| 2.A | Acceptance test: pipe `ctx-packer pack --query "auth" --format json` into `python3 -c` | Fail | `src/context_packer/cli/cli.py:588-597` | Current CLI prints success/status and saves the JSON to disk; it does not stream the JSON payload to stdout in that form. |

### Phase 2 verdict

**Status: Partial**  
The new JSON/Markdown pack formats are real, and the cache-backed secret scanner exists. The biggest blockers are missing `secretlint` integration, incomplete `--secrets-scan` parity across formats, and `index_health` not being consistently surfaced across outputs.

---

## Phase 3 — MCP Server

Plan source: `docs/for-agents/ctx-packer-agent-plan-v4.md:771-819`

### Week 7–8: Core MCP Infrastructure

| # | Plan item | Status | Evidence | Notes |
|---|---|---|---|---|
| 3.1 | Create `context_packer/mcp_server.py` | Pass | `src/context_packer/mcp_server.py:1-9` | File exists and forwards to the MCP server runtime. |
| 3.2 | Implement `ctx-packer mcp --workspace PATH` entry point | Pass | `src/context_packer/cli/cli.py:307-347` | Implemented. |
| 3.3 | Implement workspace-binding / scope isolation | Pass | `src/context_packer/mcp/server.py:13-30`, `src/context_packer/mcp/tools.py:25-35`, `src/context_packer/mcp/config.py:100-111` | Implemented. |
| 3.4 | Implement Layer 3 path traversal protection | Pass | `src/context_packer/mcp/security/path_guard.py:6-30`, `src/context_packer/mcp/tools.py:158-180` | Implemented and exercised by tests. |
| 3.5 | Generate `SESSION_TOKEN` at startup | Pass | `src/context_packer/mcp/security/rade_delimiter.py:6-17`, `src/context_packer/mcp/tools.py:31-33` | Implemented through `RADESession`. |
| 3.6 | Implement Layer 1 read-only enforcement | Pass | `src/context_packer/mcp/tools.py:37-82` | Only 4 read-only tools are exposed; unknown tools are rejected. |

### Week 9: Tool Implementation

| # | Plan item | Status | Evidence | Notes |
|---|---|---|---|---|
| 3.7 | Implement `search_codebase` tool | Pass | `src/context_packer/mcp/tools.py:113-140` | Implemented. |
| 3.8 | Implement `get_file_context` tool | Pass | `src/context_packer/mcp/tools.py:142-221` | Implemented. |
| 3.9 | Implement `get_domain_map` tool | Pass | `src/context_packer/mcp/tools.py:223-279` | Implemented with cache support. |
| 3.10 | Implement `get_index_status` tool | Pass | `src/context_packer/mcp/tools.py:280-299` | Implemented. |
| 3.11 | Implement `index_health` computation for all tools | Pass | `src/context_packer/mcp/tools.py:126-136,156-168,274-277,289-299` | Implemented across MCP responses. |

### Week 10: Security Layer

| # | Plan item | Status | Evidence | Notes |
|---|---|---|---|---|
| 3.12 | Integrate secret scan cache into `get_file_context` | Pass | `src/context_packer/mcp/tools.py:183-195`, `src/context_packer/secret_scanner.py:29-81` | Always-on in MCP path. |
| 3.13 | RADE delimiter wrapping in all file reads | Pass | `src/context_packer/mcp/security/rade_delimiter.py:6-22`, `src/context_packer/mcp/tools.py:210-220` | Implemented. |
| 3.14 | Rate limiting middleware — token bucket, configurable | Partial | `src/context_packer/mcp/security/rate_limiter.py:7-29`, `src/context_packer/mcp/config.py:9-14,59-80` | Configurable limits exist, but implementation is a sliding-window counter, not a token bucket. |
| 3.15 | Security audit of all four tools | Partial | `tests/unit/test_mcp_tools.py:9-53,177-189`, `tests/property/test_mcp_security_properties.py:29-79` | Strong security test coverage exists, but no dedicated audit artifact/report was found. |

### Week 11: Integration & Config

| # | Plan item | Status | Evidence | Notes |
|---|---|---|---|---|
| 3.16 | `.context-pack/mcp_config.json` schema | Pass | `src/context_packer/mcp/config.py:21-111`, `src/context_packer/templates/mcp/mcp_config.json.tpl:1-10` | Implemented. |
| 3.17 | Claude Desktop integration guide | Fail | Repo-wide search found no dedicated guide beyond plan/proposal docs | No concrete guide file or configuration guide was found. |
| 3.18 | Cursor integration guide | Fail | Repo-wide search found no dedicated guide beyond plan/proposal docs | No `.cursor/mcp.json` guide was found. |
| 3.19 | Windsurf integration guide | Fail | Repo-wide search found no dedicated guide beyond plan/proposal docs | No dedicated MCP guide for Windsurf was found. |
| 3.20 | `ctx-packer-init` emits MCP config | Pass | `src/context_packer/scripts/init.sh:72-76`, `src/context_packer/scripts/lib/mcp.sh:4-15` | Implemented. |

### Week 12: Testing & Hardening

| # | Plan item | Status | Evidence | Notes |
|---|---|---|---|---|
| 3.21 | Integration tests for all 4 tools | Pass | `tests/integration/test_mcp_integration.py:93-126` | Implemented. |
| 3.22 | Security tests: path traversal, RADE injection | Pass | `tests/property/test_mcp_security_properties.py:29-79` | Implemented. |
| 3.23 | Performance benchmark: `search_codebase` p50/p99 latency | Pass | `tests/integration/test_mcp_benchmarks.py:78-102` | Benchmark exists and asserts `p99 < 200ms`. |
| 3.24 | Secret scan cache benchmark / hit rate | Pass | `tests/integration/test_mcp_benchmarks.py:105-191` | Implemented. |
| 3.25 | Documentation: full MCP server reference | Fail | Repo-wide search found no dedicated reference document beyond the plan | Missing. |
| 3.D | Deliverable: running MCP server usable via `mcpServers` config | Pass | `src/context_packer/cli/cli.py:307-347`, `src/context_packer/mcp/server.py:13-48` | Core runtime is present. |

### Phase 3 verdict

**Status: Partial**  
The MCP implementation is the strongest part of the work and is close to feature-complete. The main gaps are:

- literal mismatch on rate-limiter design vs plan,
- missing Week 11 integration guides,
- missing Week 12 full MCP reference documentation.

---

## 2) Important Spec Deviations / Ambiguities

### 2.1 `session_token` contradiction in the plan

The plan contains an internal contradiction:

- Section 6.1 says all responses include a `session_token` field.
- Section 6.4 says the session token is never exposed to the client.

The implementation follows the **safer** interpretation:

- the token stays private in `RADESession`, and
- responses expose content markers rather than the token field itself.

Evidence:
- `docs/for-agents/ctx-packer-agent-plan-v4.md:249`
- `docs/for-agents/ctx-packer-agent-plan-v4.md:629-633`
- `src/context_packer/mcp/security/rade_delimiter.py:6-22`
- `src/context_packer/mcp/tools.py:210-220`

This is a reasonable implementation choice, but it is **not a literal 1:1 match** with the earlier wording in the plan.

---

## 3) What Is Missing To Reach 100%

## Priority 0 — Required to claim “fully implemented”

1. **Complete global `--agent-mode` behavior across commands**
   - Ensure `query`, `pack`, `status`, and other commands suppress human-readable panels/messages in agent mode.
   - Emit clean NDJSON/stdout behavior consistently.

2. **Update all agent templates to prefer `search`**
   - Replace `CTX_CMD_QUERY` usage where the plan expects semantic file discovery through `search`.
   - Update Cursor-equivalent template behavior as well.

3. **Add `secretlint` subprocess integration with regex fallback**
   - Current scanner is regex-only.
   - This is the clearest missing Phase 2 item.

4. **Apply `--secrets-scan` consistently across all pack formats**
   - JSON/MD currently use the scanner.
   - XML/ZIP still bypass that path.

5. **Surface `index_health` consistently in all outputs/responses promised by the plan**
   - Add it to Markdown/XML/ZIP rendered outputs if the plan is to be followed literally.

6. **Add missing MCP integration documentation**
   - Claude Desktop guide
   - Cursor guide
   - Windsurf guide
   - Full MCP server reference

## Priority 1 — Needed to match the plan more literally

7. **Decide whether Phase 2 JSON should be file output, stdout output, or both**
   - Current acceptance test wording implies parseable stdout.
   - Current implementation writes to a file.

8. **Align rate limiting with the planned “token bucket” design**
   - Current implementation is workable, but different from the spec.
   - If the goal is plan fidelity, this should be rewritten or the plan should be updated.

9. **Resolve the `session_token` wording in the plan**
   - Keep current secure behavior, but update the plan/documentation to remove the contradiction.

## Priority 2 — Nice-to-have hardening / polish

10. **Add a dedicated security audit artifact**
   - There are already strong tests.
   - A separate audit note/report would make Week 10 easier to mark complete.

11. **Add command-shape tests for the exact CLI invocations shown in the plan**
   - Especially `ctx-packer search "..." --agent-mode --limit 3`
   - And the Phase 2 stdout-based JSON acceptance path if that behavior is intended.

---

## 4) Recommended Next Steps

If the objective is to close the audit quickly with minimal scope, the fastest path is:

1. Fix `--agent-mode` consistency.
2. Migrate templates from `query` to `search` where intended.
3. Implement `secretlint` integration with fallback.
4. Extend `secrets-scan` and `index_health` to all pack outputs.
5. Add the missing MCP documentation set.
6. Either:
   - change implementation to satisfy the exact acceptance tests, or
   - update the plan so the acceptance tests match the actual product behavior.

---

## Final Conclusion

**The plan has been implemented substantially, but not completely.**

A fair characterization of the current state is:

- **Phase 1:** mostly implemented, not complete.
- **Phase 2:** materially incomplete.
- **Phase 3:** functionally strong, but still not fully complete against the literal plan.

If you want to claim “plan v4 is fully implemented”, the missing items above should be closed first, or the plan/spec should be revised to match the implementation that now exists.
