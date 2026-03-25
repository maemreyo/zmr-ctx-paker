# ws-ctx-engine Init — Enhanced Architecture Plan

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
│   ├── install.sh               # Install/upgrade ws-ctx-engine via pip/pipx
│   └── index.sh                 # Run ws-ctx-engine index (với timeout/error handling)
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
│   └── ws-ctx-engine.mdc.tpl
├── windsurf/
│   └── ws-ctx-engine.md.tpl
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
# wsctx-init — AI Agent Configuration Installer
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
log_header "ws-ctx-engine init"
install_ws_ctx_engine          # lib/install.sh
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
# Target: .claude/skills/ws-ctx-engine/SKILL.md
#         .claude/CLAUDE.md (append nếu chưa có section)

install_claude() {
  local skill_dir="$CTX_TARGET/.claude/skills/ws-ctx-engine"
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

  # Append ws-ctx-engine section vào CLAUDE.md nếu chưa có
  if ! grep -q "ws-ctx-engine" "$claude_md" 2>/dev/null; then
    mkdir -p "$(dirname "$claude_md")"
    echo "" >> "$claude_md"
    _render_template "claude/CLAUDE_append.md.tpl" >> "$claude_md"
    log_ok "Updated $claude_md (appended ws-ctx-engine section)"
  else
    log_skip "$claude_md (ws-ctx-engine section already present)"
  fi
}
```

**Template `.claude/skills/ws-ctx-engine/SKILL.md`:**

```markdown
---
name: ws-ctx-engine
description: >
  Use when user wants to search, index, or pack codebase context for AI.
  Triggers on: "find files about X", "pack context for X", "index the codebase",
  "search codebase for Y", "what files handle Z".
user-invocable: true
---

# ws-ctx-engine Skill

ws-ctx-engine indexes your codebase and builds context bundles for AI agents.

## Commands

```bash
ws-ctx-engine index .          # Build/update index for current dir
ws-ctx-engine search <query>   # Search indexed codebase
ws-ctx-engine pack <path>      # Pack context from path into bundle
ws-ctx-engine status           # Show index status
```

## When to use

- User asks to find files related to a topic
- User wants to understand codebase structure before a change
- User asks "what handles authentication?" or similar navigation queries
- Before making cross-cutting changes to multiple files

## Workflow

1. Run `ws-ctx-engine index .` if index is stale (check with `ws-ctx-engine status`)
2. Run `ws-ctx-engine search "<query>"` to find relevant files
3. Use results to inform your next action
```

### 5.2 `agents/cursor.sh` — Cursor

```bash
install_cursor() {
  local rules_dir="$CTX_TARGET/.cursor/rules"
  local rules_file="$rules_dir/ws-ctx-engine.mdc"

  if _should_write "$rules_file"; then
    mkdir -p "$rules_dir"
    _render_template "cursor/ws-ctx-engine.mdc.tpl" > "$rules_file"
    log_ok "Created $rules_file"
  else
    log_skip "$rules_file"
  fi
}
```

**Template `.cursor/rules/ws-ctx-engine.mdc`:**
```markdown
---
description: >
  Guide for using ws-ctx-engine to index and search the codebase.
  Apply when navigating unfamiliar code or before cross-file edits.
alwaysApply: false
---

# ws-ctx-engine — Codebase Navigator

Before exploring unfamiliar areas of the codebase, use ws-ctx-engine:

```bash
ws-ctx-engine index .           # Build index (run once or after major changes)
ws-ctx-engine search "<topic>"  # Find relevant files by topic
ws-ctx-engine status            # Check if index is fresh
```

