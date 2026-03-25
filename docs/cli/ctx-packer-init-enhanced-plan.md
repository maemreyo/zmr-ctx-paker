# ctx-packer Init — Enhanced Architecture Plan

> Deep research + redesign với Modular/SoC, Plugin Registry, và multi-agent selector.

---

## 1. Bối cảnh & Research Insights

### 1.1 Thực trạng format của từng AI Agent (2025–2026)

| Agent | Config file | Format | Activation logic |
|---|---|---|---|
| **Claude Code** | `.claude/skills/<name>/SKILL.md` | YAML frontmatter + Markdown | `description` field → auto-invoke; hoặc `/skill-name` |
| **OpenAI Codex** | `.agents/skills/<name>/SKILL.md` | YAML frontmatter + Markdown | Tương tự Claude Code |
| **Cursor** | `.cursor/rules/<name>.mdc` | YAML frontmatter + Markdown | `alwaysApply`, `globs`, `description` |
| **Windsurf** | `.windsurf/rules/<name>.md` | Markdown (no strict frontmatter) | Always On / Model Decision / Glob |
| **TRAE** | `.rules` (project root) | Markdown (giống .cursorrules) | Always loaded |
| **GitHub Copilot** | `.github/copilot-instructions.md` | Plain Markdown | Always loaded |
| **AGENTS.md** (open standard) | `AGENTS.md` (project root) | Plain Markdown | Read by Codex, Copilot, Cursor, Jules, Amp, RooCode, v0... |

**Key finding**: AGENTS.md là open standard được Linux Foundation steward, hỗ trợ bởi hầu hết agents. Đây là "universal fallback" quan trọng nhất.

### 1.2 Vấn đề của plan gốc

- Script `init.sh` monolithic — thêm agent mới phải sửa file chính
- Không có template system — content lẫn với logic
- Thiếu registry pattern — không `--list-agents` được
- Thiếu Codex, Copilot, Gemini CLI support
- Câu hỏi "Overwrite behavior" và "Default agents" chưa có câu trả lời rõ ràng

---

## 2. Kiến trúc mới — Plugin Registry + SoC

### 2.1 Toàn bộ cấu trúc thư mục

```
scripts/
├── init.sh                      # Entry point (thin orchestrator, ~80 lines)
├── lib/
│   ├── core.sh                  # Logging, colors, path utils, skip logic
│   ├── install.sh               # Install/upgrade ctx-packer via pip/pipx
│   └── index.sh                 # Run ctx-packer index (với timeout/error handling)
└── agents/
    ├── _registry.sh             # Agent registry — source of truth
    ├── agents_md.sh             # ① AGENTS.md (universal)
    ├── claude.sh                # ② Claude Code
    ├── cursor.sh                # ③ Cursor
    ├── windsurf.sh              # ④ Windsurf / Cascade
    ├── trae.sh                  # ⑤ TRAE (ByteDance)
    ├── codex.sh                 # ⑥ OpenAI Codex
    └── copilot.sh               # ⑦ GitHub Copilot

templates/
├── agents_md/
│   └── AGENTS.md.tpl
├── claude/
│   ├── SKILL.md.tpl
│   └── CLAUDE_append.md.tpl    # Đoạn append vào CLAUDE.md có sẵn
├── cursor/
│   └── ctx-packer.mdc.tpl
├── windsurf/
│   └── ctx-packer.md.tpl
├── trae/
│   └── .rules.tpl               # Append vào .rules nếu đã có
├── codex/
│   └── SKILL.md.tpl
└── copilot/
    └── copilot-instructions.md.tpl
```

**Nguyên tắc SoC:**
- `init.sh` chỉ parse args + gọi handlers → không biết gì về từng agent
- Mỗi `agents/*.sh` chỉ biết về agent của mình
- `templates/` chứa content thuần túy, không có logic bash
- `lib/core.sh` chứa tất cả shared utilities

---

## 3. `scripts/agents/_registry.sh` — Plugin Registry

Đây là trái tim của kiến trúc. Thêm agent mới = thêm 1 dòng vào registry + tạo 1 file adapter.

