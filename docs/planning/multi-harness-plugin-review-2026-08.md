# 멀티 하네스 공유 플러그인 형태 검토

- 문서 목적: 하나의 플러그인 아티팩트를 **여러 하네스가 공유**할 수 있는지 판정하고 아키텍처를 권고한다 (TASK-2026-08-12-main-012, 사용자 지시 — [플러그인 검토](./plugin-distribution-review-2026-08.md) 의 후속).
- 범위: 하네스별 확장 포맷 (2026-08 공식 문서 실사) + 개방 표준 (Agent Skills / Agent Plugins 1.0 / MCP 패키징) + 권고
- 대상 독자: maintainer, 배포 정책 소유자
- 상태: 검토 완료 — 권고안 제시 (구현은 후속 task)
- 최종 수정일: 2026-08-20
- 관련 문서: [plugin-distribution-review-2026-08.md](./plugin-distribution-review-2026-08.md), [cli-distribution-review-2026-08.md](./cli-distribution-review-2026-08.md)

## 1. 판정 요약

**"하나의 아티팩트를 전 하네스가 무변환으로 읽는" 표준이 부분적으로 이미 존재한다:**

| 공유 층 | 표준 | 무변환으로 읽는 하네스 (2026-08) |
|---|---|---|
| **스킬** | Agent Skills (`SKILL.md`, agentskills.io — AAIF governance) | ~40개 제품 채택. 특히 `.agents/skills/` 디렉터리는 **Codex·OpenCode·goose 가 공통으로 읽고**, OpenCode·goose 는 `.claude/skills/` 도 읽음 |
| **스킬+MCP 패키지** | **Agent Plugins 1.0** (`plugin.json` + `skills/` + `mcp.json`, agent-plugins.org — 2026-08-06 출범, Amazon·Cursor·Microsoft·OpenAI·Vercel·Google) | VS Code / Cursor / GitHub Copilot / ChatGPT·Codex / Kiro. **Claude Code·Gemini CLI·goose·OpenCode 는 아직 미합류** |
| **도구** | MCP (`mcpServers` JSON 스키마) | 사실상 전 하네스 — 우리 mcp.py 가 이미 7개 방언으로 emit 중 |

**여전히 하네스별 어댑터가 필요한 층**: manifest (Claude `.claude-plugin/plugin.json` /
Gemini `gemini-extension.json` / goose `config.yaml` / OpenCode `opencode.json`+JS) 와
**hooks·commands·상시 컨텍스트** — Agent Plugins v1 이 명시적으로 제외한 영역이고
포맷 자체가 갈린다 (commands: Claude md vs Gemini TOML).

**결론: 가능하다 — "공유 payload + 하네스별 얇은 manifest" 형태로.** 그리고 이것은
이 저장소가 이미 쓰는 "정본 하나 + 하네스별 파생본" 아키텍처의 플러그인 판이다.

## 2. 하네스별 확장 포맷 실사 (요지)

- **Gemini CLI extensions** — `gemini-extension.json` 하나로 context 파일(GEMINI.md!) +
  `commands/`(TOML) + MCP + `hooks/` + `agents/` + **`skills/`** 전부 번들.
  `gemini extensions install <github url>` + auto-update. **우리 요구 컴포넌트를
  전부 담는 유일한 타 하네스 포맷** — 상시 컨텍스트 주입도 지원 (Claude Code 플러그인의
  핵심 갭이 Gemini 에는 없음).
- **OpenCode** — plugin 은 JS 모듈 (manifest 없음), 스킬은 네이티브
  (`.opencode/skills/` + `.claude/skills/` + `.agents/skills/` 모두 읽음).
- **Codex CLI** — 스킬이 원자 단위 (`.agents/skills/` 탐색 체인 + `agents/openai.yaml`
  로 MCP 의존 선언). ChatGPT·Codex 는 Agent Plugins 1.0 클라이언트.
