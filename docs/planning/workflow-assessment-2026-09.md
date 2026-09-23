# 표준 AI 워크플로우 — 구성·상태 평가 (2026-09)

- 문서 목적: v1.11.0 시점의 워크플로우 구성과 운영 상태를 실측으로 평가하고, 도출된 이슈를 할일·로드맵으로 연결한다
- 범위: 검증 체계, 상태 관리, 배포 채널, 멀티 에이전트 운영, 세션 컨텍스트 비용, 메모리 계층, 작업 구성비
- 대상 독자: 소유자 (다음 사이클 방향 결정), maintainer, workflow 설계자
- 상태: active — 이슈 7건 등록 (TASK-2026-09-23-main-012 ~ main-018), 새 기능 축 M-013 개설. 후속 §7: M-014 + main-019 ~ main-021
- 최종 수정일: 2026-09-23
- 관련 문서: [`roadmap/index.md`](../../ai-workflow/memory/active/roadmap/index.md), [`M-013`](../../ai-workflow/memory/active/roadmap/M-013-session-context-budget.md), [`M-014`](../../ai-workflow/memory/active/roadmap/M-014-ci-gate-throughput.md), [`M-007`](../../ai-workflow/memory/active/roadmap/M-007-operations-standing.md), [`session_handoff.md`](../../ai-workflow/memory/active/main/session_handoff.md)

## 0. 한 줄 결론

> **검증은 두껍고 정확하다. 비용과 주변부가 관리되지 않는다.** 검사가 검사의
> 사각지대까지 잡는 수준에 올랐지만, 세션마다 읽는 문서가 약 190KB 로 불었고,
> 로컬 배포본·중첩 worktree·task ID 처럼 **게이트 밖에 있는 상태**가 조용히 낡거나
> 충돌한다. 다음 사이클은 검사를 더 늘리기보다 이 두 축(M-013 · M-007 7.2~7.4)으로
> 옮기는 것을 권한다.

## 1. 방법

모든 수치는 2026-09-23 (87차 세션, macOS 호스트) 실측이다.

| 대상 | 수단 |
|---|---|
| 지표 패널 | `wk --command=dashboard --format=json` (tool_version 1.11.0) |
| 채널 상태 | `wk doctor` (content_drift · runtime_load · marketplace_sources) |
| task·로드맵 | `backlog/tasks/*.md` frontmatter, `roadmap_state.json` |
| 검사·CI | `run_all_checks.py --branch-context=all`, `gh run list --workflow smoke --limit 60` |
| 부피 | `wc -c` (handoff · state.json · CLAUDE.md), 섹션별 바이트 |
| 작업 구성비 | `git log --since=2026-08-24` 커밋 접두 집계, `--shortstat` |

## 2. 강점

| 영역 | 실측 |
|---|---|
| 검증 체계 | 검사 293개, 로컬 게이트 586/586 (native/slash), CI smoke 4셀(브랜치 2 × 해석기 2) + mcp-sdk-matrix · os-matrix · mypy-strict. 되주입(수리를 일부러 되돌려 발화 확인)이 관행이다 |
| 자기 교정 | 87차 main-011 이 그 예 — 커밋 전 `--changed` 가 소스 열거 결함을 잡았다 |
| 상태 관리 | `state.json` · `roadmap_state.json` 이 생성물 (SSOT 는 task 파일 + handoff). task 416 중 done 413 |
| 로드맵 | M-001~M-006 · M-008~M-012 done, 상설 M-007 in_progress (leaf 2/4) |
| 배포 표면 | 하네스 10종, skill 14종 stable, MCP 도구 11종 stable (+1 removed), transport 2종 stable |
| 드리프트 가드 | dashboard guard 7/7, silent failing cycle 0 (20 사이클 실측) |

## 3. 이슈

### 3.1 세션 시작 컨텍스트 비용 — 선언도 측정도 없다 (→ M-013, main-012)

| 필독 문서 | 부피 | 비고 |
|---|---|---|
| `session_handoff.md` | 108KB | §5 57KB·748줄, §1 41KB (기준선 한 줄 최대 18KB) |
| `state.json` | 65KB | 그중 `memory_entries` 35KB |
| `CLAUDE.md` | 18KB | 263줄 |
| **합계** | **약 190KB** | 세션마다 |

