# 워크플로우 허브 스펙 (2.0)

- 문서 목적: 2.0.0 워크플로우 허브의 kit 계약 — 프로세스 · 모듈 · DB 스키마와 이관 · MCP 도구와 HTTP API · 흐름(부트스트랩 · 세션 시작 · 세션 끝 · compact · 지침 렌더링 · 1.x 전환) · 검증 — 을 정의한다.
- 범위: `python -m workflow_kit hub …` 명령, 허브가 여는 경로(`/mcp` · `/v1/…` · 화면 · `/healthz` · `/v1/bootstrap`), SQLite 스키마, 허브 MCP 도구, 쓰기 지시 형식, 진입 파일 렌더 영역, 1.x 들여오기 매핑. 화면의 구체 디자인은 M-037, 선택 클라이언트의 명령 세부는 M-034 가 정한다.
- 대상 독자: 구현자(M-033~M-039), workflow 설계자, 소유자 (DS 결정)
- 상태: draft (ADR-033 accepted 2026-11-21 — M-032 design 완료, DS1~DS9 소유자 확정. 구현은 M-033~M-039)
- 최종 수정일: 2026-11-21
- 관련 문서: `../../docs/planning/workflow-hub-requirements-2026-11.md` (요구 R0~R16 · 실측 §16 — 아래에서 "요구 R…" · "실측 §16.n"), `../../docs/planning/workflow-hub-review-2026-11.md` (concept), `../../ai-workflow/wiki/decisions/adr-033-workflow-hub.md`, `./claim_plan_spec.md`, `./plan_workbench_spec.md`, `./compact_relay_spec.md`, `./roadmap_milestone_wbs_spec.md`, `./stable_guarantee.md`

> **결정 근거는 concept · ADR-033 에, 요구와 실측은 requirements 에 있다.** 이 문서는 *계약* 만 적는다.
> 괄호 안의 `R…` 은 requirements 의 요구 번호다 — 대응표는 §9. design 이 새로 정한 것은 `DS…` 이고 §10 에 모았다.

## 1. 불변 조건 (요구 R0)

1. 1.x 생성물 형식(`state.json` `schema_version` "1" · `roadmap_state` v1 · `workbench-state/1` · `workflow-kit-plan-response/1`)을 허브도 그대로 낸다 (R0.1).
2. `workflow_kit.__all__` 은 추가만 한다 (R0.2). 허브 모듈은 `workflow_kit.hub` 아래 새 이름이다.
3. 허브 · 선택 클라이언트 · 부트스트랩 원문은 Python 이다 (R0.3). 선택 클라이언트 · `/v1/bootstrap` 원문은 **표준 라이브러리만**, 하한 Python 3.10 (R0.4).
4. 허브 기록 어디에도 토큰을 싣지 않는다 — 쓰기 전에 콜사인 토큰 · 허브 토큰과 같은 문자열을 찾으면 `secret_in_payload` 로 거절한다 (R0.5 · R11.4).
5. 모르는 필드 · 계약 판 · 클라이언트 판은 거절한다 — 조용한 기본값이 없다 (R0.6).
6. 판정은 1.x 와 **같은 함수**를 부른다 — 계획 린트 · 응답 자격 · 결정 상태 · done 게이트 · WBS 게이트 · 로드맵 진척 · 상태 생성 (R0.7, §2.2).
7. 시각은 허브가 한 번 정해 판정 함수에 **인자로** 넘긴다 — 함수 안에서 시계를 읽지 않는다 (실측 §16.1 결합 3).
8. 허브는 프로젝트 git 원격에 접속하지 않는다 — 위키 원격 읽기(§5.6)를 프로젝트가 켠 경우만 예외 (R3.7 · R8.4).
9. 재지 못한 것은 '미측정' 이다 — 통과로 세지 않는다 (R8.4 · R10.3 · 실측 §16.1 결합 2).

## 2. 프로세스 · 모듈

### 2.1 명령

```
python -m workflow_kit hub serve   --db PATH [--bind 127.0.0.1] [--port 8770] [--public-url URL]
python -m workflow_kit hub backup  --db PATH --out PATH
python -m workflow_kit hub admin   --db PATH token issue --role {web,admin} --name NAME | token revoke --name NAME
python -m workflow_kit hub admin   --db PATH callsign revoke --project ID --callsign NAME
```

- `serve` 는 DB 판이 모자라면 이관(§3.4)한 뒤 뜬다. loopback 이 아닌 `--bind` 는 기동 때 경고 한 줄 — "누구나 프로젝트를 등록할 수 있다" 를 포함한다 (R13.1 · R13.3).
- `--public-url` 하나가 허브의 공개 주소다. 추측하지 않는다 (워크벤치 §1-5 와 같다). 화면 출처 대조 · 안내 페이지 명령 · `/v1/bootstrap` 주소가 이 값에서 나온다.
- `admin` 은 DB 파일에 직접 접근하는 로컬 명령이다 — 네트워크로 열지 않는다.

### 2.2 모듈 (`workflow_kit/hub/`)

