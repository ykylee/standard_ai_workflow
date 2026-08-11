# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-11 (리팩터링 사이클 착수 — TASK-2026-08-11-main-001)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **저장소 리팩터링 사이클 착수** (2026-08-11). 3차 세션 조사(§7)의
  후보 1 완료 — `check_mypy_strict_v0_11_3~10` 8개 제거 (TASK-2026-08-11-main-001,
  smoke **268→260**, 파생 수치 3문서 동기). 부산물로 **amend Guard 2 의 staged-삭제
  fatal** 결함 발견 → TASK-2026-08-11-main-002 (planned). 남은 리팩터링 후보는 §5.
- 직전 기준선: **CI 재현성 회복 + smoke 병렬화 완결** (TASK-016~019). 시작은
  `smoke` **15연속 red** 발견이었다 — 그런데 handoff 는 내내 "전량 검사 green" 을
  기록하고 있었다. 로컬(native 1축)과 CI(native+slash 2축)가 **다른 것을 재고
  있었다**. TASK-016 이 red 를 껐고 (검사가 살아있는 브랜치 상태에 의존),
  TASK-017 이 근본을 고쳤다 (`branch_matrix.py` 정본 + `--branch-context=all` 로
  로컬 재현을 관행화, SDK 매트릭스와 같은 처방). TASK-018 은 병목을 측정으로 좁혀
  (**CI job 604s 중 smoke 576s**) 병렬화했고 — **CI 실측 576s → 220s**, 전량
  268/268 — 그 과정에서 `check_source_without_runtime_layer` 가 원본 `ai-workflow/`
  를 rename 해 숨기던 것(`finally` 는 SIGKILL 에 안 돈다 = 저장소 파괴 위험)을
  사본 검증으로 교체했다. TASK-019 는 병렬화가 드러낸 사전 결함 — **검사 4건이
  원본 저장소에 `--apply` 를 돌린 뒤 되돌리고 있었다** (pyproject version →
  `99.99.99`, README/`__init__` drift, memory_index/wiki, 실빌드 산출물) — 을
  `_repo_sandbox.py` 로 격리했다. 정숙 구간 9→3. 직전: **v1.1.6-beta 발행 완료**
  (TASK-015, `cmd_release` 3번째 실전). 그 이전 이력은 §4 와 [3차 세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md) 참조.
- 현재 주 작업 축: **저장소 리팩터링** (조사 근거 §7). 다음 후보: 아카이브 정리 / `check_cache_*` 통합 / `release_pipeline.py` 분할 / presentations 바이너리 (§5).
- 다음 후보 축: branch protection (소유자 결정) / darwin homelab 에서 mavis e2e + federation cross-host 재확인 / v1.1.0·v1.1.1 노트 누적 표기 사후 삽입 여부 / memory_index 3-tuple 지표 추이 관찰. **v1.1.6-beta 발행 완료, ADR-006 후속 W-1~W-4 완결**.
- 발견한 cross-project 패턴 (agent memory 추가):
  - **Federation pattern** (4 후보 검토: central ❌ / git ❌ / S3 ❌ / federation ✅)
  - **MCP/CLI dual mode** (operational tool 의 4종 wrapper)
  - **3-layer defense** (규약 + client hook + server protection)
  - **Scope drift detection** (3-way enum: planned_done / planned_undone / unplanned_done)
  - **time.mktime → calendar.timegm** (UTC timestamp KST 환경 함정)
  - **[project.scripts] entry points** (CLI 化 A안, venv e2e 검증)
  - **기존 dispatcher 확장 > 새 dispatcher** (진입점이 둘로 갈리면 `--help` 도 갈린다)
  - **serving 없는 pull 은 반쪽** (API 만 있고 부를 CLI 가 없으면 기능이 없는 것과 같다)
  - **모름 ≠ 안전** (검사에서 못 읽은 필드를 통과로 치면 거짓 안심을 준다)
- 최근 핵심 기준 문서:
  - [multi_workspace_orchestration.md](../../../../workflow-source/core/multi_workspace_orchestration.md) — **§0.7 상태표 + §7.1·§7.3 구현 표시** + §0.8 *아직 열려 있는 것* 4건
  - [global_workflow_standard.md §10](../../../../workflow-source/core/global_workflow_standard.md) — 다중 작업·협업 규칙
  - [MEMORY_GOVERNANCE.md](../../../../workflow-source/MEMORY_GOVERNANCE.md)

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
-
## 3. 차단 작업

