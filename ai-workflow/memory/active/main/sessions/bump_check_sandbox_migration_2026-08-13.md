# 29차 세션 기록 — 원본 bump 검사 sandbox 이관 (2026-08-13)

- 문서 목적: 29차 세션의 작업 내용·산출물·다음 시작 포인트 기록
- 범위: TASK-2026-08-13-main-001 (bump 검사 sandbox 이관) + TASK-004 원인 기록
- 상태: done
- 최종 수정일: 2026-08-13
- 관련 문서: [28차 세션 기록](./plugin_p5_channel_verdict_2026-08-13.md), `workflow-source/tests/_repo_sandbox.py`

## 1. 지시

사용자: "좋아 다음 진행" — state.json current_focus 인 TASK-001 실행. 릴리스
발행은 소유자 명시 지시 대기로 유보.

## 2. 측정 먼저 — writer 를 현장에서 특정했다

`watch_transient_writer` (P4 가 저장소에 고정해 둔 감시 도구) 를 전량 1축 옆에
세워 **왕복 2건을 재포착** (1.1.8→1.1.9→1.1.8, 50ms 간격). diff 는 version 줄
하나, ps 스냅샷의 실행 중 검사 목록과 코드 대조로 writer 를 **단 1건**으로
특정: `check_release_pipeline.py::test_version_bump_apply_and_restore`.
(용의 계열이던 poststep 2종(check_v0_7_27/29)은 write 경로가 전부 mock —
원본 무접촉이었다.)

## 3. 이관

- `test_version_bump_apply_and_restore` → `test_version_bump_apply_in_sandbox`:
  `repo_sandbox` 사본에서 release_pipeline CLI 를 서브프로세스로 돌려
  (`version-bump --patch --apply --skip-sync-hash --json`) 사본의
  pyproject/__init__ 갱신을 검증. 마지막에 **원본 pyproject byte 무손상 assert**.
- `check_no_repo_write` WATCHED_CHECKS 13→**15**: `check_release_pipeline.py`
  (되돌리는 구현으로 회귀하면 실행-중 폴링이 잡는다) +
  `check_agent_plugin_payload.py` (P4 의 plugin/ manifest 원본 덮임 사고 계열
  이중 방어 — plugin/ 산출물은 전부 git 추적이라 porcelain/digest 감시 범위).

## 4. 완료 기준 실측

| 기준 | 결과 |
|---|---|
| 원본 pyproject 를 bump 하는 검사 0건 | ✔ 이관 후 전량 **2축** 옆에서 watcher **관측 0건 / 12,403 poll** (이관 전 같은 조건 1축에서 2건) |
| check_no_repo_write 감시 목록에 plugin/ 계열 | ✔ 15 감시 대상 전부 저장소 변경 0 (실행-중 폴링 포함) |
| 전량 회귀 | ✔ 252/252 ×2 green |

## 5. 파생 효과 — TASK-004 (CI mypy flake) 유력 원인 제거

mypy 는 시작 시 pyproject.toml 을 config 로 읽는다. CI native 셀의 mypy 게이트
exit 2 (config/blocking 오류 코드) 는 이 왕복과 mypy 시작이 겹친 race 로 정확히
설명된다 — 이관으로 그 왕복 자체가 사라졌으므로 TASK-004 는 **재발 관찰만**
남긴다 (일정 기간 무재발이면 close).

## 6. 남은 것

- 별건 대기: [TASK-2026-08-13-main-002] bootstrap OpenCode 방언,
  [TASK-2026-08-13-main-003] hook 조건부 규칙 주입,
  [TASK-2026-08-12-main-019] macOS PEP 668.
- v1.1.9/v1.2.0 릴리스 — 소유자 발행 지시 대기 (P1~P5 + 2nd cycle 예약분).
