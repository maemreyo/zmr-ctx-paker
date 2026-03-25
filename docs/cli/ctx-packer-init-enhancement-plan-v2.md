# ctx-packer-init — Enhancement Plan v2

> Deep review của commit mới nhất. Bao gồm: trạng thái fix từng issue cũ,
> 3 câu hỏi cụ thể, và các bugs mới phát sinh.

---

## Phần 1 — Trạng thái fix từ review trước

| # | Issue cũ | Trạng thái | Ghi chú |
|---|---|---|---|
| ① | `init_cli.py` broken path sau pip install | ✅ Đã fix | Di chuyển `scripts/` vào `src/context_packer/`, sửa path |
| ② | Timeout khai báo nhưng không dùng | ✅ Đã fix | `timeout "$timeout_seconds" ctx-packer index ...` |
| ③ | Hardcode macOS Python path | ✅ Đã fix | `_ensure_ctx_packer_in_path()` dùng `python3 -m site` |
| ④ | `envsubst` nuốt `$VAR` trong code block | ✅ Đã fix | Scoped: `envsubst '${CTX_DATE} ${CTX_PACKER_VERSION} ...'` |
| ⑤ | `--force` không hoạt động với append-only | ✅ Đã fix | `_remove_section()` + force-replace trong 4 adapters |
| ⑥ | `check_git` check sai directory | ✅ Đã fix | `[[ ! -d "$CTX_TARGET/.git" ]]` |
| ⑦ | `source` trong vòng lặp thừa I/O | ✅ Đã fix | Tách thành 2 loops: source all → install all |
| ⑧ | IFS parsing fragile trong registry | ❌ Chưa fix | Vẫn vỡ nếu desc chứa dấu `:` |
| ⑨ | `2>&1` nuốt stderr vào stdout | ❌ Chưa fix | Vẫn còn trong `index.sh` |

---

## Phần 2 — Bugs mới phát sinh trong commit này

### Bug A — `_remove_section` không hoạt động đúng với multi-paragraph sections (Critical)

**File:** `src/context_packer/scripts/lib/core.sh`

```bash
# IMPLEMENTATION HIỆN TẠI
sed -i "/^# ${marker}/,/^$/d" "$file"
```

**Vấn đề 1 — Cross-platform:** `sed -i` trên macOS yêu cầu argument suffix, dù là empty string:
```bash
# macOS
sed -i '' "/pattern/d" file   # OK
sed -i "/pattern/d" file      # ERROR hoặc tạo file backup

# Linux
sed -i "/pattern/d" file      # OK
sed -i '' "/pattern/d" file   # ERROR (không nhận empty string)
```

**Vấn đề 2 — Range `/^# marker/,/^$/d` dừng ở dòng trống đầu tiên.** Toàn bộ templates đều có blank lines nội bộ (giữa sections). Ví dụ `AGENTS.md.tpl`:
```markdown
# ctx-packer — Code Packaging   ← marker, bắt đầu delete
                                  ← blank line → SED DỪNG Ở ĐÂY
## What is ctx-packer?           ← vẫn còn trong file sau remove!
```

**Fix đúng:**
```bash
_remove_section() {
  local file="$1"
  local marker="${2:-ctx-packer}"
  [[ -f "$file" ]] || return 0

  # Portable: detect macOS vs Linux sed
  local SED_INPLACE
  if sed --version 2>/dev/null | grep -q GNU; then
    SED_INPLACE=(sed -i)
  else
    SED_INPLACE=(sed -i '')
  fi

  # Delete from marker to NEXT marker-level heading OR end of file
  # Dùng Python vì sed không handle "đến EOF" tốt
  python3 - "$file" "$marker" <<'PYEOF'
import sys, re
path, marker = sys.argv[1], sys.argv[2]
text = open(path).read()
# Remove section: from "# <marker>" to next "## " heading or end of file
pattern = rf'\n# {re.escape(marker)}.*?(?=\n# |\Z)'
result = re.sub(pattern, '', text, flags=re.DOTALL)
open(path, 'w').write(result)
PYEOF
}
```

Hoặc nếu muốn giữ thuần bash — dùng `awk` thay `sed`:
```bash
_remove_section() {
  local file="$1" marker="${2:-ctx-packer}"
  [[ -f "$file" ]] || return 0
  local tmp
  tmp="$(mktemp)"
  awk -v marker="^# ${marker}" '
    /^# / && found { found=0 }
    $0 ~ marker { found=1 }
    !found { print }
  ' "$file" > "$tmp" && mv "$tmp" "$file"
}
```

