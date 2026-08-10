# Beta v1.1.4 (2026-08-10)

> **상태: 릴리스 준비.** `tool_version = v1.1.4-beta`, tag `v1.1.4-beta`.
> **patch release** — 릴리스 파이프라인 자체를 쓸 수 있게 만든다.
> v1.1.0 부터 네 번 연속 수동 발행하게 만든 pre_check 만성 실패의 3뿌리를 해소했고,
> **본 릴리스가 `cmd_release` 경로의 첫 실전 발행**이다.
>
> PyPI 배포는 정책상 미실행 (릴리스 채널 = GitHub Releases).

## 0. 릴리스 판정

v1.1.3 노트는 "cmd_release 를 쓸 수 있게 만들기" 를 후속으로 남겼다. 본 릴리스가
그 자리를 닫는다. 만성 실패는 셋 다 **게이트가 실제를 재지 않는** 부류였다:

- **doctor** — 호출 경로가 `workflow-source/workflow-source/` 를 탐색해 **0 개
  파일을 재고 non_compliant** 를 보고했다. 아무것도 안 잰 검사가 실패를 내고
  있었다. 경로를 고쳐도 남는 TST-WF-01 만성 red 는 측정이 정당한 case 관행
  (inline `check()` / `failures.append`) 을 못 보는 판정식 문제 — dummy wrapper
  전례(v0.15.18) 대신 `partial_rules.testing` **선언된 예외** 로 전환했다.
- **state** — 판정 필드 `memory.last_freeze` 는 writer 가 사라진 죽은 계약이었다
  (reader 만 legacy 에 남은 silent failing 재발형). 현 스키마 `generated_at` 로 교체.
- **기본값** — 무인자 `release` 가 APPLY 로 진입했다. dry-run 기본으로 반전.

항상 red 인 지표는 판정식이 나쁜 것이고, 실행 못 한 검사는 통과가 아니다.

## 1. 릴리스 요약

- 범위: `v1.1.3-beta..HEAD` (TASK-2026-08-10-main-001~003)
- `release --dry-run` pre_check **5/5 실측 통과** + 파이프라인 완주 (venv)
- 전량 검사 **260/260 PASS** (격리 venv, `--tmp-dir` 실디스크)

## 2. deliverable

### 2.1 cmd_release 사용성 회복 (TASK-001, `e741de6`)

- doctor 호출: `--project-root` 저장소 루트 + `--config-path workflow-source/`
  명시 + subprocess `PYTHONPATH` 명시 (caller 환경 상속 암묵 의존 제거).
- `[tool.workflow-doctor] partial_rules.testing = [TST-WF-02..06]` — TST-WF-01
  선언 예외 (이유는 pyproject 주석 + `stable_guarantee.md` §5.1).
- state freshness: `generated_at` 판정 (legacy `last_freeze` 하위호환, parse
  실패는 fail).
- `release` 무인자 = dry-run, `--apply` 명시 시에만 발행, `--dry-run --apply`
  는 dry-run 승. 개별 `--skip-packaging/-doctor/-state/-git/-mypy` 신설
  (`--skip-validate` 의 all-or-nothing 해소).
- mypy 게이트: `-m mypy` 모듈 부재(rc 1 + stderr)를 "오류 발견" 과 구분해 보고
  (기존 FileNotFoundError 분기는 이 호출 형태에서 절대 타지 않았다).

### 2.2 mavis e2e 호스트 사본 제거 (TASK-002, `4b67621`)

`check_mavis_attach_e2e` 가 mavis 글로벌 mcp.json 항목의 **사본**(darwin 절대
경로)을 하드코딩해 darwin 외 호스트에서 무조건 red 였다. 실제
`~/.minimax/mcp/mcp.json` 정본을 읽고, 부재 시 graceful skip
(`--require-mavis` 로 강제). 로드 경로는 fake 항목 실증 ALL PASS.

### 2.3 본 릴리스 = 파이프라인 실전 검증 (TASK-003)

version-bump post-step (`sync_release_hash` + amend 가드) 이 **처음으로 정상
동작** — 미push 커밋에만 amend (`head_pushed` 확인). 발행 절차 전체가
`cmd_release` 경로로 진행됐다.

## 3. smoke 회귀

누적 smoke test **260/260 PASS** (2026-08-10, `dev,release,mcp-sdk` extra 를 깐
격리 venv, `--tmp-dir` 실디스크). 이 줄은 릴리스 시점 스냅샷이 아니라 *최신 전량
결과* 를 반영하는 살아있는 지표다.

신규 smoke:

- `check_release_pre_check_gates.py` **10/10** — argparse default (AST) / 무인자
  dry-run / dry-run 승 / doctor argv / baselines 실측 ≥100 files / doctor·state
  functional / **결함 되주입** / legacy 하위호환 / partial 선언 고정.
  `check_no_repo_write` 감시 목록 등록 (release dry-run 실호출 계열).

## 4. 1차 출처 (cross-ref)

- [TASK-2026-08-10-main-001](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-10-main-001.md)
- [TASK-2026-08-10-main-002](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-10-main-002.md)
- [TASK-2026-08-10-main-003](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-10-main-003.md)
- 이전 release note: [Beta-v1.1.3.md](./Beta-v1.1.3.md)

## 5. 후속

- **TST-WF-01 측정 재설계** — 관행 인식형 counting 이 되면 partial 예외를 제거.
- **darwin homelab 에서 mavis e2e 재확인** — 정본 읽기 전환 후 첫 실행.
- branch protection (소유자 결정) / `dist` 의 `--apply default True` 동류 (보류).

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-08-10T02:48:54Z)_

- total wiki pages: **92**
- total memory entries: **7**
- symmetric links: **0**
- asymmetric count: **1**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **1**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