```bash
# scripts/agents/_registry.sh
# ──────────────────────────────────────────────────────────
# AGENT REGISTRY — source of truth cho tất cả supported agents
# Format: "id:display_name:description:default_enabled"
# ──────────────────────────────────────────────────────────

AGENT_REGISTRY=(
  "agents_md:AGENTS.md (Universal):Open standard, works with Codex/Copilot/Jules/Amp/RooCode:true"
  "claude:Claude Code:Anthropic's terminal-based agentic coding tool:true"
  "cursor:Cursor:.cursor/rules/*.mdc format for Cursor IDE:true"
  "windsurf:Windsurf:Cascade rules in .windsurf/rules/:true"
  "trae:TRAE:.rules file for ByteDance TRAE IDE:false"
  "codex:OpenAI Codex:.agents/skills/ format for Codex CLI:false"
  "copilot:GitHub Copilot:.github/copilot-instructions.md:false"
)

# Helpers
get_agent_ids()        { for entry in "${AGENT_REGISTRY[@]}"; do echo "${entry%%:*}"; done; }
get_default_agents()   { for e in "${AGENT_REGISTRY[@]}"; do [[ "$e" == *":true" ]] && echo "${e%%:*}"; done; }
is_valid_agent()       { get_agent_ids | grep -qx "$1"; }
get_agent_display()    { for e in "${AGENT_REGISTRY[@]}"; do [[ "$e" =~ ^$1: ]] && { IFS=: read -r _ name _ _ <<< "$e"; echo "$name"; break; }; done; }
```

**Thêm agent mới** trong tương lai chỉ cần:
1. Thêm 1 dòng vào `AGENT_REGISTRY` trong `_registry.sh`
2. Tạo `scripts/agents/<id>.sh`
3. Tạo `templates/<id>/<file>.tpl`

Không cần chạm vào `init.sh` hay bất kỳ file khác.

---

## 4. `scripts/init.sh` — Thin Orchestrator

```bash
#!/usr/bin/env bash
# ctx-packer-init — AI Agent Configuration Installer
# Usage: ./scripts/init.sh [options]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/core.sh"
source "$SCRIPT_DIR/lib/install.sh"
source "$SCRIPT_DIR/lib/index.sh"
source "$SCRIPT_DIR/agents/_registry.sh"

# ── Defaults ────────────────────────────────────────────────
TARGET_PATH="$(pwd)"
SELECTED_AGENTS=()     # empty = use defaults from registry
SKIP_INDEX=false
FORCE=false

# ── Arg parsing ─────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --path)        TARGET_PATH="$2"; shift 2 ;;
    --agents)      IFS=',' read -ra SELECTED_AGENTS <<< "$2"; shift 2 ;;
    --skip-index)  SKIP_INDEX=true; shift ;;
    --force)       FORCE=true; shift ;;
    --list-agents) list_agents; exit 0 ;;
    --help|-h)     show_help; exit 0 ;;
    *)             log_error "Unknown option: $1"; show_help; exit 1 ;;
  esac
done

# ── Resolve agents ──────────────────────────────────────────
if [[ ${#SELECTED_AGENTS[@]} -eq 0 ]]; then
  mapfile -t SELECTED_AGENTS < <(get_default_agents)
elif [[ "${SELECTED_AGENTS[0]}" == "all" ]]; then
  mapfile -t SELECTED_AGENTS < <(get_agent_ids)
fi

# Validate
for agent_id in "${SELECTED_AGENTS[@]}"; do
  is_valid_agent "$agent_id" || { log_error "Unknown agent: '$agent_id'. Run --list-agents."; exit 1; }
done

# ── Main flow ────────────────────────────────────────────────
log_header "ctx-packer init"
install_ctx_packer          # lib/install.sh
export CTX_FORCE="$FORCE"
export CTX_TARGET="$TARGET_PATH"

for agent_id in "${SELECTED_AGENTS[@]}"; do
  log_section "$(get_agent_display "$agent_id")"
  source "$SCRIPT_DIR/agents/${agent_id}.sh"
  "install_${agent_id}"     # Convention: mỗi adapter expose hàm install_<id>()
done

[[ "$SKIP_INDEX" == false ]] && run_index "$TARGET_PATH"  # lib/index.sh

log_success "Done! $(echo "${SELECTED_AGENTS[@]}" | tr ' ' ',') configured."
```

---

## 5. Interface của từng Agent Adapter

Mỗi `scripts/agents/<id>.sh` phải implement 1 hàm duy nhất: `install_<id>()`.

### 5.1 `agents/claude.sh` — Claude Code

