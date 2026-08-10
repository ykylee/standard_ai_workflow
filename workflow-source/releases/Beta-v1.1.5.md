# Beta v1.1.5 (2026-08-10)

> **상태: 릴리스 준비.** `tool_version = v1.1.5-beta`, tag `v1.1.5-beta`.
> **patch release** — TST-WF-01 측정 재설계로 마지막 선언 예외를 제거하고,
> `dist` 기본값을 dry-run 으로 반전한다. `cmd_release` 경로의 **2번째 실전 발행**
> (한 번은 우연일 수 있다 — 반복이 경로를 검증한다).
>
> PyPI 배포는 정책상 미실행 (릴리스 채널 = GitHub Releases).

## 0. 릴리스 판정

v1.1.4 가 "게이트가 실제를 재게" 만들었다면, 본 릴리스는 그 중 임시로 우회했던
자리(TST-WF-01 partial 선언 예외)를 **측정 자체를 고쳐** 없앤다.

- **실측이 설계를 결정했다** — AST 로 4개 관행(def test_/case_ · assert ·
  reporter 호출 · 실패 수집 append)을 세고 `assert True` dummy 153개를 배제하니
  260개 전 파일이 ≥1 신호였다. hard floor 는 "파일당 ≥1"(검증 없는/parse 불가
  파일 검출), ≥5 는 권장으로 doctor notes 에 노출.
- **가짜 신호는 세지 않는다** — v0.15.18 의 dummy wrapper 는 측정을 채우려고
  만든 것이라 배제했다. 측정이 정직해지자 **만성 red 를 fixture 로 기대던
  테스트가 부서졌다** (doctor exit-on-fail smoke) — 살아있는 저장소 상태는
  기대값이 아니다. 결정적 fixture 로 교체.

## 1. 릴리스 요약

- 범위: `v1.1.4-beta..HEAD` (TASK-2026-08-10-main-004~006)
- TST-WF-01: partial 예외 제거, **hard 복귀 + 정직하게 compliant**
- `dist` 무인자 = dry-run (release 의 v1.1.4 반전과 정합)
- 전량 검사 **264/264 PASS** (격리 venv, `--tmp-dir` 실디스크)

## 2. deliverable

### 2.1 TST-WF-01 측정 재설계 (TASK-004, `ff744b4`)

- `_count_verification_signals()` (AST): def test_/case_(dummy 제외) + assert
  (상수 조건 제외) + reporter 호출식(`check()` 등) + 실패 수집식
  (`failures.append` 등). parse 불가 = 0.
- `partial_rules.testing` 제거 — TST-WF-01 hard 복귀. 재도입은
  `check_release_pre_check_gates` case 10 이 잡는다 (예외 *부재* 고정).
- 정본 문서 동기: `testing-baseline.md` §3.1 / `stable_guarantee.md` §5.1.
- `check_tst_wf01_signals.py` **9/9** 신설 — 관행 counting 3종 + dummy 배제 +
  되주입 3종 (신호 0 / parse 불가 / 빈 디렉터리 → non_compliant).

### 2.2 doctor exit-on-fail 테스트 fixture 교체 (`c0ad1a6`)

"저장소에 non_compliant 가 늘 있다"를 전제로 쓰던 테스트를 결정적 fixture
(신호 0 smoke 파일 생성)로 교체. 만성 red 를 고치면 그 red 에 기대던 소비자가
드러난다.

### 2.3 dist 기본값 dry-run 반전 (TASK-005)

release 의 v1.1.4 반전과 같은 결함이 `dist` subparser 에 복제돼 있었다
(`--apply` default True 가 main() 의 "둘 다 없으면 dry-run" 정규화를 무력화).
무인자 `dist` 는 이제 빌드 plan 만 낸다. lib wrapper 는 이미 dry-run 기본이라
세 진입 경로 정합. `check_release_pre_check_gates` 10 → **12/12**.

### 2.4 본 릴리스 = cmd_release 2번째 실전 (TASK-006)

v1.1.4 에서 배운 파생물 재생성(fixtures 3종 + samples 24건 + stamp 4종)을
이번에는 **릴리스 전에** 수행 — 릴리스 직후 red 를 만들지 않는 절차 확인.

## 3. smoke 회귀

누적 smoke test **264/264 PASS** (2026-08-10, `dev,release,mcp-sdk` extra 를 깐
격리 venv, `--tmp-dir` 실디스크). 이 줄은 릴리스 시점 스냅샷이 아니라 *최신 전량
결과* 를 반영하는 살아있는 지표다.

신규 smoke:

- `check_tst_wf01_signals.py` **9/9** (§2.1)

## 4. 1차 출처 (cross-ref)

- [TASK-2026-08-10-main-004](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-10-main-004.md)
- [TASK-2026-08-10-main-005](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-10-main-005.md)
- [TASK-2026-08-10-main-006](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-10-main-006.md)
- 이전 release note: [Beta-v1.1.4.md](./Beta-v1.1.4.md)

## 5. 후속

- branch protection (소유자 결정) / darwin homelab 에서 mavis e2e 재확인.
- v0.15.18 dummy wrapper 물리 제거 (측정에서는 이미 배제, 별건).
- P2-1 ADR-006 Memory Index 회고 (2026-08-19 이후 착수 조건 충족).

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-08-10T04:23:04Z)_

- total wiki pages: **92**
- total memory entries: **7**
- symmetric links: **0**
- asymmetric count: **1**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **1**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
