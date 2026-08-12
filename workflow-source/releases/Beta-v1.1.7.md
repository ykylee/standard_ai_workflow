# Beta v1.1.7 (2026-08-12)

> **상태: 릴리스 준비.** `tool_version = v1.1.7-beta`, tag `v1.1.7-beta`.
> **patch release** — 6~14차 세션 묶음: **state.json 생성물 체계** (`wk refresh-state`
> + drift 검사) + **전량 검사 배타 락** + 6차 구성 리뷰(하네스/스킬·CLI/MCP)가 발견한
> 도구 결함 6건 종결 + **federation self-host 상시 가동**. `cmd_release` 경로의
> **4번째 실전 발행**.
>
> PyPI 배포는 정책상 미실행 (릴리스 채널 = GitHub Releases).

## 0. 릴리스 판정

본 릴리스의 공통 주제는 **"안내하는 명령은 실행 가능해야 하고, 파생물은 정본에서
나와야 한다"** 다 — TASK-020 이 연 "소비자에게 실행 경로가 없다" 계열이 이 릴리스로
완결됐다 (렌더러 결함 26→0).

- **state.json 은 생성물** — 정본 §11.2 에 선언되고, `wk refresh-state` 가 재생성
  창구이며, 검사가 이 저장소 자신의 정합을 상시 판정한다 (자기 적용).
- **검사가 허위를 강제할 수 있다** — "전 도구 `readOnlyHint=true`" 단언은 정책
  검사처럼 보였지만 write 도구 2종의 허위 광고를 고정하는 장치였다. 단언의 근거를
  정책 문장이 아니라 행동 사실(write 하는가)로 바꿨다.
- **동시 실행된 전량의 결과는 근거가 못 된다** — runner 진입 배타 락이 정숙 구간
  침범을 차단한다 (3층 방어: 규약 + 락 + 되주입 검사).

## 1. 릴리스 요약

- 범위: `v1.1.6-beta..HEAD` (TASK-2026-08-11-main-017~028 + TASK-2026-08-12-main-001, 20+ commit)
- state.json 생성물 전환 + `wk session-start` 무인자 동작 + `wk refresh-state` 신설 (wk 71→72)
- 6차 구성 리뷰 후속 6건: backlog-update 병합 의미론 / MCP readOnlyHint 정직화 /
  §11 단일출처 강화 / MCP 도구 목록 단일출처 / 소비자 표면 `wk` 통일 / 보조 렌더러 §11 주입
- 전량 검사 배타 락 + federation self-host 상시 가동 (`--print-systemd-unit`)
- 전량 검사 **251/251 PASS** ×2축 (격리 venv, `--tmp-dir` 실디스크)

## 2. deliverable

### 2.1 state.json 생성물 전환 (TASK-2026-08-11-main-018, `39dc234`)

- 정본 §11.1 에 `wk refresh-state` 행 + §11.2 에 "state.json 은 생성물 (손 편집
  금지)" · "handoff/backlog 는 생성기 입력" 선언. 배포 사본·스냅샷·CLAUDE.md 동시 갱신.
- `wk refresh-state` 신설: 재생성 + `--check` drift 판정. `check_state_json_generated`
  **6 case** — 되주입 양방향 + **자기 적용** (이 저장소의 state.json 정합 상시 검사)
  + 선언↔창구 정합.
- `wk session-start` 무인자 동작 (workspace 자동 탐색) + branch-scoped daily backlog
  관측 (인덱스 링크가 task 상세 파일을 최신 backlog 로 오판하던 결함 해소).

### 2.2 6차 구성 리뷰 후속 6건 (TASK-023~028, `30563a4`·`e6f1653`·`267dfaf`·`8f8e95d`·`2d799f5`·`d35fe61`)

- **backlog-update 병합 의미론** (023) — update 모드가 task 파일을 인자로 전체
  재생성하며 미지정 필드를 삭제하던 결함 (실측: 손 복원 필요했음). `merge_task_file`
  (명시 인자만 반영) + index block 보존 + handoff task ID dedupe. 검사 5→**8 case**,
  신설 3 case 는 버그 코드에서 FAIL 실증.
- **MCP readOnlyHint 정직화** (024) — `apply_robust_patch`(파일 write) /
  `rotate_workflow_logs`(handoff rewrite) 가 read-only 로 광고되던 허위를
  registry `read_only` 선언 파생으로 정정. 검사가 선언↔사실 목록↔descriptor 삼자
  일치를 강제. ADR-003 v1.1.7 개정 (6+1 → 13 도구 현실).
- **§11 단일출처 강화** (026) — §11.1 명령의 손 사본 7곳을 `find_memory_command`
  정본 파생으로. goose `on_session_end` 의 깨진 경로(`skills/` + 없는 플래그) →
  `wk refresh-state`. 검출기가 §11 명령·계약을 판정 대상에 추가, case 8 이
  `PRIMARY ∪ EXEMPT == SUPPORTED_HARNESSES` 단언 (미분류 mavis 해소).