`CLAUDE.md` 는 "handoff 와 backlog 에는 다음 세션에 필요한 핵심 사실만 남긴다" 고
하지만 이를 재는 수단이 없다. 기준선 상한은 **줄 수**라 줄은 4개로 유지되면서 한
줄이 계속 커진다. 줄이는 것 자체가 목적이 아니다 — 무엇을 잃는지 재지 않고 줄이면
'숫자만 좋아진다'. 그래서 구현이 아니라 concept 부터 연다.

### 3.2 로컬 배포본이 조용히 낡는다 (→ main-013, main-014)

87차에 이 호스트에서 두 가지가 동시에 낡아 있었다.

1. Claude Code 설치본 **1.9.1** — 두 릴리스 뒤처짐. marketplace 는 `directory`
   소스라 이미 1.11.0 을 보는데 설치 기록만 낡아 있었다.
2. 플러그인 `.mcp.json` 은 `python3 -m workflow_kit…` 만 부른다. 저장소 밖에서는
   주변 python3 에 깔린 kit 이 뜨는데, 그것이 옛 worktree 를 가리키는 editable
   **1.2.0** 이었다. 저장소 안에서는 `PYTHONPATH=workflow-source` 가 가린다.

`wk doctor` 는 플러그인 **사본**을 대조해 전부 in-sync 로 보였다 — MCP 가 실제로
실행하는 코드는 재지 않는다. 발행 절차에도 이 호스트의 채널 재적용 단계가 없다.
주변 해석기에 기대는 구조는 blocked 인 `08-25-main-017`(Windows `python3` 부재)과
같은 계열이다.

### 3.3 멀티 에이전트 — 지표가 0 인데 충돌이 있었다 (→ main-016, main-017)

- 다른 에이전트가 미커밋으로 `TASK-2026-09-23-main-009` 를 쓰는 사이 원격이 같은
  ID 를 다른 task 에 채번했다. 동기화 때 소유자 확인을 받아 main-010 으로 재번호했다.
  dashboard `multi_agent_concurrent_write_conflict` 는 git 충돌만 세어 **0 (pass)**.
- 방치된 worktree 4개 — `.worktrees/feat-auto-20260814-13740747` 는 main-011 의
  원인이었고, herdr `clear-field-f112` 는 시스템 python 1.2.0 editable 의 대상이었다.

### 3.4 상수 표시 (→ main-015)

- dashboard `drift_prevention.phase`: "Phase 12 (done, v0.15.20) → Phase 13 (planned, v1.0.0 stable 진입 후)"
- `docs/planning/README.md` §1: "v0.15.15-beta 기준 · Phase 12 in_progress"

현재 v1.11.0 이다. 이 저장소가 계속 잡아 온 '버전을 올려도 안 바뀌는 지표' 결함족이다.

### 3.5 로컬 green / CI red 가 여전히 생긴다 (→ 기존 09-23-main-009)

smoke 최근 60회: success 51 · failure 8 · 진행 1. 최근 사례는 86차 마지막 push —
스탬프 판정의 '미커밋 변경 유예'가 로컬 게이트에서 축을 가렸다. 이미 등록된
`09-23-main-009` 가 다룬다.

### 3.6 작업이 자기 측정 쪽으로 쏠려 있다 (→ 로드맵 판단)

| 지표 (2026-08-24 ~ 09-23) | 값 |
|---|---|
| 커밋 | 157 (chore 54 · fix 45 · release 26 · feat 21 · docs 9) |
| `chore(memory)` | 43 |
| 테스트 코드 / kit 코드 | 83k줄 / 67k줄 |
| 추가 줄 | workflow-source +22.9k, ai-workflow(메모리) +11.0k |

최근 결함 대부분은 '검사가 아무것도 재지 않는데 숫자가 멀쩡했다' 계열이고, 그것을
찾은 것 역시 검사다. 품질은 높지만 한계 효용이 줄고 있다. 새 기능 축으로 무게를
옮기는 근거다.

### 3.7 memory_index 소비 편중 (→ main-018)

조회 805건 중 session-start 724 · backlog-update 77 · doc-sync 3 · dispatcher 1.
적중률 0.47, 30 entry 중 한 번이라도 검색된 것 9. 편중이 배선 누락인지 설계인지는
아직 판정되지 않았다.

