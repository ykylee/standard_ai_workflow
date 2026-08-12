# 8차 세션 — MCP readOnlyHint 정직화 (2026-08-12)

- 문서 목적: TASK-2026-08-11-main-024 종결 기록.
- 상태: done
- 관련: [TASK-024](../backlog/tasks/TASK-2026-08-11-main-024.md), [6차 세션 기록](./state_generated_and_composition_review_2026-08-11.md) §4.3

## 요약

MCP bundle 의 `readOnlyHint` 가 **하드코딩된 허위에서 registry 선언 파생으로** 바뀌었다.
`apply_robust_patch` (파일 write, dry-run 입력 없음) 와 `rotate_workflow_logs`
(handoff rewrite) 가 read-only 로 광고되던 것을 정정 — 하네스가 이 hint 로
auto-approve 할 수 있어 안전 문제였다.

| 변경 | 내용 |
|---|---|
| `ReadOnlyToolSpec.read_only` 필드 | descriptor 의 hint 가 이 선언에서 나온다. write 2종만 `False` |
| `WRITE_CAPABLE_TOOL_NAMES` 사실 목록 | 검사가 registry 선언과 대조 — 한쪽만 고치면 red |
| `check_read_only_mcp_server` | "전 도구 true 강제" (허위를 강제하던 검사) → 선언↔사실 목록↔descriptor **삼자 일치** 강제 |
| committed 산출물 재생성 | transport descriptors / jsonrpc fixtures / harness examples — write 2종만 `false` 로 flip |
| ADR-003 v1.1.7 개정 | 6+1 → **13 도구** 현실 반영, v0.5.7~v1.1.6 의 허위 이력 명기, 서버 이름은 config 호환으로 유지 ("read-only 우선 bundle"), bundle 분리는 후속 후보 |
| wiki 갱신 | entity `mcp-read-only-bundle` (13종 표) + ADR 미러 |

검증: read_only 9검사 + mcp 13검사 green. **되주입** — hint 를 다시 True 하드코딩으로
되돌리면 `check_read_only_mcp_server` 가 즉시 FAIL. 전량 2축 250/250 ×2 green.

## 교훈

- **검사가 허위를 강제할 수 있다** — "전 도구 readOnlyHint=true" 단언은 정책 검사처럼
  보였지만, 현실이 바뀐 뒤에는 허위를 고정하는 장치였다. 단언의 근거는 정책 문장이
  아니라 **행동 사실**(write 하는가)이어야 한다.
- 사실 목록(`WRITE_CAPABLE_TOOL_NAMES`)과 선언(`read_only=`)을 둘 다 두고 검사로
  묶으면, 새 write 도구가 한쪽만 고치고 지나가는 경로가 막힌다.
