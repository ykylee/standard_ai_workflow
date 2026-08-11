# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-11 (5차 세션 — TASK-2026-08-11-main-017 종결: macOS 회귀 4건 발견 후 검사 이식성 fix, 2026-08-11 backlog 17건 전부 종결)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **2026-08-11 backlog 17건 전부 종결** (5차 세션 TASK-017 추가 종결). **darwin homelab (macOS) 검증 완료** — 이 호스트에서 전량 2축 green.
  - **TASK-017 (done)**: 1챕터에서 macOS 1패스 **245/249, 4 FAIL** 발견 (4차 handoff 의 "249/249" 는 Linux CI 환경). 2챕터에서 4건이 **전부 같은 뿌리**로 판명 — macOS 에서 `/var`·`/tmp` 가 `/private/...` 로 가는 symlink 라, 정규 경로를 방출하는 production 과 `mktemp` raw 경로를 string 비교한 **검사** 가 갈렸다. **production 무수정, 검사 fixture 4곳을 `.resolve()` 로 통일.** 3챕터에서 재검증 중 별개 FAIL 2건 (이 task 파일의 frontmatter 부재 + handoff 미등재로 인한 `task_status_mismatch`) = 1챕터가 남긴 메모리 문서 드리프트, 3문서 정합으로 해소.
  - **얻은 것**: 기능 회귀가 아니라 **검사의 플랫폼 이식성 결함**이었고, Linux CI 에서는 `/tmp` 가 symlink 가 아니라 **영영 안 드러난다**. SDK 매트릭스·브랜치 매트릭스와 같은 계열의 "로컬에 그 축이 없어서 못 보던 것" 이 하나 더 닫혔다 — **darwin homelab 이 그 축이다.**
  - 부수: `.venv` 미존재 → uv venv 신설 (3.13.13) + `uv pip install -e 'workflow-source/[dev,release,mcp-sdk]'`. mavis 데몬 system-wide 정상. `~/.mavis/bin/mavis` symlink broken = user-level (구 격리) stale, 무시 가능.
- 직전 기준선: **2026-08-11 backlog 16건 전부 종결** (4차 세션 — TASK-014~016). **기술보고서 논문 양식 문서** 완성 (`docs/reports/` 계획 md + 보고서 html, 사후 검토 4회전: 수치 날조 정정 → 어휘 정리 → 학습회 독립화) + **로컬 병렬 TIMEOUT flake 근본 해소** (`CHECK_TIMEOUT_S` 파일 안 선언 신설, 위험군 6검사 150s, 전량 2축 ×2회 TIMEOUT 0) + **watcher ready handshake** (CI flake 수정) + 소유자 결정 2건 (TASK-014 누적 표기 미삽입 / branch protection 보류). 상세: [4차 세션 기록](./sessions/tech_report_and_timeout_fix_2026-08-11.md). 그 이전 (저장소 리팩터링 사이클 TASK-001~013, 대형 파일 분할 −3,208줄 + 결함 4건 + 아카이브 + check 통합, smoke 268→249): [리팩터링 세션](./sessions/repo_refactoring_and_defect_fixes_2026-08-11.md). 그 이전 (CI 재현성 회복 + smoke 병렬화, 15연속 red 해소): [3차 세션](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md).
- 현재 주 작업 축: (없음 — TASK-2026-08-11-main-017 종결로 2026-08-11 backlog 17건 전부 done).
- **소유자 결정 대기 (1건)**: `state.json` 을 **생성물로 볼 것인가, 손 문서로 볼 것인가**. TASK-017 4챕터에서 기계 판독 필드는 생성기와 정합시켰으나, `recent_done_items` 의 산문·정렬은 여전히 다르다 (생성기 = task 제목 + 날짜 정렬 / 유지본 = 상세 요약 + 손 정렬). 어느 쪽도 명시돼 있지 않아 다음 사람이 또 밟는다.
- 다음 후보 축: federation self-host add (multi_workspace_orchestration.md §0.7) → cross-host federation (두 번째 호스트 = ? — 사용자 결정) / memory_index 3-tuple 지표 추이 관찰. **v1.1.6-beta 발행 완료, ADR-006 후속 W-1~W-4 완결**. (v1.1.0·v1.1.1 노트 누적 표기는 TASK-014 에서 **미삽입 확정**, branch protection 은 소유자가 **보류 결정** (2026-08-11) — 둘 다 후보 축에서 제거.)
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
- TASK-2026-08-11-main-018 — state.json 을 생성물로 전환 (정본 선언 + 종료 절차 + drift 검사)
## 3. 차단 작업

