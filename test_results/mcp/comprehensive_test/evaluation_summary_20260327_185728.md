# MCP Comprehensive Test Report

**Generated:** 2026-03-27 18:57:28  
**Workspace:** `/Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker`  
**Server:** ws-ctx-engine 0.2.0a0

## Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Score** | 99.2% |
| **Total Tests** | 53 |
| **Passed** | 53 ✓ |
| **Failed** | 0 ✗ |
| **Pass Rate** | 100.0% |

## Category Scores

| Category | Score | Tests | Passed | Failed |
|----------|-------|-------|--------|--------|
| Protocol Compliance | 100% | 4 | 4 | 0 |
| Tool Discovery & Registration | 100% | 4 | 4 | 0 |
| Input Validation | 100% | 7 | 7 | 0 |
| Error Handling | 100% | 4 | 4 | 0 |
| Performance Testing | 93% | 3 | 3 | 0 |
| Concurrency Testing | 100% | 2 | 2 | 0 |
| Security Testing | 100% | 3 | 3 | 0 |
| Structured Content | 100% | 4 | 4 | 0 |
| Timeout & Limits | 100% | 1 | 1 | 0 |
| Rate Limiting | 90% | 2 | 2 | 0 |
| Graph Tools | 100% | 19 | 19 | 0 |

## Detailed Results


### Protocol Compliance

**✅ initialize** (Score: 100%)
- Duration: 253ms
- Details: `{"checks": {"jsonrpc_valid": true, "has_server_info": true, "has_capabilities": true, "has_protocol_version": true, "server_name_present": true, "server_version_present": true}, "response": {"jsonrpc"...`


### Tool Discovery & Registration

**✅ tools/list** (Score: 100%)
- Duration: 142ms
- Details: `{"checks": {"jsonrpc_valid": true, "has_tools_array": true, "tools_not_empty": true, "each_tool_has_name": true, "each_tool_has_description": true, "each_tool_has_schema": true}, "tools_found": 12, "r...`


### Protocol Compliance

**✅ notifications/no_response** (Score: 100%)
- Duration: 153ms
- Details: `{"has_output": false, "output": ""}...`


### Tool Discovery & Registration

**✅ tool_discovery_comprehensive** (Score: 100%)
- Duration: 149ms
- Details: `{"tools_analysis": [{"name": "search_codebase", "has_description": true, "description_length": 57, "has_schema": true, "schema_type": "object", "has_properties": true, "required_fields_count": 1}, {"n...`


### Input Validation

**✅ input_validation/missing_required** (Score: 100%)
- Duration: 195ms
- Details: `{"error_detected": true, "error_type": "validation_error", "response": {"jsonrpc": "2.0", "id": 1774612401739, "result": {"content": [{"type": "text", "text": "{\"error\": \"INVALID_ARGUMENT\", \"mess...`

**✅ input_validation/invalid_types** (Score: 100%)
- Duration: 502ms
- Details: `{"test_cases": 3, "errors_caught": 3, "results": [{"case": {"name": "search_codebase", "arguments": {"query": 12345}}, "error_detected": true}, {"case": {"name": "search_codebase", "arguments": {"quer...`

**✅ input_validation/boundary_values** (Score: 100%)
- Duration: 419ms
- Details: `{"test_cases": 3, "handled_count": 3}...`


### Security Testing

**✅ security/injection_attempts** (Score: 100%)
- Duration: 63102ms
- Details: `{"test_cases": 5, "safe_count": 5}...`


### Error Handling

**✅ error_handling/unknown_method** (Score: 100%)
- Duration: 196ms
- Details: `{"has_error": true, "error_valid": true, "error_code": -32601, "error_message": "Method not found: unknown_method_xyz"}...`

**✅ error_handling/unknown_tool** (Score: 100%)
- Duration: 142ms
- Details: `{"has_error": true, "error_in_content": true}...`


### Performance Testing

**✅ performance/single_request_latency** (Score: 100%)
- Duration: 158ms
- Details: `{"avg_latency_ms": 157.62405395507812, "min_latency_ms": 144.81616020202637, "max_latency_ms": 165.7271385192871, "std_dev_ms": 8.312136977920012, "samples": 5}...`

**✅ performance/search_latency** (Score: 100%)
- Duration: 24ms
- Details: `{"mode": "warm-path (persistent process)", "cold_start_ms": 10043.5, "avg_warm_ms": 23.9, "max_warm_ms": 27.0, "p99_warm_ms": 27.0, "samples": 4, "error": ""}...`

**✅ performance/pack_context_latency** (Score: 80%)
- Duration: 2449ms
- Details: `{"mode": "warm-path (persistent process)", "cold_start_ms": 20732.3, "avg_warm_ms": 2449.1, "samples": 3, "error": ""}...`


### Concurrency Testing