Prefer ws-ctx-engine search over manual grep/glob for semantic queries.
```

### 5.3 `agents/windsurf.sh` — Windsurf / Cascade

```bash
install_windsurf() {
  local rules_dir="$CTX_TARGET/.windsurf/rules"
  local rules_file="$rules_dir/ws-ctx-engine.md"

  if _should_write "$rules_file"; then
    mkdir -p "$rules_dir"
    _render_template "windsurf/ws-ctx-engine.md.tpl" > "$rules_file"
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
  if [[ -f "$rules_file" ]] && ! grep -q "ws-ctx-engine" "$rules_file"; then
    echo "" >> "$rules_file"
    _render_template "trae/.rules.tpl" >> "$rules_file"
    log_ok "Appended ws-ctx-engine section to $rules_file"
  elif [[ ! -f "$rules_file" ]]; then
    _render_template "trae/.rules.tpl" > "$rules_file"
    log_ok "Created $rules_file"
  else
    log_skip "$rules_file (ws-ctx-engine already present)"
  fi
}
```

**Note quan trọng**: TRAE dùng `.rules` ở project root, không phải `.trae/rules/`. Logic phải **append** nếu file đã có, không overwrite.

### 5.5 `agents/agents_md.sh` — Universal AGENTS.md

```bash
install_agents_md() {
  local agents_file="$CTX_TARGET/AGENTS.md"

  if [[ -f "$agents_file" ]] && ! grep -q "ws-ctx-engine" "$agents_file"; then
    echo "" >> "$agents_file"
    _render_template "agents_md/AGENTS.md.tpl" >> "$agents_file"
    log_ok "Appended ws-ctx-engine to $agents_file"
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
  # Inject common vars: CTX_ENGINE_VERSION, CTX_DATE, CTX_TARGET_NAME
  CTX_ENGINE_VERSION="$(ws-ctx-engine --version 2>/dev/null | head -1 || echo 'latest')"
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

Usage: wsctx-init [options]

Options:
  --path <dir>       Target project path (default: current dir)
  --agents <list>    Comma-separated agent IDs, or 'all'
  --skip-index       Skip running ws-ctx-engine index after setup
  --force            Overwrite existing config files
  --list-agents      Show all supported agents
  -h, --help         Show this help

Examples:
  wsctx-init
  wsctx-init --agents claude,cursor,agents_md
  wsctx-init --agents all --force
  wsctx-init --path ~/my-project --skip-index

EOF
}
```

---

## 7. Trả lời các câu hỏi trong plan gốc

| Câu hỏi | Quyết định | Lý do |
|---|---|---|
| **Tên script** | `init.sh` trong `scripts/`, expose thêm `ws-ctx-engine init` CLI command | Consistent với convention |
| **Default agents** | `agents_md`, `claude`, `cursor`, `windsurf` | 4 agents phổ biến nhất; TRAE/Codex/Copilot là opt-in |
| **Overwrite behavior** | Default **skip**, `--force` để overwrite | An toàn, idempotent |
| **CLI integration** | Có, thêm `ws-ctx-engine init` vào `pyproject.toml` | Better UX, không cần nhớ đường dẫn script |
| **Qoder support** | Thêm vào registry khi research xong format | 1 dòng registry + 1 adapter file |

---

## 8. Implementation Steps (Updated)

| Step | File | Mô tả |
|---|---|---|
| 1 | `scripts/agents/_registry.sh` | Agent registry — làm đầu tiên |
| 2 | `scripts/lib/core.sh` | Logging, template render, helpers |
| 3 | `scripts/lib/install.sh` | pip/pipx install ws-ctx-engine |
| 4 | `scripts/lib/index.sh` | ws-ctx-engine index runner |
| 5 | `scripts/init.sh` | Thin orchestrator |
| 6 | `templates/agents_md/AGENTS.md.tpl` | Universal template |
| 7 | `templates/claude/SKILL.md.tpl` | Claude Code template |
| 8 | `templates/claude/CLAUDE_append.md.tpl` | CLAUDE.md snippet |
| 9 | `templates/cursor/ws-ctx-engine.mdc.tpl` | Cursor template |
| 10 | `templates/windsurf/ws-ctx-engine.md.tpl` | Windsurf template |
| 11 | `templates/trae/.rules.tpl` | TRAE template |
| 12 | `scripts/agents/agents_md.sh` | Universal adapter |
| 13 | `scripts/agents/claude.sh` | Claude adapter |
| 14 | `scripts/agents/cursor.sh` | Cursor adapter |
| 15 | `scripts/agents/windsurf.sh` | Windsurf adapter |
| 16 | `scripts/agents/trae.sh` | TRAE adapter |
| 17 | `pyproject.toml` | Add `ws-ctx-engine init` CLI entry point |
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
ws-ctx-engine = "ws_ctx_engine.cli:main"
wsctx-init = "ws_ctx_engine.init_cli:main"  # NEW
```

Hoặc nếu muốn subcommand:
```bash
ws-ctx-engine init                    # = ./scripts/init.sh
ws-ctx-engine init --agents claude    # selective
ws-ctx-engine init --list-agents      # list
```

Python wrapper `ws_ctx_engine/init_cli.py` chỉ cần gọi `scripts/init.sh` via `subprocess`, hoặc re-implement logic bằng Python nếu muốn cross-platform.

---

## 11. Sơ đồ kiến trúc

```
wsctx-init
       │
       ▼
  scripts/init.sh          ← Thin orchestrator (parse args only)
       │
       ├── lib/core.sh      ← Logging, _should_write, _render_template
       ├── lib/install.sh   ← pip install ws-ctx-engine
       ├── lib/index.sh     ← ws-ctx-engine index runner
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
         .claude/skills/ws-ctx-engine/SKILL.md
         .claude/CLAUDE.md (appended)
         .cursor/rules/ws-ctx-engine.mdc
         .windsurf/rules/ws-ctx-engine.md
         .rules (appended)
         .agents/skills/ws-ctx-engine/SKILL.md
         .github/copilot-instructions.md
         AGENTS.md
```

---

## 12. Edge cases cần handle

| Case | Xử lý |
|---|---|
| `.rules` đã có content (TRAE) | **Append** section, không overwrite |
| `CLAUDE.md` đã tồn tại | **Append** ws-ctx-engine section nếu chưa có |
| `AGENTS.md` đã tồn tại | **Append** nếu chưa có `ws-ctx-engine` keyword |
| ws-ctx-engine chưa install | Auto-install, fail rõ ràng nếu pip không available |
| `--force` với append-only files | Xóa section cũ trước, append mới |
| Non-git directory | Warn nhưng vẫn tiếp tục |
| Permission denied | Fail fast với message rõ ràng |