- 현재 `blocked` 작업:
-
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-08-11-main-001 **check_mypy_strict_v0_11_3~10 8개 제거** — 릴리스별 2파일 부분집합 재측정은 FULL mypy strict (129 파일) + `mypy-strict` CI 전체 검사 아래서 정보 0. `ci_v0_11_11` / `release_gate_v0_11_12` 는 전체-범위 계약이라 보존. smoke 268→260, 파생 수치 3문서 동기 (CODE_INDEX / INSTALLATION / v1.1.6 노트 누적 줄 — 대조 검사 3종이 전부 잡아냄). **부산물**: staged 삭제 상태에서 amend Guard 2 (`release_pipeline.py:1030`) 가 `git add` pathspec fatal → TASK-2026-08-11-main-002 (planned).
- TASK-2026-08-10-main-019 **원본 저장소에 --apply 하던 검사 4건을 사본으로** — `_repo_sandbox.py` 신설. `version_auto_sync`(pyproject→99.99.99, `__init__`) / `self_recovering_v0_13_2`(README·pyproject·`__init__` drift) / `bidir_link_v0_13_3`(memory_index·wiki) / `release_pipeline_phase3`(실빌드 산출물) 이 **원본을 바꿨다 되돌리고** 있었다. 되돌리므로 `no_repo_write` 전후 비교는 통과 — 그러나 그 사이 다른 에이전트가 읽으면 잘못된 값을 본다. 원본 무손상을 **실행 경로에서** assert. 정숙 9→3, 전량 268/268 × 2 컨텍스트. **성능 이득은 사실상 0** (사본 복사가 정숙 절감을 상쇄) — 값어치는 협업 안전.
- TASK-2026-08-10-main-018 **smoke 병렬화** — CI job 604s 중 smoke 576s 가 병목, 시간 분포는 극단적(상위 13개=50%, 하위 133개 합계 9.8s). `--jobs auto` + **정숙 구간**(파일 안 `REQUIRES_QUIET_REPO` 선언, §2.53). `check_source_without_runtime_layer` 의 원본 rename → 사본 검증 (**`finally` 는 SIGKILL 에 안 돈다**). **CI 576s→220s**, 로컬 345s→118.8s. `check_parallel_smoke` 8 case.
- TASK-2026-08-10-main-017 **브랜치 컨텍스트 정본화 + 로컬 재현 관행화** — CI 2축 / 로컬 1축 비대칭이 뿌리. `branch_matrix.py` 정본 + `run_all_checks --branch-context=<label|all>` + smoke.yml prepare job 주입(복제 제거) + `check_branch_context_matrix` 8 case + CLAUDE.md 관행. **새 축이 첫 실행에서 결함 2건을 잡았고 하나는 자기 것** — `--branch-context=native` 가 상속 오버라이드를 안 지워 slash 패스에서 native 를 요청하자 slash 를 쟀다 (막으려던 실패 양상 그 자체).
- TASK-2026-08-10-main-016 **smoke slash job 15연속 red 해소** — `check_release_pre_check_gates` case 7 이 살아있는 브랜치의 `state.json` 존재를 전제. 게이트는 부재를 정당 통과로 설계했는데 검사만 fail. 되주입으로 결정적화 + 환경 의존은 7b 로 분리(명시 SKIP) + **아무도 안 재던 absent 계약을 case 11 로 고정**.
- TASK-2026-08-10-main-015 **v1.1.6-beta 발행** — `cmd_release` 3번째 실전 완주 (bump → 파생물 선재생성 10검사 사전 green → note → dist → dry-run pre_check 5/5 → push → apply → verify). tag `v1.1.6-beta` (2026-08-10T11:30:53Z, whl+sdist). 범위 TASK-007~014, smoke 261→266 (신규 5). post-apply 잔여 4파일 — v1.1.5 와 동일, 선재생성 절차 재현 확인. dirty 가드가 미커밋 task 등록을 정확히 잡음 (가드 실전 검증 1회 추가).
- TASK-2026-08-10-main-014 **ADR-006 W-4 지표 재정의** — telemetry `selected_ids` additive + `summarize_telemetry` 3-tuple (query_diversity / entries_new_30d / distinct_entries_retrieved, **`*_measurable` 분모로 미측정≠0**) + Panel 8 `utilization_3tuple` north-star 교체 (hit_rate 는 은퇴 대신 보조 강등). measurable 판정은 값 비어있음이 아니라 **필드 존재** — miss(0건 조회)도 측정이다 (구현 중 이 함정을 실제로 밟고 고침). 첫 실측 = 정직한 저점 (1/8 · 1 · 0/1). `check_utilization_3tuple` 9/9, 회귀 sweep 9종 green, smoke 266. **W-1~W-4 완결**.
- TASK-2026-08-10-main-013 **ADR-006 W-3 entry 간 링크** — `related_ids` additive (legacy stem 규약 하위호환 유지) + expansion 추적 + dangling/self validation ("태어난 적 없는 링크" 검출) + W-1 skeleton 프리필 (신규 entry 가 링크를 갖고 태어남) + merge union. 실물 링크 (회고 001 ↔ ADR-005 결정 002) 로 **33일 만의 expansion 첫 발동** — `[retrospective]`/`[memora]` 양방향 cue 1 + exp 1. `check_entry_links` 9/9 (되주입 포함), smoke 265.
- TASK-2026-08-10-main-012 **ADR-006 W-2 질의 다양화** — `derive_context_query_tokens` (state.json 축 + 최근 done 제목 → token 유도, 실패 시 skill 별 trio fallback + **출처 보고**) 를 3 skill 공용으로, telemetry 에 `query_tokens`/`query_source` additive (구 라인 하위호환). 실사: 컨텍스트 8 token + **정직한 miss** (cue 0 — index 가 최근 한 달을 모른다는 신호) — 그 첫 miss 가 33일간 hit_rate=1.0 뒤에 숨어 있던 **패널 간 반올림 불일치** 를 드러내 round-at-source 로 통일. 변하지 않는 지표는 자기 소비자의 결함도 숨긴다. `check_context_query_tokens` 8/8, smoke 264.
- TASK-2026-08-10-main-011 **ADR-006 W-1 write-path advisory 루프** — `wk suggest-memory-entries` 신설: handoff §4 제목을 entry corpus 와 대조 (coverage < 0.5 → 후보 + skeleton, **무-write advisory**). 루프 실증 완주 — 첫 실측 10/10 후보 (max 0.14, 회고 재확인) → 회고를 `MEM-2026-08-10-001` 로 적재 (**33일 만의 첫 신규 entry**) → covered 0→1 + `query [retrospective,write-path]` 적중. smoke 8/8 (되주입: corpus 에 넣으면 후보가 사라짐), dispatcher 정합 10/10, mypy clean. smoke 263.
그 이전 완료 항목은 [2차 세션 기록](./sessions/adr006_retrospective_and_calibration_2026-08-10.md)과 각 task 파일에 있다.