```bash
#!/usr/bin/env bash
# Claude Code adapter
# Target: .claude/skills/ctx-packer/SKILL.md
#         .claude/CLAUDE.md (append nếu chưa có section)

install_claude() {
  local skill_dir="$CTX_TARGET/.claude/skills/ctx-packer"
  local skill_file="$skill_dir/SKILL.md"
  local claude_md="$CTX_TARGET/.claude/CLAUDE.md"

  # SKILL.md
  if _should_write "$skill_file"; then
    mkdir -p "$skill_dir"
    _render_template "claude/SKILL.md.tpl" > "$skill_file"
    log_ok "Created $skill_file"
  else
    log_skip "$skill_file (use --force to overwrite)"
  fi

  # Append ctx-packer section vào CLAUDE.md nếu chưa có
  if ! grep -q "ctx-packer" "$claude_md" 2>/dev/null; then
    mkdir -p "$(dirname "$claude_md")"
    echo "" >> "$claude_md"
    _render_template "claude/CLAUDE_append.md.tpl" >> "$claude_md"
    log_ok "Updated $claude_md (appended ctx-packer section)"
  else
    log_skip "$claude_md (ctx-packer section already present)"
  fi
}
```

**Template `.claude/skills/ctx-packer/SKILL.md`:**

```markdown
---
name: ctx-packer
description: >
  Use when user wants to search, index, or pack codebase context for AI.
  Triggers on: "find files about X", "pack context for X", "index the codebase",
  "search codebase for Y", "what files handle Z".
user-invocable: true
---

# ctx-packer Skill

ctx-packer indexes your codebase and builds context bundles for AI agents.

## Commands

```bash
ctx-packer index .          # Build/update index for current dir
ctx-packer search <query>   # Search indexed codebase
ctx-packer pack <path>      # Pack context from path into bundle
ctx-packer status           # Show index status
```

## When to use

- User asks to find files related to a topic
- User wants to understand codebase structure before a change
- User asks "what handles authentication?" or similar navigation queries
- Before making cross-cutting changes to multiple files

## Workflow

1. Run `ctx-packer index .` if index is stale (check with `ctx-packer status`)
2. Run `ctx-packer search "<query>"` to find relevant files
3. Use results to inform your next action
```

### 5.2 `agents/cursor.sh` — Cursor

```bash
install_cursor() {
  local rules_dir="$CTX_TARGET/.cursor/rules"
  local rules_file="$rules_dir/ctx-packer.mdc"

  if _should_write "$rules_file"; then
    mkdir -p "$rules_dir"
    _render_template "cursor/ctx-packer.mdc.tpl" > "$rules_file"
    log_ok "Created $rules_file"
  else
    log_skip "$rules_file"
  fi
}
```

**Template `.cursor/rules/ctx-packer.mdc`:**
```markdown
---
description: >
  Guide for using ctx-packer to index and search the codebase.
  Apply when navigating unfamiliar code or before cross-file edits.
alwaysApply: false
---

# ctx-packer — Codebase Navigator

Before exploring unfamiliar areas of the codebase, use ctx-packer:

```bash
ctx-packer index .           # Build index (run once or after major changes)
ctx-packer search "<topic>"  # Find relevant files by topic
ctx-packer status            # Check if index is fresh
```

Prefer ctx-packer search over manual grep/glob for semantic queries.
```

### 5.3 `agents/windsurf.sh` — Windsurf / Cascade

```bash
install_windsurf() {
  local rules_dir="$CTX_TARGET/.windsurf/rules"
  local rules_file="$rules_dir/ctx-packer.md"

  if _should_write "$rules_file"; then
    mkdir -p "$rules_dir"
    _render_template "windsurf/ctx-packer.md.tpl" > "$rules_file"
    log_ok "Created $rules_file"
  else
    log_skip "$rules_file"
  fi
}
```

**Note về Windsurf**: File trong `.windsurf/rules/` là Markdown thuần. Windsurf có 4 activation modes (Always On, Model Decision, Glob, Manual) — nhưng khi tạo file bằng script thì Cascade tự detect từ filename. Nên template dùng headers rõ ràng.

### 5.4 `agents/trae.sh` — TRAE

```bash
install_trae() {
  local rules_file="$CTX_TARGET/.rules"

  # TRAE dùng .rules ở project root — có thể đã có content khác
  if [[ -f "$rules_file" ]] && ! grep -q "ctx-packer" "$rules_file"; then
    echo "" >> "$rules_file"
    _render_template "trae/.rules.tpl" >> "$rules_file"
    log_ok "Appended ctx-packer section to $rules_file"
  elif [[ ! -f "$rules_file" ]]; then
    _render_template "trae/.rules.tpl" > "$rules_file"
    log_ok "Created $rules_file"
  else
    log_skip "$rules_file (ctx-packer already present)"
  fi
}
```

**Note quan trọng**: TRAE dùng `.rules` ở project root, không phải `.trae/rules/`. Logic phải **append** nếu file đã có, không overwrite.