- **goose** — extension = MCP 서버 그 자체 (`config.yaml`). Agent Skills 채택
  (`.goose/skills/`, `.agents/skills/`, `~/.claude/skills/`).
- **MCPB (.mcpb)** — 로컬 MCP 서버 원클릭 아티팩트이나 지원 클라이언트가 좁아
  (Claude 계열 중심) cross-harness 범용으로는 미달.

## 3. 권고 아키텍처 — 공유 payload 의 물리 배치를 Agent Plugins 1.0 으로

```
plugin/                          # ← 정본에서 렌더러가 생성 (손 편집 금지)
├── plugin.json                  # Agent Plugins 1.0 manifest (공유 정본)
├── skills/                      # agentskills.io 스펙 SKILL.md (공유 정본)
│   ├── session-start/SKILL.md   #   §11 명령·계약은 render_memory_update_section 파생
│   ├── backlog-update/SKILL.md
│   └── doc-sync/SKILL.md
├── mcp.json                     # Agent Plugins 스키마 (read-only bundle; write 는 opt-in 문서)
└── adapters/                    # 하네스별 얇은 manifest (전부 payload 를 참조)
    ├── claude-code/.claude-plugin/plugin.json   (+ marketplace.json)
    ├── gemini-cli/gemini-extension.json         (+ GEMINI.md 컨텍스트 — Gemini 는 상시 주입 가능)
    ├── goose/config-snippet.yaml
    └── opencode/opencode-snippet.json
```

- **payload 두 축 (skills / mcp.json) 은 표준 스키마라 어댑터가 정말 얇다** — 대부분
  경로 참조와 이름 필드뿐. Claude Code·Gemini·goose 가 Agent Plugins 에 합류하는
  순간 해당 어댑터를 지울 수 있는 위치다 (Google 은 확대 공언).
- 스킬 이중 마운트 활용: `.agents/skills/` 로 심으면 Codex·OpenCode·goose 3개가
  **어댑터 없이** 즉시 읽는다 — bootstrap 의 스킬 emit 위치를 하네스별 dot-dir 에서
  `.agents/skills/` 중심으로 수렴하는 후속 검토 가치.
- 기존 자산 재사용: `export_harness_package.py` (하네스별 zip 6종) 가 이 구조의
  원형 — payload/어댑터 분리로 일반화한다.

## 4. 이행 경로 (앞선 검토의 Phase A~C 를 대체·확장)

1. **Phase A′**: `render_agent_plugin()` — 공유 payload (plugin.json + skills/ +
   mcp.json) 를 정본에서 생성 + `check_standard_single_source` 계열 검사 확장.
   스킬 본문의 §11 명령·계약은 `render_memory_update_section` 파생 (손 사본 금지).
2. **Phase B′**: 하네스 어댑터 4장 (claude-code / gemini-cli / goose / opencode) —
   각각 payload 참조만. Claude marketplace.json + Gemini extensions install 경로 문서화.
3. **Phase C′ (실측 게이트)**: ① Claude Code SessionStart hook 규칙 주입 실효
   ② Gemini extension 의 GEMINI.md 상시 주입 실측 (성립하면 Gemini 채널이 규칙
   주입까지 완결) ③ `.agents/skills/` 를 Claude Code 가 읽는지 (미확인) ④ `wk`
   부재 시 graceful.
4. **미결 (표준 밖)**: hooks·commands 는 하네스별 생성 유지 — Agent Plugins v2 가
   포함하면 그때 수렴.

## 5. 불확실 (실측·재확인 필요)

- Claude Code 의 `.agents/skills/` 읽기 여부 (조사에서 미확인).
- Agent Plugins 1.0 의 실 설치 UX 가 클라이언트마다 다름 (설치 메커니즘은 표준 밖).
- Gemini CLI extension 의 GEMINI.md 주입이 프로젝트 GEMINI.md 와 병합되는 방식.
