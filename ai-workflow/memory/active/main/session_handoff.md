# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-10 (릴리스 파이프라인 정상화 사이클 TASK-001~004 close)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **dummy wrapper 물리 제거 완료** (TASK-007, 153개/60파일 -827줄, 신호 분포 불변 실증). 직전: **v1.1.5-beta 발행 완료 — `cmd_release` 2번째 실전** (2026-08-10, tag `v1.1.5-beta`, TASK-004~006 묶음: TST-WF-01 예외 제거 + dist dry-run 반전). **파생물 선재생성** 으로 post-apply 잔여 73→4 파일. 전량 검사 **261/261 PASS**. 직전: **TST-WF-01 측정 재설계 완료** (TASK-004) — AST verification-signal 기반, `assert True` dummy 배제, `partial_rules.testing` 예외 제거, **hard 복귀 + 정직하게 compliant**. 전량 검사 **261/261 PASS**. 직전: **v1.1.4-beta 발행 완료 — `cmd_release` 경로 첫 실전 발행** (2026-08-10, tag `v1.1.4-beta`, [GitHub Release](https://github.com/ykylee/standard_ai_workflow/releases/tag/v1.1.4-beta), whl+sdist). **수동 발행 관행 종료** (v1.1.0 부터 4연속이던 것). pre_check **5/5 를 skip 플래그 없이 통과**, 전량 검사 **260/260 PASS**. version-bump post-step(amend 가드)도 첫 정상 완주.
- 현재 주 작업 축: 릴리스 파이프라인 정상화 사이클 **완결** (TASK-001~006, 릴리스 2회 실전).
- 다음 후보 축: branch protection (소유자 결정) / darwin homelab 에서 mavis e2e 재확인 / **P2-1 ADR-006 회고 (2026-08-19 이후 착수 조건 충족)** / v1.1.0·v1.1.1 노트 누적 표기 사후 삽입 여부.
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
- TASK-2026-08-10-main-007 **dummy wrapper 물리 제거** — v0.15.18 이 심은 `assert True` dummy 153개/60파일 제거 (-827줄, 참조 걸림 0 = 전부 고아 def). **신호 분포 완전 불변 실증** (min 1 / under-5 7 동일) — TASK-004 측정이 dummy 를 안 세고 있었다는 물리적 재확인. 자기 보고 수치가 정직해짐 (예: 5/5 → 3/3).
- TASK-2026-08-10-main-006 **v1.1.5-beta 발행** — `cmd_release` 2번째 실전 완주. **파생물 선재생성** (v1.1.4 교훈: fixtures 3종 + samples 24건 + stamp 4종을 릴리스 *전에*, 10개 검사 사전 green) → post-apply 잔여 73→**4 파일**. pre_check 5/5 skip 없이, step 3.4 261/261 정합.
- TASK-2026-08-10-main-005 **dist 기본값 dry-run 반전** — release 의 v1.1.4 반전과 같은 결함이 dist subparser 에 복제돼 있었다 (default True 가 main() 정규화를 무력화). 무인자 dist = plan 만. pre_check_gates 10 → **12/12** (default AST + 무인자 subprocess). 기존 소비자 전부 flag 명시라 회귀 없음.
- TASK-2026-08-10-main-004 **TST-WF-01 측정 재설계** — 실측이 설계를 결정: AST 로 4개 관행(def/assert/reporter 호출/failures.append)을 세고 `assert True` dummy 153개를 배제하니 **260개 전 파일 ≥1 신호**. hard floor = 파일당 ≥1 (검증 없는/parse 불가 파일 검출), ≥5 는 권장으로 notes 노출. partial 예외 제거 + pre_check_gates case 10 을 예외 *부재* 고정으로 반전. `check_tst_wf01_signals` 9/9 (되주입 3종). 정본 문서 2곳 동기. smoke 261.
- TASK-2026-08-10-main-003 **v1.1.4-beta 를 `cmd_release` 경로로 발행** — 수동 발행 관행 종료. version-bump(dirty 거부 → amend 가드 첫 정상 완주) → note-draft → stamp 정합(검사 4종으로 탐지) → dist(twine PASSED) → dry-run(pre_check **5/5 skip 없이 통과**) → apply(tag push + gh release + dashboard emit + audit append 자동 완주) → verify 실증. 자동 후처리(최종 수정일 68건 + CHANGELOG `[1.1.4]`)는 post-release 커밋으로 수습.
- TASK-2026-08-10-main-001 **cmd_release 사용성 회복** — pre_check 만성 실패 3뿌리 해소: (1) doctor 호출이 `workflow-source/workflow-source/` 를 탐색해 **0 files 를 재고 non_compliant** → repo root + `--config-path` + env 명시 (2) TST-WF-01 이 inline `check()`/`failures.append` 관행을 못 봐 만성 red → dummy wrapper 전례 대신 `partial_rules.testing` **선언된 예외** (3) state 검사의 `memory.last_freeze` 는 writer 가 사라진 죽은 계약 → `generated_at` (legacy 하위호환). + **무인자 `release` dry-run 반전** + 개별 `--skip-*` 5종 + mypy "실행 불가 vs 오류" 출처 구분. `check_release_pre_check_gates` 10/10 신설. venv 실측 pre_check 5/5 통과. 전량 **260/260 PASS**.
- TASK-2026-08-10-main-002 **check_mavis_attach_e2e 호스트 사본 제거** — darwin 절대경로 하드코딩 사본 탓에 darwin 외 호스트에서 무조건 red 였던 것을 실제 `~/.minimax/mcp/mcp.json` 정본 읽기로 교체. 부재 시 graceful skip (`--require-mavis` 로 강제). 로드 경로는 fake 항목 실증 ALL PASS (13 tools + tool call 2종).
- TASK-2026-08-09-main-017 **v1.1.3-beta 발행** (TASK-009~016, 11 커밋). 오늘 고친 릴리스 도구 3건이 **이번 릴리스에서 실제 검증됐다** — `_git_toplevel`(정당한 amend 거부) / `release-verify`(실제 조회 성공) / **step 3.4**(`ok: True, 259/259` — 실제 경로 동작). 수동 발행 이유: `cmd_release` pre_check 의 doctor/state 가 만성 실패인데 개별 skip 이 없다. **주의: `release` 는 `--dry-run` 없으면 기본이 APPLY**.
- TASK-2026-08-09-main-016 릴리스 절차에 **노트 누적 수치 검증** step 3.4 신설 — TASK-015 가 "검사가 아니라 절차 문제" 로 짚은 자리. note 부재 / 표기 부재 / 수치 불일치를 각각 잡고 조치를 안내한다. **자동으로 채우지 않는다** — 그 줄은 *전량 PASS 했다* 는 주장이고, 도구가 대신 적으면 거짓이 된다 (회귀 case 9b 가 쓰기 금지를 고정). 정규식은 dashboard 와 같은 것을 쓴다. 10/10 PASS.
- TASK-2026-08-09-main-015 `check_smoke_trend_cross` **오독 정정 — 검사가 맞았다**. 노트의 누적 수치는 *릴리스 스냅샷이 아니라 살아있는 지표* 였다 (smoke 가 늘면 최신 노트를 갱신해 온 관행; `Beta-v1.0.0.md` 199→…→234). 내가 본 '모순' 은 **사후 갱신을 모르고** 한 오독 — 태그 시점엔 199/199 정합. red 구간은 v1.1.0·v1.1.1 이 **표기를 빠뜨린** 탓. 판정 복원 + 노트 257→**259**. **검사를 고치기 전에 그 검사가 지켜 온 관행을 먼저 확인한다.**
## 5. 다음 세션 시작 포인트

