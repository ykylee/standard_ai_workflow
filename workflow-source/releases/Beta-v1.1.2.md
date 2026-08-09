# Beta v1.1.2 (2026-08-09)

> **상태: 릴리스 준비.** `tool_version = v1.1.2-beta`, tag `v1.1.2-beta`.
> **minor 성격의 patch release** — federation 의 *쓰기* 쪽 신설 + CLI 化 B안 +
> 3-layer defense 3rd layer 확인 + title drift v2, 그리고 **고장난 채 서 있던
> 도구·검사 정리**.
>
> PyPI 배포는 정책상 미실행 (릴리스 채널 = GitHub Releases).

## 0. 릴리스 판정

Beta-v1.1.1 이 CLI 化 **A안**(29 entry point)을 닫았다. 본 릴리스는 그 후속 4건과,
그 과정에서 드러난 **"검사가 있는데도 보이지 않던 것들"** 을 함께 담는다.

이번 사이클의 성격은 기능 추가보다 **가려져 있던 사실의 노출**에 가깝다:

- `rotate_workflow_logs` 는 이 저장소에서 **한 번도 동작한 적이 없었다** — 그런데
  그것을 감싼 `check_cli_wrappers` 는 4 case ALL PASS 였다 (CLI 와 MCP 가 *똑같이*
  `error` 를 냈으므로).
- `add_known_host()` API 는 v1.1.0 부터 있었지만 **부르는 CLI 가 없어** federation 은
  어느 쪽으로도 돌 수 없었다 — API 단위 smoke 8 case 는 전부 green 이었다.
- `workflow_kit/` 의 **FULL mypy strict 가 깨져 있었다** (24 errors). `release-doctor`
  의 mypy gate 가 그것 때문에 red 였다.
- 두 검사는 **한쪽 플랫폼에서만** 돌고 있었다 (`/var/tmp` 문자열 비교 → macOS 상시
  red / `multiprocessing` local function → Linux 에서만 통과).

## 1. 릴리스 요약

- **CLI 化 B안 close** — 단일 dispatcher `wk`. 새 dispatcher 를 만들지 않고 기존
  `workflow_kit_cli.COMMANDS` 를 확장했다 (38 + 27 = 65 command).
- **federation *쓰기* 쪽 신설** — registry HTTP server + known-host 등록 CLI.
  v1.1.1 까지는 pull 만 있고 서빙도 등록도 없었다.
- **3-layer defense 3rd layer 확인 도구** — branch protection 을 *켜지 않고 판정만*.
- **title semantic drift v2** — 같은 TASK-ID 안의 내용 교체를 후보로 고른다 (advisory).
- **FULL mypy strict 복구** — `workflow_kit/` 128 files clean.
- breaking change: ❌ (모든 추가는 additive, 기존 호출 경로 보존)

## 2. deliverable

### 2.1 CLI 化 B안 — 단일 dispatcher `wk` (TASK-002)

`wk <name> [args...]` 하나로 `workflow_kit_cli` 의 38 subcommand 와 `tools/` 29개를
같은 이름 공간에서 부른다. 기존 `--command=<name>` 경로는 그대로다.

| 구성 | 위치 |
|---|---|
| dispatch 로직 | `workflow_kit/common/tool_dispatch.py` (`TOOL_MODULES` 정본) |
| entry point | `pyproject.toml` `wk = "workflow_kit.workflow_kit_cli:wk_main"` |
| completion | `tools/completions/wk.bash` / `wk.zsh` (`wk --list-commands` 소비) |

**새 dispatcher 를 만들지 않은 이유**: `workflow_kit_cli.py` 가 이미 38 subcommand
dispatcher 였다. 하나 더 만들면 `--help` 가 둘로 갈리고 어느 쪽이 정본인지 흐려진다.
정공법도 이미 있었다 — `score-wiki-trend`(v0.7.56+) wrapper 의 *sys.argv 치환 +
SystemExit → rc* 를 29개로 일반화했다.

`main()` 시그니처가 `main(argv)` 13 : `main()` 16 으로 갈려 있는데, 29개 파일을
통일하는 대신 `inspect.signature` 로 읽어서 맞춘다.

### 2.2 registry HTTP server — federation 의 *쓰기* 쪽 (TASK-003)

| 구성 | 위치 |
|---|---|
| 서버 로직 | `workflow_kit/common/registry_server.py` |
| CLI | `tools/host_serve_registry.py` (`wk host-serve-registry`) |
| 등록 CLI | `tools/host_pull_registry.py add-known-host` / `remove-known-host` |

