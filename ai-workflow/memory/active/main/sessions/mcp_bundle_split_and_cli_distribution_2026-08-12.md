# 16차 세션 — MCP bundle 분리 + CLI 배포 검토 (2026-08-12)

- 문서 목적: TASK-2026-08-12-main-003 (bundle 분리) + 004 (CLI 배포 검토) 종결 기록.
- 상태: done
- 관련: [TASK-003](../backlog/tasks/TASK-2026-08-12-main-003.md), [TASK-004](../backlog/tasks/TASK-2026-08-12-main-004.md), [ADR-003 v1.1.8 절](../../../../docs/architecture/ADR-003-read-only-mcp-default-policy.md), [배포 검토](../../../../docs/planning/cli-distribution-review-2026-08.md)

## 1. MCP bundle 분리 (TASK-003)

"read_only" bundle 안에 write 도구 2종이 살던 긴장 (v1.1.7 후속 후보) 의 근본 정리.

| 층 | 내용 |
|---|---|
| registry | bundle 선택자 — `read-only`(11) / `write`(2, `workflow_write_bundle`) / `all`(13, 1st cycle 기본) |
| 서버 | jsonrpc `--bundle` + bundle 밖 tools/call 거부. `all` 기본 + deprecation 경고 (기존 config 무수정 동작). stdio-sdk 는 1st cycle 미지원 (ADR 명시) |
| bootstrap | 기존 alias 전부 `--bundle read-only` 로. claude-code·MiniMax 는 `standardAiWorkflowWrite` 동시 emit (MiniMax write = `manual_review_only`). mavis 글로벌은 read-only 만 |
| 자기 적용 | 저장소 `.mcp.json` 2-server 분리 |
| 검사 | `check_read_only_mcp_server`: RO∪W==all + 교집합 0 + RO 서버의 write 호출 거부. case 7 은 entry args 의 `--bundle` 로 기대 목록 결정 (bundle-aware) |

되주입: server 3파일을 구버전으로 되돌리면 rc=1. 다음 cycle 에 기본값 all→read-only 전환.

## 2. CLI 배포 방법 검토 (TASK-004)

산출물: [`docs/planning/cli-distribution-review-2026-08.md`](../../../../docs/planning/cli-distribution-review-2026-08.md).

- **핵심 발견 (실측)**: wheel 의 top-level 이 `workflow_kit` + `bootstrap_lib` +
  `tools` — 뒤 둘은 일반명이라 **PyPI 공개 시 site-packages 충돌 위험**. PyPI 는
  `workflow_kit.*` 네임스페이스 격상이 선행 조건 (별도 task 후보).
- **권고**: 단기 = uv/pipx + GitHub Release wheel 격리 설치를 공식 경로로
  (INSTALLATION_AND_USAGE §3 에 즉시 반영 — 격리라 이름 충돌도 차단). 중기 = PyPI
  는 네임스페이스 정리와 한 묶음으로 소유자 재검토.

## 교훈

- **분리는 서버 능력 + 렌더러 기본값 + 검사 3층이 같이 움직여야 실효한다** — 서버에
  선택자만 넣고 emit 기본값을 안 바꾸면 분리는 장식이다.
- **배포 채널 결정 전에 wheel 내용물부터 실측한다** — top-level 이름 하나가 채널
  선택지를 제약하고 있었다.