---

### Bug B — `scripts/publish.sh` bị bundle vào package (Major)

**File:** `pyproject.toml`

```toml
context_packer = ["py.typed", "scripts/**", "templates/**"]
```

`scripts/**` include cả `publish.sh` — đây là dev/release tool, không liên quan đến người dùng cuối. Ai install `ctx-packer` qua pip sẽ có `publish.sh` trong `site-packages`.

**Fix:**
```toml
# Cách 1: Explicit whitelist thay vì glob
context_packer = [
  "py.typed",
  "scripts/init.sh",
  "scripts/lib/*.sh",
  "scripts/agents/*.sh",
  "templates/**"
]

# Cách 2: Thêm exclude trong MANIFEST.in
# MANIFEST.in:
# prune src/context_packer/scripts/publish.sh
```

---

### Bug C — Package data không preserve execute permissions (Major)

Khi pip cài `package_data`, các file bash script mất bit `+x`. `init_cli.py` gọi `bash init.sh` nên `init.sh` không cần `+x`. Nhưng `init.sh` gọi các scripts khác — nếu bất kỳ chỗ nào dùng `./script.sh` thay vì `bash script.sh`, sẽ `Permission denied`.

Cần audit toàn bộ `init.sh` và các adapters: tất cả phải dùng `source` hoặc `bash <path>`, không dùng `./`.

**Fix trong `init_cli.py`:**
```python
import stat

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    init_script = os.path.join(script_dir, "scripts", "init.sh")

    # Ensure executable bit (lost during pip install)
    st = os.stat(init_script)
    os.chmod(init_script, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    result = subprocess.run(["bash", init_script] + sys.argv[1:], cwd=os.getcwd())
    sys.exit(result.returncode)
```

---

## Phần 3 — Câu hỏi 1: `gum` cho interactive agent selection

### 3.1 Hiện trạng

**CHƯA implement.** Hiện tại chỉ có `--agents claude,cursor` flag. Không có interactive prompt khi chạy không có flag.

### 3.2 Design: gum-first với graceful fallback

Khi user chạy `ctx-packer-init` không có `--agents`, flow nên là:

```
Có gum?
  ├── Có → Show interactive multi-select
  └── Không → Hỏi install gum, nếu từ chối → dùng defaults
```

### 3.3 Implementation

**`lib/core.sh` — thêm gum detection và install:**

```bash
# Detect gum
_has_gum() { command -v gum &>/dev/null; }

# Install gum nếu chưa có
_ensure_gum() {
  _has_gum && return 0

  log_warn "gum (interactive UI) not found."

  if _has_gum_installer; then
    if gum confirm "Install gum for interactive agent selection?"; then
      _install_gum && return 0
    fi
  else
    log_warn "Cannot auto-install gum. Using defaults."
  fi
  return 1
}

_has_gum_installer() {
  command -v brew &>/dev/null || command -v apt-get &>/dev/null || \
  command -v pacman &>/dev/null || command -v nix-env &>/dev/null
}

_install_gum() {
  if command -v brew &>/dev/null; then
    brew install gum
  elif command -v apt-get &>/dev/null; then
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://repo.charm.sh/apt/gpg.key \
      | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg
    echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" \
      | sudo tee /etc/apt/sources.list.d/charm.list
    sudo apt update && sudo apt install -y gum
  elif command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm gum
  fi
}
```

**`lib/selector.sh` — tách selector logic ra file riêng (SoC):**

