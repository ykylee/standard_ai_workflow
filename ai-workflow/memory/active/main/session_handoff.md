# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-10 (cmd_release 사용성 회복 + session close)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **cmd_release 사용성 회복** (2026-08-10, TASK-2026-08-10-main-001~002). 전량 검사 **260/260 PASS** (격리 venv). `release --dry-run` 이 pre_check 5/5 를 실제로 통과한다 — v1.1.0~v1.1.3 네 릴리스를 수동 발행하게 만들던 doctor/state 만성 실패의 3뿌리(경로 이중 결함 / TST-WF-01 판정식 / state 죽은 계약)를 해소. **무인자 `release` 는 이제 dry-run** (`--apply` 명시 시에만 발행). 직전 기준선: v1.1.3-beta 발행 (2026-08-09, tag → `6cadcca`).
- 현재 주 작업 축: 릴리스 파이프라인 정상화 close. **다음 릴리스는 `cmd_release` 경로로 발행해 실전 검증할 것** (수동 절차 불필요해졌는지 확인).
- 다음 후보 축: TST-WF-01 측정 재설계 (관행 인식형 counting → partial 예외 제거) / branch protection (소유자 결정) / v1.1.0·v1.1.1 노트 누적 표기 사후 삽입 여부.
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
- TASK-2026-08-10-main-001 **cmd_release 사용성 회복** — pre_check 만성 실패 3뿌리 해소: (1) doctor 호출이 `workflow-source/workflow-source/` 를 탐색해 **0 files 를 재고 non_compliant** → repo root + `--config-path` + env 명시 (2) TST-WF-01 이 inline `check()`/`failures.append` 관행을 못 봐 만성 red → dummy wrapper 전례 대신 `partial_rules.testing` **선언된 예외** (3) state 검사의 `memory.last_freeze` 는 writer 가 사라진 죽은 계약 → `generated_at` (legacy 하위호환). + **무인자 `release` dry-run 반전** + 개별 `--skip-*` 5종 + mypy "실행 불가 vs 오류" 출처 구분. `check_release_pre_check_gates` 10/10 신설. venv 실측 pre_check 5/5 통과. 전량 **260/260 PASS**.
- TASK-2026-08-10-main-002 **check_mavis_attach_e2e 호스트 사본 제거** — darwin 절대경로 하드코딩 사본 탓에 darwin 외 호스트에서 무조건 red 였던 것을 실제 `~/.minimax/mcp/mcp.json` 정본 읽기로 교체. 부재 시 graceful skip (`--require-mavis` 로 강제). 로드 경로는 fake 항목 실증 ALL PASS (13 tools + tool call 2종).
- TASK-2026-08-09-main-017 **v1.1.3-beta 발행** (TASK-009~016, 11 커밋). 오늘 고친 릴리스 도구 3건이 **이번 릴리스에서 실제 검증됐다** — `_git_toplevel`(정당한 amend 거부) / `release-verify`(실제 조회 성공) / **step 3.4**(`ok: True, 259/259` — 실제 경로 동작). 수동 발행 이유: `cmd_release` pre_check 의 doctor/state 가 만성 실패인데 개별 skip 이 없다. **주의: `release` 는 `--dry-run` 없으면 기본이 APPLY**.
- TASK-2026-08-09-main-016 릴리스 절차에 **노트 누적 수치 검증** step 3.4 신설 — TASK-015 가 "검사가 아니라 절차 문제" 로 짚은 자리. note 부재 / 표기 부재 / 수치 불일치를 각각 잡고 조치를 안내한다. **자동으로 채우지 않는다** — 그 줄은 *전량 PASS 했다* 는 주장이고, 도구가 대신 적으면 거짓이 된다 (회귀 case 9b 가 쓰기 금지를 고정). 정규식은 dashboard 와 같은 것을 쓴다. 10/10 PASS.
- TASK-2026-08-09-main-015 `check_smoke_trend_cross` **오독 정정 — 검사가 맞았다**. 노트의 누적 수치는 *릴리스 스냅샷이 아니라 살아있는 지표* 였다 (smoke 가 늘면 최신 노트를 갱신해 온 관행; `Beta-v1.0.0.md` 199→…→234). 내가 본 '모순' 은 **사후 갱신을 모르고** 한 오독 — 태그 시점엔 199/199 정합. red 구간은 v1.1.0·v1.1.1 이 **표기를 빠뜨린** 탓. 판정 복원 + 노트 257→**259**. **검사를 고치기 전에 그 검사가 지켜 온 관행을 먼저 확인한다.**
- TASK-2026-08-09-main-014 `memory-index-query` **beta → stable** — §3.1 6 조건 중 2 미충족을 채움: **error_code 3종**(이전엔 stderr + rc 2 뿐이라 실패 종류 구분 불가 → `ErrorOutput` 을 stdout 에) + SKILL.md 실행 예시. smoke 26/26. **skill 14 stable / 0 beta**. **이번엔 문서가 맞았다** — 기준 문서(criteria)는 살아 있었고 상태 문서만 낡았다.
- TASK-2026-08-09-main-013 `phase_13_followup` **전반 실측 대조** — 정합 5 / 정정 3. **harness 는 숫자가 아니라 정의가 문제였다**: `mavis` 를 matrix 에 넣자 `check_harness_v0_15_9` 가 깨졌고, 그건 **project-local 산출물 0** 인 harness 라 디렉터리 없는 게 설계였기 때문이다 (`custom` 도 같은 부류). `harnesses.supported` = *overlay 배포* 목록 → 11 이 맞다. `NON_OVERLAY_HARNESSES` 에 이유와 함께 선언. **검사도 하드코딩 10개에 갇혀 새 harness 를 몰랐다** → 정본 유도로 교체.
- TASK-2026-08-09-main-012 Phase 13 **P1 묶음 close** — **세 항목이 전부 실제와 달랐다**. P1-1 "pre-step 부재" → v0.15.21+ 에 이미 있었고, 남은 건 (a) 최근 3 release 가 수동 발행이라 CHANGELOG 가 안 갱신된 것(**오늘 내가 그렇게 냈다**) (b) `(v3.0)` 오탐이 `[3.0.1]` 을 최신 자리에 앉힌 것 → `NON_RELEASE_VERSIONS` 선언 예외. P1-2/P1-3 은 **이미 v0.11.24 에서 stable**. 실측 skill stage **13 stable / 1 beta**(유일 beta = `memory-index-query`).
- TASK-2026-08-09-main-011 telemetry acceptance 를 **윈도 기반** 으로 — TASK-010 이 적은 사각을 메움. `summarize_telemetry(window_days=30)` 에 `window_source_count` 등 additive (전체 기간 필드 불변). `check_telemetry_window.py` 8/8 — **case 4 가 핵심**: *전체 4 source 인데 윈도 1* 을 잡는다. AC2 acceptance 를 "최근 30일 window_source_count ≥ 4" 로 갱신. 발견: `check_telemetry_source_diversity.py` docstring 은 자동 활성 전환을 **이미 정확히 적고 있었다** — TASK-010 의 문서 오류를 **검사는 알고 있었다**.
- TASK-2026-08-09-main-010 Phase 13 **P0-2 close** — AC2 4 source + hit_rate 1.0 수렴. **문서가 두 군데 틀려 있었다**: 1 source 는 `dispatcher` 가 아니라 `session-start` 였고(132 calls), "3 skill 활성화 필요" 는 **이미 v0.15.21+ 에서 끝난 일**이었다 (세 스크립트 코드가 동일). 남은 건 wiring 이 아니라 **실행 이력의 부재** — 한 번씩 돌리자 즉시 4 source. acceptance 약점도 기록: "4 source 등장" 은 1회씩이면 충족돼 *지속적 사용* 을 못 잰다.
## 5. 다음 세션 시작 포인트

