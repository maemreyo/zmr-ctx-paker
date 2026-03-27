# MCP Comprehensive Test Report

**Generated:** 2026-03-27 09:44:36  
**Workspace:** `/Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker`  
**Server:** ws-ctx-engine 0.2.0a0

## Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Score** | 94.1% |
| **Total Tests** | 17 |
| **Passed** | 15 ✓ |
| **Failed** | 2 ✗ |
| **Pass Rate** | 88.2% |

## Category Scores

| Category | Score | Tests | Passed | Failed |
|----------|-------|-------|--------|--------|
| Protocol Compliance | 100% | 2 | 2 | 0 |
| Tool Discovery & Registration | 100% | 2 | 2 | 0 |
| Input Validation | 100% | 3 | 3 | 0 |
| Error Handling | 100% | 2 | 2 | 0 |
| Performance Testing | 67% | 3 | 1 | 2 |
| Concurrency Testing | 100% | 2 | 2 | 0 |
| Security Testing | 100% | 1 | 1 | 0 |
| Structured Content | 100% | 1 | 1 | 0 |
| Timeout & Limits | 100% | 1 | 1 | 0 |

## Detailed Results


### Protocol Compliance

**✅ initialize** (Score: 100%)
- Duration: 301ms
- Details: `{"checks": {"jsonrpc_valid": true, "has_server_info": true, "has_capabilities": true, "has_protocol_version": true, "server_name_present": true, "server_version_present": true}, "response": {"jsonrpc"...`


### Tool Discovery & Registration

**✅ tools/list** (Score: 100%)
- Duration: 240ms
- Details: `{"checks": {"jsonrpc_valid": true, "has_tools_array": true, "tools_not_empty": true, "each_tool_has_name": true, "each_tool_has_description": true, "each_tool_has_schema": true}, "tools_found": 7, "re...`


### Protocol Compliance

**✅ notifications/no_response** (Score: 100%)
- Duration: 246ms
- Details: `{"has_output": false, "output": ""}...`


### Tool Discovery & Registration

**✅ tool_discovery_comprehensive** (Score: 100%)
- Duration: 273ms
- Details: `{"tools_analysis": [{"name": "search_codebase", "has_description": true, "description_length": 57, "has_schema": true, "schema_type": "object", "has_properties": true, "required_fields_count": 1}, {"n...`


### Input Validation

**✅ input_validation/missing_required** (Score: 100%)
- Duration: 259ms
- Details: `{"error_detected": true, "error_type": "validation_error", "response": {"jsonrpc": "2.0", "id": 1774579278038, "result": {"content": [{"type": "text", "text": "{\"error\": \"INVALID_ARGUMENT\", \"mess...`

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
- Duration: 417ms
- Details: `{"has_error": true, "error_valid": true, "error_code": -32601, "error_message": "Method not found: unknown_method_xyz"}...`

**✅ error_handling/unknown_tool** (Score: 100%)
- Duration: 326ms
- Details: `{"has_error": true, "error_in_content": true}...`


### Performance Testing

**✅ performance/single_request_latency** (Score: 100%)
- Duration: 327ms
- Details: `{"avg_latency_ms": 327.1376132965088, "min_latency_ms": 287.08410263061523, "max_latency_ms": 384.1729164123535, "std_dev_ms": 38.28653790661951, "samples": 5}...`

**❌ performance/search_latency** (Score: 100%)
- Duration: 0ms
- Details: `{"mode": "warm-path (persistent process)", "cold_start_ms": 11391.1, "avg_warm_ms": 0.0, "max_warm_ms": 0.0, "p99_warm_ms": 0.0, "samples": 0, "error": ""}...`

**❌ performance/pack_context_latency** (Score: 0%)
- Duration: 10509ms
- Details: `{"mode": "warm-path (persistent process)", "cold_start_ms": 12427.8, "avg_warm_ms": 10509.1, "samples": 3, "error": ""}...`


### Concurrency Testing

**✅ concurrency/parallel_requests** (Score: 100%)
- Duration: 2215ms
- Details: `{"total_requests": 10, "successful": 10, "errors": 0, "total_duration_ms": 2214.585065841675, "success_rate": 1.0}...`

**✅ concurrency/mixed_tools** (Score: 100%)
- Duration: 0ms
- Details: `{"total_requests": 6, "successful": 6}...`


### Timeout & Limits

**✅ timeout/handling** (Score: 100%)
- Duration: 261ms
- Details: `{"duration_ms": 261.31391525268555, "timeout_set": 5}...`


### Structured Content

**✅ structured_content/format** (Score: 100%)
- Duration: 12996ms
- Details: `{"has_content": true, "has_structured_content": true, "content_is_array": true, "content_items_have_type": true}...`


## MCP Compliance Rating

Based on the test results, this MCP server achieves a **94%** compliance score.

### Rating Scale:
- **95-100%**: Excellent - Full MCP compliance
- **85-94%**: Good - Minor issues, production ready
- **70-84%**: Fair - Some gaps, review recommended
- **50-69%**: Poor - Significant issues, not recommended
- **Below 50%**: Critical - Major compliance failures

### Recommendation
✓ **Good** - This MCP server is production-ready with minor areas for improvement.