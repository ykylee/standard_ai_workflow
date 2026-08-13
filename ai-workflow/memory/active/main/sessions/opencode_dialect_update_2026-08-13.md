# 30차 세션 기록 — bootstrap OpenCode MCP 방언 갱신 (2026-08-13)

- 문서 목적: 30차 세션의 작업 내용·산출물·다음 시작 포인트 기록
- 범위: TASK-2026-08-13-main-002 (OpenCode 방언 실측 형태 반영 + 단일화)
- 상태: done
- 최종 수정일: 2026-08-13
- 관련 문서: [29차 세션 기록](./bump_check_sandbox_migration_2026-08-13.md), `workflow_kit/bootstrap_lib/mcp.py`

## 1. 지시

사용자: "다음 진행하자" — 별건 대기 중 TASK-002 실행 (P3 실측이 반증한
bootstrap 방언).

## 2. 무엇이 문제였나

bootstrap 의 `render_opencode_mcp_config` 가 emit 하던 entry (문자열 `command` +
`args` 분리, `env` 키, `enabled` 없음) 를 opencode 1.17.12 가 **거부한다**
(*"Expected array"* / *"Missing key enabled"*). 독립 증인
`examples/mcp_config_examples/opencode-mcp.json` 도 같은 구형이었다 — 최상위
키만 대조하던 case 6 의 사각지대에서 **entry 형태**가 통째로 낡아 있었다.

## 3. 조치 — 형태를 아는 자리를 하나로

- `opencode_mcp_server_entry(command, env)` 신설 (bootstrap_lib/mcp.py) — 실측
  확정 형태 (배열 `command` + `enabled` + `environment` + timeout). **bootstrap
  emit 과 플러그인 payload snippet 이 같은 함수에서 파생** — payload 재생성
  diff 0 (P3 때 payload 쪽만 먼저 실측 형태로 갔던 것과 정확히 일치).
- 독립 증인 opencode-mcp.json 실측 형태로 갱신.
- 예시 생성기 draft(주석 스니펫) + `schemas/read_only_harness_mcp_examples.json`
  재생성.
- `check_bootstrap_mcp_roundtrip` spawner — 배열 command / `environment` 정규화
  (타 방언의 문자열+args+env 는 유지).
- `check_mcp_tool_descriptors` **case 8 신설**: 렌더러와 독립 증인 **양쪽**의
  entry 형태를 대조 (자기 자신 비교 금지 원칙 — 어느 쪽이 낡아도 깨진다).
  되주입 실증: 구형으로 회귀시키면 FAIL 3건.

## 4. 검증

| 항목 | 결과 |
|---|---|
| 새 emit 로드 실측 | ✔ `opencode mcp list` **connected** (PYTHONPATH env 포함, 실 emit 그대로) |
| case 8 되주입 | ✔ 구형 회귀 시 FAIL 3건 → 복원 후 8/8 |
| 전량 회귀 | ✔ 252/252 ×2 green |

## 5. 남은 것

- 별건 대기: [TASK-2026-08-13-main-003] hook 조건부 규칙 주입,
  [TASK-2026-08-12-main-019] macOS PEP 668, [TASK-2026-08-13-main-004] CI mypy
  flake 재발 관찰 (유력 원인 제거됨).
- v1.1.9/v1.2.0 릴리스 — 소유자 발행 지시 대기.