### 무엇이 끝났나 (2026-08-10 세션)

**cmd_release 사용성 회복** (TASK-001) + **mavis e2e 호스트 사본 제거** (TASK-002).
전량 검사 **260/260 PASS**. 상세는 §4 두 항목과 task 파일에 있다.

**다음 릴리스가 실전 검증이다** — 이제 `cmd_release` 경로로 발행해 본다:

```bash
# 1. dry-run 으로 plan 검토 (무인자도 dry-run 이다, v1.1.4+)
PYTHONPATH=workflow-source .venv/bin/python workflow-source/tools/release_pipeline.py release --dry-run
# 2. pre_check 5/5 확인 후 발행
PYTHONPATH=workflow-source .venv/bin/python workflow-source/tools/release_pipeline.py release --apply
```

주의: **mypy/mcp/twine 이 있는 venv 에서 돌릴 것** (시스템 python 은 mypy 게이트가
"mypy unavailable" 로 정당 fail). 게이트 개별 skip 은 `--skip-doctor/-state/-git/-packaging/-mypy`.

세션 시작 플로우는 그대로다 (v1.1.2+ 부터는 `wk` 로도 부를 수 있다):

```bash
wk survey-remote-workspaces
wk claim-workspace --branch <b> --axis "<축>" --task-title "<제목>" --apply
python3 workflow-source/scripts/generate_workflow_state.py \
  --project-profile-path docs/PROJECT_PROFILE.md --output-path ai-workflow/memory/active/<b>/state.json
```