| 모듈 | 몫 |
|---|---|
| `app.py` | ASGI 앱 조립 — `/mcp` (MCP streamable HTTP) · `/v1/tools/<name>` · 화면 · `/healthz` · `/v1/bootstrap` · 인증 앞단 |
| `db.py` · `migrations.py` | 스키마 · 이관 · 백업 · `version` 대조 쓰기 |
| `tools/*.py` | 도구 함수 — **MCP 와 HTTP 가 같은 함수를 부른다** (DS5) |
| `judge.py` | 1.x 판정 함수의 데이터 입구 (아래 표) |
| `render.py` | 지침 렌더링 — 1.x 진입 파일 생성기(`bootstrap_lib/harnesses`) 재사용 |
| `gitkey.py` | git 주소 정규화 (§3.2) |
| `migrate1x.py` | 1.x 감지 · 들여오기 매핑 (§6.6) |
| `export.py` | git 내보내기 (R15) |
| `client/hub_client.py` | 선택 클라이언트 원문 (표준 라이브러리만, `/v1/bootstrap` 이 내려준다) |

`judge.py` 가 부르는 1.x 함수와 필요한 손질 (실측 §16.1 — M-033 이 손질한다):

| 판정 | 1.x 함수 | 손질 |
|---|---|---|
| 계획 파싱 · 린트 | `plan_claims.parse_plan` · `lint_plan` · `has_error_rules` | 없음. L5 는 `file_line_count=None` → 결과에 L5 '미측정' 표식 (R5.5) |
| 응답 자격 · 결정 상태 | `plan_responses.parse_response` · `qualify` → `plan_claims.compute_states` | 없음. **순서 고정**: `has_error_rules` → `qualify` → `compute_states` (실측 §16.1 결합 1) |
| done 게이트 | `planning.determine_conservative_task_status` + `enforce_plan_contract` 의 판정부 | `enforce_plan_contract` 에 응답 목록 · 줄 수 콜백 · 대기 수 인자 입구 |
| WBS 게이트 | `state/roadmap.evaluate_wbs_gate` | 판정부를 `judge_wbs(roadmap, is_draft, wbs)` 로 떼고 기존 함수는 그 래퍼 (정본 하나) |
| 로드맵 파싱 · 진척 | `parse_milestone_text` · `parse_index_text` · `derive_state` | `derive_state` 에 산출물 존재 콜백 · 시각 인자 |
| 상태 생성 | `state/builder.build_workflow_state_payload` | **손질 없음** — 허브 데이터를 임시 디렉터리에 1.x 배치로 펼쳐 그대로 부른다 (`hub/memory.py`, 위키 lint §6.7 과 같은 방식). 펼침이 1.x 배치를 잘못 흉내 내면 생성기가 조용히 빈 값을 내므로, 검사는 **손으로 쓴 1.x 배치**의 출력과 대조한다 (`check_hub_memory` case 2) |
| handoff 파싱 | `project_docs.HandoffParser` | 허브는 handoff 를 구조로 저장하므로 파싱이 필요 없다 (1.x 들여오기 때만 — 파일이 있는 자리에서) |

### 2.3 의존 (DS1)

허브 쪽 설치는 `workflow_kit[hub]` — MCP 공식 SDK (`mcp`, streamable HTTP 서버 · 실측 §16.3 의 탐침이 1.27.0 으로 섰다) 와 그것이 끌어오는 ASGI 서버를 쓴다. **판 범위를 상한까지 고정**하고 판이 바뀌면 하네스 4종 실측(§8)을 다시 돈다. 작업 환경은 이 의존을 갖지 않는다 (R0.4).

## 3. 스키마 · 이관 (WBS-32.1)

### 3.1 공통 규칙

- SQLite 파일 하나, `journal_mode=WAL`, `foreign_keys=ON`. 모든 시각은 UTC ISO-8601 (`…Z` 가 아니라 `+00:00` — 1.x 응답 형식이 오프셋 표기만 받는다, 실측 §16.1 2a).
- 고칠 수 있는 레코드는 `version INTEGER` 를 갖는다. 쓰기는 `expected_version` 을 받고 다르면 **409 `version_conflict`** + 지금 `version` · 값을 돌려준다. 자동 병합하지 않는다 (R1.2 · R12.2 · R8.2).
- 모든 쓰기는 같은 트랜잭션에서 `event` 한 줄을 남긴다 (R1.5). `event` 는 지우거나 고치지 않는다.
- 모든 쓰기 요청은 `request_id` (클라이언트가 만드는 ULID)를 받을 수 있다. 같은 `(project, callsign, request_id)` 를 두 번 받으면 처음 결과를 돌려주고 다시 쓰지 않는다 — 보낼편지함 재전송 · 응답 중복 수신의 멱등 (R12.2 · R5.8).

### 3.2 git 주소 정규화 (요구 R3.2)

`gitkey.normalize(url) -> key`:

1. scp 형식 `user@host:path` → `ssh://user@host/path` 로 읽는다.
2. 스킴 · 사용자 정보 · 포트를 뗀다. 호스트를 소문자로.
3. 경로 끝의 `/` · `.git` 을 뗀다. 연속 `/` 는 하나로.
4. 경로 대소문자: 대소문자를 구분하지 않는 호스트(`github.com` · `gitlab.com` · `bitbucket.org`)는 소문자, 그 밖은 그대로 (DS8 — 다른 호스트는 소유자가 별칭으로 묶는다).
5. 서브그룹(`gitlab.com/a/b/c`)은 경로 그대로 둔다.
6. 결과 `host/path`. 로컬 경로 · `file://` 은 `invalid_remote` 로 거절 (F1).

[검증] requirements R3.2 의 표 + 이 규칙의 경우별 표 (`check_hub_gitkey`).

### 3.3 표

