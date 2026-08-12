# 17차 세션 — CLI cross-platform + 네임스페이스 격상 1단계 (2026-08-12)

- 문서 목적: TASK-2026-08-12-main-005 (cross-platform) + 006 (네임스페이스 1단계) 종결 기록.
- 상태: done
- 관련: [TASK-005](../backlog/tasks/TASK-2026-08-12-main-005.md), [TASK-006](../backlog/tasks/TASK-2026-08-12-main-006.md), [배포 검토](../../../../docs/planning/cli-distribution-review-2026-08.md)

## 1. cross-platform (TASK-005)

- POSIX 감사: top-level 의존은 `profiling.py` 의 `import resource` 단 1건 (Windows
  에서 wk 전체 import 사) — 가드. fcntl 2곳은 기가드.
- `os-matrix.yml` 신설: windows-latest + macos-latest 에서 소비자 경로
  (`pip install ./workflow-source`) + 8-probe. **Windows 첫 실측 8/8 PASS** (30s).
  `PYTHONUTF8=1` 로 cp125x 한국어 출력 가드.
- 지원 tier: Linux 전량 / macOS probe+darwin 실측 / Windows probe.
- 부수: 루트 낡은 `workflow_kit/` pycache 그림자 제거 + venv editable 재설치.

## 2. 네임스페이스 격상 1단계 (TASK-006)

`tools` 43모듈 → `workflow_kit.tools` 물리 이동 (PyPI blocker 해소의 절반).
구경로는 vars-copy shim (private 이름까지 노출 — path-load 소비자 호환), 자산
(hooks/completions) 은 원위치. entry points·TOOL_MODULES 재표적, 테스트 70파일
재표적, mypy 는 overrides 로 tools 오류 무시 (crawl 137→181).

### 사고 기록 (복원 완료, HEAD 무손상)

이관 중 **shim 경유 monkeypatch 가 impl 에 안 먹혀** version-bump 계열 검사의
무력화 장치가 풀린 채 돌았고, 검사가 실저장소 pyproject 를 `0.7.29` 로 오염시켰다
(README·__init__ 포함 4곳, 즉시 복원). "가짜도 범위가 있다"(2026-07-29) 의 재림 —
**source-bound / monkeypatch-bound 소비자는 shim 이 아니라 impl 을 직표적해야 한다**
가 이번 이관의 핵심 규칙이었다.

## 남긴 것

- 2단계: `bootstrap_lib` → `workflow_kit.*` (PyPI 의 남은 blocker), 2nd cycle 에
  shim drop. 두 단계 후에야 top-level 충돌이 완전 해소.