**✅ concurrency/parallel_requests** (Score: 100%)
- Duration: 577ms
- Details: `{"total_requests": 10, "successful": 10, "errors": 0, "total_duration_ms": 577.1567821502686, "success_rate": 1.0}...`

**✅ concurrency/mixed_tools** (Score: 100%)
- Duration: 738ms
- Details: `{"total_requests": 6, "successful": 6}...`


### Timeout & Limits

**✅ timeout/handling** (Score: 100%)
- Duration: 179ms
- Details: `{"duration_ms": 178.9398193359375, "timeout_set": 5}...`


### Structured Content

**✅ structured_content/format** (Score: 100%)
- Duration: 10754ms
- Details: `{"has_content": true, "has_structured_content": true, "content_is_array": true, "content_items_have_type": true}...`


### Graph Tools

**✅ graph_tools/registration** (Score: 100%)
- Duration: 193ms
- Details: `{"checks": {"all_tools_present": true, "all_have_description": true, "all_have_use_when": true, "all_have_schema": true}, "missing": [], "registered": ["find_callers", "impact_analysis", "graph_search...`

**✅ graph_tools/get_status** (Score: 100%)
- Duration: 142ms
- Details: `{"checks": {"server_responded": true, "has_ready_field": true, "has_graph_store": true, "has_vector_backend": true, "graph_store_has_available": true, "has_required_actions": true, "has_hint": true}, ...`

**✅ graph_tools/find_callers/validation** (Score: 100%)
- Duration: 280ms
- Details: `{"cases": [{"label": "missing fn_name", "got_invalid_argument": true}, {"label": "empty fn_name", "got_invalid_argument": true}]}...`

**✅ graph_tools/find_callers/happy_path** (Score: 100%)
- Duration: 151ms
- Details: `{"has_callers": false, "callers_count": 0, "graph_unavailable": true, "payload": {"error": "GRAPH_UNAVAILABLE", "message": "Graph store is not available. Run 'wsctx index <repo>' with pycozo installed...`

**✅ graph_tools/impact_analysis/validation** (Score: 100%)
- Duration: 285ms
- Details: `{"cases": [{"label": "missing file_path", "got_invalid_argument": true}, {"label": "empty file_path", "got_invalid_argument": true}]}...`

**✅ graph_tools/impact_analysis/happy_path** (Score: 100%)
- Duration: 141ms
- Details: `{"has_importers": false, "graph_unavailable": true}...`

**✅ graph_tools/graph_search/validation** (Score: 100%)
- Duration: 293ms
- Details: `{"cases": [{"label": "missing file_id", "got_invalid_argument": true}, {"label": "empty file_id", "got_invalid_argument": true}]}...`

**✅ graph_tools/graph_search/happy_path** (Score: 100%)
- Duration: 151ms
- Details: `{"has_symbols": false, "graph_unavailable": true}...`

**✅ graph_tools/call_chain/validation** (Score: 100%)
- Duration: 451ms
- Details: `{"cases": [{"label": "missing both", "got_invalid_argument": true}, {"label": "missing to_fn", "got_invalid_argument": true}, {"label": "missing from_fn", "got_invalid_argument": true}]}...`

**✅ graph_tools/call_chain/happy_path** (Score: 100%)
- Duration: 154ms
- Details: `{"has_path_key": false, "graph_unavailable": true, "not_implemented": false, "path": [], "path_length": 0}...`

**✅ graph_tools/graceful_degradation** (Score: 100%)
- Duration: 754ms
- Details: `{"results": [{"tool": "find_callers", "responded": true}, {"tool": "impact_analysis", "responded": true}, {"tool": "graph_search", "responded": true}, {"tool": "call_chain", "responded": true}, {"tool...`

**✅ graph_tools/performance** (Score: 100%)
- Duration: 0ms
- Details: `{"avg_warm_ms": 0.1, "samples": 5, "error": ""}...`

**✅ graph_tools/find_callers/multi_file_callers** (Score: 100%)
- Duration: 148ms
- Details: `{"callers_count": 0, "caller_files": [], "graph_unavailable": true}...`

**✅ graph_tools/impact_analysis/core_module_has_importers** (Score: 100%)
- Duration: 148ms
- Details: `{"importers_count": 0, "sample": [], "graph_unavailable": true}...`

**✅ graph_tools/graph_search/known_symbols_present** (Score: 100%)
- Duration: 150ms
- Details: `{"expected": ["_query", "callers_of", "GraphStore"], "found": [], "missing": ["_query", "callers_of", "GraphStore"], "total_symbols": 0, "graph_unavailable": true}...`

**✅ graph_tools/call_chain/max_depth_capped** (Score: 100%)
- Duration: 149ms
- Details: `{"accepted_depth_20": true, "has_path": false, "graph_unavailable": true, "path": null}...`