| 표 | 칼럼 (핵심) | 키 · 제약 | 요구 |
|---|---|---|---|
| `meta` | `key` · `value` | `schema_version` · `hub_id` · `created_at` | R1.3 |
| `project` | `id` (`P-<ULID>`) · `display_name` · `owner_callsign` · `settings_json` · `created_at` · `version` | — | R3.1 · R3.4 |
| `project_alias` | `key` (정규화 주소) · `project_id` · `kind` (`primary`/`alias`) · `added_by` · `added_at` | `key` 유일 | R3.2 · R3.5 · R3.6 |
| `callsign` | `project_id` · `id` · `kind` (`human`/`agent`) · `human_approved` · `role` (`owner`/`editor`) · `label` · `host` · `token_hash` · `guide_version_seen` · `client_version_seen` · `last_seen_at` · `revoked_at` · `version` | `(project_id, id)` 유일 · `id` 는 `^[a-z][a-z0-9-]{1,30}[a-z0-9]$`, 예약 `hub` | R4.1 · R4.7 · R7.7 · R7.8 · Q3 |
| `hub_token` | `token_hash` · `role` (`web`/`admin`) · `name` · `created_at` · `revoked_at` | — | R13.2 · R13.2a |
| `task` | `project_id` · `id` · `title` · `status` · `priority` · `assignee` (콜사인, 빈 값 허용) · `branch` · `wbs` · `wbs_exempt_reason` · `description` · `plan_md` · `fields_json` · `progress_note` · `progress_at` · `created_at` · `updated_at` · `version` | `(project_id, id)` 유일 · `status` ∈ 4 값 | R5.1~R5.7 |
| `task_seq` | `project_id` · `date` · `namespace` · `next` | `(project_id, date, namespace)` | R5.2 |
| `task_commit` | `project_id` · `task_id` · `sha` · `branch` · `added_by` · `added_at` | — | R5.9 · R10.4 |
| `plan_response` | `project_id` · `task_id` · `seq` · `body` (BLOB, response/1 그대로) · `body_sha256` · `received_at` · `verdict_json` · `applied_at` | `(project_id, body_sha256)` 유일 | R5.8 |
| `handoff` | `project_id` · `callsign` · `sections_json` · `updated_at` · `version` | `(project_id, callsign)` 유일 — 콜사인 하나에 하나 | R6.1 · R6.2 · G1 |
| `memory_note` | `project_id` · `callsign` · `kind` (`session`/`lesson`/`handoff_rollover`/`archive_1x`) · `title` · `body_md` · `meta_json` · `created_at` | — (추가만) | R4.5 · R6.2 · R14.4 |
| `checkpoint` | `project_id` · `callsign` · `created_at` · `body_json` (1.x `checkpoint.json` 칸) · `summary_md` | — (추가만) | R11.1 |
| `guide` | `project_id` · `version` · `body_md` · `updated_by` · `updated_at` | `(project_id, version)` — 판마다 한 줄 | R7.1 · R7.4 |
| `guide_proposal` | `project_id` · `id` · `base_version` · `body_md` · `proposed_by` · `status` (`open`/`approved`/`rejected`) · `decided_by` · `decided_at` | — | R7.5 · R7.7 |
| `roadmap_doc` | `project_id` · `path` (`index.md` · `M-NNN-*.md`) · `body_md` · `version` | `(project_id, path)` | R9.1 |
| `wiki_page` | `project_id` · `path` · `body_md` · `source_repo_key` · `source_sha` · `version` · `updated_by` · `updated_at` | `(project_id, path)` | R8.1~R8.4 |
| `wiki_ingest` | `project_id` · `id` · `callsign` · `at` · `log_line` · `pages_json` | — | R8.2 |
| `memory_entry` | `project_id` · `id` · `body_json` · `version` | — | R8.1 (E5) |
| `event` | `seq` (자동 증가) · `project_id` · `at` · `callsign` · `target_kind` · `target_id` · `op` · `before_json` · `after_json` · `via` (`mcp`/`http`/`client`) · `client_version` | 추가만 | R1.5 · R5.10 · R2.7 |
| `applied_request` | `project_id` · `callsign` · `request_id` · `result_json` · `at` | 유일 | §3.1 |
| `migration_1x` | `project_id` · `id` · `at` · `callsign` · `plan_json` · `report_json` | — | R14 |

- **task 의 칸 (DS2)** — 1.x task 파일의 Description 칸은 구조 칼럼과 `fields_json` (영향 문서 · 완료 기준 · 결과 · 위험 · 후속 · 검증 결과)에, **`## 🧭 Plan` 절은 `plan_md` 에 1.x 원문 그대로** 둔다. 판정 함수가 줄 목록을 받기 때문이다 (실측 §16.1 1 · 3a). 내보내기(R15)는 같은 칸에서 1.x 파일을 다시 만든다.
- **ID 네임스페이스 (DS3)** — 새 task ID 는 `TASK-<UTC 날짜>-<콜사인>-<NNN>`. 1.x 의 브랜치 slug 자리에 콜사인이 들어간다. 들여온 task 는 원래 ID 그대로 (R5.2).
- **로드맵 · 위키는 1.x 원문 텍스트** — 파싱 함수가 텍스트를 받는다 (`parse_milestone_text` · 실측 §16.1 5a). 위키 lint 는 페이지를 임시 디렉터리에 펼쳐 1.x 검사를 돈다 (§6.7).

### 3.4 이관 · 백업 (요구 R1.3 · R1.4)

