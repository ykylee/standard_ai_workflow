# 10차 세션 — MCP 도구 목록 단일출처화 (2026-08-12)

- 문서 목적: TASK-2026-08-11-main-025 종결 기록.
- 상태: done
- 관련: [TASK-025](../backlog/tasks/TASK-2026-08-11-main-025.md), [6차 세션 기록](./state_generated_and_composition_review_2026-08-11.md) §4.3

## 요약

MCP 도구 목록의 사본 3계열이 registry (`READ_ONLY_TOOL_SPECS`) 하나로 수렴했다.

| 변경 | 내용 |
|---|---|
| MiniMax 렌더러 `_read_only_tool_names()` | 손 목록 10개 (3개 누락) → registry 파생 13개 |
| 예시 config 2종 갱신 + case 7 신설 | `examples/mcp_config_examples/minimax-code-mcp*.json` 의 `tools` 배열을 registry 와 대조 (`check_mcp_tool_descriptors`, 대상 0건은 통과 아님) |
| 유령 `script_path` 2건 실물화 | `mcp_servers/rotate-workflow-logs/` + `milestone-progress/` 신설 (스크립트 + MCP.md, 기존 `lib/common_utils` 패턴, 실행 검증) — manifest 가 광고하던 존재하지 않는 경로 해소 |
| script_path 실존 강제 | `check_read_only_mcp_server` 가 전 spec 의 `script_path.is_file()` 단언 — 앞으로 registry-만 등록은 red |
| ADR-003 표면 의도 명시 | MCP = 하네스 자동 노출용 **선별 부분집합** (read-only 우선) / `wk` = 소비자 **전체 창구**. 이원 레지스트리는 의도이고, session-start 류 메모리 쓰기 경로는 CLI 전용 |

검증: mcp 13 + read_only 9 검사 green, **되주입** (예시를 옛 10개 목록으로 복원 →
case 7 FAIL) 실증, 신설 스크립트 2종 실행 검증 (`--help` / 실데이터 평가), 전량 2축
250/250 ×2 green.

## 교훈

- **레지스트리 확장은 파생물 전수 갱신을 요구한다** — rotate/milestone/apply 를
  registry 에 추가할 때 렌더러 손 목록·예시·mcp_servers 디렉터리가 안 따라갔고,
  대조 검사가 없어 3계열이 제각각 낡았다. 파생물은 코드로 파생시키고, 따로 작성된
  사본(예시)은 검사로 대조한다.
