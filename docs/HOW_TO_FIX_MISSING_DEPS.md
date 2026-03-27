# 🚑 Xử Lý Thiếu Dependencies - Hướng Dẫn Toàn Diện

**Vấn đề:** Khi gọi MCP tools bị lỗi do thiếu dependencies (FAISS, PyCozo, etc.)  
**Giải pháp:** Tự động phát hiện + Đề xuất sửa + Cài đặt tự động

---

## 📋 Mục Lục

1. [Phát Hiện Lỗi](#phát-hiện-lỗi)
2. [Chẩn Đoán Nguyên Nhân](#chẩn-đoán-nguyên-nhân)
3. [Cách Sửa Theo Từng Lỗi](#cách-sửa-theo-từng-lỗi)
4. [Cài Đặt Tự Động](#cài-đặt-tự-động)
5. [Phòng Ngừa](#phòng-ngừa)

---

## 🔍 Phát Hiện Lỗi

### Dấu Hiệu Nhận Biết

Khi gọi tool và thấy các lỗi sau:

#### 1. **SEARCH_FAILED** - Thiếu Vector Search
```json
{
  "error": "SEARCH_FAILED",
  "message": "Failed to load vector index: No module named 'faiss'"
}
```

**Tools bị ảnh hưởng:**
- `search_codebase`
- `pack_context` (có search)

#### 2. **GRAPH_UNAVAILABLE** - Thiếu Graph Database
```json
{
  "error": "GRAPH_UNAVAILABLE",
  "message": "Graph store is not available. Run 'wsctx index' with pycozo installed"
}
```

**Tools bị ảnh hưởng:**
- `find_callers`
- `impact_analysis`
- `graph_search`
- `call_chain`

#### 3. **EMBEDDING_FAILED** - Thiếu Embedding Model
```json
{
  "error": "EMBEDDING_FAILED",
  "message": "No module named 'sentence_transformers'"
}
```

**Tools bị ảnh hưởng:**
- `search_codebase` (semantic search)

---

## 🩺 Chẩn Đoán Nguyên Nhân

### Script Tự Động Chẩn Đoán

```bash
# Chạy diagnostic tool
uv run python scripts/dependency_doctor.py
```

**Output mẫu:**
```
🔍 Đang kiểm tra dependencies...

✅ Vector search engine (FAISS)
   Module: faiss | Package: faiss-cpu

❌ Graph database for dependency analysis
   Module: pycozo | Package: pycozo[embedded] [THIẾU]

❌ Local embedding model for semantic search
   Module: sentence-transformers | Package: sentence-transformers [THIẾU]

================================================================================
📊 KẾT QUẢ CHẨN ĐOÁN
================================================================================
✅ Đã cài: 1 dependencies
❌ Thiếu: 2 dependencies
⚠️  Tools bị ảnh hưởng: 2 tools

📋 Tools bị lỗi:
   • find_callers: thiếu pycozo[embedded]
   • search_codebase: thiếu sentence-transformers
```

---

## 🔧 Cách Sửa Theo Từng Lỗi

### Lỗi 1: Missing FAISS (Vector Search)

**Triệu chứng:**
- `search_codebase` trả về `SEARCH_FAILED`
- Lỗi: `No module named 'faiss'`

**Nguyên nhân:**
- Chưa cài FAISS vector index backend

**Cách sửa:**

```bash
# Option 1: Cài riêng FAISS (nhanh nhất)
uv add faiss-cpu

# Option 2: Cài tier "fast" (bao gồm FAISS + NetworkX)
uv add ws-ctx-engine[fast]

# Option 3: Cài tất cả (recommended)
uv add ws-ctx-engine[all]
```

**Verify:**
```bash
uv run python -c "import faiss; print('✅ FAISS OK')"
```

---

### Lỗi 2: Missing PyCozo (Graph Database)

**Triệu chứng:**
- `find_callers`, `impact_analysis`, `graph_search` trả về `GRAPH_UNAVAILABLE`
- Lỗi: `No module named 'pycozo'`

**Nguyên nhân:**
- Chưa cài graph database backend

**Cách sửa:**

```bash
# Option 1: Cài riêng PyCozo
uv add 'pycozo[embedded]'

# Option 2: Cài tier "graph-store"
uv add ws-ctx-engine[graph-store]

# Option 3: Cài tất cả (recommended)
uv add ws-ctx-engine[all]
```

**Verify:**
```bash
uv run python -c "import pycozo; print('✅ PyCozo OK')"
```

---

### Lỗi 3: Missing Sentence Transformers (Embeddings)

**Triệu chứng:**
- Semantic search chậm hoặc dùng TF-IDF fallback
- Lỗi: `No module named 'sentence_transformers'`

**Nguyên nhân:**
- Chưa cài local embedding model

**Cách sửa:**

```bash
# Option 1: Cài riêng
uv add sentence-transformers torch

# Option 2: Cài tier "all"
uv add ws-ctx-engine[all]
```

**Verify:**
```bash
uv run python -c "from sentence_transformers import SentenceTransformer; print('✅ Sentence Transformers OK')"
```

---

## ⚡ Cài Đặt Tự Động

### Sử Dụng Dependency Doctor

Script này tự động phát hiện và cài tất cả dependencies thiếu:

```bash
# Bước 1: Chạy diagnostic
uv run python scripts/dependency_doctor.py

# Bước 2: Auto-fix (có xác nhận)
uv run python scripts/dependency_doctor.py --fix

# Bước 3: Dry-run trước (xem sẽ cài gì)
uv run python scripts/dependency_doctor.py --fix --dry-run
```

### Interactive Wizard

```bash
# Chạy wizard tương tác
uv run python examples/graceful_error_handling.py --fix
```

**Output:**
```
🎯 WIZARD: Tự động phát hiện và sửa thiếu dependencies
================================================================================

📋 Bước 1/3: Đang chẩn đoán...
❌ Tool không hoạt động: Missing PyCozo dependency

📋 Bước 2/3: Vấn đề phát hiện
   ❌ Missing PyCozo dependency
   📦 Package thiếu: pycozo[embedded]
   🔧 Tools bị ảnh hưởng:
      • find_callers
      • impact_analysis
      • graph_search
      • call_chain

📋 Bước 3/3: Đề xuất sửa

🎯 Tùy chọn 1 (Recommended - Cài tất cả):
   uv add ws-ctx-engine[all]
   → Cài đầy đủ tất cả dependencies

🎯 Tùy chọn 2 (Cài riêng lẻ):
   uv add 'pycozo[embedded]'
   → Chỉ cài package thiếu

Chọn phương án (1/2/3/q để thoát): 
```

---

## 🎯 Giải Pháp Tối Ưu

### Recommended Installation Path

```bash
# 1. Cài đầy đủ MỘT LẦN DUY NHẤT
uv add ws-ctx-engine[all]

# 2. Rebuild index với đầy đủ features
uv run ws-ctx-engine index . --verbose

# 3. Verify tất cả working
uv run python examples/debug_tool_calls.py
```

**Tại sao nên cài `all` tier?**
- ✅ Đầy đủ tất cả features
- ✅ Không phải lo thiếu deps sau này
- ✅ Performance tốt nhất (FAISS + igraph + ONNX)
- ✅ Hỗ trợ nhiều ngôn ngữ (AST parsers)
- ✅ Nghiên cứu mới nhất (cAST, LEANN)

---

## 📊 So Sánh Các Tier

| Tier | Packages | Size | Tools Available | Recommended For |
|------|----------|------|-----------------|-----------------|
| **core** | 9 | ~50MB | Basic only | Testing |
| **fast** | +6 | ~200MB | + Vector search | Quick setup |
| **graph-store** | +1 | ~100MB | + Graph features | Graph analysis |
| **all** ⭐ | +13 | ~500MB | **ALL 12 TOOLS** | **Production** |
| **leann** | +1 | ~50MB | + LEANN index | Large codebases |

---

## 🛡️ Phòng Ngừa

### 1. Check Dependencies Trước Khi Dùng

```python
from scripts.dependency_doctor import DependencyDoctor

doctor = DependencyDoctor()
results = doctor.diagnose()

if results["missing"]:
    print("⚠️  Thiếu dependencies:")
    for dep in results["missing"]:
        print(f"   ❌ {dep['package']}")
    print("\n💡 Chạy: uv add ws-ctx-engine[all]")
else:
    print("✅ Tất cả dependencies đã cài!")
```

### 2. Add to Project Dependencies

Trong `pyproject.toml`:

```toml
[project.optional-dependencies]
context-packaging = [
    "ws-ctx-engine[all]>=0.2.0"
]
```

### 3. CI/CD Check

Thêm vào workflow để đảm bảo dependencies luôn đầy đủ:

```yaml
- name: Check ws-ctx-engine dependencies
  run: |
    uv add ws-ctx-engine[all]
    uv run ws-ctx-engine index .
```

---

## 🚀 Quick Reference Commands

```bash
# Diagnostic
uv run python scripts/dependency_doctor.py

# Auto-fix with confirmation
uv run python scripts/dependency_doctor.py --fix

# Install all at once
uv add ws-ctx-engine[all]

# Rebuild index after install
uv run ws-ctx-engine index . --verbose

# Test all tools
uv run python examples/debug_tool_calls.py

# Verify specific dependency
uv run python -c "import faiss; import pycozo; print('✅ OK')"
```

---

## 📝 Checklist Sau Khi Cài

```bash
# 1. Check imports
uv run python -c "
import faiss
import pycozo
import sentence_transformers
import tree_sitter
print('✅ All imports successful!')
"

# 2. Check index health
uv run ws-ctx-engine index-status .

# 3. Test search
uv run python -c "
from ws_ctx_engine.mcp.server import MCPStdioServer
server = MCPStdioServer(workspace='.')
response = server._handle_request({
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'tools/call',
    'params': {
        'name': 'search_codebase',
        'arguments': {'query': 'test', 'limit': 3}
    }
})
print('✅ Search works!' if 'results' in str(response) else '❌ Still broken')
"

# 4. Test graph
uv run python -c "
from ws_ctx_engine.mcp.server import MCPStdioServer
server = MCPStdioServer(workspace='.')
response = server._handle_request({
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'tools/call',
    'params': {
        'name': 'graph_search',
        'arguments': {'file_id': 'src/test.py'}
    }
})
print('✅ Graph works!' if 'symbols' in str(response) else '❌ Still broken')
"
```

---

## 🆘 Troubleshooting

### Vấn đề: Cài xong vẫn lỗi

**Giải pháp:**
```bash
# 1. Restart Python kernel/session
# 2. Rebuild index
uv run ws-ctx-engine index . --rebuild

# 3. Clear cache
rm -rf .ws-ctx-engine/
uv run ws-ctx-engine index . --verbose
```

### Vấn đề: Compilation errors khi cài

**macOS:**
```bash
xcode-select --install
uv add ws-ctx-engine[all]
```

**Linux:**
```bash
sudo apt-get install build-essential python3-dev
uv add ws-ctx-engine[all]
```

**Windows:**
```powershell
# Install Visual Studio Build Tools
# Then:
uv add ws-ctx-engine[all]
```

### Vấn đề: Out of memory

**Giải pháp:**
```bash
# Install với ít dependencies hơn
uv add ws-ctx-engine[fast]  # вместо all

# Hoặc tăng swap space
# macOS: Already managed
# Linux: sudo fallocate -l 4G /swapfile
```

---

## 📞 Need Help?

Nếu vẫn gặp vấn đề:

1. Chạy diagnostic và lưu output:
```bash
uv run python scripts/dependency_doctor.py > diagnostic.log
```

2. Kiểm tra log file:
```bash
cat diagnostic.log
```

3. Tạo issue với thông tin:
- Output từ diagnostic
- OS và Python version
- Lỗi cụ thể (screenshot)

---

**Cập nhật:** 2026-03-27  
**Version:** 1.0  
**Tested on:** Python 3.13.5, ws-ctx-engine 0.2.0a0