- `migrations.py` 의 함수 목록이 판 순서다. 기동 때 `meta.schema_version` < 최신이면 **먼저 `hub backup` 과 같은 방식으로 `<db>.pre-v<n>-<시각>` 사본**을 만들고 순서대로 적용한다. 한 판은 한 트랜잭션.
- DB 판이 허브가 아는 최신보다 크면 기동을 거절한다 (`db_newer_than_hub`).
- `hub backup` 은 SQLite 온라인 백업 API 로 일관된 사본을 만든다 — 허브가 도는 중에도.

## 4. 도구 · HTTP API (WBS-32.2)

### 4.1 경로

| 경로 | 인증 | 몫 |
|---|---|---|
| `GET /healthz` | 없음 | `{ok, kit_version, contract, db_version, exposure}` (R1.6 · R13.3) |
| `/mcp` | Bearer (부트스트랩 묶음은 없음) | MCP streamable HTTP (R2.1) |
| `POST /v1/tools/<name>` | 같음 | **MCP 도구와 같은 함수 · 같은 인자 · 같은 결과** (DS5 · R2.7) |
| `GET /v1/bootstrap` | 없음 | 선택 클라이언트 원문 (`text/x-python`, 머리 `X-Hub-Client-Version` · `X-Hub-Client-Sha256`) (R2.7) |
| `GET /` | 없음 | 안내 페이지 — 지원 하네스 4종의 등록 명령 (R2.6) |
| `GET /ui/…` · `GET /api/…` | 화면 (§4.6) | 허브 화면 (M-037) |

### 4.2 판 협상 (요구 R0.6 · R1.6)

- 모든 응답 머리: `X-Hub-Kit` (kit 판) · `X-Hub-Contract` (`hub/1`) · `X-Hub-Db` (DB 판) · `X-Hub-Guide` (프로젝트가 정해진 요청이면 지침 판).
- 요청은 `contract` 를 실을 수 있다 (MCP: 도구 인자 · HTTP: 머리 `X-Hub-Contract`). 허브가 모르는 값이면 `unknown_contract` 400. 없으면 `hub/1` 로 본다.
- 선택 클라이언트는 `X-Hub-Client: hub-client/<판>` 을 싣고, 허브가 받아들이는 판 범위 밖이면 `client_outdated` 400 + 갱신 경로.
- 도구 이름 · 인자를 바꿀 때는 G4 (§17.1 의 2.0판) — 한 판 동안 옛 이름을 받고 결과에 `deprecated` 경고를 싣고, 다음 판에서 지운다.

### 4.3 오류 형식

```json
{"error_code": "version_conflict", "message": "…", "detail": {"current_version": 7, "current": {…}}}
```

| `error_code` | HTTP | 언제 |
|---|---|---|
| `unauthorized` | 401 | 토큰 없음 · 틀림 · 거둔 토큰 |
| `forbidden` | 403 | 역할 · 콜사인 범위 밖 (다른 콜사인 handoff 쓰기 · `web` 토큰 쓰기 · 에이전트의 지침 판 올림) |
| `not_found` | 404 | 프로젝트 · task · 페이지 없음 |
| `version_conflict` | 409 | §3.1 |
| `already_claimed` | 409 | 맡기 충돌 (R5.3) |
| `callsign_taken` | 409 | 쓰는 이름 재등록 |
| `invalid_field` · `unknown_field` | 400 | 스키마 오류 — `detail` 에 필드 · 제약 (R9.2) |
| `secret_in_payload` | 400 | §1-4 |
| `gate_denied` | 422 | 판정 거절 — `detail.kit_error_code` 에 1.x 코드 (`open_decisions` · `plan_lint_error` · `wbs_gate_denied` …) (R5.5 · R5.6) |
| `invalid_remote` | 400 | 원격 없음 · 로컬 경로 (F1) |
| `ignore_not_effective` | 409 | `.gitignore` 확인 실패 — 토큰 지시를 내지 않음 (R4.2) |
| `unknown_contract` · `client_outdated` | 400 | §4.2 |
| `payload_too_large` | 413 | 본문 상한 (기본 256KiB, 위키 묶음 2MiB — R13.5) |

### 4.4 도구 — 부트스트랩 묶음 (토큰 없이, 요구 R2.3 · R3)

| 도구 | 인자 | 결과 |
|---|---|---|
| `hub_project_lookup` | `remote_url` | `{key, project_id \| null, display_name}` |
| `hub_project_register` | `remote_url` · `display_name` · `callsign` · `kind` · `label` · `host` | `{project_id, callsign, token}` — 토큰은 **이 응답에서 한 번만**. 등록자 = `owner`, `human` 바로 승인 (Q3) |
| `hub_callsign_register` | `project_id` · `callsign` · `kind` · `label` · `host` | `{callsign, token, human_pending}` — `human` 은 소유자 승인 전 `agent` 권한 (Q3) |
| `hub_setup_plan` | `project_id` · `token` · `harnesses[]` · `scan` (`{files: {경로: 지금 내용 \| null}}` — `.gitignore` · `.mcp.json` · 진입 파일) | `{stage, steps: [쓰기 지시 …], blocked: […]}` — `stage` 는 `gitignore` → `files` (§6.1). 1.x 전환 계획은 M-038 |
| `hub_setup_confirm` | `project_id` · `token` · `files: [{path, sha256}]` · `checks: [{name, output}]` | `{confirmed[], unconfirmed[], next_steps[]}` (R2.4) |

