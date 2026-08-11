# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-11 (리팩터링 사이클 + 후속 완결 — TASK-2026-08-11-main-001~011 전부 done)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **저장소 리팩터링 사이클 완결** (2026-08-11, TASK-001~008).
  3차 세션 조사(§7) 후보 4건 전부 완료 — mypy strict 부분집합 8개 제거
  (TASK-001) + **아카이브 185파일 정리** (TASK-003) + **`check_cache_*` 13개
  → 1개 통합** (TASK-004) + **`release_pipeline.py` 안전 부분 분할**
  (TASK-007, 3908→3174줄 + 모듈 4개 — 소스-스캔 검사 25종 기준 분석 지도를
  먼저 만들고 ATTR-ONLY 그룹만 추출, 검사 무수정 21종 green). smoke
  **268→248**. 도중 결함 수정 4건: **CI smoke red 해소** (TASK-005),
  **amend Guard 2 staged-삭제 fatal** (TASK-002), **PERF-WF-04 저장소 오염 +
  sandbox race** (TASK-006), **원본-무결성 관찰 검사 3건 정숙화** (TASK-008).
  남은 후보는 §5. 상세: [세션 기록](./sessions/repo_refactoring_and_defect_fixes_2026-08-11.md).
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
- 현재 주 작업 축: **대형 파일 분할 완결 (3/3)** — release_pipeline (TASK-007) + dashboard_data (TASK-010) + workflow_kit_cli (TASK-011, 2095→583 + 모듈 5개). 누적 −3,208줄, 전부 verbatim 이동·테스트 무수정. 남은 후보는 소유자 결정 항목들 (§5).
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
- TASK-2026-08-11-main-011 **workflow_kit_cli.py 안전 부분 분할** — 2095→**583줄** (−1512) + 모듈 5개 (`cli_registry` 48 / cache 619 / memory 618 / release 262 / okf 216). 디스패처가 argparse 가 아니라 **`@register` 레지스트리**라 `cli_registry.py` 선행 분리가 핵심 처방 — 신규 모듈이 registry 만 import 해 순환 0 이고, `check_workflow_kit_cli` 의 최상위-이름 재-exec 방식과도 양립 (COMMANDS 가 캐시된 registry 에 산다). SOURCE-BOUND 2핸들러 (`cmd_release_create`/`cmd_release_status`) 잔류, 신규 import 는 tool 등록 호출보다 위 (ALREADY_REGISTERED 순서), `python -m`·`[project.scripts] wk` 계약 보존. mypy strict 137파일 0 오류, CLI **53/53** · dispatcher **10/10** · entry points 32종 · release 5종 green, 테스트 수정 0.
- TASK-2026-08-11-main-010 **dashboard_data.py 안전 부분 분할** — 2488→**1526줄** (−962) + 모듈 3개 (HTML 렌더러 515 / MD 렌더러 283 / workspace-roots 헬퍼 287). 분석 지도: 소스-바인딩은 `check_convention_single_source` 의 `DRIFT_LEDGER_RELPATH` **정의 잔류** 1건뿐, monkeypatch 0 — release_pipeline (25검사 바인딩) 보다 자유. package 라 명시 from-import 재수출 + `__all__` 확장 (underscore 16개 — mypy `no_implicit_reexport` + ruff F401 동시 충족), `_render_panel_1` 의 `DRIFT_LEDGER_RELPATH` 는 function-level import 로 순환 회피. **mypy strict 132파일 0 오류** (CI 게이트), 관련 검사 12종 green, 테스트 수정 0, verbatim 이동 byte 대조.
- TASK-2026-08-11-main-009 **docs/presentations 파생 바이너리 제거** — `ai-agent-onboarding.pdf` (5.2MB, 트리 추적 용량 대부분) + `.pptx` (134KB) 제거, 소스 3건 (`.html` deck + design md + intro html) 보존. PDF 는 HTML 에서 Chrome headless 로 재생성 가능 (TASK-2026-08-06-main-004 기록 확인). 참조는 과거 task 기록뿐, git 이력 보존 (TASK-003 처방).
- TASK-2026-08-11-main-008 **원본-무결성 관찰 검사 3건 정숙화** — TASK-007 검증에서 `version_auto_sync` 가 "원본을 건드렸다: pyproject.toml" assert 로 1회 flake. 단독 green + 재현 시도 (표적 3회 + 전량 2회 + md5 watcher) 전부 미재현, 용의자 2건 (`auto_bump` 검사 / drift case 7 auto-bump dry-run) 은 코드·실측 무혐의. 같은 byte-대조 assert 를 가진 3검사 (`version_auto_sync`/`self_recovering`/`bidir_link`) 는 **전역 관찰**이므로 `REQUIRES_QUIET_REPO` 선언 대상이었다 (TASK-018 §2.53 규칙의 적용 누락). 정숙 3→6. **잔여**: transient pyproject writer 정체 미상 (§6).
- TASK-2026-08-11-main-007 **release_pipeline.py 안전 부분 분할** — 3908→**3174줄** (−734) + 모듈 4개 (changelog 335 / dist 163 / frontmatter 178 / emit 187). **분석 지도 먼저**: 25개 검사가 이 파일 소스를 스캔하므로 심볼 전수를 SOURCE-BOUND (문자열/AST/monkeypatch 바인딩 — 잔류) vs ATTR-ONLY (재수출로 이동 가능) 로 분류 후 안전 그룹만 추출. 함정 2건 명중: `import *` 는 `_` 이름을 안 가져온다 (`__all__` 명시로 해결) / package-less 로드라 상대 import 불가 (sys.path + 절대 import). 순환이 필요해지는 emit 2함수 (`read_version` 직접 호출) 는 잔류 — 작은 안전한 분할 > 영리한 깨진 분할. 격리 worktree 에서 구현·검증 (관련 검사 21종 green, 테스트 수정 0) 후 반영. 잔여 대형 파일: `dashboard_data.py` 2488 / `workflow_kit_cli.py` 2095 — 같은 절차 권장.
- TASK-2026-08-11-main-006 **PERF-WF-04 저장소 오염 제거 + sandbox 소멸-파일 내성** — 전량 실행 중 `check_bidir_link_v0_13_3` flake (`shutil.Error`, `tmp_audit_perf.log` 소멸 race). 근본 2겹: PERF-WF-04 벤치마크가 **살아있는 저장소 루트에** 임시 파일을 100회 명멸 (PERF-WF-05 는 v1.0.0 에 temp 처방을 받았는데 04 만 누락) → temp 로; `_repo_sandbox` copytree 에 소멸(ENOENT)-내성 (`copy_function` + 선별 재던짐 — 그 외 오류는 그대로). 테스트 2건 (경로 포착 / 소멸·권한 주입), **되주입 양방향 실증**. 부수 교훈: **게이트 명령을 파이프에 넣으면 exit 이 덮인다** — 이 flake 가 push 를 통과한 이유 (pushed commit 은 사후 무결 확인). 이후 검증 체인은 pipefail/단계 분리.
- TASK-2026-08-11-main-002 **amend Guard 2 staged-삭제 fatal 수정** — `git add -- *dirty` 가 이미 staged 된 삭제 (`D `, worktree·index 모두 부재) 에서 pathspec fatal. `_git_dirty_paths(needs_add_only=True)` 신설 (porcelain worktree 열 기준 add 대상 선별, 기본 동작 불변 — bump clean-tree 가드는 계속 전체를 봄) + Guard 2 에서 보고용 전체와 add 대상 분리 (add 대상이 비면 amend 직행). unstaged 삭제 (` D`) 는 선별에 **포함** — add 로 삭제를 stage 하는 정당 경로. 검사: case 5 삭제-인지 / case 6 선별 대조 / **case 10 되주입** (tmp repo + `_git_toplevel` monkeypatch — full add rc=128 함정과 해법을 결정적 고정). 11/11, 무력화 시 case 10 이 잡음. mypy 전후 89 동일 (신규 0).
- TASK-2026-08-11-main-005 **smoke CI red 해소 (version_flag ← phase3 dist 오염 우연 의존)** — CI smoke 는 **전 세션 TASK-019 (59f3365) 부터 red** 였다 (f4f7fc6 까지 green, 이후 4연속 red — 전 세션 마지막 2 push 는 CI 미확인 종료, handoff 는 로컬 green 만 기록). 원인: `check_release_pipeline_phase3` 가 원본 `dist/` 에 실빌드를 남기던 오염을 TASK-019 가 격리하자, 그 부산물에 우연히 의존하던 `check_release_pipeline_version_flag` test 3 의 무조건 `out["tag"]` 기대가 CI (dist 부재) 에서 KeyError. 로컬은 릴리스가 남긴 dist (gitignored) 로 계속 green — 로컬/CI 비대칭 4번째 사례. test 2 의 `has_staging` 분기와 같은 처방, dist 유/무 **양방향 3/3 실증**. **오염 제거는 그 오염에 기대던 소비자를 드러낸다 + push 후 CI 확인까지가 검증이다.**
- TASK-2026-08-11-main-004 **check_cache_* 13개 → check_cache.py 1개 통합** — test 본문 verbatim 보존 (31 case, 버전 이력이 담긴 함수명 유지), 변경은 로더 보일러플레이트 공용화뿐 (`_load` bare 등록 / `_load_wk` package 등록 — 로드 의미론이 달라 2계보를 하나로 합치지 않음). 충돌 상수 5건은 byte-identical 로드라 최초 정의로 dedupe (본문 수정 0). 31/31 PASS, smoke 260→248, 파생 수치 3문서 동기.
- TASK-2026-08-10-main-018 **smoke 병렬화** — CI job 604s 중 smoke 576s 가 병목, 시간 분포는 극단적(상위 13개=50%, 하위 133개 합계 9.8s). `--jobs auto` + **정숙 구간**(파일 안 `REQUIRES_QUIET_REPO` 선언, §2.53). `check_source_without_runtime_layer` 의 원본 rename → 사본 검증 (**`finally` 는 SIGKILL 에 안 돈다**). **CI 576s→220s**, 로컬 345s→118.8s. `check_parallel_smoke` 8 case.
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
- ~~`ai-workflow` 아카이브 정리~~ — ✅ **완료** (TASK-2026-08-11-main-003,
  185파일 제거, wiki 참조 1건 + freeze 최소 세트 6건 보존, README 링크 교정).