### 5.5 `agents/agents_md.sh` — Universal AGENTS.md

```bash
install_agents_md() {
  local agents_file="$CTX_TARGET/AGENTS.md"

  if [[ -f "$agents_file" ]] && ! grep -q "ctx-packer" "$agents_file"; then
    echo "" >> "$agents_file"
    _render_template "agents_md/AGENTS.md.tpl" >> "$agents_file"
    log_ok "Appended ctx-packer to $agents_file"
  elif [[ ! -f "$agents_file" ]]; then
    _render_template "agents_md/AGENTS.md.tpl" > "$agents_file"
    log_ok "Created $agents_file"
  else
    log_skip "$agents_file"
  fi
}
```

---

## 6. `lib/core.sh` — Shared Utilities

```bash
#!/usr/bin/env bash
# Shared utilities — logging, colors, skip logic, template rendering

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log_header()  { echo -e "\n${BOLD}${BLUE}▶ $*${NC}"; }
log_section() { echo -e "\n${CYAN}━━ $* ━━${NC}"; }
log_ok()      { echo -e "  ${GREEN}✓${NC} $*"; }
log_skip()    { echo -e "  ${YELLOW}○${NC} $*"; }
log_error()   { echo -e "  ${RED}✗${NC} $*" >&2; }
log_success() { echo -e "\n${GREEN}${BOLD}✔ $*${NC}"; }

# Should we write this file?
_should_write() {
  local file="$1"
  [[ ! -f "$file" ]] || [[ "${CTX_FORCE:-false}" == "true" ]]
}

# Render template (simple variable substitution)
_render_template() {
  local tpl="$SCRIPT_DIR/../templates/$1"
  [[ -f "$tpl" ]] || { log_error "Template not found: $tpl"; return 1; }
  # Inject common vars: CTX_PACKER_VERSION, CTX_DATE, CTX_TARGET_NAME
  CTX_PACKER_VERSION="$(ctx-packer --version 2>/dev/null | head -1 || echo 'latest')"
  CTX_DATE="$(date +%Y-%m-%d)"
  CTX_TARGET_NAME="$(basename "$CTX_TARGET")"
  envsubst < "$tpl"
}

# List all agents with descriptions
list_agents() {
  echo -e "\n${BOLD}Available agents:${NC}"
  for entry in "${AGENT_REGISTRY[@]}"; do
    IFS=: read -r id name desc default <<< "$entry"
    local marker="○"
    [[ "$default" == "true" ]] && marker="${GREEN}●${NC}"
    printf "  %b %-12s ${CYAN}%-18s${NC} %s\n" "$marker" "$id" "$name" "$desc"
  done
  echo -e "\n  ${GREEN}●${NC} = enabled by default, ○ = opt-in"
}

show_help() {
  cat <<EOF

Usage: ctx-packer-init [options]

Options:
  --path <dir>       Target project path (default: current dir)
  --agents <list>    Comma-separated agent IDs, or 'all'
  --skip-index       Skip running ctx-packer index after setup
  --force            Overwrite existing config files
  --list-agents      Show all supported agents
  -h, --help         Show this help

Examples:
  ctx-packer-init
  ctx-packer-init --agents claude,cursor,agents_md
  ctx-packer-init --agents all --force
  ctx-packer-init --path ~/my-project --skip-index

EOF
}
```

---

## 7. Trả lời các câu hỏi trong plan gốc

| Câu hỏi | Quyết định | Lý do |
|---|---|---|
| **Tên script** | `init.sh` trong `scripts/`, expose thêm `ctx-packer init` CLI command | Consistent với convention |
| **Default agents** | `agents_md`, `claude`, `cursor`, `windsurf` | 4 agents phổ biến nhất; TRAE/Codex/Copilot là opt-in |
| **Overwrite behavior** | Default **skip**, `--force` để overwrite | An toàn, idempotent |
| **CLI integration** | Có, thêm `ctx-packer init` vào `pyproject.toml` | Better UX, không cần nhớ đường dẫn script |
| **Qoder support** | Thêm vào registry khi research xong format | 1 dòng registry + 1 adapter file |

---

## 8. Implementation Steps (Updated)