**등록 직후 토큰 (DS4)** — 하네스의 MCP 연결은 등록 전에 만들어져 헤더 토큰이 없다. 그래서 부트스트랩 묶음의 셋업 도구는 인자 `token` 을 받는다. 다른 묶음은 **헤더 토큰만** 받는다 — 셋업이 끝나 하네스가 환경 변수 참조로 다시 연결한 뒤에야 보인다.

### 4.5 도구 — 토큰 묶음 (요구 R2.2)

| 묶음 | 도구 | 비고 |
|---|---|---|
| 세션 | `hub_session_start(repo_results?)` · `hub_session_end(handoff, progress[])` · `hub_checkpoint_put(body)` · `hub_compact_resume(summary_ids[])` | §6.2 ~ §6.4 |
| task | `hub_task_list(filter)` · `hub_task_get(id)` · `hub_task_create(…)` · `hub_task_update(id, expected_version, fields)` · `hub_task_claim(id)` · `hub_task_release(id)` · `hub_task_progress(id, note)` · `hub_task_close(id, expected_version, validation_result)` · `hub_task_link_commit(id, sha, branch)` | 게이트는 `create` · `update` · `close` 에서 (R5.5 · R5.6) |
| handoff · 상태 | `hub_handoff_get(callsign?)` · `hub_handoff_put(expected_version, sections)` · `hub_state(scope)` | `scope` = `callsign` / `project`, 결과는 `state.json` v1 (R6.3) |
| 결정 응답 | `hub_plan_respond(task_id, body)` · `hub_plan_status(task_id)` | body = response/1 바이트 그대로 (R5.8) |
| 지침 | `hub_guide_render(harness)` · `hub_guide_propose(base_version, body)` · `hub_guide_decide(proposal_id, approve)` | `decide` 는 승인된 `human` 만 (R7.7) |
| 로드맵 | `hub_roadmap_get()` · `hub_roadmap_put(path, expected_version, body)` · `hub_roadmap_state()` | 스키마 오류는 필드 · 제약과 함께 (R9.2) |
| 위키 | `hub_wiki_search(q)` · `hub_wiki_get(path)` · `hub_wiki_ingest(pages[{path, expected_version, body}], log_line)` · `hub_wiki_lint()` | 묶음 하나 = ingest 하나, 하나라도 409 면 전체 거절 (R8.2) |
| 전환 | `hub_migrate_plan(scan)` · `hub_migrate_import(batch, choices)` · `hub_migrate_report(id)` | §6.6 |
| 내보내기 | `hub_export(kinds[])` | 쓰기 지시로 1.x 형식 파일 (R15) |

### 4.6 화면 인증 (요구 R13.2 · R13.2a)

- 토큰은 `Authorization: Bearer` 로만 받는다. 쿼리 · 쿠키로 받지 않는다.
- 화면은 로그인이 없다. 브라우저에서 콜사인을 등록(`hub_callsign_register` 와 같은 함수)해 받은 토큰을 브라우저 저장소 키 `hub:<public_url 호스트>:<project_id>:token` 에 두고 쓰기에 싣는다.
- 토큰 없는 화면 요청은 허브 설정의 **화면 공용 `web` 토큰**이 켜져 있을 때만 `web` 권한(읽기 · 콜사인 등록)으로 돈다 — `hub serve --web-token-name NAME` 또는 앞단 프록시가 '토큰 없는 요청에만' 머리를 붙인다. **기본 꺼짐.**
- 화면 응답은 `Content-Security-Policy: default-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'` · `Referrer-Policy: same-origin` (워크벤치 선례). 링크 · API 호출은 상대 경로 (R13.4).

## 5. 쓰기 지시 · 렌더 영역

### 5.1 쓰기 지시 (요구 R2.4 · I1)

```json
{"op": "write", "path": ".gitignore", "mode": "append_line", "content": "/.workflow-hub/\n",
 "sha256_after": null, "verify": {"run": ["git", "check-ignore", "-v", ".workflow-hub/env"], "expect": "match"}}
```

- `op` ∈ `write` (전체 내용 · `sha256` 지정) · `append_line` (없을 때만 더함) · `run_and_report` (명령을 돌려 출력을 `hub_setup_confirm` 의 `checks` 로) · `user_scope_write` (저장소 밖 하네스 설정 — 경고 문구 동반, R2.5a).
- `path` 는 저장소 뿌리 상대 경로이거나 `~/` 로 시작하는 사용자 범위 경로(`user_scope_write` 만). `..` · 절대 경로는 허브가 만들지 않는다.
- **토큰을 담는 지시는 `.workflow-hub/env` · `user_scope_write` 둘뿐**이다. 저장소 안 다른 경로에 토큰이 들어가는 지시는 만들 수 없다 (R2.5a).
- 지시는 순서가 있다 — 앞 지시의 확인이 끝나야 다음 지시가 나온다 (`hub_setup_confirm` 의 `next_steps`).

### 5.2 진입 파일 렌더 영역 (요구 R7.4 · R7.5 · D10)

```
<!-- workflow-hub:begin project=P-… guide=<kit판>+p<프로젝트 판> sha256=<영역 본문 해시> -->
… 표준 규칙 층 (2.0판) + 프로젝트 지침 층 — 하네스 어댑터가 형식 · 예산을 맞춘다 …
<!-- workflow-hub:end -->
```

