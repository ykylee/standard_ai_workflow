#!/usr/bin/env bash
# 하네스 중립 프론트엔드 툴셋 — 프로젝트 범위 설치. 사용 가이드: docs/FRONTEND_TOOLKIT.md
#
#   setup.sh [--harness claude,codex] [--no-hooks] [--local] [--dry-run]
#
# 대상 프로젝트의 뿌리에서 돌린다. 하는 일:
#   1. DESIGN.md 가 없으면 템플릿을 놓고, @google/design.md 로 lint 한다 (오류면 멈춘다)
#   2. impeccable 스킬(+ 디자인 hook)을 프로젝트 범위로 설치한다
#   3. 브라우저 확인 MCP(chrome-devtools-mcp)를 연결한다 — Claude Code 는 .mcp.json 에 병합, 그 밖은 명령만 보인다
# --local: 이 클론에만 둔다 — 설치물은 .git/info/exclude 에 적고, Claude Code MCP 는 커밋된 .mcp.json 대신
#          `claude mcp add -s local` 로 넣는다. 도구를 저장소 기여자 모두에게 강요하지 않을 때.
# 사용자 범위 설정(~/.claude · ~/.codex)은 쓰지 않는다 (--local 의 Claude MCP 는 ~/.claude.json 의 이 프로젝트 칸에만). 판은 아래에 고정한다 — 올릴 때는 가이드 §7 순서로.
set -euo pipefail

IMPECCABLE_VERSION=4.11.0
DESIGN_MD_VERSION=0.4.0
CHROME_DEVTOOLS_MCP_VERSION=1.14.0

HARNESS=claude,codex
HOOKS=1
DRY=0
LOCAL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --harness) HARNESS="$2"; shift 2 ;;
    --harness=*) HARNESS="${1#*=}"; shift ;;
    --no-hooks) HOOKS=0; shift ;;
    --dry-run) DRY=1; shift ;;
    --local) LOCAL=1; shift ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "setup.sh: 모르는 인자 $1" >&2; exit 2 ;;
  esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export DO_NOT_TRACK=1 DISABLE_TELEMETRY=1   # impeccable · skills CLI 의 익명 사용 기록을 끈다

run() { echo "+ $*"; if [ "$DRY" = 0 ]; then "$@"; fi; }

node_major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
if [ "$node_major" -lt 20 ]; then
  echo "setup.sh: Node.js 20 이상이 필요하다 (지금: $(node -v 2>/dev/null || echo 없음))" >&2
  exit 1
fi

# 1. DESIGN.md ------------------------------------------------------------------
if [ ! -f DESIGN.md ]; then
  run cp "$HERE/DESIGN.template.md" DESIGN.md
  echo "  DESIGN.md 를 템플릿으로 놓았다 — 토큰과 글을 이 제품에 맞게 고친다"
fi
if [ "$DRY" = 0 ]; then
  if ! npx -y "@google/design.md@${DESIGN_MD_VERSION}" lint DESIGN.md > .design-lint.json; then
    echo "setup.sh: DESIGN.md lint 오류 — .design-lint.json 을 본다" >&2
    exit 1
  fi
  python3 -c "import json;s=json.load(open('.design-lint.json'))['summary'];print(f\"  DESIGN.md lint: 오류 {s['errors']} · 경고 {s['warnings']}\")"
  rm -f .design-lint.json
fi

# 2. 리뷰 · 감각 스킬 (impeccable) ---------------------------------------------------
providers="$HARNESS"
hook_flag=()
[ "$HOOKS" = 1 ] || hook_flag=(--no-hooks)
run npx -y "impeccable@${IMPECCABLE_VERSION}" install -y "--providers=${providers}" --scope=project "${hook_flag[@]}"
echo "  주의: 프로젝트 범위여도 엔진은 ~/.impeccable/ 에, Chrome 네이티브 메시징 호스트는"
echo "        ~/.config/google-chrome/NativeMessagingHosts/style.impeccable.browser.json 에 들어간다 (가이드 §6)"
if [ "$LOCAL" = 1 ]; then
  exclude="$(git rev-parse --git-path info/exclude 2>/dev/null || true)"
  if [ -z "$exclude" ]; then
    echo "setup.sh: --local 은 git 저장소 안에서만 — 설치물을 숨길 곳이 없다" >&2
    exit 1
  fi
  for pat in /.claude/skills/impeccable/ "/.claude/agents/impeccable-*.md" /.agents/skills/impeccable/ /.codex/skills/impeccable/ /.cursor/skills/impeccable/ /.gemini/skills/impeccable/; do
    if [ "$DRY" = 0 ]; then
      mkdir -p "$(dirname "$exclude")"; touch "$exclude"
      grep -qxF "$pat" "$exclude" || echo "$pat" >> "$exclude"
    fi
  done
  echo "+ 설치물 경로를 $exclude 에 적었다 (커밋되지 않는다)"
fi

# 3. 브라우저 확인 MCP --------------------------------------------------------------
cdt_args=(-y "chrome-devtools-mcp@${CHROME_DEVTOOLS_MCP_VERSION}" --headless --isolated --no-usage-statistics)
IFS=',' read -r -a hs <<< "$HARNESS"
for h in "${hs[@]}"; do
  case "$h" in
    claude)
      if [ "$LOCAL" = 1 ]; then
        if ! command -v claude >/dev/null; then
          echo "  Claude Code: claude 명령이 없다 — 손으로: claude mcp add -s local chrome-devtools -- npx ${cdt_args[*]}"
        elif claude mcp get chrome-devtools >/dev/null 2>&1; then
          echo "  Claude Code: chrome-devtools 가 이미 있다 — 건드리지 않는다 (claude mcp get chrome-devtools)"
        else
          run claude mcp add -s local chrome-devtools -- npx "${cdt_args[@]}"
        fi
        continue
      fi
      echo "+ .mcp.json 에 chrome-devtools 병합"
      if [ "$DRY" = 0 ]; then
        python3 - "${cdt_args[@]}" <<'PY'
import json, pathlib, sys
p = pathlib.Path(".mcp.json")
data = json.loads(p.read_text(encoding="utf-8")) if p.exists() and p.read_text(encoding="utf-8").strip() else {}
servers = data.setdefault("mcpServers", {})
servers["chrome-devtools"] = {"type": "stdio", "command": "npx", "args": sys.argv[1:]}
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
      fi
      ;;
    codex)
      echo "  Codex: 프로젝트의 .codex/ 설정은 신뢰한 프로젝트에서만 읽힌다. 실행마다 붙이려면:"
      echo "    codex exec \\"
      echo "      -c 'mcp_servers.chrome-devtools.command=\"npx\"' \\"
      printf "      -c 'mcp_servers.chrome-devtools.args=[%s]' \\\\\n" "$(printf '"%s",' "${cdt_args[@]}" | sed 's/,$//')"
      echo "      -c 'mcp_servers.chrome-devtools.default_tools_approval_mode=\"approve\"' \"<과제>\""
      echo "    (늘 붙이려면 사용자 범위: codex mcp add chrome-devtools -- npx ${cdt_args[*]})"
      if [ "$HOOKS" = 1 ]; then echo "  Codex 디자인 hook 은 /hooks 에서 승인해야 돈다 (codex exec 는 --trust 필요)"; fi
      ;;
    *)
      echo "  $h: MCP 연결은 그 하네스의 설정 방식으로 — 명령: npx ${cdt_args[*]}"
      ;;
  esac
done

echo
echo "끝. 다음: 하네스를 다시 열고 '/impeccable init' (Codex 는 \$impeccable init) → 가이드 §4 작업 순서"
