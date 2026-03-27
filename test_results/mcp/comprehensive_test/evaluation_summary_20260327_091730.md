# MCP Comprehensive Test Report

**Generated:** 2026-03-27 09:17:30  
**Workspace:** `/Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker`  
**Server:** ws-ctx-engine 0.2.0a0

## Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Score** | 92.4% |
| **Total Tests** | 17 |
| **Passed** | 16 ✓ |
| **Failed** | 1 ✗ |
| **Pass Rate** | 94.1% |

## Category Scores

| Category | Score | Tests | Passed | Failed |
|----------|-------|-------|--------|--------|
| Protocol Compliance | 100% | 2 | 2 | 0 |
| Tool Discovery & Registration | 100% | 2 | 2 | 0 |
| Input Validation | 100% | 3 | 3 | 0 |
| Error Handling | 100% | 2 | 2 | 0 |
| Performance Testing | 57% | 3 | 2 | 1 |
| Concurrency Testing | 100% | 2 | 2 | 0 |
| Security Testing | 100% | 1 | 1 | 0 |
| Structured Content | 100% | 1 | 1 | 0 |
| Timeout & Limits | 100% | 1 | 1 | 0 |

## Detailed Results


### Protocol Compliance

**✅ initialize** (Score: 100%)
- Duration: 271ms
- Details: `{"checks": {"jsonrpc_valid": true, "has_server_info": true, "has_capabilities": true, "has_protocol_version": true, "server_name_present": true, "server_version_present": true}, "response": {"jsonrpc"...`


### Tool Discovery & Registration

**✅ tools/list** (Score: 100%)
- Duration: 215ms
- Details: `{"checks": {"jsonrpc_valid": true, "has_tools_array": true, "tools_not_empty": true, "each_tool_has_name": true, "each_tool_has_description": true, "each_tool_has_schema": true}, "tools_found": 7, "re...`


### Protocol Compliance

**✅ notifications/no_response** (Score: 100%)
- Duration: 229ms
- Details: `{"has_output": false, "output": ""}...`


### Tool Discovery & Registration

**✅ tool_discovery_comprehensive** (Score: 100%)
- Duration: 263ms
- Details: `{"tools_analysis": [{"name": "search_codebase", "has_description": true, "description_length": 57, "has_schema": true, "schema_type": "object", "has_properties": true, "required_fields_count": 1}, {"n...`


### Input Validation

**✅ input_validation/missing_required** (Score: 100%)
- Duration: 224ms
- Details: `{"error_detected": true, "error_type": "validation_error", "response": {"jsonrpc": "2.0", "id": 1774577669198, "result": {"content": [{"type": "text", "text": "{\"error\": \"INVALID_ARGUMENT\", \"mess...`

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
- Duration: 252ms
- Details: `{"has_error": true, "error_valid": true, "error_code": -32601, "error_message": "Method not found: unknown_method_xyz"}...`

**✅ error_handling/unknown_tool** (Score: 100%)
- Duration: 233ms
- Details: `{"has_error": true, "error_in_content": true}...`


### Performance Testing

**✅ performance/single_request_latency** (Score: 100%)
- Duration: 266ms
- Details: `{"avg_latency_ms": 265.7015323638916, "min_latency_ms": 253.24201583862305, "max_latency_ms": 276.2577533721924, "std_dev_ms": 11.551911119928524, "samples": 5}...`

**❌ performance/search_latency** (Score: 0%)
- Duration: 12021ms
- Details: `{"avg_latency_ms": 12020.570516586304, "max_latency_ms": 12344.106912612915, "samples": 4}...`

**✅ performance/pack_context_latency** (Score: 70%)
- Duration: 11496ms
- Details: `{"avg_latency_ms": 11496.060689290365, "samples": 3}...`


### Concurrency Testing

**✅ concurrency/parallel_requests** (Score: 100%)
- Duration: 1378ms
- Details: `{"total_requests": 10, "successful": 10, "errors": 0, "total_duration_ms": 1377.718210220337, "success_rate": 1.0}...`

**✅ concurrency/mixed_tools** (Score: 100%)
- Duration: 0ms
- Details: `{"total_requests": 6, "successful": 6}...`


### Timeout & Limits

**✅ timeout/handling** (Score: 100%)
- Duration: 283ms
- Details: `{"duration_ms": 283.113956451416, "timeout_set": 5}...`


### Structured Content

**✅ structured_content/format** (Score: 100%)
- Duration: 11611ms
- Details: `{"has_content": true, "has_structured_content": true, "content_is_array": true, "content_items_have_type": true}...`


## MCP Compliance Rating

Based on the test results, this MCP server achieves a **92%** compliance score.

### Rating Scale:
- **95-100%**: Excellent - Full MCP compliance
- **85-94%**: Good - Minor issues, production ready
- **70-84%**: Fair - Some gaps, review recommended
- **50-69%**: Poor - Significant issues, not recommended
- **Below 50%**: Critical - Major compliance failures

### Recommendation
✓ **Good** - This MCP server is production-ready with minor areas for improvement.