- 영역 밖(환경 덧붙임 · 손 문단)은 허브가 건드리지 않는다.
- 다시 쓰기 전에 지금 영역 본문의 해시를 머리의 `sha256` 과 대조한다. **다르면 쓰기 지시를 내지 않고** `local_edit_detected` 를 보고한다 — 고칠 것은 `hub_guide_propose` 로 (R7.5).
- 표준 규칙 층의 정본은 kit 의 새 파일 `core/hub_workflow_standard.md` (DS6) — 1.x `global_workflow_standard.md` 처럼 생성 블록의 원천이고, 세션 시작 확인(R10) · compact 직후 확인(R11) · 세션 끝 순서(R6.4) · 쓰기 금지 규칙을 담는다. 명령은 허브 MCP 도구 이름이다 (R7.3).
- 크기 예산은 1.x `ENTRY_BUDGET_BYTES` (8KiB) 를 영역 전체에 (R7.2).

## 6. 흐름 (WBS-32.3)

### 6.1 부트스트랩 (요구 R3 · R4.2 · R2.4)

1. 사람이 안내 페이지(`/`)의 그 하네스 한 줄로 허브 MCP 를 등록한다 (R2.6). 지원 4종의 등록 방식은 실측 §16.3 표 그대로: Claude Code `.mcp.json` · Codex `bearer_token_env_var` + `default_tools_approval_mode` · MiniMax `.mcp.json` · Antigravity 사용자 범위 + 경고.
2. 에이전트가 `git remote get-url origin` (없으면 원격 목록) 을 읽어 `hub_project_lookup`.
3. 없으면 `hub_project_register`, 있으면 `hub_callsign_register` → 토큰.
4. 에이전트가 `hub_setup_plan` 에 **저장소 훑기 결과**를 실어 부른다. 훑기는 허브가 정한 명령 목록(에이전트가 실행): 진입 파일 4종의 존재 · 머리 줄, `ai-workflow/` 의 1.x 흔적 (§6.6), `.gitignore` 의 해당 줄. 1.x 흔적이 있으면 결과에 전환 계획이 같이 온다.
5. 지시 순서: ① `.gitignore` `append_line` + `check-ignore` 확인 → ② (확인 통과 시에만) `.workflow-hub/env` `write` (모드 600 — Windows 는 사실대로 보고, R4.3) → ③ 진입 파일 렌더 영역 → ④ 하네스 설정 조각 (환경 변수 참조 · Antigravity 는 사용자 범위) → ⑤ 사람에게 '하네스를 다시 연결' 안내.
6. `hub_setup_confirm` 이 모두 확인되면 콜사인의 셋업 상태 = 완료. 확인 안 된 단계가 있으면 '미완료' 그대로 (R2.4).

### 6.2 세션 시작 확인 (요구 R10 · Q5)

`hub_session_start` 는 두 번 부른다.

1. 인자 없이 → `{hub: {…}, repo_check: {commands: [...], rules: [...]}, outbox_hint}`. 허브 쪽 결과: 지침 판(바뀌면 `[바뀜]` 과 렌더 지시) · 클라이언트 · 규칙 판 · 내 handoff · 내 task (진행 한 줄 포함) · 맡은 이 없는 열린 task · 대기 중 결정 응답. 저장소 쪽 명령 (`hub/session.py` 가 정본): `git fetch --prune`, `git status --porcelain=v2 --branch` (앞섬 · 뒤처짐은 `# branch.ab` 줄에서), `git rev-parse --abbrev-ref origin/HEAD`, `git check-ignore -v .workflow-hub/env`, 셋업한 진입 파일마다 `git grep --no-index -h -e workflow-hub:begin -- <파일>`, 내 task 에 묶인 커밋마다 `git cat-file -e <sha>^{commit}`. 명령 결과는 `{이름: {rc, output}}` — 요청하지 않은 이름은 거절한다.
2. `repo_results` 를 실어 다시 → 대조 보고: 뒤처짐 → 'fast-forward 후 시작' · 갈라짐 / 미커밋 변경 → **'멈추고 묻기'** · `.gitignore` 규칙 빠짐 → 경고 · 내 task 의 묶인 sha 가 저장소에 없음 → 보고 (R10.4).
3. 보고는 `confirmed[]` 와 `unconfirmed[]` 를 나눈다. 두 번째 호출이 없으면 저장소 항목은 전부 `unconfirmed` 다 (R10.3).
4. 허브에 닿지 않으면 도구 자체가 없다 — 표준 규칙 층의 지침이 "허브 미확인 · 캐시(있으면)로 연다" 를 말하고, 선택 클라이언트가 있으면 캐시 · 보낼편지함 건수로 보고한다 (R12.1 · R12.3).

### 6.3 세션 끝 (요구 R6.4 · R6.1)

`hub_session_end(handoff, progress[])` — 진행 중 task 의 진행 한 줄들과 콜사인 handoff 를 **한 트랜잭션**으로 쓴다. 결과에 '커밋 → push' 안내와 렌더 영역 커밋 여부(D10)를 싣는다. 실패하면 `incomplete` 로 보고한다. handoff §1 기준선 · §4 최근 완료의 상한은 허브가 강제하고 넘친 것은 `memory_note(kind=handoff_rollover)` 로 **옮긴다** (R6.2).

### 6.4 compact (요구 R11)