| Step | File | Mô tả |
|---|---|---|
| 1 | `scripts/agents/_registry.sh` | Agent registry — làm đầu tiên |
| 2 | `scripts/lib/core.sh` | Logging, template render, helpers |
| 3 | `scripts/lib/install.sh` | pip/pipx install ctx-packer |
| 4 | `scripts/lib/index.sh` | ctx-packer index runner |
| 5 | `scripts/init.sh` | Thin orchestrator |
| 6 | `templates/agents_md/AGENTS.md.tpl` | Universal template |
| 7 | `templates/claude/SKILL.md.tpl` | Claude Code template |
| 8 | `templates/claude/CLAUDE_append.md.tpl` | CLAUDE.md snippet |
| 9 | `templates/cursor/ctx-packer.mdc.tpl` | Cursor template |
| 10 | `templates/windsurf/ctx-packer.md.tpl` | Windsurf template |
| 11 | `templates/trae/.rules.tpl` | TRAE template |
| 12 | `scripts/agents/agents_md.sh` | Universal adapter |
| 13 | `scripts/agents/claude.sh` | Claude adapter |
| 14 | `scripts/agents/cursor.sh` | Cursor adapter |
| 15 | `scripts/agents/windsurf.sh` | Windsurf adapter |
| 16 | `scripts/agents/trae.sh` | TRAE adapter |
| 17 | `pyproject.toml` | Add `ctx-packer init` CLI entry point |
| 18 | Test | `./scripts/init.sh --list-agents`, then full run |

---

## 9. Thêm agent mới trong tương lai

Ví dụ thêm **Gemini CLI** (Google):

```bash
# 1. Thêm vào _registry.sh
"gemini:Gemini CLI:Google Gemini CLI agent instructions:false"

# 2. Tạo scripts/agents/gemini.sh
install_gemini() {
  local file="$CTX_TARGET/GEMINI.md"
  _should_write "$file" || { log_skip "$file"; return; }
  _render_template "gemini/GEMINI.md.tpl" > "$file"
  log_ok "Created $file"
}

# 3. Tạo templates/gemini/GEMINI.md.tpl
# ... content here
```

**Tổng cộng: 3 bước, không chạm vào init.sh hay bất kỳ file có sẵn nào.**

---

## 10. `pyproject.toml` — CLI Integration

```toml
[project.scripts]
ctx-packer = "ctx_packer.cli:main"
ctx-packer-init = "ctx_packer.init_cli:main"  # NEW
```

Hoặc nếu muốn subcommand:
```bash
ctx-packer init                    # = ./scripts/init.sh
ctx-packer init --agents claude    # selective
ctx-packer init --list-agents      # list
```

Python wrapper `ctx_packer/init_cli.py` chỉ cần gọi `scripts/init.sh` via `subprocess`, hoặc re-implement logic bằng Python nếu muốn cross-platform.

---

## 11. Sơ đồ kiến trúc

```
ctx-packer-init
       │
       ▼
  scripts/init.sh          ← Thin orchestrator (parse args only)
       │
       ├── lib/core.sh      ← Logging, _should_write, _render_template
       ├── lib/install.sh   ← pip install ctx-packer
       ├── lib/index.sh     ← ctx-packer index runner
       │
       ├── agents/_registry.sh    ← Plugin registry (add agent = 1 line)
       │
       ├── agents/agents_md.sh    ① install_agents_md()
       ├── agents/claude.sh       ② install_claude()
       ├── agents/cursor.sh       ③ install_cursor()
       ├── agents/windsurf.sh     ④ install_windsurf()
       ├── agents/trae.sh         ⑤ install_trae()
       ├── agents/codex.sh        ⑥ install_codex()
       └── agents/copilot.sh      ⑦ install_copilot()
              │
              ▼
       templates/<agent>/      ← Content thuần túy (không có logic)
              │
              ▼
       Project files created:
         .claude/skills/ctx-packer/SKILL.md
         .claude/CLAUDE.md (appended)
         .cursor/rules/ctx-packer.mdc
         .windsurf/rules/ctx-packer.md
         .rules (appended)
         .agents/skills/ctx-packer/SKILL.md
         .github/copilot-instructions.md
         AGENTS.md
```

---

## 12. Edge cases cần handle

| Case | Xử lý |
|---|---|
| `.rules` đã có content (TRAE) | **Append** section, không overwrite |
| `CLAUDE.md` đã tồn tại | **Append** ctx-packer section nếu chưa có |
| `AGENTS.md` đã tồn tại | **Append** nếu chưa có `ctx-packer` keyword |
| ctx-packer chưa install | Auto-install, fail rõ ràng nếu pip không available |
| `--force` với append-only files | Xóa section cũ trước, append mới |
| Non-git directory | Warn nhưng vẫn tiếp tục |
| Permission denied | Fail fast với message rõ ràng |
