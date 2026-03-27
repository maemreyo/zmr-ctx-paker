# MCP Comprehensive Test Report

**Generated:** 2026-03-27 17:19:19  
**Workspace:** `/Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker`  
**Server:** ws-ctx-engine 0.2.0a0

## Executive Summary

| Metric            | Value  |
| ----------------- | ------ |
| **Overall Score** | 100.0% |
| **Total Tests**   | 29     |
| **Passed**        | 29 ✓   |
| **Failed**        | 0 ✗    |
| **Pass Rate**     | 100.0% |

## Category Scores

| Category                      | Score | Tests | Passed | Failed |
| ----------------------------- | ----- | ----- | ------ | ------ |
| Protocol Compliance           | 100%  | 2     | 2      | 0      |
| Tool Discovery & Registration | 100%  | 2     | 2      | 0      |
| Input Validation              | 100%  | 3     | 3      | 0      |
| Error Handling                | 100%  | 2     | 2      | 0      |
| Performance Testing           | 100%  | 3     | 3      | 0      |
| Concurrency Testing           | 100%  | 2     | 2      | 0      |
| Security Testing              | 100%  | 1     | 1      | 0      |
| Structured Content            | 100%  | 1     | 1      | 0      |
| Timeout & Limits              | 100%  | 1     | 1      | 0      |
| Graph Tools                   | 100%  | 12    | 12     | 0      |

## Detailed Results

### Protocol Compliance

**✅ initialize** (Score: 100%)

- Duration: 249ms
- Details: `{"checks": {"jsonrpc_valid": true, "has_server_info": true, "has_capabilities": true, "has_protocol_version": true, "server_name_present": true, "server_version_present": true}, "response": {"jsonrpc"...`

### Tool Discovery & Registration

**✅ tools/list** (Score: 100%)

- Duration: 290ms
- Details: `{"checks": {"jsonrpc_valid": true, "has_tools_array": true, "tools_not_empty": true, "each_tool_has_name": true, "each_tool_has_description": true, "each_tool_has_schema": true}, "tools_found": 12, "r...`

### Protocol Compliance

**✅ notifications/no_response** (Score: 100%)

- Duration: 318ms
- Details: `{"has_output": false, "output": ""}...`

### Tool Discovery & Registration

**✅ tool_discovery_comprehensive** (Score: 100%)

- Duration: 271ms
- Details: `{"tools_analysis": [{"name": "search_codebase", "has_description": true, "description_length": 57, "has_schema": true, "schema_type": "object", "has_properties": true, "required_fields_count": 1}, {"n...`

### Input Validation

**✅ input_validation/missing_required** (Score: 100%)

- Duration: 231ms
- Details: `{"error_detected": true, "error_type": "validation_error", "response": {"jsonrpc": "2.0", "id": 1774606655970, "result": {"content": [{"type": "text", "text": "{\"error\": \"INVALID_ARGUMENT\", \"mess...`

**✅ input_validation/invalid_types** (Score: 100%)

- Duration: 0ms
- Details: `{"test_cases": 3, "errors_caught": 3, "results": [{"case": {"name": "search_codebase", "arguments": {"query": 12345}}, "error_detected": true}, {"case": {"name": "search_codebase", "arguments": {"quer...`

**✅ input_validation/boundary_values** (Score: 100%)

- Duration: 0ms
- Details: `{"test_cases": 3, "handled_count": 3}...`

### Security Testing

**✅ security/injection_attempts** (Score: 100%)

- Duration: 0ms
- Details: `{"test_cases": 5, "safe_count": 5}...`

### Error Handling

**✅ error_handling/unknown_method** (Score: 100%)

- Duration: 288ms
- Details: `{"has_error": true, "error_valid": true, "error_code": -32601, "error_message": "Method not found: unknown_method_xyz"}...`

**✅ error_handling/unknown_tool** (Score: 100%)

- Duration: 231ms
- Details: `{"has_error": true, "error_in_content": true}...`

### Performance Testing

**✅ performance/single_request_latency** (Score: 100%)

- Duration: 301ms
- Details: `{"avg_latency_ms": 300.9552478790283, "min_latency_ms": 270.48397064208984, "max_latency_ms": 335.2019786834717, "std_dev_ms": 24.758300506603973, "samples": 5}...`

**✅ performance/search_latency** (Score: 100%)

- Duration: 20ms
- Details: `{"mode": "warm-path (persistent process)", "cold_start_ms": 10157.2, "avg_warm_ms": 19.8, "max_warm_ms": 20.0, "p99_warm_ms": 20.0, "samples": 4, "error": ""}...`