- 압축 전: `hub_checkpoint_put` — 1.x `checkpoint.json` 의 판단 층 칸(`next` · `unverified` · `verified` · `rejected`)과 기계 층(진행 task · 브랜치) (compact_relay_spec §3). hook 이 있는 하네스는 선택 클라이언트가 `PreCompact` 에서 올린다.
- 압축 직후: `hub_compact_resume(summary_ids)` — ① 내 task 상태 · 진행 · 결정 응답 도착 · 다른 콜사인의 변경(체크포인트 이후 `event` 의 `version` 차이) ② 체크포인트의 식별자 중 `summary_ids` 에 없는 것 ③ 이어 갈 '다음 걸음' 과 미검증 목록. 요약 식별자를 못 받으면 ② 는 '대조 불가' 로 (1.x §5 와 같다).

### 6.5 지침 렌더링 · 갱신 (요구 R7)

- `hub_guide_render(harness)` = 표준 층(kit 판) + 프로젝트 층(`guide` 최신 판) → 하네스 어댑터 → §5.2 영역 + 쓰기 지시.
- 지침 판 = `<kit 판>+p<프로젝트 판>`. kit 판이 바뀌어도(허브 업그레이드) 판이 바뀐다 → 다음 세션 시작이 `[바뀜]` 으로 알린다.
- 승인 흐름: `hub_guide_propose` → `guide_proposal(open)` → 승인된 `human` 이 `hub_guide_decide` → `guide` 새 판. 승인된 `human` 의 제안은 바로 판이 오른다 (R7.7).
- 콜사인이 렌더를 받으면 `callsign.guide_version_seen` 갱신 — 화면에 '옛 지침으로 도는 환경' (R7.8).

### 6.6 1.x 전환 매핑 (요구 R14)

감지 목록(에이전트가 실행하는 명령의 결과로 허브가 판정): `ai-workflow/memory/active/*/` (브랜치 네임스페이스) · 그 안의 `state.json` · `session_handoff.md` · `backlog/tasks/*.md` · `sessions/` · `lessons.md` · `.compact/` · `ai-workflow/memory/active/roadmap/` · `ai-workflow/wiki/` · memory_index · 진입 파일의 kit 생성 블록 · `.claude-plugin` 등 kit 플러그인 · hook · stdio MCP 설정, 그리고 1.x kit 판.

| 1.x 원천 | 허브 | 규칙 |
|---|---|---|
| `active/<branch>/backlog/tasks/<ID>.md` | `task` (+ `plan_md`) | 같은 ID 여럿이면 그 파일을 마지막으로 바꾼 커밋 시각이 가장 늦은 것이 정본, 같으면 기본 브랜치 (Q1). 나머지는 그 task 의 `event` (`op=imported_variant`) |
| `active/<branch>/session_handoff.md` · `sessions/*` · `lessons.md` | `memory_note(kind=archive_1x)` — 원문 그대로 + `meta_json{branch, path, commit, imported_at}` | 읽기 전용 (Q2). 전환한 콜사인의 `handoff` 는 **현재 브랜치** handoff 의 칸에서 시작 (R14.4) |
| `.compact/checkpoint.json` | `checkpoint` | 현재 브랜치 것만 |
| `roadmap/*.md` | `roadmap_doc` | 원문 그대로 (R9.1) |
| `ai-workflow/wiki/**` · memory_index | `wiki_page` · `memory_entry` | OKF v0.2 로 운반 (R8.6) · 출처에 저장소 키 + 지금 HEAD sha |
| 진입 파일 | 생성 블록은 버림 · 손 문단은 `guide_proposal` (초안, D11 승인 대상) | R14.5 |
| kit 플러그인 · hook · stdio MCP | 하네스별 교체 안내 · 삭제는 등록자 확인 뒤 | R14.9 · 4종 밖 하네스는 '지원 대상 아님' |

- 들여오기는 `hub_migrate_import` 로 묶음 전송(에이전트가 파일을 읽어 싣는다 · 묶음 상한 §4.3). 원본 파일은 지우지 않는다.
- 끝나면 쓰기 지시로 **'허브로 옮김' 표식** `ai-workflow/HUB_MIGRATED.json` `{hub: public_url, project_id, migrated_at, kit_version}` 을 쓰고 커밋을 안내한다 (R14.6). 1.x 안내 판(R16.4)의 쓰기 도구는 이 파일을 보면 거절한다. 표식을 지우면 1.x 로 돌아간다 (R14.7).

### 6.7 위키 lint (요구 R8.3 · 실측 §16.2)

허브가 페이지를 임시 디렉터리에 `ai-workflow/wiki/…` 배치로 펼치고, 경로 인자를 받게 고친 V-4 · 정위치 확인(V-1 의 정위치 부분만) · 점수 함수(coverage · cross_ref · discoverability · lifecycle — 기준 시각 인자) · `bidir_link` 를 돈다. freshness 는 원격 읽기(R8.4)가 켜진 경우만 재고 아니면 '미측정' + 대상 수 0. operational · trend 는 돌지 않는다.

## 7. 선택 클라이언트 (요구 R2.7 · R11.3 · R12)

`/v1/bootstrap` 이 내려주는 `hub_client.py` 한 파일. 하는 일은 셋뿐이다 — ① hook 에서 체크포인트 올리기 · compact 직후 재주입 ② 오프라인 보낼편지함 `.workflow-hub/outbox/<ULID>.json` (`request_id` 포함, 재전송 멱등) ③ 마지막 브리핑 · handoff · 내 task 캐시. 모든 호출은 `POST /v1/tools/<name>` — MCP 도구와 같은 함수다. 명령 세부는 M-034.