```bash
#!/usr/bin/env bash
# lib/selector.sh — Agent selection: gum-first, fallback to defaults

# Build display label từng agent: "● claude   Claude Code      (default)"
_agent_label() {
  local id="$1"
  local name desc default
  for e in "${AGENT_REGISTRY[@]}"; do
    [[ "$e" =~ ^${id}: ]] || continue
    IFS=: read -r _ name desc default <<< "$e"
    local marker=""
    [[ "$default" == "true" ]] && marker="(default)"
    printf "%-14s %-20s %s" "$id" "$name" "$marker"
    return
  done
}

# Interactive selection với gum choose --no-limit
select_agents_interactive() {
  local all_ids
  mapfile -t all_ids < <(get_agent_ids)

  # Build display lines cho gum
  local labels=()
  local defaults_map=()
  for id in "${all_ids[@]}"; do
    labels+=("$(_agent_label "$id")")
  done

  # Pre-select defaults bằng cách dùng gum filter với --value
  # gum choose --no-limit cho phép multi-select với spacebar
  local selected
  selected=$(
    printf '%s\n' "${labels[@]}" | \
    gum choose \
      --no-limit \
      --header "Select AI agents to configure (space to toggle, enter to confirm):" \
      --selected="$(get_default_agents | xargs | tr ' ' ',')" \
      --cursor-prefix "○ " \
      --selected-prefix "● " \
      --unselected-prefix "  "
  )

  # Parse lại id từ selected lines (lấy field đầu tiên)
  local result=()
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    local id
    id=$(awk '{print $1}' <<< "$line")
    result+=("$id")
  done <<< "$selected"

  printf '%s\n' "${result[@]}"
}

# Fallback: dùng defaults mà không hỏi
select_agents_defaults() {
  get_default_agents
}

# Main entry point cho selection
resolve_agents() {
  local -n _out=$1  # nameref — array để nhận kết quả

  if [[ ${#SELECTED_AGENTS[@]} -gt 0 ]]; then
    # User đã pass --agents flag → dùng luôn
    _out=("${SELECTED_AGENTS[@]}")
    return
  fi

  if [[ "${SELECTED_AGENTS[0]:-}" == "all" ]]; then
    mapfile -t _out < <(get_agent_ids)
    return
  fi

  # Không có flag → try interactive
  if _ensure_gum 2>/dev/null; then
    mapfile -t _out < <(select_agents_interactive)
    if [[ ${#_out[@]} -eq 0 ]]; then
      log_warn "No agents selected. Using defaults."
      mapfile -t _out < <(select_agents_defaults)
    fi
  else
    log_warn "Running with default agents. Pass --agents to customize."
    mapfile -t _out < <(select_agents_defaults)
  fi
}
```

**`init.sh` — integrate selector:**

```bash
source "$SCRIPT_DIR/lib/selector.sh"
# ...

# Thay đoạn resolve agents hiện tại bằng:
resolve_agents SELECTED_AGENTS
```

### 3.4 UX Flow hoàn chỉnh

```
$ ctx-packer-init

▶ ctx-packer init
  ✓ Target: /home/user/my-project

  ━━ Select agents ━━
  ┌─ Select AI agents to configure ─────────────────┐
  │  ● agents_md   AGENTS.md (Universal)  (default) │
  │  ● claude      Claude Code            (default) │
  │  ● cursor      Cursor                 (default) │
  │  ● windsurf    Windsurf               (default) │
  │  ○ trae        TRAE                             │
  │  ○ codex       OpenAI Codex                     │
  │  ○ copilot     GitHub Copilot                   │
  └─────────────────────────────────────────────────┘
  (space to toggle, enter to confirm)
```

### 3.5 Xử lý non-interactive (CI/CD)

Khi chạy trong CI (không có TTY), `gum` sẽ fail. Cần detect:

```bash
_is_interactive() {
  [[ -t 0 ]] && [[ -t 1 ]]  # stdin và stdout đều là TTY
}

# Trong _ensure_gum hoặc select flow:
if ! _is_interactive; then
  log_warn "Non-interactive mode detected. Using defaults (or --agents flag)."
  mapfile -t _out < <(select_agents_defaults)
  return
fi
```

---

## Phần 4 — Câu hỏi 2: Templates phải inject từ CLI thực, không hardcode

### 4.1 Hiện trạng — vấn đề cốt lõi

Tất cả 7 templates hardcode command strings:
```
ctx-packer index .
ctx-packer query "<query>"
ctx-packer pack . --query "<topic>"
ctx-packer status
ctx-packer vacuum
```

Nếu `query` đổi thành `search`, hoặc `pack` đổi thành `bundle`, phải update 7 file thủ công. Đây là **Single Source of Truth** problem.

### 4.2 Solution: Command Manifest + Template injection

**Bước 1 — `lib/commands.sh` là source of truth duy nhất:**