안전 기본값과 근거:

- **bind 는 `127.0.0.1`** — registry 에는 워크스페이스 절대 경로와 브랜치가 들어 있다.
  파일을 0o600 으로 지키면서 HTTP 를 0.0.0.0 에 열면 그 보호가 무의미하다.
- **`SimpleHTTPRequestHandler` 미사용** — 디렉터리 노출 + path traversal 표면이 딸려
  온다. 아는 경로는 `/registry.json` + `/healthz` 둘뿐.
- **read-only** (쓰기 405) — 원격이 남의 registry 를 고칠 수 있으면 federation 모델이
  무너진다.
- **토큰은 환경변수 *이름*으로** (`--token-env`) — `--token=SECRET` 은 `ps` 와 shell
  history 에 남는다. `KnownHost.token_env` 도 이름만 저장 (additive, 하위호환).
- **registry 부재 → 빈 registry** (404 아님) — 404 면 상대가 *호스트가 죽었다* 고 오해한다.

### 2.3 branch protection 자동 check — 3rd layer (TASK-004)

`workflow_kit/common/branch_protection.py` (pure 판정) + `tools/check_branch_protection.py`.

- **보호를 켜지 않는다. 판정만 한다** (§5D.4 — 되돌릴 수 없는 결정은 사람).
- **필드를 못 읽으면 통과로 치지 않는다** — 권한 부족의 `null` 과 실제 off 를 섞으면
  검사가 거짓 안심을 준다.
- `gh` 부재/미인증은 graceful skip (모름 ≠ 없음), `--require-gh` 로 구분.

> **실측**: `ykylee/standard_ai_workflow@main` 에 branch protection 이 **없다**(404).
> 3rd layer 가 비어 있다 — 켜는 것은 저장소 소유자 판단.

### 2.4 title semantic drift v2 (TASK-005)

v1 (`detect_scope_drift`) 은 TASK-ID **집합** 만 비교해서, 같은 ID 안에서 내용이
통째로 바뀌어도 언제나 clean 이었다. v2 는 같은 ID 의 **제목** 을 `difflib` 로 비교해
후보를 고르고, 판정은 LLM prompt 로 넘긴다 (`purpose_refresh` 와 같은 advisory 모델 —
LLM API 직접 호출 ❌). `detect_scope_drift()` 에 `title_drift` **additive**.

### 2.5 rotate 도구 수정 — 순서 규약 통일 (TASK-006)

`rotate_workflow_logs` 가 `status: error` 만 내고 있었다. 결함이 **둘** 이었고,
하나만 고쳤으면 더 나빴다:

1. 섹션을 고정 문자열(`## 5. 최근 완료 작업` / `## 6. 잔여 작업`)로 찾았다. 실제
   문서는 `## 4.` 이고 다음 섹션 제목도 다르다.
2. `items[-max:]` 로 뒤를 남겼다. handoff §4 는 **앞이 최신** 이다 —
   **1번만 고쳤다면 도구가 "동작하면서" 최신을 지웠을 것이다.**

규약은 새로 정하지 않았다. `check_recent_done_items_order` 계약 1 이 이미
*"`recent_done_items` 는 최신순"* 이라 적고 있었고 실제 문서도 그랬다. writer
(`sync_handoff_status`) 만 `append` 로 반대였으므로 writer 를 고쳤다.

부수로 드러난 것: **`check_cli_wrappers` 가 저장소의 실제 handoff 를 수정하고 있었다.**
rotate 가 늘 `error` 라 아무것도 안 써서 보이지 않았다. 호출마다 tempdir 복사본을
주도록 고치고 `check_no_repo_write` 의 `WATCHED_CHECKS` 에 등록했다.

### 2.6 남은 red 정리 + FULL mypy strict 복구 (TASK-007)

| 대상 | 원인 | 처리 |
|---|---|---|
| `read_only_*.json` 3건 | `tool_version` 이 v1.0.0-beta | 재생성 |
| 정리 없는 `mkdtemp` 11건 | `TemporaryDirectory` 미사용 | 6 파일에 `atexit` 헬퍼 |
| `/var/tmp` 문자열 비교 | macOS 는 `/private/var/tmp` — **구현이 아니라 검사가 틀림** | resolve 비교 |
| `multiprocessing` local function | spawn(macOS)에서 `PicklingError` — **Linux 에서만 돌던 검사** | 모듈 레벨로 이동 |
| `workspace_registry.py` mypy 24건 | `type-arg` 17 / `attr-defined` 6 / `no-any-return` 1 | 전부 정리 |
| R3 `branch_from_module_repo` | `survey()` 가 `repo_root` 를 받는데 브랜치는 모듈 앵커에서 | `paths.branch_slug_for()` 신설 |