## 8. 검증 (요구 §21)

- 허브 왕복 검사는 **실제 프로세스 · 실제 포트**로 (가짜 HTTP 클라이언트가 출처 · 머리를 대신 싣지 않게). 화면은 실브라우저(CDP).
- 하네스 4종 실측은 실측 §16.3 의 탐침 방식 — **비밀은 환경 변수에만**, 서버 로그의 User-Agent 로 MCP 경로를 가린다, 대조(변수 없음) 실행을 같이 돈다. 의존 판(DS1)이 바뀌면 다시 돈다.
- kit 없는 환경 검증은 venv 없는 깨끗한 Python 3.10 으로 (R0.4).
- 판정 대조 fixture: 같은 task 를 1.x 경로(파일)와 허브 경로(데이터)로 판정해 같은 결과 · 같은 `error_code` (R0.7).

## 9. requirements 대응

| 요구 | 절 |
|---|---|
| R0.1~R0.7 | §1 · §2.2 |
| R1.1~R1.6 | §2.1 · §3.1 · §3.4 · §4.2 |
| R2.1~R2.8 · R2.5a | §4.1 · §4.4 · §4.5 · §5.1 · §6.1 · §7 · §8 |
| R3.1~R3.8 | §3.2 · §3.3 · §4.4 · §6.1 · §6.6 |
| R4.1~R4.7 | §3.3 (`callsign`) · §4.3 · §6.1 |
| R5.1~R5.10 | §2.2 · §3.3 (`task` · `task_seq` · `task_commit` · `plan_response` · `event`) · §4.5 |
| R6.1~R6.4 | §3.3 (`handoff` · `memory_note`) · §6.3 |
| R7.1~R7.8 | §3.3 (`guide` · `guide_proposal`) · §5.2 · §6.5 |
| R8.1~R8.6 | §3.3 (`wiki_*` · `memory_entry`) · §4.5 · §6.7 |
| R9.1~R9.3 | §3.3 (`roadmap_doc`) · §2.2 · §4.3 |
| R10.1~R10.4 | §6.2 |
| R11.1~R11.4 | §3.3 (`checkpoint`) · §6.4 · §7 |
| R12.1~R12.3 | §3.1 (`request_id`) · §6.2 · §7 |
| R13.1~R13.5 · R13.2a | §2.1 · §4.3 · §4.6 |
| R14.1~R14.9 | §6.6 |
| R15.1~R15.4 | §2.2 (`export.py`) · §4.5 · (A2A · 유휴 점검 도구 없음) |
| R16.1~R16.8 | 1.x 줄 정책 — 이 스펙 밖 (1.x 발행 절차 · RELEASE.md). 허브 쪽 접점은 §6.6 의 표식 |

## 10. design 결정 (DS) — 소유자 확정 (2026-11-21, 권고안 전부)

| # | 결정 | 확정 (권고안) | 버린 길 |
|---|---|---|---|
| DS1 | 허브의 HTTP · MCP 서버 구현 | **MCP 공식 SDK (`mcp`) + 그 ASGI 서버**, `workflow_kit[hub]` 추가 의존 · 판 범위 상한 고정 (§2.3) — 원격 MCP 전송 · 세션 · 형식을 직접 짜지 않는다 | 표준 라이브러리 HTTP 위에 MCP JSON-RPC 를 직접 구현 (1.x 읽기 전용 서버의 lines 구현처럼) |
| DS2 | task 계획 절의 저장 형태 | **1.x Plan 절 원문 텍스트 (`plan_md`)** — 판정 함수 재사용 · 내보내기 왕복 (§3.3) | 주장 · 결정을 표로 정규화 (판정 함수 대폭 수정) |
| DS3 | 새 task ID 네임스페이스 | **콜사인** — `TASK-<날짜>-<콜사인>-<NNN>` (§3.3) | 프로젝트 공용 연번 `TASK-<날짜>-<NNN>` |
| DS4 | 등록 직후 셋업의 인증 | **부트스트랩 묶음 셋업 도구만 인자 `token`**, 다른 묶음은 헤더만 (§4.4) | 등록 뒤 하네스 재연결을 먼저 요구 |
| DS5 | HTTP API 형태 | **`POST /v1/tools/<name>` — MCP 도구의 거울** (같은 함수 · 인자 · 결과) | REST 자원 경로 (`/v1/projects/{id}/tasks/{id}`) 를 따로 설계 |
| DS6 | 표준 규칙 층의 정본 | **새 파일 `core/hub_workflow_standard.md`** (1.x `global_workflow_standard.md` 는 1.x 줄에 그대로) | 1.x 파일 하나에 두 판을 넣는다 |
| DS7 | 콜사인의 범위 | **프로젝트마다** — 같은 사람도 프로젝트마다 등록 · 토큰 (§3.3) | 허브 전역 콜사인 + 프로젝트 참여 |
| DS8 | 주소 경로 대소문자 | **GitHub · GitLab · Bitbucket 은 소문자, 그 밖은 그대로** + 소유자 별칭 (§3.2) | 모두 그대로 · 모두 소문자 |
| DS9 | '허브로 옮김' 표식 파일 | **`ai-workflow/HUB_MIGRATED.json`** (§6.6) | `ai-workflow/memory/active/` 안 · 진입 파일 머리 |