## 4. 잔여 업무 현황 (평가 시점)

| task | 상태 | 처리 |
|---|---|---|
| `09-07-main-009` 낡은 호스트 3개 | planned → **done** | 평가 중 재측정 — 세 PID 소멸, runtime_load 낡은 호스트 0 (claude-code · codex) |
| `09-23-main-009` 스탬프 유예가 로컬 게이트를 가림 | planned | 유지 — 우선순위 1 |
| `08-25-main-017` Windows `python3` 부재 | blocked | 유지 — Windows 호스트 확보 시 재개 (소유자 결정) |

## 5. 할일·로드맵 연결

| task | 제목 | WBS | 우선순위 |
|---|---|---|---|
| 09-23-main-009 | 스탬프 유예가 로컬 게이트에서 축을 가린다 | M-007/WBS-7.3 | high (기존) |
| **main-012** | 세션 시작 필독 문서 부피 예산 — concept 검토 | **M-013/WBS-13.1** | high |
| **main-013** | doctor 가 플러그인 MCP 가 실제로 띄우는 해석기의 kit 버전을 재지 않는다 | M-007/WBS-7.2 | high |
| **main-014** | 발행 후 로컬 소비 채널 갱신이 절차에 없다 | M-007/WBS-7.4 | medium |
| **main-015** | 상위 요약의 phase 표시가 v0.15 에 멈춤 | M-007/WBS-7.3 | medium |
| **main-016** | 멀티에이전트 충돌 지표가 task ID 충돌을 못 센다 | M-007/WBS-7.3 | medium |
| **main-017** | 방치된 worktree 4개 정리 (소유자 확인) | M-007/WBS-7.4 | low |
| **main-018** | memory_index 소비가 session-start 에 편중 | M-007/WBS-7.3 | low |
| 08-25-main-017 | Windows `python3` 부재 | M-007/WBS-7.1 | blocked (기존) |

**M-013 을 새 기능 축으로 연 이유**: 3.1 은 개별 결함이 아니라 운영 방식의 변경이다
(무엇을 필독에 남기고 무엇을 옮길지). 반복 범주 leaf(M-007)에 넣으면 구현부터 하게
되므로, SDLC 온보딩 순서대로 concept 부터 연다. `parallel_allowed: [M-007]`.

## 6. 권고 순서

1. `09-23-main-009` — CI red 를 실제로 낸 원인
2. `main-013` + `main-014` — 배포본이 낡는 것을 탐침과 절차 양쪽에서 막는다
3. `main-012` (M-013 concept) — 세션 비용의 선언과 측정
4. `main-015` · `main-016` — 상수 표시와 지표 사각지대
5. `main-017` · `main-018` — 소유자 확인·관찰 성격

검사를 재는 검사의 추가는 이 목록이 끝날 때까지 새로 열지 않는 것을 권한다 (3.6).

## 7. 후속 — CI·게이트 처리량 (M-014)

평가 직후 소유자가 Linear 의 CI 재작업 글
([AI coding has made CI a bottleneck, so we reworked ours to keep up](https://linear.app/now/ci-bottleneck-reworked))
을 참고로 제기했다. 대조 실측의 요점:

- CI 셀은 **CPU 포화**다 — CPU 합 ~960s / 벽시계 ~277s = 3.48 (4 vCPU). 같은 작업량에
  셀 간 1.56배 편차.
- 검사당 고정비(기동 + import)는 ~40ms 로 병목이 아니다. 비용은 **무거운 검사 내부의
  반복 계산**에 있다 — `check_root_anchor_audit` 는 전 저장소 감사를 13회,
  `check_release_summary_v0_11_15` 는 release 파이프라인 전체와 CI 조회를 반복한다.

| task | 제목 | WBS |
|---|---|---|
| main-019 | CI·게이트 처리량 — concept 검토 | M-014/WBS-14.1 |
| main-020 | root_anchor_audit 전 저장소 감사 반복 (파싱 13배) | M-007/WBS-7.2 |
| main-021 | release 계열 검사의 파이프라인·CI 조회 반복 — 네트워크 의존 확인 | M-007/WBS-7.2 |

§3.6 의 권고(검사를 재는 검사 추가 중단)와 부딪히지 않는다 — 이 축은 새 검사를
늘리지 않고 **같은 전량을 더 싸게** 돌린다.