**✅ performance/pack_context_latency** (Score: 100%)

- Duration: 121ms
- Details: `{"mode": "warm-path (persistent process)", "cold_start_ms": 9980.3, "avg_warm_ms": 120.9, "samples": 3, "error": ""}...`

### Concurrency Testing

**✅ concurrency/parallel_requests** (Score: 100%)

- Duration: 1827ms
- Details: `{"total_requests": 10, "successful": 10, "errors": 0, "total_duration_ms": 1826.6019821166992, "success_rate": 1.0}...`

**✅ concurrency/mixed_tools** (Score: 100%)

- Duration: 0ms
- Details: `{"total_requests": 6, "successful": 6}...`

### Timeout & Limits

**✅ timeout/handling** (Score: 100%)

- Duration: 319ms
- Details: `{"duration_ms": 318.5269832611084, "timeout_set": 5}...`

### Structured Content

**✅ structured_content/format** (Score: 100%)

- Duration: 11075ms
- Details: `{"has_content": true, "has_structured_content": true, "content_is_array": true, "content_items_have_type": true}...`

### Graph Tools

**✅ graph_tools/registration** (Score: 100%)

- Duration: 298ms
- Details: `{"checks": {"all_tools_present": true, "all_have_description": true, "all_have_use_when": true, "all_have_schema": true}, "missing": [], "registered": ["find_callers", "impact_analysis", "graph_search...`

**✅ graph_tools/get_status** (Score: 100%)

- Duration: 858ms
- Details: `{"checks": {"server_responded": true, "has_ready_field": true, "has_graph_store": true, "has_vector_backend": true, "graph_store_has_available": true}, "payload": {"ready": true, "index_exists": true,...`

**✅ graph_tools/find_callers/validation** (Score: 100%)

- Duration: 0ms
- Details: `{"cases": [{"label": "missing fn_name", "got_invalid_argument": true}, {"label": "empty fn_name", "got_invalid_argument": true}]}...`

**✅ graph_tools/find_callers/happy_path** (Score: 100%)

- Duration: 766ms
- Details: `{"has_callers": true, "graph_unavailable": false, "payload": {"callers": []}}...`

**✅ graph_tools/impact_analysis/validation** (Score: 100%)

- Duration: 0ms
- Details: `{"cases": [{"label": "missing file_path", "got_invalid_argument": true}, {"label": "empty file_path", "got_invalid_argument": true}]}...`

**✅ graph_tools/impact_analysis/happy_path** (Score: 100%)

- Duration: 1058ms
- Details: `{"has_importers": true, "graph_unavailable": false}...`

**✅ graph_tools/graph_search/validation** (Score: 100%)

- Duration: 0ms
- Details: `{"cases": [{"label": "missing file_id", "got_invalid_argument": true}, {"label": "empty file_id", "got_invalid_argument": true}]}...`

**✅ graph_tools/graph_search/happy_path** (Score: 100%)

- Duration: 791ms
- Details: `{"has_symbols": true, "graph_unavailable": false}...`

**✅ graph_tools/call_chain/validation** (Score: 100%)

- Duration: 0ms
- Details: `{"cases": [{"label": "missing both", "got_invalid_argument": true}, {"label": "missing to_fn", "got_invalid_argument": true}, {"label": "missing from_fn", "got_invalid_argument": true}]}...`

**✅ graph_tools/call_chain/happy_path** (Score: 100%)

- Duration: 780ms
- Details: `{"has_path_key": true, "graph_unavailable": false, "not_implemented": false, "path": []}...`

**✅ graph_tools/graceful_degradation** (Score: 100%)

- Duration: 0ms
- Details: `{"results": [{"tool": "find_callers", "responded": true}, {"tool": "impact_analysis", "responded": true}, {"tool": "graph_search", "responded": true}, {"tool": "call_chain", "responded": true}, {"tool...`

**✅ graph_tools/performance** (Score: 100%)

- Duration: 1ms
- Details: `{"avg_warm_ms": 0.8, "samples": 5, "error": ""}...`

## MCP Compliance Rating

Based on the test results, this MCP server achieves a **100%** compliance score.

### Rating Scale:

- **95-100%**: Excellent - Full MCP compliance
- **85-94%**: Good - Minor issues, production ready
- **70-84%**: Fair - Some gaps, review recommended
- **50-69%**: Poor - Significant issues, not recommended
- **Below 50%**: Critical - Major compliance failures

### Recommendation

✨ **Excellent** - This MCP server demonstrates full compliance with MCP standards.