### 무엇이 끝났나 (2026-08-10 세션)

**cmd_release 사용성 회복** (TASK-001) + **mavis e2e 호스트 사본 제거** (TASK-002)
+ **v1.1.4-beta 를 `cmd_release` 경로로 실전 발행** (TASK-003) + **TST-WF-01 측정
재설계** (TASK-004, partial 예외 제거·hard 복귀). 전량 검사 **261/261 PASS**.
상세는 §4 네 항목과 task 파일에 있다.

앞으로의 릴리스 절차 (v1.1.4-beta 에서 실증된 경로):

```bash
# venv 필수 (mypy/mcp/twine — 시스템 python 은 mypy 게이트가 정당 fail)
PYTHONPATH=workflow-source .venv/bin/python workflow-source/tools/release_pipeline.py version-bump --apply
PYTHONPATH=workflow-source .venv/bin/python workflow-source/tools/release_pipeline.py note-draft --from <직전태그> --to <버전> --apply  # + 수동 편집
PYTHONPATH=workflow-source .venv/bin/python workflow-source/tools/release_pipeline.py dist --apply
PYTHONPATH=workflow-source .venv/bin/python workflow-source/tools/release_pipeline.py release --dry-run   # 무인자도 dry-run (v1.1.4+)
git push  # tag 대상 커밋이 원격에 있어야 --verify-tag 통과
PYTHONPATH=workflow-source .venv/bin/python workflow-source/tools/release_pipeline.py release --apply
```

stamp 정합은 bump 후 검사 4종(readme_cross / code_index / installation_usage /
drift_prevention)을 돌려 붉어진 곳만 갱신하면 된다. apply 후 자동 후처리
(최종 수정일 stamp + dashboard + CHANGELOG + 노트 audit)가 트리를 수정하므로
post-release 커밋으로 수습한다. 게이트 개별 skip: `--skip-doctor/-state/-git/-packaging/-mypy`.

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

- ~~다음 릴리스를 `cmd_release` 경로로 발행~~ — ✅ **완료** (v1.1.4-beta, TASK-003).
  수동 발행 관행 종료.
- ~~TST-WF-01 측정 재설계~~ — ✅ **완료** (TASK-004). partial 예외 제거, hard 복귀.
- **branch protection** (소유자 결정) — 이 저장소 `main` 은 미보호 (404 실측, TASK-2026-08-09-main-004).
- v1.1.0 / v1.1.1 노트의 누적 표기 사후 삽입 여부 (선택).

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
- 이 밖의 과거 세션 리스크 (registry loopback 만 실측 / title drift 임계 0.6 heuristic /
  `--force` 3rd layer 미가동)는 변화 없음 — 2026-08-09 까지의 세션 기록 참조.

**이전 세션들의 교훈**은 각 세션 기록에 있다:
[2026-08-09](./sessions/cli_dispatcher_and_rotation_2026-08-09.md) ·
[2026-08-08](./sessions/multi_workspace_orchestration_2026-08-08.md) ·
[2026-08-05](./sessions/self_application_and_mcp_2026-08-05.md) ·
[2026-08-07 MCP](./sessions/mcp_load_verification_2026-08-07.md) ·
[2026-07-27](./sessions/selfref_cleanup_and_ci_measurement_2026-07-27.md)