`workflow_kit/` **128 files mypy strict clean** 복구 — Phase 13 **P0-1**
(mypy strict venv 직접 verify) 의 acceptance 를 실측으로 충족한다.

### 2.7 문서 stamp 정합 회복

v1.1.0 / v1.1.1 릴리스에서 빠뜨린 갱신을 되돌렸다: `README.md` / `docs/RELEASE.md` /
`docs/CODE_INDEX.md` / `docs/INSTALLATION_AND_USAGE.md` 의 버전·smoke count +
`examples/output_samples/*.json` 24건의 `tool_version`.

효과: dashboard `drift_prevention.guard_status` **`fail` → `pass`**.

## 3. smoke 회귀

누적 smoke test **257/257 PASS** (2026-08-09, `dev,release,mcp-sdk` extra 를 깐 격리 venv,
`--tmp-dir` 실디스크, 305s). 직전 v1.1.1 시점의 claim 은 234 였고 실제 파일은 257 이었다 —
그 격차 자체가 `check_smoke_trend_cross` 의 red 였다.

신규 smoke:

| smoke | case | 상태 |
|---|---|---|
| `check_wk_dispatcher.py` | 10 | ✅ |
| `check_registry_server.py` | 9 | ✅ |
| `check_branch_protection_smoke.py` | 8 | ✅ |
| `check_title_drift.py` | 11 | ✅ |
| `check_handoff_rotation.py` | 9 | ✅ |

기존 smoke 갱신: `check_entry_points`(`DISPATCHER_EXCEPTIONS`) /
`check_handoff_done_cap`(순서 계약 반전) / `check_cli_wrappers`(tempdir 복사본) /
`check_no_repo_write`(감시 목록) / `check_tempdir_leak_guard`(플랫폼) /
`check_code_index_v0_15_17`(`EXPECTED_LAST_UPDATED`).

## 4. 1차 출처 (cross-ref)

- `core/multi_workspace_orchestration.md` §0.7 상태표 / §5D.4 (b) / §7.4 / §7.5
- `workflow_kit/common/tool_dispatch.py` — `TOOL_MODULES` 정본
- `workflow_kit/common/registry_server.py` / `branch_protection.py`
- `workflow_kit/common/rotation.py` — 순서 규약
- `ai-workflow/memory/active/main/sessions/cli_dispatcher_and_rotation_2026-08-09.md`
- `releases/Beta-v1.1.1.md` — 직전 release

## 5. 후속

- **Phase 13 P0-2** — telemetry source 다양성 ≥ 4. 실측 `by_source` 는
  `session-start` 하나 (hit_rate 1.0). `phase_13_followup.md` 는 "현 1 source
  (dispatcher)" 라고 적고 있어 **문서가 실제와 다르다** — 정정도 함께.
- **Phase 13 P1** — CHANGELOG auto-gen lockdown / `automated-repro-scaffold` stable /
  `git-conflict-resolver` beta.
- **branch protection 켜기** — 저장소 소유자 결정 (본 릴리스의 도구는 판정만 한다).
- **registry HTTP server 실환경 검증** — loopback 왕복만 실측했다. LAN / 방화벽 너머 /
  reverse proxy / TLS 종단은 확인한 적 없다.
- **title drift 임계 0.6** — 운영 데이터로 고른 값이 아니다.

## 6. compatibility

- breaking change: ❌
- 기존 호출 경로 전부 보존 — `python3 workflow-source/tools/X.py`,
  `workflow-X`(v1.1.1 binary), `--command=<name>`
- `KnownHost.token_env` / `RegistryEntry` — additive, missing → `""` 하위호환
- `detect_scope_drift()` 의 `title_drift` — additive (v1 필드 불변)
- MCP server 변경 ❌
- **동작 변경 1건**: `sync_handoff_status` 가 handoff §4 에 `append` 하던 것을
  `insert(0)` 으로 바꿨다. state.json 의 `recent_done_items` 계약(최신순)과 실제
  문서 관행에 맞춘 정정이며, `check_handoff_done_cap` 의 계약 2 도 함께 반전했다.