- 현재 `blocked` 작업:
-
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-08-11-main-022 **하네스 파생본 통일** — 정본에 **§11 메모리 갱신 경로 + 파싱 계약**을 신설하고 `render_entrypoint_rules()` 경로로 전 하네스에 주입, `check_standard_single_source` 가 진입점의 §11 누락을 잡는다. **결함 26→14** (주요 진입점 8개는 기존 주입점을 타고 자동, `.claude/commands/*` 3개는 직접 주입 — 이번 조사의 출발점이던 파일들). 부수: goose 가 emit 하던 **존재하지 않는 경로**를 `wk` 로 교체 + `pyproject` 의 "bootstrap 이 skills 를 복사한다" 거짓 전제 정정. **커밋 전 FAIL 10건이 단일 뿌리로 잡혔다** — 필드 추가 시 스냅샷 fallback 생성자를 놓쳤고, **정본이 없는 환경에서만 실행되는 경로**라 mypy strict 가 아니었으면 배포처에서만 터졌을 결함이다. 교훈: **정본·추출기·스냅샷은 한 커밋 안에서 같이 움직인다.**
- TASK-2026-08-11-main-020 **하네스 진입점 전수검사 (진단)** — 렌더러 32개 중 **26개**가 메모리 갱신을 지시하며 방법을 안 알려줬고, 유일한 '정상' 1개조차 **존재하지 않는 경로**를 가리켰다. 배포물을 전수 확인해 근본이 뒤집혔다: 이건 문서 결함이 아니라 **소비자에게 실행 가능한 경로가 처음부터 없는 것**이었다 (`skills/` 는 pip 패키지에도 bootstrap 번들에도 없고, `wk` 68개 명령 중 해당 기능 0개). 에이전트가 손으로 쓴 것은 규율 부족이 아니라 다른 선택지가 없어서였다. 아키텍처 결정(정본 하나 + `wk` 창구 하나 + 하네스별 파생본) 기록 후 TASK-021/022/018 로 분해.
- TASK-2026-08-11-main-021 **`wk` 에 session-start / backlog-update / doc-sync 노출** — skill 구현 3개(1,561줄)를 배포되는 `tools/` 로 올려 **소비자에게 없던 실행 경로를 만들었다**. `skills/` 는 pip 패키지에도 bootstrap 번들에도 안 들어가서, `pip install` 을 해도 이 기능을 부를 방법이 없었고 그래서 모든 하네스에서 에이전트가 메모리 문서를 손으로 썼다 (`workflow_writes.py` 의 계약이 한 번도 적용되지 않은 이유). 원 경로엔 wrapper 만, **wk 68→71 명령**. 이동이 검사 3종을 깼고 전량 2축이 잡았다 — **참조 지도를 `read_text` 만으로 뜬 것이 화근**이었다 (모듈 로드·소스 문자열 스캔이 같은 결합). 검증: 정숙 저장소 2축 249/249.
- TASK-2026-08-11-main-017 **darwin homelab 검증** — macOS 에서 전량 2축 1패스 → **245/249, 4 FAIL 발견** (4차의 "249/249" 는 Linux CI 환경). 4건이 **전부 같은 뿌리**: macOS 에서 `/var`·`/tmp` 가 `/private/...` 로 가는 symlink 라, **정규 경로를 방출하는 production 과 `mktemp` raw 경로를 string 비교한 검사**가 갈렸다. production 무수정, 검사 fixture 4곳을 `.resolve()` 로 통일 (`branch_resolver_agreement` 5/5 · `branch_scoped_memory` 10/10 · `git_conflict_resolver_v0_11_24` 8/8 · `workflow_state_refresh_hint` PASS). `git_conflict_resolver` 는 한 응답 안에 `conflicts[].file_path`(resolve) 와 `source_context.files`(raw) 가 **공존**해 case 4 만 실패했다. **기능 회귀가 아니라 검사의 플랫폼 이식성 결함이고, Linux CI 에서는 영영 안 드러난다** — SDK 매트릭스·브랜치 매트릭스와 같은 계열의 "로컬에 없던 축". 재검증 중 별개 FAIL 2건 (이 task 파일 frontmatter 부재 + handoff 미등재 `task_status_mismatch`) 은 1챕터가 남긴 메모리 문서 드리프트로, **task 를 열 때 3문서를 동시에 맞추지 않으면 그 자체가 red** 라는 것을 검사가 잡아냈다.
- TASK-2026-08-11-main-015 **로컬 병렬 TIMEOUT flake 해소** — `CHECK_TIMEOUT_S` 파일 안 선언 신설 (runner 가 AST 로 읽어 `--timeout` 과 **max** — 상한을 늘릴 수만 있음, `REQUIRES_QUIET_REPO` 와 같은 패턴). 부하 실측 ≥40s 위험군 6검사 (wiki_score 57s / release_status·auto_bump·summary 53~55s / release_pipeline_lib 44s / mypy_config_actually_loaded 43s) 에 150s 선언. `check_parallel_smoke` case 10 (되주입 양방향 + decoy 불인정 + max 의미론) + `--tests-dir` 외부 경로 ValueError 수정. **전량 2축 ×2회 = 4패스 249/249, TIMEOUT 0.** CLAUDE.md 에 규약 문서화 (solo ~25s+ 는 선언).
- TASK-2026-08-11-main-016 **학습회 자료 → 사내 기술보고서 논문 양식 문서** — 산출물 2건: 작성 계획 (`docs/reports/ai-agent-workflow-tech-report-plan.md`) + 보고서 (`docs/reports/ai-agent-workflow-tech-report.html`, 논문 8장 + 참고문헌, 단일 파일, A4 12p). 사례 3건 실명 승격, 수치는 dashboard·태그 트리 실측. **사후 검토 4회전** — ①내용 (실명 오류·전재 누락), ②수치 전수 (기간 "14개월" 날조 → 4개월, "smoke 24→249" → 199→249, CLI 65+ → 68 등 정정 8건 — 교훈: **산문 속 수치가 날조의 주 경로**), ③문체·어휘 (비일상 어휘 12종 교체/풀이, 3원리 일상어 표기, 폭 920px·부제 축약), ④**학습회 독립화** (사용자 결정 — 보고서에서 학습회·발표 서술 전부 제거, 참고문헌의 덱 항목 삭제. 계획 문서는 이력이므로 유지). placeholder (작성자/문서번호) 는 사용자 기입. 부수: 검증 중 CI flake 발견 → watch_transient_writer ready handshake 수정 (708eb94).
- TASK-2026-08-11-main-014 **v1.1.0·v1.1.1 노트 누적 표기 미삽입 확정** — 태그 시점 smoke 파일 수는 실측 (251/252, `git ls-tree`) 이나 당시 **전량 green 실행 기록이 없어** N/N PASS 사후 삽입은 검증 안 된 주장 날조 (v1.1.3 §2.8 원칙). 파서 2곳 (`check_smoke_trend_cross` / `cmd_release` step 3.4) 은 최신 노트만 읽어 동작 지장 0, 재발은 v1.1.3+ 절차가 방지. 두 노트 무수정, 후보 축에서 제거 (사용자 결정).
- TASK-2026-08-11-main-011 **workflow_kit_cli.py 안전 부분 분할** — 2095→**583줄** (−1512) + 모듈 5개 (`cli_registry` 48 / cache 619 / memory 618 / release 262 / okf 216). 디스패처가 argparse 가 아니라 **`@register` 레지스트리**라 `cli_registry.py` 선행 분리가 핵심 처방 — 신규 모듈이 registry 만 import 해 순환 0 이고, `check_workflow_kit_cli` 의 최상위-이름 재-exec 방식과도 양립 (COMMANDS 가 캐시된 registry 에 산다). SOURCE-BOUND 2핸들러 (`cmd_release_create`/`cmd_release_status`) 잔류, 신규 import 는 tool 등록 호출보다 위 (ALREADY_REGISTERED 순서), `python -m`·`[project.scripts] wk` 계약 보존. mypy strict 137파일 0 오류, CLI **53/53** · dispatcher **10/10** · entry points 32종 · release 5종 green, 테스트 수정 0.
- TASK-2026-08-11-main-010 **dashboard_data.py 안전 부분 분할** — 2488→**1526줄** (−962) + 모듈 3개 (HTML 렌더러 515 / MD 렌더러 283 / workspace-roots 헬퍼 287). 분석 지도: 소스-바인딩은 `check_convention_single_source` 의 `DRIFT_LEDGER_RELPATH` **정의 잔류** 1건뿐, monkeypatch 0 — release_pipeline (25검사 바인딩) 보다 자유. package 라 명시 from-import 재수출 + `__all__` 확장 (underscore 16개 — mypy `no_implicit_reexport` + ruff F401 동시 충족), `_render_panel_1` 의 `DRIFT_LEDGER_RELPATH` 는 function-level import 로 순환 회피. **mypy strict 132파일 0 오류** (CI 게이트), 관련 검사 12종 green, 테스트 수정 0, verbatim 이동 byte 대조.
- TASK-2026-08-11-main-009 **docs/presentations 파생 바이너리 제거** — `ai-agent-onboarding.pdf` (5.2MB, 트리 추적 용량 대부분) + `.pptx` (134KB) 제거, 소스 3건 (`.html` deck + design md + intro html) 보존. PDF 는 HTML 에서 Chrome headless 로 재생성 가능 (TASK-2026-08-06-main-004 기록 확인). 참조는 과거 task 기록뿐, git 이력 보존 (TASK-003 처방).
그 이전 완료 항목은 [3차 세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md)·[2차 세션 기록](./sessions/adr006_retrospective_and_calibration_2026-08-10.md)과 각 task 파일에 있다.

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
- ~~branch protection~~ — **보류 결정** (2026-08-11, 소유자). `main` 미보호 (404 실측)
  상태를 인지한 채 일단 켜지 않기로 함. 재검토 시 `wk check-branch-protection` 으로
  현황 판정부터 (도구는 판정만 한다 — v1.1.2 §2.3).
- ~~`mooneye` 브랜치 처리~~ — ✅ **완료** (TASK-2026-08-11-main-012, `origin/mooneye`
  삭제. 고유 커밋 0 — 172 커밋 전부 main 에 존재, `active/mooneye/` 부재로
  memory 아카이브 해당 없음).

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
  관찰자 3검사는 정숙화(TASK-008)로 위양성 차단됨. **감시 수단은 저장소에
  고정됨** (TASK-013, `workflow-source/tools/watch_transient_writer.py` —
  일회용 `~/tmp` 스크립트의 승격판): 재발 의심 시 전량 검사 옆에 백그라운드로
  세워 두면 diff + ps 전량 + fuser 를 이벤트별로 남긴다 (로그는 temp 에만,
  저장소 안 로그는 거부). `check_watch_transient_writer` 5 case 가 되주입
  양방향으로 계약을 고정. `check_no_repo_write` 의 "실행 후 복원" 계약 한계와
  같은 뿌리로 추정 — writer 특정 자체는 재발 시의 일이다.
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