```bash
#!/usr/bin/env bash
# lib/commands.sh — Canonical command strings, sourced from CLI output
# Đây là single source of truth cho tất cả templates.
# Khi CLI thay đổi, chỉ update file này.

_discover_commands() {
  # Thử introspect từ CLI thực nếu đã install
  if command -v ctx-packer &>/dev/null; then
    # Parse help output để verify commands tồn tại
    local help_output
    help_output="$(ctx-packer --help 2>&1)"

    # Validate từng subcommand
    CMD_INDEX="index"
    CMD_QUERY="query"
    CMD_PACK="pack"
    CMD_STATUS="status"
    CMD_VACUUM="vacuum"

    # Nếu subcommand không có trong help → warn + dùng fallback
    for cmd in "$CMD_INDEX" "$CMD_QUERY" "$CMD_PACK" "$CMD_STATUS"; do
      if ! grep -q "^  $cmd\b" <<< "$help_output" 2>/dev/null; then
        log_warn "Command 'ctx-packer $cmd' not found in --help output."
        log_warn "Template may be outdated. Please update lib/commands.sh."
      fi
    done
  fi

  # Full command strings cho templates
  export CTX_CMD_INDEX="ctx-packer ${CMD_INDEX:=index} ."
  export CTX_CMD_QUERY='ctx-packer '"${CMD_QUERY:=query}"' "<query>"'
  export CTX_CMD_PACK='ctx-packer '"${CMD_PACK:=pack}"' . --query "<topic>"'
  export CTX_CMD_STATUS="ctx-packer ${CMD_STATUS:=status} ."
  export CTX_CMD_VACUUM="ctx-packer ${CMD_VACUUM:=vacuum}"
  export CTX_CMD_FULL_ZIP='ctx-packer '"${CMD_PACK:=pack}"' . --query "<topic>" --format zip'
  export CTX_CMD_FULL_XML='ctx-packer '"${CMD_PACK:=pack}"' . --query "<topic>" --format xml'
}
```

**Bước 2 — `_render_template` inject thêm CMD vars:**

```bash
# lib/core.sh
_render_template() {
  local tpl="$SCRIPT_DIR/../templates/$1"
  [[ -f "$tpl" ]] || { log_error "Template not found: $tpl"; return 1; }

  export CTX_PACKER_VERSION="$(ctx-packer --version 2>/dev/null | head -1 || echo 'latest')"
  export CTX_DATE="$(date +%Y-%m-%d)"
  export CTX_TARGET_NAME="$(basename "$CTX_TARGET")"

  # CMD vars đã được export bởi _discover_commands
  envsubst '
    ${CTX_DATE}
    ${CTX_PACKER_VERSION}
    ${CTX_TARGET_NAME}
    ${CTX_CMD_INDEX}
    ${CTX_CMD_QUERY}
    ${CTX_CMD_PACK}
    ${CTX_CMD_STATUS}
    ${CTX_CMD_VACUUM}
    ${CTX_CMD_FULL_ZIP}
    ${CTX_CMD_FULL_XML}
  ' < "$tpl"
}
```

**Bước 3 — Templates dùng variables thay vì hardcode:**

```markdown
# Ví dụ templates/claude/SKILL.md.tpl (sau khi refactor)

## Commands

```bash
${CTX_CMD_INDEX}          # Build/update index
${CTX_CMD_QUERY}          # Search indexed codebase
${CTX_CMD_FULL_ZIP}       # Full workflow + ZIP output
${CTX_CMD_STATUS}         # Show index status
${CTX_CMD_VACUUM}         # Optimize database
```
```

**Bước 4 — Init sequence:**

```bash
# init.sh
source "$SCRIPT_DIR/lib/commands.sh"
# ...
install_ctx_packer       # install trước
_discover_commands       # discover sau khi đã install
```

### 4.3 Benefit

Khi `ctx-packer query` đổi thành `ctx-packer search`:
- Chỉ cần sửa `lib/commands.sh`: `CMD_QUERY="search"`
- Tất cả 7 templates tự động dùng string mới
- Không cần grep-and-replace qua templates

Khi CLI thêm flag mới:
- Cập nhật `CTX_CMD_FULL_ZIP` trong `commands.sh`
- Ngay lập tức reflect trong tất cả templates

---

## Phần 5 — Remaining Issues chưa fix

### Issue 8 — IFS parsing fragile trong `_registry.sh`

```bash
# HIỆN TẠI — vỡ nếu description có dấu ':'
IFS=: read -r _ _ desc _ <<< "$e"
```