## 5. 다음 세션 시작 포인트

### 무엇이 끝났나 (2026-08-10, 3차 세션)

**CI 재현성 회복 + smoke 병렬화** (TASK-016~019). 상세는
[세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md).
2차 세션(TASK-008~015, ADR-006 후속 + v1.1.6-beta 발행)은 §4 하단 항목 참조.

**push 전 재현 명령이 둘로 늘었다** — 둘 다 CLAUDE.md 에 적혀 있다:

```bash
# 브랜치 매트릭스 (CI 는 2축, 로컬 무인자는 1축 — 이 비대칭이 15연속 red 를 만들었다)
python3 workflow-source/tests/run_all_checks.py --branch-context=all --tmp-dir=<실디스크경로>

# SDK 매트릭스 (mcp 를 쓰는 코드를 건드렸으면)
PYTHONPATH=workflow-source python3 -m workflow_kit.common.sdk_matrix --run-local
```

전량 검사는 이제 **기본이 병렬**(`--jobs auto`)이다. 재현이 필요하면 `--jobs 1`.
저장소 전역을 관찰하는 검사를 새로 만들면 파일 안에 `REQUIRES_QUIET_REPO = True` 를
선언해야 한다 — 안 하면 병렬에서 오탐이 난다.

### 다음에 할 일 (순서)

이 세션에서 **저장소 리팩터링 조사**를 했고, 아래는 그 결과다 (근거는 §6 아래
"조사로 확정된 것" 참조). 사용자가 우선순위를 정한 항목만 실행했다 (정숙 구간 근본
수정 = TASK-019). 나머지는 미착수:

- ~~`check_mypy_strict_v0_11_3` ~ `v0_11_10` 8개 제거~~ — ✅ **완료**
  (TASK-2026-08-11-main-001, smoke 268→260).
- **`ai-workflow` 아카이브 정리** — `memory/archived/gemini/` (다른 에이전트의 옛
  백로그 50여 파일), `memory/archive/2026-07-22/` (112 파일). git 이력에 남으므로
  트리에서 덜어내도 잃는 것이 없다. 문서 스캔 검사(`check_wiki_score` 29.8s 등)가
  가벼워진다.
- **`check_cache_*` 13개 통합** — 각 1~4 케이스, 65~195줄. 영역이 같은데 잘게 쪼개져
  subprocess 기동만 13번이다.
- **`release_pipeline.py` 3897줄 분할** (위험도 높음 — 단독 task 로). 이어서
  `dashboard_data.py` 2488줄, `workflow_kit_cli.py` 2095줄.
- **`docs/presentations/*.pdf|pptx` 5.2MB** — 추적 용량의 대부분인 바이너리.
- **branch protection** (소유자 결정) — 이 저장소 `main` 은 미보호 (404 실측).
- **`mooneye` 브랜치 처리** — idle 429h+, 삭제/유지 사용자 확인 필요.

## 6. 남은 리스크 / 확인하지 못한 것