- **MCP 도구 목록 단일출처** (025) — MiniMax 렌더러 손 목록 (10개, 3개 누락) →
  registry 파생. 유령 `script_path` 2건은 `mcp_servers/` 실물 생성 + 실존 강제.
  예시 config 의 tools 배열 ↔ registry 대조 case 신설.
- **소비자 표면 wk 통일** (027) — SKILL.md 3종 + apply_guide 의 미배포 `skills/`
  경로 안내 제거. `check_packaging` 이 `tools` 배포를 wheel 에서 검증 (구판 1.1.6
  wheel 에서 즉시 FAIL 실증). `--copy-core-docs` 는 죽는 wrapper 대신 문서만 복사.
- **보조 렌더러 §11 주입 완결** (028) — `render_memory_update_section` 신설, 1순위
  6개 주입 + 잔여 8개는 이유 명시 원장 (case 9 양방향 판정). **TASK-020 의 결함
  26 → 0** (주입 9+4+6 / 원장 8 / 무관 5).

### 2.3 전량 검사 배타 락 (TASK-2026-08-11-main-019, `e7f3ef1`)

- 두 에이전트가 같은 워킹 트리에서 전량을 동시 실행하면 정숙 구간이 침범돼 결과가
  조용히 거짓이 된다 (2026-08-11 실측). runner 진입 `fcntl.flock`
  (`.git/run_all_checks.lock`) — 계쟁 시 보유자 정보 출력 후 즉시 실패, stale 은
  커널 자동 해제로 원천 해소, 자식 runner 는 env 마커 승계, `--no-lock` 은 크게 기록.
- `check_run_all_checks_lock` **5 case** (부모 runner 보유 시 적응 모드).
  한계 명시: 직접 편집 충돌은 worktree 분리가 정공법 — 락은 안전망.

### 2.4 federation self-host 상시 가동 (TASK-2026-08-12-main-001, `e625c91`)

- `host-serve-registry --print-systemd-unit` 신설 — 상시 가동의 실행 가능 경로.
  토큰은 `EnvironmentFile` (0o600) 로 실행 시점 공급 (unit 에 값이 안 남음).
- plex 에 `wk-registry` user unit 가동 (LAN 실측: healthz 200 / 무토큰 401 /
  토큰 200 / POST 405). 합류 절차는 `environments/plex.md` — 두 번째 호스트
  (MacBook, 사용자 확정) 는 두 명령이면 합류.
- `check_registry_server` case 11 (unit 계약 고정).

### 2.5 darwin 검증 + 하네스 통일 (TASK-017 · 020~022, `24bcc90`·`1d06147`·`a3d00a6`)

v1.1.6 이후 이 릴리스 범위에 포함된 5차 세션 작업: macOS `/private` symlink 이식성
결함 4건 (검사 fixture `.resolve()` 통일, production 무수정) + 렌더러 32개 전수검사
진단 + skill 구현 3종의 `tools/` 이동 (wk 68→71) + 정본 §11 신설·전 하네스 주입.

## 3. smoke 회귀

누적 smoke test **251/251 PASS** (2026-08-12, `dev,release,mcp-sdk` extra 를 깐
격리 venv, `--tmp-dir` 실디스크). 이 줄은 릴리스 시점 스냅샷이 아니라 *최신 전량
결과* 를 반영하는 살아있는 지표다.

신규 smoke (2, 249→251):

- `check_state_json_generated.py` **6/6** (§2.1)
- `check_run_all_checks_lock.py` **5/5** (§2.3)

기존 검사 case 확장: `check_backlog_update_layout` 5→8 · `check_standard_single_source`
7→9 · `check_registry_server` 9→11 · `check_mcp_tool_descriptors` 6→7 ·
`check_read_only_mcp_server` (삼자 일치 + script_path 실존).

## 4. 1차 출처 (cross-ref)

- [TASK-2026-08-11-main-017](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-11-main-017.md) ~ [TASK-2026-08-11-main-028](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-11-main-028.md), [TASK-2026-08-12-main-001](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-12-main-001.md)
- 세션 기록: `ai-workflow/memory/active/main/sessions/` 5차~14차 (darwin 검증 → federation self-host)
- [ADR-003 v1.1.7 개정](../../docs/architecture/ADR-003-read-only-mcp-default-policy.md)
- 이전 release note: [Beta-v1.1.6.md](./Beta-v1.1.6.md)

## 5. 후속

- cross-host federation — 두 번째 호스트 = MacBook 확정 (시점 추후, 사용자 결정).
  합류 시 방화벽 / TLS 종단 실측.
- MCP bundle 분리 (write 도구 2종과 "read_only" 이름의 긴장 근본 정리 — ADR-003 후속 후보).
- backlog-update `--status` 미지정 시 in_progress 리셋 보수 규칙 재검토.
- `check_no_repo_write` 실행-중 감시 강화 (§6 리스크, 범위 큼).

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-08-12T04:11:20Z)_

- total wiki pages: **93**
- total memory entries: **9**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
