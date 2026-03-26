# MCP Comprehensive Test Report

**Generated:** 2026-03-26 21:38:40  
**Workspace:** `/Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker`  
**Server:** Unknown 

## Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Score** | 80.6% |
| **Total Tests** | 17 |
| **Passed** | 14 ✓ |
| **Failed** | 3 ✗ |
| **Pass Rate** | 82.4% |

## Category Scores

| Category | Score | Tests | Passed | Failed |
|----------|-------|-------|--------|--------|
| Protocol Compliance | 50% | 2 | 1 | 1 |
| Tool Discovery & Registration | 50% | 2 | 1 | 1 |
| Input Validation | 100% | 3 | 3 | 0 |
| Error Handling | 100% | 2 | 2 | 0 |
| Performance Testing | 57% | 3 | 2 | 1 |
| Concurrency Testing | 100% | 2 | 2 | 0 |
| Security Testing | 100% | 1 | 1 | 0 |
| Structured Content | 100% | 1 | 1 | 0 |
| Timeout & Limits | 100% | 1 | 1 | 0 |

## Detailed Results


### Protocol Compliance

**❌ initialize** (Score: 0%)
- Duration: 402ms
- Details: `{"checks": {"jsonrpc_valid": false, "has_server_info": false, "has_capabilities": false, "has_protocol_version": false, "server_name_present": false, "server_version_present": false}, "response": {"js...`
- Error: `ID mismatch: expected 1001, got 1774535790482`


### Tool Discovery & Registration

**❌ tools/list** (Score: 0%)
- Duration: 330ms
- Details: `{"checks": {"jsonrpc_valid": false, "has_tools_array": false, "tools_not_empty": false, "each_tool_has_name": false, "each_tool_has_description": false, "each_tool_has_schema": false}, "tools_found": ...`


### Protocol Compliance

**✅ notifications/no_response** (Score: 100%)
- Duration: 253ms
- Details: `{"has_output": false, "output": ""}...`


### Tool Discovery & Registration

**✅ tool_discovery_comprehensive** (Score: 100%)
- Duration: 279ms
- Details: `{"tools_analysis": [{"name": "search_codebase", "has_description": true, "description_length": 57, "has_schema": true, "schema_type": "object", "has_properties": true, "required_fields_count": 1}, {"n...`


### Input Validation

**✅ input_validation/missing_required** (Score: 100%)
- Duration: 264ms
- Details: `{"error_detected": true, "error_type": "validation_error", "response": {"jsonrpc": "2.0", "id": 1774535791746, "result": {"content": [{"type": "text", "text": "{\"error\": \"INVALID_ARGUMENT\", \"mess...`

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
- Duration: 364ms
- Details: `{"has_error": true, "error_valid": true, "error_code": -32601, "error_message": "Method not found: unknown_method_xyz"}...`

**✅ error_handling/unknown_tool** (Score: 100%)
- Duration: 265ms
- Details: `{"has_error": true, "error_in_content": true}...`


### Performance Testing

**✅ performance/single_request_latency** (Score: 100%)
- Duration: 262ms
- Details: `{"avg_latency_ms": 261.6807460784912, "min_latency_ms": 236.69099807739258, "max_latency_ms": 280.8520793914795, "std_dev_ms": 17.187138856761603, "samples": 5}...`

**❌ performance/search_latency** (Score: 0%)
- Duration: 10023ms
- Details: `{"avg_latency_ms": 10023.21857213974, "max_latency_ms": 10372.814893722534, "samples": 4}...`

**✅ performance/pack_context_latency** (Score: 70%)
- Duration: 9740ms
- Details: `{"avg_latency_ms": 9740.04832903544, "samples": 3}...`


### Concurrency Testing

**✅ concurrency/parallel_requests** (Score: 100%)
- Duration: 1361ms
- Details: `{"total_requests": 10, "successful": 10, "errors": 0, "total_duration_ms": 1360.9130382537842, "success_rate": 1.0}...`

**✅ concurrency/mixed_tools** (Score: 100%)
- Duration: 0ms
- Details: `{"total_requests": 6, "successful": 6}...`


### Timeout & Limits

**✅ timeout/handling** (Score: 100%)
- Duration: 468ms
- Details: `{"duration_ms": 468.13321113586426, "timeout_set": 5}...`


### Structured Content

**✅ structured_content/format** (Score: 100%)
- Duration: 10085ms
- Details: `{"has_content": true, "has_structured_content": true, "content_is_array": true, "content_items_have_type": true}...`


## MCP Compliance Rating

Based on the test results, this MCP server achieves a **81%** compliance score.

### Rating Scale:
- **95-100%**: Excellent - Full MCP compliance
- **85-94%**: Good - Minor issues, production ready
- **70-84%**: Fair - Some gaps, review recommended
- **50-69%**: Poor - Significant issues, not recommended
- **Below 50%**: Critical - Major compliance failures

### Recommendation
⚠ **Fair** - This MCP server has some compliance gaps. Review failed tests.