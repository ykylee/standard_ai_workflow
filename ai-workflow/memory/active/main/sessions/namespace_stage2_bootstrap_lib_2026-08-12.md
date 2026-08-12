# 18차 세션 — 네임스페이스 격상 2단계: bootstrap_lib (2026-08-12)

- 문서 목적: TASK-2026-08-12-main-007 종결 기록. PyPI blocker 의 이동 단계 완결.
- 상태: done
- 관련: [TASK-007](../backlog/tasks/TASK-2026-08-12-main-007.md), [17차 세션 기록](./cross_platform_and_namespace_2026-08-12.md)

## 요약

`scripts/bootstrap_lib` (9모듈 + harnesses) → `workflow_kit/bootstrap_lib` 물리 이동.
1단계 (tools) 와 같은 처방: 구경로는 vars-copy shim 패키지 (`python -m bootstrap_lib`
호환 포함), source-bound 소비자는 impl 직표적.

| 층 | 내용 |
|---|---|
| 이동 | 내부 import 28건 재표적 + 신규 `__init__` (기존엔 top `__init__` 부재) |
| shim | 10파일 (모듈 7 + `__main__` + init 2), harnesses 하위 깊이 보정 |
| 소비면 | import 14파일 + 경로 문자열 10파일 재표적, pyproject packages 4항, mypy overrides, check_packaging REQUIRED_IMPORTS |
| 검출·복원 | 일괄 sed 가 wiki_cascade docstring 예시를 오변경 → 검사가 즉시 잡아 복원 (의미 밖 매치는 검사가 잡는다) / wheel 에 신경로 0개 → packages 누락 실측으로 발견 (배포 전제는 배포물에서 잰다, 11차 교훈 재적용) |

검증: 전량 2축 251/251 ×2, mypy 191파일 0, wheel (impl 10 + shim 10, packaging
PASS), `python -m` 양경로, probe 8/8.

## PyPI 로드맵 현황

- ~~1단계 tools~~ ✅ (17차) / ~~2단계 bootstrap_lib~~ ✅ (본 세션)
- **잔여**: 2nd cycle 에 shim 2종 + `--bundle` 기본값 drop → wheel top-level =
  `workflow_kit` 하나 → PyPI 발행은 소유자 결정만 남는다.