**Fix — dùng index-based substring extraction:**

```bash
get_agent_display() {
  local id="$1"
  for e in "${AGENT_REGISTRY[@]}"; do
    [[ "$e" =~ ^${id}: ]] || continue
    # Lấy field thứ 2: giữa dấu : đầu và : thứ 3
    local rest="${e#*:}"          # bỏ "id:"
    echo "${rest%%:*}"            # lấy đến : tiếp theo
    return
  done
  echo "$id"
}

get_agent_desc() {
  local id="$1"
  for e in "${AGENT_REGISTRY[@]}"; do
    [[ "$e" =~ ^${id}: ]] || continue
    local rest="${e#*:}"          # bỏ "id:"
    rest="${rest#*:}"             # bỏ "name:"
    echo "${rest%:*}"             # lấy đến : cuối cùng (bỏ default field)
    return
  done
}
```

### Issue 9 — `2>&1` trong `index.sh` nuốt stderr

```bash
# HIỆN TẠI — error messages từ ctx-packer không phân biệt được
if timeout "$timeout_seconds" ctx-packer index "$target" 2>&1; then

# FIX — giữ stderr riêng, chỉ redirect khi cần
if timeout "$timeout_seconds" ctx-packer index "$target"; then
    log_ok "Index built successfully"
else
    local exit_code=$?
    # Stderr đã hiển thị trực tiếp cho user
    if [[ $exit_code -eq 124 ]]; then
      log_warn "Index timed out after ${timeout_seconds}s"
    else
      log_warn "Index exited with code $exit_code. Check output above."
    fi
fi
```

---

## Phần 6 — Implementation Roadmap

```
Priority 1 — Critical bugs (fix trước khi release):
├── Bug A: _remove_section cross-platform + multi-paragraph  [core.sh]
├── Bug B: publish.sh bị bundle                              [pyproject.toml]
└── Bug C: package_data không preserve +x                   [init_cli.py]

Priority 2 — Remaining issues:
├── Issue 8: IFS parsing fragile                             [_registry.sh]
└── Issue 9: stderr merge vào stdout                        [index.sh]

Priority 3 — Feature: gum interactive selection
├── lib/selector.sh (new file)
├── lib/core.sh (_has_gum, _ensure_gum, _is_interactive)
└── init.sh (integrate resolve_agents)

Priority 4 — Feature: Template injection từ CLI
├── lib/commands.sh (new file — source of truth)
├── lib/core.sh (_render_template mở rộng envsubst vars)
├── init.sh (_discover_commands sau install_ctx_packer)
└── templates/**/*.tpl (thay hardcode bằng ${CTX_CMD_*})
```

### File changes tổng cộng

| File | Change |
|---|---|
| `pyproject.toml` | Whitelist scripts, exclude publish.sh |
| `scripts/init_cli.py` | `chmod +x` trước khi gọi bash |
| `scripts/lib/core.sh` | Fix `_remove_section` (awk), thêm gum utils, mở rộng `_render_template` |
| `scripts/lib/commands.sh` | **New** — command manifest |
| `scripts/lib/selector.sh` | **New** — gum-first agent selector |
| `scripts/lib/index.sh` | Bỏ `2>&1` |
| `scripts/init.sh` | Source selector, gọi `resolve_agents`, gọi `_discover_commands` |
| `scripts/agents/_registry.sh` | Fix IFS parsing helpers |
| `templates/**/*.tpl` | Thay hardcode bằng `${CTX_CMD_*}` vars |

---

## Phần 7 — Quick Reference: gum `choose --no-limit` syntax

```bash
# Multi-select: space để toggle, enter để confirm
SELECTED=$(printf '%s\n' "claude" "cursor" "windsurf" "trae" | \
  gum choose \
    --no-limit \
    --header "Select agents:" \
    --cursor-prefix "[ ] " \
    --selected-prefix "[x] " \
    --unselected-prefix "[ ] "
)

# Pre-select items (dùng --selected với giá trị match item text)
SELECTED=$(gum choose \
  --no-limit \
  --selected="claude,cursor" \
  "claude" "cursor" "windsurf" "trae" "codex"
)

# Kết quả: mỗi dòng là 1 item được chọn
echo "$SELECTED"
# claude
# cursor

# Parse thành array
mapfile -t AGENTS <<< "$SELECTED"
```