federation 을 실제로 돌리려면 (v1.1.2+):

```bash
wk host-serve-registry --port 8765                      # 이 호스트가 서빙
wk host-pull-registry add-known-host --host-id <상대> \
    --endpoint http://<host>:8765/registry.json --apply  # 상대 등록
wk host-pull-registry pull --host <상대>
```

### 다음에 할 일 (순서)

- **다음 릴리스를 `cmd_release` 경로로 발행** — 위 명령. 파이프라인 정상화의 실전 검증.
  성공하면 "수동 발행" 관행을 종료한다.
- **TST-WF-01 측정 재설계** — 관행 인식형 counting (inline `check()` /
  `failures.append` / def test_·case_ 3종) 이 되면 `partial_rules.testing` 예외를
  제거한다. pyproject 주석과 stable_guarantee §5.1 에 조건이 적혀 있다.
- **branch protection** (소유자 결정) — 이 저장소 `main` 은 미보호 (404 실측, TASK-2026-08-09-main-004).
- v1.1.0 / v1.1.1 노트의 누적 표기 사후 삽입 여부 (선택).

## 6. 남은 리스크 / 확인하지 못한 것

- **`cmd_release --apply` 는 아직 실전 미검증** — 이번 세션은 dry-run 완주 + pre_check
  5/5 까지만 실측했다. apply 경로(tag push + gh release create + post-step)는 다음
  릴리스에서 처음 검증된다.
- **호스트 환경 의존 게이트** — 시스템 python 에는 mypy/mcp/twine 이 없어 관련 검사가
  fail 한다 (venv 에서 전부 PASS — `.venv` 에 dev,release,mcp-sdk 설치돼 있음).
  release 는 반드시 venv 에서 돌린다.
- **TST-WF-01 은 여전히 advisory red** — 선언된 예외일 뿐 측정이 고쳐진 게 아니다.
  doctor 출력에 계속 보인다 (그래야 한다).
- **darwin homelab 에서 mavis e2e 재확인 필요** — 검사를 정본 읽기로 바꿨으므로 mavis
  설치 호스트에서 한 번 돌려 기존과 동일하게 green 인지 확인하는 것이 안전하다.
- 이 밖의 과거 세션 리스크 (registry loopback 만 실측 / title drift 임계 0.6 heuristic /
  `--force` 3rd layer 미가동)는 변화 없음 — 2026-08-09 까지의 세션 기록 참조.

**이전 세션들의 교훈**은 각 세션 기록에 있다:
[2026-08-09](./sessions/cli_dispatcher_and_rotation_2026-08-09.md) ·
[2026-08-08](./sessions/multi_workspace_orchestration_2026-08-08.md) ·
[2026-08-05](./sessions/self_application_and_mcp_2026-08-05.md) ·
[2026-08-07 MCP](./sessions/mcp_load_verification_2026-08-07.md) ·
[2026-07-27](./sessions/selfref_cleanup_and_ci_measurement_2026-07-27.md)