- ~~`cmd_release --apply` 실전 미검증~~ — ✅ **해소** (v1.1.4-beta 발행으로 apply
  경로 전체 실증: tag push / gh release / dashboard emit / audit append).
- **호스트 환경 의존 게이트** — 시스템 python 에는 mypy/mcp/twine 이 없어 관련 검사가
  fail 한다 (venv 에서 전부 PASS — `.venv` 에 dev,release,mcp-sdk 설치돼 있음).
  release 는 반드시 venv 에서 돌린다.
- ~~TST-WF-01 advisory red~~ — ✅ **해소** (TASK-004, 측정 재설계로 hard 복귀 +
  compliant). 남은 흔적: v0.15.18 dummy wrapper 는 측정에서 배제될 뿐 파일에
  남아 있다 — 물리 제거는 115 파일 churn 이라 별건.
- **darwin homelab 에서 mavis e2e 재확인 필요** — 검사를 정본 읽기로 바꿨으므로 mavis
  설치 호스트에서 한 번 돌려 기존과 동일하게 green 인지 확인하는 것이 안전하다.
- ~~title drift 임계 0.6 heuristic~~ — ✅ **해소** (TASK-008, 실측 캘리브레이션으로
  0.6 유지 확정 + `check_title_drift_calibration` 이 재캘리브레이션을 강제).
- ~~registry loopback 만 실측~~ — **부분 해소** (TASK-009, 비-loopback bind + pull
  왕복은 이 호스트에서 실측). **잔여**: 진짜 cross-host / 방화벽 / reverse proxy /
  TLS 종단 — 두 번째 호스트 필요 (darwin homelab).
- **`check_no_repo_write` 의 계약 한계 (미해소)** — 판정이 "실행 **후** 복원되었는가"
  라, 건드렸다 되돌리면 통과한다. `check_bidir_link_v0_13_3` 은 **이미 감시 목록에
  있었는데도** 그 이유로 안 잡혔다. 실행 *중* 감시(폴링)로 강화하면 남은 감시 대상
  다수가 같은 이유로 red 가 될 수 있어 범위가 크다. **되돌리는 것은 안 건드리는 것이
  아니다.**
- **amend Guard 2 의 staged-삭제 fatal (TASK-2026-08-11-main-002, planned)** —
  `_git_dirty_paths()` 를 `git add -- ` 에 넘기는 경로가 이미 staged 된 삭제
  (`D `) 에서 pathspec 불일치로 fatal. `--allow-dirty` + staged 삭제 조합의 실전
  release 에서 재현 가능. `check_release_wrapper_args` case 5·6 도 같은 상태에서
  red (tree clean 이면 자동 통과라 평소엔 안 보인다).
- **정숙 구간 3건은 본질적으로 직렬** — `check_no_repo_write`(15.6s, 전역 관찰),
  `check_parallel_smoke`(runner 호출), `check_source_without_runtime_layer`(저장소
  복사). 병렬화로 더 줄이려면 이들의 설계 자체를 바꿔야 한다.
- 이 밖의 과거 세션 리스크 (`--force` 3rd layer 미가동)는 변화 없음 —
  2026-08-09 까지의 세션 기록 참조.

## 7. 저장소 구성 조사 (2026-08-10 3차 세션)

리팩터링 판단 근거. git 추적 **1766 파일**:

| 영역 | 파일 | 비고 |
|---|---|---|
| `workflow-source` | 898 | tests 268, workflow_kit 129, releases 171, tools 74 |
| `ai-workflow` | 778 | **backlog tasks 193 + 아카이브 142**, wiki 81, sessions 18 |
| `docs` | 36 | presentations PDF/PPTX 가 **5.2MB** |

- **"버전 접미사 71개 = 중복" 은 틀렸다** (이 세션에서 정정). 주제별로 갈라보니
  대부분 고유하고, 진짜 중복은 `mypy_strict_v0_11_3~10` 8개뿐이다.
- 테스트가 느렸던 주된 원인은 **저장소 크기가 아니라 실행 방식**이었다 (순차 →
  병렬로 345s→118.8s). 위 정리 항목 중 실행 시간을 실제로 줄이는 것은 mypy 8개
  (15초) 뿐이고 나머지는 저장소 위생 문제다 — 섞어서 "정리하면 빨라진다" 고 말하지
  않는 편이 정확하다.

**이전 세션들의 교훈**은 각 세션 기록에 있다:
[2026-08-09](./sessions/cli_dispatcher_and_rotation_2026-08-09.md) ·
[2026-08-08](./sessions/multi_workspace_orchestration_2026-08-08.md) ·
[2026-08-05](./sessions/self_application_and_mcp_2026-08-05.md) ·
[2026-08-07 MCP](./sessions/mcp_load_verification_2026-08-07.md) ·
[2026-07-27](./sessions/selfref_cleanup_and_ci_measurement_2026-07-27.md)
