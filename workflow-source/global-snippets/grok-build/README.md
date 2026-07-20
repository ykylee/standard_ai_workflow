# Grok Build Global Snippet

- 문서 목적: Grok Build 전역 설정에 넣어도 비교적 안전한 workflow snippet 예시와 사용 원칙을 정리한다.
- 범위: additive MCP 예시, skill paths, memory opt-in, 주의점, 프로젝트 로컬 레이어와의 관계
- 대상 독자: Grok Build 사용자, 저장소 관리자, 운영 담당자
- 상태: draft
- 최종 수정일: 2026-07-20
- 관련 문서: `../../core/workflow_global_injection_policy.md`, `../../harnesses/grok-build/apply_guide.md`, `./config.toml.snippet`

## 권장 원칙

- Grok Build 전역 설정에는 additive MCP 연결, skill paths, memory opt-in, permission 기본값만 넣는다.
- `models.default` / `models.web_search` 등 model/provider 기본값은 넣지 않는다 (Grok Build 의 default `grok-build` 를 보존).
- 실제 프로젝트 workflow 진입은 `AGENTS.md` + `GROK.md` 와 `ai-workflow/memory/` 문서에서 수행한다.

## 포함된 파일

- [config.toml.snippet](./config.toml.snippet)

## 사용 방법

1. 현재 `~/.grok/config.toml` 과 병합 전에 diff 로 검토한다.
2. 이미 존재하는 MCP 서버 정의 / skill paths / memory 설정과 충돌하지 않는지 확인한다.
3. Codex / Claude / Cursor MCP 와 동시 등록 시 alias 충돌 주의. 동일 alias `standardAiWorkflowReadOnly` 가 양쪽 config 에 있으면 runtime 에서 중복 spawn 가능 → 한쪽만 활성화 권장.
4. 프로젝트별 규칙은 절대 전역 snippet 에 추가하지 않는다.

## 호환성 (compat)

- Grok Build 는 `[compat.claude] mcps` / `[compat.cursor] mcps` / `[compat.codex] sessions` 로 기존 Claude / Cursor / Codex 자산을 자동 import.
- 자동 import 가 의도치 않은 override 를 일으키면 snippet 의 `[compat.<vendor>] mcps = false` 로 비활성화.

## 다음에 읽을 문서

- Grok Build 적용 가이드: [../../harnesses/grok-build/apply_guide.md](../../harnesses/grok-build/apply_guide.md)
- 비침투적 주입 정책: [../../core/workflow_global_injection_policy.md](../../core/workflow_global_injection_policy.md)
- 설정 계층 가이드: [../../core/workflow_configuration_layers.md](../../core/workflow_configuration_layers.md)
- MCP 설치 by 하네스: [../../core/mcp_installation_by_harness.md](../../core/mcp_installation_by_harness.md)