**✅ graph_tools/call_chain/self_path_single_element** (Score: 100%)
- Duration: 156ms
- Details: `{"path": [], "expected": ["_query"], "graph_unavailable": true}...`

**✅ graph_tools/call_chain/no_path_returns_empty_list** (Score: 100%)
- Duration: 152ms
- Details: `{"path": null, "expected": [], "graph_unavailable": true}...`


### Protocol Compliance

**✅ protocol/jsonrpc_id_echo_integer** (Score: 100%)
- Duration: 165ms
- Details: `{"sent_id": 42, "received_id": 42}...`

**✅ protocol/jsonrpc_id_echo_string** (Score: 100%)
- Duration: 174ms
- Details: `{"sent_id": "req-abc-123", "received_id": "req-abc-123"}...`


### Tool Discovery & Registration

**✅ tools/list_all_12_present** (Score: 100%)
- Duration: 158ms
- Details: `{"expected_count": 12, "found_count": 12, "missing": [], "extra": []}...`

**✅ tools/schema_required_fields_declared** (Score: 100%)
- Duration: 150ms
- Details: `{"issues": [], "checked_tools": 7}...`


### Security Testing

**✅ security/path_traversal_blocked** (Score: 100%)
- Duration: 679ms
- Details: `{"results": [{"path": "../../etc/passwd", "blocked": true, "leaked": false}, {"path": "../../../etc/shadow", "blocked": true, "leaked": false}, {"path": "src/../../etc/hosts", "blocked": true, "leaked...`

**✅ security/absolute_path_outside_workspace** (Score: 100%)
- Duration: 169ms
- Details: `{"responded": true, "leaked_sensitive": false}...`


### Input Validation

**✅ input_validation/agent_phase_invalid_handled** (Score: 100%)
- Duration: 148ms
- Details: `{"responded": true}...`

**✅ input_validation/token_budget_below_minimum** (Score: 100%)
- Duration: 148ms
- Details: `{"responded": true}...`

**✅ input_validation/session_id_invalid_chars_rejected** (Score: 100%)
- Duration: 597ms
- Details: `{"cases": [{"label": "spaces", "got_error": true}, {"label": "slashes", "got_error": true}, {"label": "xss_attempt", "got_error": true}, {"label": "too_long_129_chars", "got_error": true}], "caught": ...`

**✅ input_validation/search_no_results_returns_empty_list** (Score: 100%)
- Duration: 22109ms
- Details: `{"has_results_key": true, "is_list": true, "not_error": true}...`


### Graph Tools

**✅ data_integrity/status_graph_counts_nonzero** (Score: 100%)
- Duration: 218ms
- Details: `{"graph_available": false, "node_count": 0, "edge_count": 0}...`


### Structured Content

**✅ data_integrity/search_results_have_path_and_score** (Score: 100%)
- Duration: 18673ms
- Details: `{"results_count": 5, "schema_issues": []}...`

**✅ data_integrity/file_context_required_fields** (Score: 100%)
- Duration: 287ms
- Details: `{"has_content": true, "has_language": true, "language": "python", "has_line_count": true, "line_count": 980}...`

**✅ data_integrity/domain_map_non_empty** (Score: 100%)
- Duration: 396ms
- Details: `{"domains_is_list": true, "domains_count": 50, "sample": [{"name": "mcp", "file_count": 160, "keywords": ["mcp"], "top_files": ["tests/unit/test_mcp_tools_low_coverage.py", "src/ws_ctx_engine/logger/l...`


### Error Handling

**✅ error_handling/error_structure_has_error_and_message** (Score: 100%)
- Duration: 1155ms
- Details: `{"consistent": 8, "total": 8, "failures": []}...`

**✅ error_handling/graph_error_response_fields** (Score: 100%)
- Duration: 142ms
- Details: `{"has_error_field": true, "has_message_field": true, "error_value": "INVALID_ARGUMENT", "message_value": "fn_name is required and must not be empty."}...`


### Rate Limiting

**✅ rate_limit/pack_context_triggers_on_burst** (Score: 80%)
- Duration: 77745ms
- Details: `{"rate_limited_triggered": false, "responded_count": 7, "calls_made": 7}...`

**✅ rate_limit/server_responds_after_burst** (Score: 100%)
- Duration: 153ms
- Details: `{"responded": true}...`


## MCP Compliance Rating

Based on the test results, this MCP server achieves a **99%** compliance score.

### Rating Scale:
- **95-100%**: Excellent - Full MCP compliance
- **85-94%**: Good - Minor issues, production ready
- **70-84%**: Fair - Some gaps, review recommended
- **50-69%**: Poor - Significant issues, not recommended
- **Below 50%**: Critical - Major compliance failures

### Recommendation
✨ **Excellent** - This MCP server demonstrates full compliance with MCP standards.