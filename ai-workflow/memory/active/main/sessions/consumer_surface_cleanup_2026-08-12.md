# 11차 세션 — 소비자 안내 표면 정리 (2026-08-12)

- 문서 목적: TASK-2026-08-11-main-027 종결 기록.
- 상태: done
- 관련: [TASK-027](../backlog/tasks/TASK-2026-08-11-main-027.md), [6차 세션 기록](./state_generated_and_composition_review_2026-08-11.md) §4.2

## 요약

소비자에게 보이는 안내 표면이 전부 `wk` 하나를 가리키고, packaging 검사가 그 전제를
wheel 에서 검증한다.

| 변경 | 내용 |
|---|---|
| SKILL.md 3종 + apply_guide | `python3 skills/.../run_*.py` (미배포 경로) 안내 전부 → `wk` (무인자 session-start 반영). wrapper 는 "저장소 내 개발용" 으로 명시 |
| `check_packaging` REQUIRED_IMPORTS | `tools` + `tools.session_start` 추가 — TASK-021 의 전제("tools/ 는 배포된다")가 wheel 에서 검증되게 됐다. **구판 1.1.6 wheel 에서 즉시 FAIL** (tools.session_start 부재 — TASK-021 이전 빌드) 로 검사가 무는 것을 실증, 현재 소스의 신선 wheel 은 PASS |
| `--copy-core-docs` | wrapper 스크립트 3종 복사 중단 (SKILL.md 문서만) — pip 설치 없는 대상에 복사되면 `from tools...` ModuleNotFoundError 로 죽는 껍데기였다 (자립형 대비 회귀). pyproject 주석 정밀화 |

검증: skill/bootstrap/onboarding/smart_update 검사 green, 신선 wheel packaging PASS
(빌드는 temp outdir — `dist/` 무오염), 전량 2축 250/250 ×2 green.

## 교훈

- **배포 전제는 배포물에서 잰다** — "tools/ 는 pip 로 배포된다" 는 pyproject 선언이
  8개 커밋 동안 wheel 에서 한 번도 검증되지 않았고, 검사에 넣자마자 구판 wheel 의
  공백을 즉시 잡았다.