- ~~`check_cache_*` 13개 통합~~ — ✅ **완료** (TASK-2026-08-11-main-004,
  31 case verbatim 보존, smoke 260→248).
- ~~`release_pipeline.py` 분할~~ — ✅ **완료** (TASK-2026-08-11-main-007,
  3908→3174 + 모듈 4개, 분석 지도 방식). `dashboard_data.py` ✅ (TASK-010, 2488→1526),
  `workflow_kit_cli.py` ✅ (TASK-011, 2095→583) — **대형 파일 분할 완결**.
- ~~`docs/presentations/*.pdf|pptx` 5.2MB~~ — ✅ **완료** (TASK-2026-08-11-main-009, 파생 바이너리 제거·소스 보존).
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
- ~~amend Guard 2 의 staged-삭제 fatal~~ — ✅ **해소** (TASK-2026-08-11-main-002,
  `needs_add_only` 선별 + case 10 되주입으로 고정. §4 참조).
- **transient pyproject writer 정체 미상 (2026-08-11 1회 관측)** — 병렬 전량
  실행 중 원본 `pyproject.toml` 이 일시 변경됐다 되돌아왔다 (version_auto_sync
  byte-대조가 포착). 재현 실패 (표적 3회 + 전량 2회 + 50ms md5 watcher).
  관찰자 3검사는 정숙화(TASK-008)로 위양성 차단됨. 재발 시
  `/home/yklee/tmp/watch_pyproject.sh` 패턴 (md5 폴링 + 프로세스 스냅샷) 으로
  writer 를 특정할 것. `check_no_repo_write` 의 "실행 후 복원" 계약 한계와
  같은 뿌리로 추정.
- **정숙 구간 6건** (TASK-008 로 3→6) — `check_no_repo_write`(전역 관찰) /
  `check_parallel_smoke`(runner 호출) / `check_source_without_runtime_layer`
  (저장소 복사) 는 본질적 직렬이고, `version_auto_sync` / `self_recovering` /
  `bidir_link` 는 원본 byte-대조 관찰 때문 (TASK-008). 병렬화로 더 줄이려면
  이들의 설계 자체를 바꿔야 한다.
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
