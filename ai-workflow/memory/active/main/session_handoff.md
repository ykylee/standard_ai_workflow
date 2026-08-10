# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-10 (ADR-006 회고 + W-1 write-path 루프 — TASK-010·011)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **ADR-006 회고 (TASK-010) + W-1 write-path advisory 루프 구현 (TASK-011)** — telemetry 256 events 실측 회고 (ADR accepted), `wk suggest-memory-entries` 신설, 루프 실증 완주 (회고를 `MEM-2026-08-10-001` 로 적재 — **33일 만의 첫 신규 entry**, covered 0→1). 남은 후속: W-2 질의 다양화 / W-3 entry 간 링크 / W-4 지표 재정의. 직전: **2026-08-09 세션의 "검증 못 한 것" 2건 close** (TASK-008·009) — title drift 임계 0.6 실측 캘리브레이션 (저장소 자신의 제목 데이터 양성 81/음성 375쌍, **0.6 유지 + 구조적 한계 동결 + 조사를 검사로 고정**) + registry server 비-loopback bind 왕복 실측 (LAN IP bind + pull + 토큰, 10/10). 직전: **dummy wrapper 물리 제거 완료** (TASK-007, 153개/60파일 -827줄, 신호 분포 불변 실증). 직전: **v1.1.5-beta 발행 완료 — `cmd_release` 2번째 실전** (2026-08-10, tag `v1.1.5-beta`, TASK-004~006 묶음: TST-WF-01 예외 제거 + dist dry-run 반전). **파생물 선재생성** 으로 post-apply 잔여 73→4 파일. 전량 검사 **261/261 PASS**. 직전: **TST-WF-01 측정 재설계 완료** (TASK-004) — AST verification-signal 기반, `assert True` dummy 배제, `partial_rules.testing` 예외 제거, **hard 복귀 + 정직하게 compliant**. 전량 검사 **261/261 PASS**. 직전: **v1.1.4-beta 발행 완료 — `cmd_release` 경로 첫 실전 발행** (2026-08-10, tag `v1.1.4-beta`, [GitHub Release](https://github.com/ykylee/standard_ai_workflow/releases/tag/v1.1.4-beta), whl+sdist). **수동 발행 관행 종료** (v1.1.0 부터 4연속이던 것). pre_check **5/5 를 skip 플래그 없이 통과**, 전량 검사 **260/260 PASS**. version-bump post-step(amend 가드)도 첫 정상 완주.
- 현재 주 작업 축: 릴리스 파이프라인 정상화 사이클 **완결** (TASK-001~006, 릴리스 2회 실전).
- 다음 후보 축: branch protection (소유자 결정) / darwin homelab 에서 mavis e2e + federation cross-host 재확인 / ADR-006 후속 **W-2 질의 다양화 → W-3 entry 간 링크 → W-4 지표 재정의** (W-1 은 ✅ TASK-011) / v1.1.0·v1.1.1 노트 누적 표기 사후 삽입 여부.
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
- TASK-2026-08-10-main-011 **ADR-006 W-1 write-path advisory 루프** — `wk suggest-memory-entries` 신설: handoff §4 제목을 entry corpus 와 대조 (coverage < 0.5 → 후보 + skeleton, **무-write advisory**). 루프 실증 완주 — 첫 실측 10/10 후보 (max 0.14, 회고 재확인) → 회고를 `MEM-2026-08-10-001` 로 적재 (**33일 만의 첫 신규 entry**) → covered 0→1 + `query [retrospective,write-path]` 적중. smoke 8/8 (되주입: corpus 에 넣으면 후보가 사라짐), dispatcher 정합 10/10, mypy clean. smoke 263.
- TASK-2026-08-10-main-010 **P2-1 ADR-006 Memory Index 회고** — telemetry 256 events (07-09~08-10) 실측: 30일 실사용 = **고정 질의 1종 → 고정 entry 1건** (BM25/expansion/merge 발동 0회, 신규 entry 0건, latency p50 0.18ms). hit_rate 1.0 은 캐시 적중이었다 — 질의 다양성을 안 재는 지표는 항상 green 이어도 정보가 없다. ADR-006 placeholder → **accepted** (~230 line, 6 영역 + 보강 2). 후속 W-1 write-path advisory 루프 / W-2 질의 다양화 / W-3 entry 간 링크 / W-4 지표 재정의. 기각: BM25 tuning·embedding·merge default 변경. wiki topic 신설, phase_13_followup stale 날짜 정정 (08-19 → 실제 tag 07-02).
- TASK-2026-08-10-main-008 **title drift 임계 0.6 실측 캘리브레이션** — 저장소 자신의 제목 데이터(정본 자리만: backlog bullet / task H1 / handoff production 섹션, 트리 326 문서 + git 576 버전)로 양성 81 / 음성 375쌍을 채굴해 **0.6 유지를 실측으로 확정** (정본 양성 노이즈 1/14, 음성 검출 373/375). 같은-축 형제 task (0.69~0.71) 는 어떤 임계로도 못 가른다 — 검사 case 6 이 한계를 동결. 괄호 제거 정규화는 실측 기각 (놓침 115→287). `calibrate_title_drift.py` + fixture + 검사 7 case (되주입 2종). 1차 채굴의 교훈: 임의 줄의 ID 언급을 먹이면 산문이 제목으로 섞여 분포가 뒤집힌다 — production 이 읽는 자리만 먹일 것.
- TASK-2026-08-10-main-009 **registry server 비-loopback bind 실측** — case 10 신설, LAN IP(192.168.0.121) bind + GET + pull + 토큰 왕복 green. LAN IP 부재는 graceful skip + `--require-lan`. cross-host / 방화벽 / TLS 는 여전히 검증 밖 (darwin homelab 몫, §7.4 명시).
- TASK-2026-08-10-main-007 **dummy wrapper 물리 제거** — v0.15.18 이 심은 `assert True` dummy 153개/60파일 제거 (-827줄, 참조 걸림 0 = 전부 고아 def). **신호 분포 완전 불변 실증** (min 1 / under-5 7 동일) — TASK-004 측정이 dummy 를 안 세고 있었다는 물리적 재확인. 자기 보고 수치가 정직해짐 (예: 5/5 → 3/3).
- TASK-2026-08-10-main-006 **v1.1.5-beta 발행** — `cmd_release` 2번째 실전 완주. **파생물 선재생성** (v1.1.4 교훈: fixtures 3종 + samples 24건 + stamp 4종을 릴리스 *전에*, 10개 검사 사전 green) → post-apply 잔여 73→**4 파일**. pre_check 5/5 skip 없이, step 3.4 261/261 정합.
- TASK-2026-08-10-main-005 **dist 기본값 dry-run 반전** — release 의 v1.1.4 반전과 같은 결함이 dist subparser 에 복제돼 있었다 (default True 가 main() 정규화를 무력화). 무인자 dist = plan 만. pre_check_gates 10 → **12/12** (default AST + 무인자 subprocess). 기존 소비자 전부 flag 명시라 회귀 없음.
- TASK-2026-08-10-main-004 **TST-WF-01 측정 재설계** — 실측이 설계를 결정: AST 로 4개 관행(def/assert/reporter 호출/failures.append)을 세고 `assert True` dummy 153개를 배제하니 **260개 전 파일 ≥1 신호**. hard floor = 파일당 ≥1 (검증 없는/parse 불가 파일 검출), ≥5 는 권장으로 notes 노출. partial 예외 제거 + pre_check_gates case 10 을 예외 *부재* 고정으로 반전. `check_tst_wf01_signals` 9/9 (되주입 3종). 정본 문서 2곳 동기. smoke 261.
- TASK-2026-08-10-main-003 **v1.1.4-beta 를 `cmd_release` 경로로 발행** — 수동 발행 관행 종료. version-bump(dirty 거부 → amend 가드 첫 정상 완주) → note-draft → stamp 정합(검사 4종으로 탐지) → dist(twine PASSED) → dry-run(pre_check **5/5 skip 없이 통과**) → apply(tag push + gh release + dashboard emit + audit append 자동 완주) → verify 실증. 자동 후처리(최종 수정일 68건 + CHANGELOG `[1.1.4]`)는 post-release 커밋으로 수습.
- TASK-2026-08-10-main-001 **cmd_release 사용성 회복** — pre_check 만성 실패 3뿌리 해소: (1) doctor 호출이 `workflow-source/workflow-source/` 를 탐색해 **0 files 를 재고 non_compliant** → repo root + `--config-path` + env 명시 (2) TST-WF-01 이 inline `check()`/`failures.append` 관행을 못 봐 만성 red → dummy wrapper 전례 대신 `partial_rules.testing` **선언된 예외** (3) state 검사의 `memory.last_freeze` 는 writer 가 사라진 죽은 계약 → `generated_at` (legacy 하위호환). + **무인자 `release` dry-run 반전** + 개별 `--skip-*` 5종 + mypy "실행 불가 vs 오류" 출처 구분. `check_release_pre_check_gates` 10/10 신설. venv 실측 pre_check 5/5 통과. 전량 **260/260 PASS**.
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
- ~~2026-08-09 "검증 못 한 것" 2건~~ — ✅ **완료** (TASK-008 title drift 캘리브레이션
  + TASK-009 비-loopback bind 실측).
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
- ~~title drift 임계 0.6 heuristic~~ — ✅ **해소** (TASK-008, 실측 캘리브레이션으로
  0.6 유지 확정 + `check_title_drift_calibration` 이 재캘리브레이션을 강제).
- ~~registry loopback 만 실측~~ — **부분 해소** (TASK-009, 비-loopback bind + pull
  왕복은 이 호스트에서 실측). **잔여**: 진짜 cross-host / 방화벽 / reverse proxy /
  TLS 종단 — 두 번째 호스트 필요 (darwin homelab).
- 이 밖의 과거 세션 리스크 (`--force` 3rd layer 미가동)는 변화 없음 —
  2026-08-09 까지의 세션 기록 참조.

**이전 세션들의 교훈**은 각 세션 기록에 있다:
[2026-08-09](./sessions/cli_dispatcher_and_rotation_2026-08-09.md) ·
[2026-08-08](./sessions/multi_workspace_orchestration_2026-08-08.md) ·
[2026-08-05](./sessions/self_application_and_mcp_2026-08-05.md) ·
[2026-08-07 MCP](./sessions/mcp_load_verification_2026-08-07.md) ·
[2026-07-27](./sessions/selfref_cleanup_and_ci_measurement_2026-07-27.md)
