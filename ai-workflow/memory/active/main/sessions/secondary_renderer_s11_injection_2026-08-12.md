# 12차 세션 — 보조 렌더러 §11 주입 완결 (2026-08-12)

- 문서 목적: TASK-2026-08-11-main-028 종결 기록. TASK-020 전수검사가 연 렌더러 결함 계열의 완결.
- 상태: done
- 관련: [TASK-028](../backlog/tasks/TASK-2026-08-11-main-028.md), [6차 세션 기록](./state_generated_and_composition_review_2026-08-11.md) §4.1

## 요약

TASK-020 의 "렌더러 26개가 메모리 갱신을 지시하며 방법을 안 알려줬다" 가 **0 이 됐다**:
주요 진입점 9 + 직접 주입 4 (TASK-022) + 보조 6 (이번) 주입, 잔여 8 은 이유가 명시된
원장, 5 는 메모리 무관.

| 변경 | 내용 |
|---|---|
| `render_memory_update_section` 신설 | 보조 문서용 §11 섹션 (명령+계약, marker 포함) — 전체 블록이 과한 자리의 표준 주입 단위 |
| 1순위 6개 주입 | `minimax_orchestrator` / `opencode_agent` (bash deny → 실행은 worker 위임 명시) / `pi_dev_agents` / `grok_build_skill` / `codewhale_skill` / `custom_skill_template` |
| pi-dev 승격 + 병합 dedup | §8 한 줄 pull → 전체 블록. codex 와 공유 `AGENTS.md` 병합 시 블록을 **exact substring 으로 통째 제거** — 병합본에서 close_order·명령·계약 각 1회 실측 |
| 부수 수확 | `grok_build_skill` 이 **낡은 flat 경로**로 `generate_workflow_state.py` 직접 호출을 안내하고 있었다 (`ai-workflow/memory/session_handoff.md` — v0.14 이전 레이아웃) → `wk refresh-state` 로 교체 |
| case 9 신설 (양방향 원장) | 주입 6개는 §11 이 **있어야**, 원장 8개 (설정 예시 3 + worker 페르소나 5, 이유 명시) 는 §11 이 **없어야** 통과 — 원장이 낡으면 그 자체가 red. 렌더러 시그니처 3종은 파라미터 이름 기반 적응 호출 |

검증: `check_standard_single_source` 8→**9 case** 9/9, 되주입 실증 (렌더러 구버전 →
case 9 FAIL), harness 검사 8종 green, 전량 2축 250/250 ×2 green.

## 교훈

- **worker 페르소나에 §11 을 안 싣는 것은 결정이다** — 메모리 갱신은 orchestrator 의
  책임이라는 토폴로지 분리를 지키는 것. 결정은 원장에 이유와 함께 남겨야 미주입과
  누락을 구분할 수 있다.
- 보조 문서의 낡은 절차 사본(grok flat 경로)은 전수 주입 작업이 아니면 발견되지
  않았다 — 주입은 커버리지 작업이면서 동시에 감사 작업이다.
