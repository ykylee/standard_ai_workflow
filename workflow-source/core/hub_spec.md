# 워크플로우 허브 스펙 (2.0)

- 문서 목적: 2.0.0 워크플로우 허브의 kit 계약 — 프로세스 · 모듈 · DB 스키마와 이관 · MCP 도구와 HTTP API · 흐름(부트스트랩 · 세션 시작 · 세션 끝 · compact · 지침 렌더링 · 1.x 전환) · 검증 — 을 정의한다.
- 범위: `python -m workflow_kit hub …` 명령, 허브가 여는 경로(`/mcp` · `/v1/…` · 화면 · `/healthz` · `/v1/bootstrap`), SQLite/PostgreSQL 스키마, 허브 MCP 도구, 쓰기 지시 형식, 진입 파일 렌더 영역, 1.x 들여오기 매핑. 화면의 구체 디자인은 M-037, 선택 클라이언트의 명령 세부는 M-034 가 정한다.
- 대상 독자: 구현자(M-033~M-039), workflow 설계자, 소유자 (DS 결정)
- 상태: draft (ADR-033 accepted 2026-11-21 — M-032 design 완료, DS1~DS9 소유자 확정. 구현은 M-033~M-039)
- 최종 수정일: 2026-11-25
- 관련 문서: `./hub_postgresql_spec.md` (backend · migration · import contract), `../../docs/planning/workflow-hub-requirements-2026-11.md` (요구 R0~R16 · 실측 §16 — 아래에서 "요구 R…" · "실측 §16.n"), `../../docs/planning/workflow-hub-review-2026-11.md` (concept), `../../ai-workflow/wiki/decisions/adr-033-workflow-hub.md`, `./claim_plan_spec.md`, `./plan_workbench_spec.md`, `./compact_relay_spec.md`, `./roadmap_milestone_wbs_spec.md`, `./stable_guarantee.md`

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
python -m workflow_kit hub serve   --db PATH [--bind 127.0.0.1] [--port 8770] [--public-url URL] [--web-token-name NAME]
python -m workflow_kit hub migrate --from-sqlite PATH --to-postgres URL
python -m workflow_kit hub backup  --db PATH --out PATH
python -m workflow_kit hub admin   --db PATH token issue --role {web,admin} --name NAME | token revoke --name NAME
python -m workflow_kit hub admin   --db PATH callsign revoke --project ID --callsign NAME
python -m workflow_kit hub admin   --db PATH project export --project ID --out FILE [--seal-to URL] [--public-url URL]
python -m workflow_kit hub admin   --db PATH project import --file FILE | seal --project ID --to URL | unseal --project ID | invite --project ID [--hours N]
```

- `--db` 는 기본 SQLite 경로 또는 PostgreSQL URL이다. SQLite는 기본·테스트 backend다. PostgreSQL의 versioned schema migration은 시작 때 자동 적용한다. SQLite 데이터 복사는 별도 `migrate` 명령으로 한다 — 상세 계약은 [`hub_postgresql_spec.md`](./hub_postgresql_spec.md).
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
| `wiki.py` | 위키 페이지 · ingest 묶음 · index/log 생성 · 읽기 · lint (§6.7) — 판정은 `common/wiki_rules.py` (1.x 검사와 공유) |
| `knowledge.py` | 프로젝트 전용 Git 문서 snapshot/search/get · DCR/ADR lifecycle (ADR-036) |
| `migrate1x.py` | 1.x 감지 · 들여오기 매핑 (§6.6) |
| `export.py` | git 내보내기 (R15) |
| `client/hub_client.py` | 선택 클라이언트 원문 (표준 라이브러리만, `/v1/bootstrap` 이 내려준다) |
| `ui.py` · `static/` | 허브 화면 — `/ui/` 정적 화면 · `/api/…` JSON (§4.7) |

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

허브 쪽 설치는 `workflow_kit[hub]` — MCP 공식 SDK `mcp>=2.3.0` (streamable HTTP 서버) 와 ASGI 서버를 쓴다. SDK v2 API (`add_request_handler`, HTTP 요청은 `ctx.request`)로 조립하며 MCP `2026-07-28` modern protocol 을 기본으로 사용한다. Go 허브도 같은 판의 `server/discover`, 요청별 metadata, HTTP routing headers 를 구현한다. 작업 환경은 이 의존을 갖지 않는다 (R0.4).

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
| `hub_account` · `hub_account_callsign` · `hub_account_session` · `hub_account_login_attempt` | 사람 계정 · 승인된 human 콜사인 연결 · 만료/폐기 가능한 세션 해시 · 로그인 실패 제한 | v16 | 3.2.2 |
| `task` | `project_id` · `id` · `title` · `status` · `priority` · `assignee` (콜사인, 빈 값 허용) · `branch` · `wbs` · `wbs_exempt_reason` · `description` · `plan_md` · `fields_json` · `progress_note` · `progress_at` · `created_at` · `updated_at` · `version` | `(project_id, id)` 유일 · `status` ∈ 4 값 | R5.1~R5.7 |
| `task_seq` | `project_id` · `date` · `namespace` · `next` | `(project_id, date, namespace)` | R5.2 |
| `task_commit` | `project_id` · `task_id` · `sha` · `branch` · `added_by` · `added_at` | — | R5.9 · R10.4 |
| `plan_response` | `project_id` · `task_id` · `seq` · `body` (BLOB, response/1 그대로) · `body_sha256` · `received_at` · `verdict_json` · `applied_at` | `(project_id, body_sha256)` 유일 | R5.8 |
| `handoff` | `project_id` · `callsign` · `sections_json` · `updated_at` · `version` | `(project_id, callsign)` 유일 — 콜사인 하나에 하나 | R6.1 · R6.2 · G1 |
| `memory_note` | `project_id` · `callsign` · `kind` (`session`/`lesson`/`handoff_rollover`/`archive_1x`) · `title` · `body_md` · `meta_json` · `created_at` | — (추가만) | R4.5 · R6.2 · R14.4 |
| `checkpoint` | `project_id` · `callsign` · `created_at` · `body_json` (1.x `checkpoint.json` 칸) · `summary_md` | — (추가만) | R11.1 |
| `guide` | `project_id` · `version` · `body_md` · `updated_by` · `updated_at` | `(project_id, version)` — 판마다 한 줄 | R7.1 · R7.4 |
| `guide_proposal` | `project_id` · `id` (`GP-<4자리>`) · `base_version` · `body_md` · `note` · `proposed_by` · `proposed_at` · `status` (`open`/`approved`/`rejected`) · `decided_by` · `decided_at` · `applied_version` | `(project_id, id)` — 판 7 (M-037 WBS-37.3) | R7.5 · R7.7 |
| `roadmap_doc` | `project_id` · `path` (`index.md` · `M-NNN-*.md`) · `body_md` · `version` | `(project_id, path)` | R9.1 |
| `wiki_page` | `project_id` · `path` · `body_md` · `source_repo_key` · `source_sha` · `version` · `updated_by` · `updated_at` · `last_ingest` | `(project_id, path)` · `index.md` · `log.md` 는 저장하지 않는다 (생성물) | R8.1~R8.4 |
| `wiki_page_revision` | `project_id` · `path` · `revision` · `body_md` · `status` (`active`/`tombstone`) · `updated_by` · `updated_at` | `(project_id,path,revision)` 불변 — 판 13, 기존 페이지는 현재 판을 초기 snapshot으로 복사 | ADR-036 |
| `knowledge_source` · `knowledge_revision` | 프로젝트 Git 원본/allowlist · path · commit SHA · content SHA-256 · 불변 Markdown body/revision | 프로젝트 범위. Git 원격 fetch 없이 호출자가 전달한 snapshot만 받는다 — 판 13 | ADR-036 |
| `decision_change` · `decision_event` | DCR proposal · target refs/base revisions · state/version · reviewer · decision · ADR path/hash · append-only timeline | `(project_id,id)` · 결정 변화와 감사 event — 판 13 | ADR-036 |
| `idea` · `idea_entry` | 상태(`new`/`reviewing`/`replied`/`adopted`/`kept`/`closed`) · 작성자 · `added_via`(`web`/`agent`) · `human_asked` · 맡은 콜사인과 기한 · 연결 task · version / 줄기(`idea`/`ask`/`reply`) | `(project_id, id)` `IDEA-<4자리>` · 원문은 고치지 않는다 — 판 19 | 3.4.0 |
| `a2a_peer` | 콜사인 간 A2A 메시지 — 보낸 · 받는 콜사인 · 맥락 · 원문 · 실림 횟수 · 답 · 거둠 시각 (상태는 저장하지 않고 파생) | `(project_id, id)` `A2M-…` · 보낸 콜사인의 `messageId` 유일 · 허브 간 이전에서 뺀다 — 판 20 | A2A A2 |
| `wiki_ingest` | `project_id` · `id` (`ING-<5자리>`) · `seq` · `callsign` · `at` · `log_line` · `pages_json` | `(project_id, seq)` 유일 — 거절된 묶음은 번호를 먹지 않는다 | R8.2 |
| `memory_entry` | `project_id` · `id` · `body_json` (1.x `MemoryEntry` 로 검증한 그대로) · `version` · `updated_by` · `updated_at` | `(project_id, id)` — 판 6 | R8.1 (E5) |
| `event` | `seq` (자동 증가) · `project_id` · `at` · `callsign` · `target_kind` · `target_id` · `op` · `before_json` · `after_json` · `via` (`mcp`/`http`/`client`) · `client_version` | 추가만 | R1.5 · R5.10 · R2.7 |
| `applied_request` | `project_id` · `callsign` · `request_id` · `result_json` · `at` | 유일 | §3.1 |
| `migration_1x` | `project_id` · `id` (`MIG-<4자리>`) · `at` · `callsign` · `status` (`planned`/`importing`/`done`) · `plan_json` · `report_json` (누적) | `(project_id, id)` — 판 8 (M-038 WBS-38.1) | R14 |

- **task 의 칸 (DS2)** — 1.x task 파일의 Description 칸은 구조 칼럼과 `fields_json` (영향 문서 · 완료 기준 · 결과 · 위험 · 후속 · 검증 결과)에, **`## 🧭 Plan` 절은 `plan_md` 에 1.x 원문 그대로** 둔다. 판정 함수가 줄 목록을 받기 때문이다 (실측 §16.1 1 · 3a). 내보내기(R15)는 같은 칸에서 1.x 파일을 다시 만든다.
- **분류 · 테스트 (M-058)** — `fields.category` 는 `level_1` · `level_2` · `level_3` 문자열을 갖는 프로젝트 task의 3단계 분류다. `wbs` 는 roadmap milestone/WBS leaf와 task를 연결하고 기존 roadmap_state v1 진척 계산을 유지한다. `fields.tests` 는 `{id,name,required,runs:[{status,summary?,run_at?,commit_sha?}]}` 배열이며 실행은 세션이 저장소에서 수행하고 결과만 허브에 기록한다. task 종료는 필수 테스트마다 가장 최근 run이 `passed`일 때만 허용한다. 선택 테스트는 완료를 막지 않는다.
- **ID 네임스페이스 (DS3)** — 새 task ID 는 `TASK-<UTC 날짜>-<콜사인>-<NNN>`. 1.x 의 브랜치 slug 자리에 콜사인이 들어간다. 들여온 task 는 원래 ID 그대로 (R5.2).
- **로드맵 · 위키는 1.x 원문 텍스트** — 파싱 함수가 텍스트를 받는다 (`parse_milestone_text` · 실측 §16.1 5a). 위키 lint 는 페이지를 임시 디렉터리에 펼쳐 1.x 검사를 돈다 (§6.7).

### 3.4 이관 · 백업 (요구 R1.3 · R1.4)

- `migrations.py` 의 함수 목록이 판 순서다. 기동 때 `meta.schema_version` < 최신이면 **먼저 `hub backup` 과 같은 방식으로 `<db>.pre-v<n>-<시각>` 사본**을 만들고 순서대로 적용한다. 한 판은 한 트랜잭션.
- DB 판이 허브가 아는 최신보다 크면 기동을 거절한다 (`db_newer_than_hub`).
- `hub backup` 은 SQLite 온라인 백업 API 로 일관된 사본을 만든다 — 허브가 도는 중에도.

### 3.5 허브 서버 간 프로젝트 이전 (M-039 WBS-39.4, 소유자 2026-11-21)

결정: **토큰은 그대로 이어받는다**(콜사인 행 — 토큰 해시 포함 — 을 옮긴다. 환경은 주소만 바꾸고, 새 허브의 `hub_setup_plan` 이 `.workflow-hub/env` · `.mcp.json` 을 새 주소로 다시 쓴다) · **원본은 봉인한다**(지우지 않는다) · **운반은 관리자 CLI 파일 묶음 먼저, HTTP 는 같은 묶음 형식으로 뒤에**.

- **묶음** `workflow-hub-project-bundle/1` — `{format, source{public_url, kit_version, db_version, exported_at}, project(행), tables{표: {columns, rows}}, counts, digest}`. 옮기는 표는 **`project_id` 열을 가진 표 전부**를 DB 에서 파생한다 (`transfer.project_tables`) — 허브 전역 표(`meta` · `hub_token` · `project` 행 자체는 따로)가 아닌 새 표는 저절로 따라오고, `check_hub_transfer` case 1 이 미분류 표를 red 로 본다. `digest` 는 project + tables 의 정규 JSON sha256. 파일은 600 으로 쓴다 (토큰 해시 · 프로젝트 기록).
- **순서** — ① 원본에서 `project export --seal-to <새 주소>` (먼저 봉인해 그 뒤 쓰기를 막고 묶음을 뜬다) ② 대상에서 `project import --file` (들이기 전 DB 사본 `.pre-import-<시각>-<난수>`) ③ 환경마다 허브 주소를 바꾸고 새 허브의 `hub_setup_plan` → `hub_setup_confirm` (토큰은 그대로) ④ 1.x 에서 전환한 저장소는 새 허브의 `hub_migrate_marker(action=issue)` 로 표식의 허브 주소를 다시 쓴다. 들이기가 실패하면 원본에서 `project unseal`.
- **들이기** — 한 트랜잭션, 외래 키는 커밋 때 본다. 이력(`event`)은 순서를 지키고 번호를 새로 매긴 뒤 `project_imported` 한 줄을 더한다. 거절(대상 변화 0): 형식 · `digest` 불일치 · 묶음 DB 판이 대상보다 새로움 · 대상에 없는 표 · 열 · 같은 프로젝트가 봉인되지 않은 채 있음(`project_exists`) · 다른 프로젝트가 쓰는 저장소 주소 키(`alias_taken`). **되옮기기**: 대상에 같은 프로젝트의 **봉인된** 사본이 있으면 그것을 새 묶음으로 바꾼다 (A → B → A).
- **봉인** — `project.settings_json.moved = {to, at}`. 그 프로젝트의 모든 도구 호출(셋업 도구는 인자의 `project_id` 로) · 화면 `/api` 가 `410 project_moved` + `moved_to`. 주소 조회는 `moved_to` 를 싣는다. 같은 허브의 다른 프로젝트는 그대로. `project unseal` 로 푼다.
- **HTTP 경로** (소유자 2026-11-21 '둘 다' · **대상 허브 일회용 초대 코드**) — ① 대상 허브 관리자가 `hub admin project invite --project <ID> [--hours 24]` 로 코드(`wfi_…`, 해시만 `hub_invite` 에 — 판 10, 허브 전역 표)를 만들어 소유자에게 준다 ② 소유자 환경에서 `hub_client.py move <대상 주소> <코드>` — 원본 `hub_project_export(seal_to)` (소유자 · 승인된 human, 먼저 봉인) → 대상 `hub_project_import(invite, bundle)` (토큰 없이 — 코드가 권한, 상한 64MiB) → 성공하면 `.workflow-hub/env` 의 주소를 대상으로 (토큰 그대로), 실패하면 **이 실행이 건 봉인만** `hub_project_unseal` 로 푼다 (원래 봉인돼 있던 프로젝트는 그대로 — 풀면 정본이 둘). 코드는 한 번 · 그 프로젝트 ID 만 · 만료 전 (`invalid_invite` · `invite_used` · `invite_expired` · `invite_wrong_project` 403). 봉인된 프로젝트에서도 `hub_project_lookup` · `hub_project_export` · `hub_project_unseal` 은 받는다 (`transfer.SEALED_ALLOWED`). 지금 허브와 같은 주소로 봉인하려 하면 거절.

## 4. 도구 · HTTP API (WBS-32.2)

### 4.1 경로

| 경로 | 인증 | 몫 |
|---|---|---|
| `GET /healthz` | 없음 | `{ok, hub_version, kit_version, contract, db_version, exposure}` (R1.6 · R13.3) |
| `/mcp` | Bearer (부트스트랩 묶음은 없음) | MCP streamable HTTP (R2.1) |
| `POST /v1/tools/<name>` | 같음 | **MCP 도구와 같은 함수 · 같은 인자 · 같은 결과** (DS5 · R2.7) |
| `GET /v1/bootstrap` | 없음 | 선택 클라이언트 원문 (`text/x-python`, 머리 `X-Hub-Client-Version` · `X-Hub-Client-Sha256`) (R2.7) |
| `GET /` | 없음 | 안내 페이지 — 지원 하네스 4종의 등록 명령 (R2.6) · `/setup.md` 링크 |
| `GET /setup.md` | 없음 | **에이전트용 셋업 절차** (`text/markdown`, M-039 WBS-39.1 · 소유자 2026-11-21) — 사람은 "이 주소를 읽고 셋업해" 한 줄만. 순서 · 지킬 것(토큰 비노출 · 지시 밖 파일 0 · 커밋은 사람) · 멈출 자리만 싣고 쓸 내용은 싣지 않는다(셋업 지시가 낸다). 하네스 명령은 안내 페이지와 한 정본(`guide_page.harness_commands`), 부르는 도구는 `guide_page.SETUP_TOOLS` |
| `GET /ui/…` · `GET /api/…` | 화면 (§4.6) | 허브 화면 (M-037) |

### 4.2 판 협상 (요구 R0.6 · R1.6)

- 모든 응답 머리: `X-Hub-Version` (허브 런타임 판) · `X-Hub-Kit` (kit 호환 판) · `X-Hub-Contract` (`hub/1`) · `X-Hub-Db` (DB 판) · `X-Hub-Guide` (프로젝트가 정해진 요청이면 지침 판). MCP `serverInfo.version` 도 허브 런타임 판을 싣는다.
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
| `payload_too_large` | 413 | 본문 상한 (기본 256KiB — R13.5. HTTP `hub_migrate_plan` · `hub_migrate_import` 만 8MiB: 선택 클라이언트의 전환 운반, `app.BIG_BODY_TOOLS`) |
| `project_moved` | 410 | 봉인된(다른 허브로 옮긴) 프로젝트의 도구 · 화면 호출 — `detail.moved_to` 에 새 주소 (§3.5). 주소 조회(`hub_project_lookup`)는 거절하지 않고 `moved_to` 를 싣는다 |
| `invalid_bundle` · `bundle_digest_mismatch` · `bundle_newer_than_hub` · `bundle_unknown_table` · `bundle_unknown_column` · `project_exists` · `alias_taken` | 400 · 409 | 이전 묶음 들이기 거절 (§3.5) — 대상 허브 변화 0 |
| `invalid_invite` · `invite_used` · `invite_expired` · `invite_wrong_project` | 403 | 허브 간 이전 초대 코드 (§3.5) |
| `unsupported_media_type` | 415 | 화면 `/api` 쓰기의 본문이 `application/json` 이 아니다 (§4.7 — 다른 출처 폼 위조 차단) |

### 4.4 도구 — 부트스트랩 묶음 (토큰 없이, 요구 R2.3 · R3)

| 도구 | 인자 | 결과 |
|---|---|---|
| `hub_project_lookup` | `remote_url` | `{key, project_id \| null, display_name}` |
| `hub_project_register` | `remote_url`? · `display_name` · `callsign` · `kind` · `label` · `host` | `{project_id, key, callsign, token}` — 토큰은 **이 응답에서 한 번만**. 등록자 = `owner`, `human` 바로 승인 (Q3). **원격이 없으면 `remote_url` 을 빼거나 비운다** — 키 `local:<난수>` (`gitkey.local_key`, 정규화 키와 겹치지 않음) · `local_key: true` · 주소 조회로는 못 찾아 다른 환경이 합류할 수 없다 → 원격이 생기면 `hub_project_bind_remote` (소유자 2026-11-21 '로컬 키 발급 · 나중에 묶기') |
| `hub_callsign_register` | `project_id` · `callsign` · `kind` · `label` · `host` | `{callsign, token, human_pending}` — `human` 은 소유자 승인 전 `agent` 권한 (Q3) |
| `hub_setup_plan` | `project_id` · `token` · `harnesses[]` · `scan` (`{files: {경로: 지금 내용 \| null}}` — `.gitignore` · MCP 설정 · 진입 파일) | `{stage, steps: [쓰기 지시 …], blocked: […]}` — `stage` 는 `gitignore` → `files` (§6.1). 미등록/미지원 하네스는 `stage=harness_support`, 빈 `steps`, `hub_harness_report` 제보 안내를 돌려주며 저장소 변경 지시를 내지 않는다. 관리자 승인 시 설정 지원 프로필을 함께 등록한다. |

### 6.8 미지원 하네스 셋업 등록

클라이언트는 `hub_session_start` 의 `harness_support` 가 `unknown` 이거나 `hub_setup_plan` 이 `harness_support` 를 돌려주면 `hub_harness_report` 로 하네스 정보와 경로 후보를 보고한다. 안전한 선언형 프로필 `mcp-http-json-v1` 을 제보하려면 `config_formats` 에 `mcp-http-json-v1`, `mcp_transports` 에 `streamable-http`, `entry_file_candidates` 와 `.json` 인 `mcp_config_candidates` 가 필요하다. 사람 허브 관리자는 웹 화면에서 후보 경로와 호환성을 확인하고, 사람 담당자 1명 이상 및 명시적 확인과 함께 승인한다. 승인되지 않은 보고는 셋업 파일을 만들지 않는다.

승인된 프로필은 `{kind: "mcp-http-json-v1", entry_file, mcp_config_path}` 이며 선택 경로는 보고된 후보여야 한다. 셋업은 승인된 진입 파일에 표준 허브 영역을 병합하고, MCP JSON 경로의 `mcpServers.workflow-hub` 에 Streamable HTTP 주소와 `${WORKFLOW_HUB_TOKEN}` 참조를 병합한다. 실행 명령/eval, 임의 코드, 토큰 값의 MCP JSON 저장은 지원하지 않는다. Go 판은 Python 판과 같은 응답·경로·쓰기 경계를 지킨다.
| `hub_setup_confirm` | `project_id` · `token` · `files: [{path, sha256}]` · `checks: [{name, output}]` | `{confirmed[], unconfirmed[], next_steps[]}` (R2.4) |

**등록 직후 토큰 (DS4)** — 하네스의 MCP 연결은 등록 전에 만들어져 헤더 토큰이 없다. 그래서 부트스트랩 묶음의 셋업 도구는 인자 `token` 을 받는다. 다른 묶음은 **헤더 토큰만** 받는다 — 셋업이 끝나 하네스가 환경 변수 참조로 다시 연결한 뒤에야 보인다.

### 4.5 도구 — 토큰 묶음 (요구 R2.2)

| 묶음 | 도구 | 비고 |
|---|---|---|
| 세션 | `hub_session_start(repo_results?, client?)` · `hub_session_end(handoff, progress[])` · `hub_checkpoint_put(body)` · `hub_compact_resume(summary_ids[])` | §6.2 ~ §6.4 |
| task | `hub_task_list(filter)` · `hub_task_get(id)` · `hub_task_create(…)` · `hub_task_update(id, expected_version, fields)` · `hub_task_claim(id)` · `hub_task_release(id)` · `hub_task_progress(id, note)` · `hub_task_close(id, expected_version, validation_result)` · `hub_task_link_commit(id, sha, branch)` | 게이트는 `create` · `update` · `close` 에서 (R5.5 · R5.6) |
| handoff · 상태 | `hub_handoff_get(callsign?)` · `hub_handoff_put(expected_version, sections)` · `hub_state(scope)` | `scope` = `callsign` / `project`, 결과는 `state.json` v1 (R6.3) |
| 결정 응답 | `hub_plan_respond(task_id, body)` · `hub_plan_status(task_id)` | body = response/1 바이트 그대로 (R5.8). **보내는 쪽은 승인된 `human` 콜사인이고 body 의 `responder` 는 그 콜사인** — 아니면 `forbidden` (소유자 2026-11-21 · R4.6: 에이전트가 자기 계획의 결정을 닫거나 남의 이름으로 답하지 못한다) |
| 콜사인 승인 | `hub_callsign_approve(callsign)` | 승인된 `human` 소유자만. 승인 전 `human` 은 `agent` 권한 (Q3) |
| 원격 묶기 | `hub_project_bind_remote(remote_url)` | 승인된 `human` 소유자만. 별칭 키(`project_alias.kind='alias'`)로 더한다 — 이미 이 프로젝트 키면 `already`, 다른 프로젝트 키면 409 `alias_taken` (합치는 길은 없다). 원격 없이 등록한 프로젝트 · 같은 저장소의 다른 표기 (DS8) |
| 지침 | `hub_guide_render(harness)` · `hub_guide_get()` · `hub_guide_propose(base_version, body, note?)` · `hub_guide_decide(proposal_id, approve)` | `decide` 는 승인된 `human` 만 (R7.7). `base_version` 이 지금 판이 아니면 409, 렌더 예산을 넘는 본문은 422 (§6.5) |
| 위키 운반 | `hub_wiki_import_dir(files[{path, content}], summary, overwrite?)` · `hub_wiki_export(format=dir\|okf, out_dir?, cursor?)` · `hub_wiki_import_okf(files, summary)` | 운반 = 1.x 위키 디렉터리 그대로 (R8.6 2026-11-21 결정). 내보내기는 쓰기 지시(§5.1 `op: write` · `sha256`)로 — 허브는 저장소에 쓰지 않는다 (R15.1). 응답 150KB 넘으면 `next_cursor`. `dir` 은 표식 `.hub-export.json` (R15.2) 을 함께 낸다. `okf` 는 출판(손실) — `excluded` (묶음에 없는 페이지 전부) · `excluded_by_error`. 남의 OKF 들여오기는 loose · 한 방향 · 묶음 하나가 요청 상한(256KB) 안 (M-036 WBS-36.3) |
| memory_index | `hub_memory_entry_put(entry, expected_version)` · `hub_memory_entry_get(id)` · `hub_memory_entry_list()` | 1.x `MemoryEntry` 스키마 · 새 entry 는 0 · 다르면 409 (M-036 WBS-36.2) |
| 위키 원격 읽기 | `hub_wiki_remote_set(fetch_url)` | **소유자만** — `project.settings_json.wiki_remote`. 빈 값이면 끈다. `https://` · `ssh://` · `git@host:path` · `file:///` 만 (git 원격 도우미 `ext::` 등 거절) (R3.7 · R8.4) |
| 로드맵 | `hub_roadmap_get()` · `hub_roadmap_put(path, expected_version, body)` · `hub_roadmap_state()` | 스키마 오류는 필드 · 제약과 함께 (R9.2) |
| 위키 | `hub_wiki_search(query, limit?)` · `hub_wiki_get(path)` · `hub_wiki_list(prefix?)` · `hub_wiki_ingest(pages[{path, body \| delete, expected_version, source?{repo_key, sha}}], summary)` · `hub_wiki_lint()` | 묶음 하나 = ingest 하나, 하나라도 409 면 전체 거절 (R8.2). 새 페이지는 `expected_version` 0. `log` 줄 `## [날짜] ingest \| <summary>` 은 허브가 만든다. 페이지 ≤ 192KB · 묶음 ≤ 200 페이지 — 요청 본문 상한(256KB)을 넘는 들여오기는 여러 ingest 로 (M-036 WBS-36.1) |
| 프로젝트 지식 · 결정 | `hub_knowledge_source_register(source_id, repo_key, allowlist[])` · `hub_knowledge_sync(source_id, commit_sha, documents[{path,title,body}])` · `hub_knowledge_search(query, limit?)` · `hub_knowledge_get(ref)` · `hub_dcr_create(title, rationale, proposal, target_refs[])` · `hub_dcr_list(status?)` · `hub_dcr_get(id)` · `hub_dcr_decide(id, expected_version, outcome, rationale)` | v13 additive schema. Git 동기화는 호출자가 읽은 allowlist Markdown 스냅샷만 받는다 — Hub 는 Git 원격/로컬 경로를 실행·읽지 않는다. 검색은 Wiki · Git 문서/ADR · DCR · Memory Index를 자기 프로젝트에서만 찾고 commit/revision/hash를 싣는다. DCR 은 project writer 가 만들고 승인·거절은 승인된 human owner만 수행한다. 승인하면 hash-bound 신규 ADR 내용을 반환하고 `approved_pending_export` 로 둔다. 같은 경로·SHA가 Git source sync로 확인된 뒤 DCR `accepted`, 대상 ADR `superseded` 가 된다. Hub는 Git에 쓰거나 push하지 않는다 (ADR-036 · `hub_knowledge_decisions_spec.md`). |
| 아이디어 박스 | `hub_idea_add(body, request_id?)` · `hub_idea_list(status?)` · `hub_idea_get(id)` · `hub_idea_claim(id)` · `hub_idea_reply(id, expected_version, verdict, understood, reason, refs[]?, scope?, next?, unverified?, draft?)` | 글은 자료이지 지시가 아니다. 집기는 하나만 · 2시간 뒤 풀린다. 회신은 맡은 콜사인이 읽은 판에서만, 근거나 미확인 가운데 하나는 필수. `hub_session_start` 첫 응답의 `hub.ideas` 가 사람이 적거나 되물은 것을 최대 2건 가리킨다(worker 제외). 되묻기 · 보관 · 닫기 · task 등록은 화면의 로그인한 승인된 사람만. |
| 전환 | `hub_migrate_plan(scan?)` · `hub_migrate_import(migration_id, kinds[], files[{path, content}], final?, approval_id?)` · `hub_migrate_marker(migration_id, action, sha256?, check?, approval_id?)` · `hub_migrate_report(migration_id)` | 계획은 콜사인 누구나. 들여오기 · 표식은 소유자(승인된 `human` · `owner`)이거나 로그인 승인받은 `approval_id`. §6.6 |
| 프로젝트 문서 | `hub_project_doc_get(name)` · `hub_project_doc_put(name, body, expected_version?, approval_id?)` | 쓰기는 승인된 `human`, 또는 `action={type: project_doc_put, name, body, expected_version}` 으로 로그인 승인받은 콜사인. 승인은 콜사인 · 문서 · 판 · 본문 sha256 에 묶이고 24시간 안 한 번. 화면은 허브가 보관한 본문과 그 판의 차이를 보인다. 그 사이 판이 오르면 409 |
| 내보내기 | `hub_export(kinds[])` | 쓰기 지시로 1.x 형식 파일 (R15) |

### 4.6 화면 인증 (요구 R13.2 · R13.2a)

- 토큰은 `Authorization: Bearer` 로만 받는다. 쿼리 · 쿠키로 받지 않는다.
- 에이전트/MCP 요청은 기존처럼 `Authorization: Bearer` 콜사인 토큰을 쓴다. 사람 웹 사용은 허브 계정(계정 이름 + PBKDF2-HMAC-SHA256 비밀번호)을 쓰며, 가입은 토큰 없이 하며 그 자체로는 권한이 없다(시간당 30건). 프로젝트 참여(`/api/account/join`)는 승인 전 human 콜사인을 만들고 소유자가 승인한다. 승인된 human 콜사인 토큰을 제시하면 바로 연결한다. 계정은 사람 콜사인을 여러 프로젝트에서 연결할 수 있고, 같은 프로젝트의 콜사인은 계정 하나에만 묶인다.
- 사람 로그인은 30일 만료 세션의 해시만 DB에 저장하고 `HttpOnly; SameSite=Strict` 쿠키로 세션을 전달한다. 출처는 설정한 공개 주소이거나 요청이 온 호스트여야 하고, 공개 주소로 오면 `Secure` 는 그 scheme 을, `Path` 는 그 하위 경로를 따른다(프록시 머리에 기대지 않는다). 공개 호스트의 Origin scheme 만 바뀌어 오면 `Sec-Fetch-Site: same-origin` 이 있을 때만 받는다. 비밀번호는 8~256자다. 로그아웃/만료 세션은 인증되지 않는다. 비밀번호 실패는 계정 이름 기준 8회/15분으로 잠근다.
- 브라우저 세션 쿠키를 동반한 쓰기 요청은 `Origin` 과 같은 출처인지 확인한다. 계정 이름은 public API 에 노출하지 않고 로그인 실패 응답도 계정 유무를 구분하지 않는다.
- 기존 콜사인 토큰 브라우저 인증은 하위 호환으로 유지하지만, 사람 사용 가이드와 화면 기본 동작은 계정 로그인을 우선한다. 화면은 계정에 연결된 프로젝트만 나열한다.
- 토큰 없는 화면 요청은 허브 설정의 **화면 공용 `web` 토큰**이 켜져 있을 때만 `web` 권한(읽기 · 콜사인 등록)으로 돈다 — `hub serve --web-token-name NAME` 또는 앞단 프록시가 '토큰 없는 요청에만' 머리를 붙인다. **기본 꺼짐.**
- 화면 응답은 `Content-Security-Policy: default-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'` · `Referrer-Policy: same-origin` (워크벤치 선례). 링크 · API 호출은 상대 경로 (R13.4).

### 4.7 화면 (M-037 WBS-37.1 · 37.2 · 37.3)

**경로** — 모두 §4.6 의 머리(CSP · Referrer-Policy)를 싣는다. 정적 자산은 데이터가 없어 인증 없이 내린다.

| 경로 | 몫 |
|---|---|
| `GET /ui` | `307 → ui/` (상대 리다이렉트) |
| `GET /ui/` · `/ui/hub.js` · `/ui/hub.css` · `/ui/favicon.svg` | 정적 화면 (`hub/static/`) — hash 길(`#/p/<id>` · `#/p/<id>/t/<task>` · `#/p/<id>/events`), DOM 은 textContent 로만 |
| `GET /api/session` | 이 요청의 주체 (`kind` · 콜사인 · `can_answer`) · 공용 토큰 켜짐 여부 |
| `POST /api/account/enroll` · `/login` · `/link` · `/logout` | 승인된 human 콜사인으로 첫 등록 · 계정 로그인 · 추가 프로젝트 콜사인 연결 · 세션 폐기. JSON + Origin 검사 |
| `GET /api/projects` | 프로젝트 목록 + status 별 task 수 — 콜사인 토큰은 자기 프로젝트 하나 |
| `GET /api/projects/{id}/callsigns` | 콜사인 표 (WBS-37.2) — 콜사인마다 종류 · 승인 · 역할 · 마지막 활동(`last_seen_at`) · 받은 지침 판과 `guide_state` (`current` / `stale` / `never` — 허브 판은 세션 시작과 같은 `render.guide_version`) · 클라이언트 판(`client_version_seen`) · 셋업 끝 여부 · 보관(거둔 콜사인) · handoff 시각 · **맡은 열린 task 와 진행 한 줄** ('지금 누가 무엇을', R5.7) |
| `GET /api/projects/{id}/callsigns/{cs}` | 표의 줄 + 그 콜사인의 handoff 칸 · version (읽기는 프로젝트 안 누구나 — G3) |
| `GET /api/projects/{id}/guide` · `POST …/guide` · `POST …/guide/proposals/{gid}` | 지침 (WBS-37.3) — 지금 판 · 본문 · 판 이력 · 제안(지금 판 대비가 아니라 **기준 판 대비** unified diff · `stale`) · `can_decide` · `can_propose`. 쓰기는 `hub_guide_propose` · `hub_guide_decide` 와 같은 함수, 콜사인 토큰만 (web 403) |
| `GET /api/projects/{id}/wiki` · `/wiki/page?path=` · `/knowledge/ref?ref=` · `/dcr[/{id}]` | 프로젝트 지식 화면 — 목록은 위키 페이지, `q` 검색은 Git 문서/ADR · Wiki · DCR · Memory Index를 provenance와 함께 찾고 ref로 연다. DCR 목록·상세는 감사 timeline 및 ADR 링크를 보인다. 모두 프로젝트 범위 읽기 함수다 |
| `POST /api/projects/{id}/callsigns/{cs}/approve` | 사람 콜사인 승인 (`hub_callsign_approve` 와 같은 함수 — 승인된 `human` 소유자만, 그 밖 403) |
| `GET /api/projects/{id}` · `/tasks` · `/tasks/{task}` · `/events` · `/roadmap` · `/orchestration` | 프로젝트(요약 KPI `summary` 포함) · task 목록(`status` · `roadmap=linked|unlinked` · `milestone` · `wbs` · `category_level_1..3` · `limit` · `offset`, 최근 순, 필터 뒤 `total`·`facets`) · task 상세(계획 원문 · 주장 · 결정 상태 · 열린 결정 · 린트 · 그 task 의 이력 · 커밋) · 프로젝트 이력 · 로드맵 파생 상태 · 2.1 오케스트레이션 현황(세션 5상태·unknown · 배정 · 미전달 · 세션 요청 · 중계 호스트). 목록은 필터/페이지를 URL에 보존하고 표/카드 보기를 제공한다 (M-061) |
| `POST /api/projects/{id}/orchestration/halt` · `/lease` · `/approvals/{rid}` · `/relays/invite` · `/relays/{hid}/revoke` | 2.1 오케스트레이션 제어(소유자 콜사인 토큰만, `application/json`, `hub/orchestration.py` · `hub/relay.py` 와 같은 함수) |
| `GET · POST /api/projects/{id}/ideas` · `GET · POST /api/projects/{id}/ideas/{iid}` | 아이디어 목록 · 적기 · 줄기 · 처리(`action` = `ask` · `keep` · `close` · `adopt`, `expected_version` 필수). 쓰기는 계정으로 로그인한 승인된 사람만. `adopt` 는 WBS 게이트를 거친 task 생성과 한 트랜잭션. |
| `GET /api/projects/{id}/confirmations` · `POST /api/projects/{id}/confirmations/{rid}` | 승인된 owner 가 사람 확인 요청을 보고 결정한다. `hub_approval_request` 요청은 허브 받은편지함 `confirmation_result` 를 요청 콜사인 받은편지함에 남기며, 승인 자체가 에이전트 작업을 실행하지 않는다. `action` 이 실린 요청은 **계정 로그인 세션**만 승인할 수 있고(토큰은 403 `account_login_required`), 승인은 `approval_grant` 에 남아 요청 콜사인 · 실행 · 대상에 묶이며 24시간 뒤 만료되고 한 번 쓰면 `used` 다. |
| `POST /api/projects/{id}/callsigns` | 콜사인 등록 (`hub_callsign_register` 와 같은 함수) — 토큰은 이 응답에서 한 번만 |
| `POST /api/projects/{id}/tasks/{task}/responses` | 결정 답 `{plan_digest, values{D: v}, opened{D: bool}, comments{대상: 글}}` → 허브가 response/1 본문을 **응답자 = 이 콜사인 · `client: hub-ui`** 로 만들어 `hub_plan_respond` 와 같은 함수에 넘긴다. 지문이 다르면 `version_conflict` 409, 선택지 밖 값은 `invalid_field` 400, 받은 시각은 같은 응답자의 앞선 응답보다 늦게 (워크벤치 §6-6 과 같은 단조 규칙) |

**주체** — 머리 토큰이 있으면 그 토큰(틀리면 401), 없으면 유효한 허브 계정 쿠키를 확인하고 요청 프로젝트에 연결된 사람 콜사인 권한으로 좁힌다. 계정도 없으면 `--web-token-name` 이 켠 공용 `web` 토큰(매 요청 확인 — 거두면 즉시 401), 셋 다 없으면 401. 읽기는 권한 확인 뒤 한 프로젝트로 좁힌 `viewer` 주체로 store 의 읽기 함수를 부른다 — `viewer` 는 도구 입구가 받지 않는다. 콜사인 토큰은 자기 프로젝트만 읽고 계정은 연결된 프로젝트만 읽는다(남의 프로젝트 403). 쓰기는 해당 프로젝트의 사람 콜사인 권한으로 판정한다.

**위조 방지** — `/api` 쓰기는 `content-type: application/json` 만 받는다 (아니면 415). 계정 세션 쿠키가 붙은 쓰기는 추가로 정확한 `Origin` 일치가 필요하다. 로그인/등록/연결도 같은 Origin 검사를 한다.

**브라우저 저장소** — 키 `hub:<public_url 호스트>:<project_id>:token` (호스트는 `/healthz` 의 `public_url`). 401 이면 '이 브라우저에서 지운 뒤 다시 등록' 을 안내하고, '이 브라우저에서 콜사인 지우기' 는 토큰이 다시 나오지 않는다는 확인을 받는다. 등록 안내는 다음 화면 머리에 실어 다시 그려도 남는다.

**받은 판 기록 (R7.8 · R4.7)** — 표가 보이는 값은 실제로 받은 것이어야 한다. `last_seen_at` 은 콜사인 토큰 인증마다, `client_version_seen` 은 그 요청에 `X-Hub-Client` 머리가 있을 때 적는다. `guide_version_seen` 은 셋업 확인(§6.1)과 **세션 시작 2단계(§6.2)** 에서 적는다 — 진입 파일을 모두 쟀고 판이 하나로 같을 때만 그 판, 섞이면 그대로 둔다 (한쪽만 다시 렌더한 환경을 '최신' 으로 보이지 않게).

**검증** — `check_hub_ui` (게이트, HTTP): 공용 토큰 꺼짐 401 · 켜짐 읽기 200 / 답 403 / 등록 1회 / 409 / 거두면 401 · 화면 머리 · 상대 경로 · 읽기 범위 · 결정 답 권한(화면 · MCP) · 415 · 409 · 400 · 콜사인 표(지금 하는 일 · 마지막 활동 · 클라이언트 판 · 보관 · handoff 읽기 범위) · 받은 지침 판(렌더 → 세션 시작 뒤 최신 · 새 판 뒤 옛 지침 · 섞이면 불변, 양쪽 순서) · 화면 승인 · 지침 제안(D11 — agent · 승인 전 human 은 제안, 사람만 판, 승인 · 거절 · 낡은 기준 409 · 예산 422, admin 포함) · 위키 읽기(목록 · 검색 · 페이지 · 생성물 · 범위). 실브라우저 왕복(등록 → 소유자 승인 → 결정 답 → 이력의 콜사인 이름 · 콘솔 오류 0)은 게이트가 아니라 task Proof 의 헤드리스 Chromium 실측이다 (워크벤치 선례).

## 5. 쓰기 지시 · 렌더 영역

### 5.1 쓰기 지시 (요구 R2.4 · I1)

```json
{"op": "write", "path": ".gitignore", "mode": "append_line", "content": "/.workflow-hub/\n",
 "sha256_after": null, "verify": {"run": ["git", "check-ignore", "-v", ".workflow-hub/env"], "expect": "match"}}
```

- `op` ∈ `write` (전체 내용 · `sha256` 지정) · `append_line` (없을 때만 더함) · `run_and_report` (명령을 돌려 출력을 확인 호출의 `checks` · `check` 로) · `run` (명령을 돌린다 — 보고 없음, `then` 이 있으면 이어서. 예: 커밋) · `delete` (그 경로의 파일을 지운다 — '허브로 옮김' 표식 되돌리기만) · `user_scope_write` (저장소 밖 하네스 설정 — 경고 문구 동반, R2.5a).
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

1. 사람이 안내 페이지(`/`)의 그 하네스 한 줄로 허브 MCP 를 등록한다 (R2.6). 지원 4종의 등록 방식은 실측 §16.3 표 그대로: Claude Code `.mcp.json` · Codex `bearer_token_env_var` · MiniMax `.mcp.json` · Antigravity 사용자 범위 + 경고. 하네스 자신의 안전 장치는 허브가 대신 풀지 않는다 (실측 §16.4): Claude Code 는 `.mcp.json` 쓰기에 사람 승인, Codex 비대화(`codex exec`)는 실행마다 `-c 'mcp_servers.workflow-hub.default_tools_approval_mode="approve"'` (자동 승인은 사람의 선택 — 셋업 지시는 설정에 쓰지 않고 말만 한다).
2. 에이전트가 `git remote get-url origin` (없으면 원격 목록) 을 읽어 `hub_project_lookup`.
3. 없으면 `hub_project_register`, 있으면 `hub_callsign_register` → 토큰.
4. 에이전트가 `hub_setup_plan` 에 **저장소 훑기 결과**를 실어 부른다. 훑은 파일에 1.x kit 표식(`setup.LEGACY_1X_MARKERS`)이 있으면 응답의 `legacy_1x` 가 그 파일과 전환 안내(선택 클라이언트 `migrate plan`)를 싣는다 — 셋업은 전환을 하지 않는다 (테스트베드 §16.6). 훑기는 허브가 정한 명령 목록(에이전트가 실행): 진입 파일 4종의 존재 · 머리 줄, `ai-workflow/` 의 1.x 흔적 (§6.6), `.gitignore` 의 해당 줄. 1.x 흔적이 있으면 결과에 전환 계획이 같이 온다.
5. 세션은 허브 원격 MCP(`/mcp`)로 직접 통신한다. PC 로컬 중계는 이 통신에 필요하지 않으며, 허브가 PC의 Claude Code/Codex 세션을 실행해야 할 때만 선택해 설치한다. 중계를 선택하면 `hub_setup_plan` 의 `scan.relay` 에 필요 여부와 토큰 없는 상태 결과를 싣는다.
6. 지시 순서: ① `.gitignore` `append_line` + `check-ignore` 확인 → ② (확인 통과 시에만) `.workflow-hub/env` `write` (모드 600 — Windows 는 사실대로 보고, R4.3) → ③ 진입 파일 렌더 영역 → ④ 하네스 설정 조각 (환경 변수 참조 · Antigravity 는 사용자 범위) → ⑤ 사람에게 '하네스를 다시 연결' 안내.
7. `hub_setup_confirm` 이 모두 확인되면 콜사인의 셋업 상태 = 완료. 확인 안 된 단계가 있으면 '미완료' 그대로 (R2.4).
8. **가이드 페이지 길** (M-039 WBS-39.1 · 소유자 2026-11-21) — 사람이 에이전트에게 `/setup.md` 를 읽게 하면 하네스 MCP 등록 없이도 끝까지 간다: 페이지가 선택 클라이언트 `hub_client.py bootstrap <허브> --harness <h> --callsign <c> --kind <k>` 를 쓰게 한다. 클라이언트가 2~7 을 HTTP 로 한 번에 한다 — 원격 조회(없으면 로컬 키 등록) · 합류 · 지시 실행 · 확인. **토큰은 출력하지 않는다** (env 에만, 다시 부르면 env 로 이어 간다). 하네스의 안전 장치를 지나야 하는 단계(`HANDOFF_STEPS` — `.mcp.json` · Antigravity 사용자 범위 평문 토큰)는 쓰지 않고 `for_agent` · `pending` 으로 넘긴다 — 에이전트가 자기 도구로 쓰고(사람 승인) 다시 부르면 sha256 으로 확인. Codex 등록 명령은 클라이언트가 실행한다. Antigravity 는 사람이 등록한 뒤 다시 부르면 `agy mcp list` (헤더 비표시) 의 이름 · 주소 · `enabled` 로 확인한다. 1.x 흔적(`legacy_1x`)이 있으면 전환 표식이 커밋되기 전까지 진입 파일을 보존한다. 데이터 가져오기와 `ai-workflow/HUB_MIGRATED.json` 커밋 뒤 다시 셋업하면 표준 1.x 시작 안내를 Hub 경로로 갱신한다. 시작 안내가 표준 문안과 다르면 자동 변경하지 않고 사람 검토를 요청한다. git 저장소가 아니면 `not_git_repo` 로 멈춘다 (빈 폴더면 페이지가 `git init` 을 시킨다). Python 이 없으면 페이지의 HTTP 직접 절차.

### 6.2 세션 시작 확인 (요구 R10 · Q5)

`hub_session_start` 는 두 번 부른다.

1. 인자 없이 → `{hub: {…}, repo_check: {commands: [...], rules: [...]}, outbox_hint}`. `hub.handoff` 는 `hub_handoff_get` 과 같은 꼴 `{callsign, handoff, version, updated_at}` — 읽은 칸을 그대로 `hub_session_end` 에 쓴다. 허브 쪽 결과: 지침 판(바뀌면 `[바뀜]` 과 렌더 지시) · 클라이언트 · 규칙 판 · 내 handoff · 내 task (진행 한 줄 포함) · 맡은 이 없는 열린 task · 대기 중 결정 응답. 저장소 쪽 명령 (`hub/session.py` 가 정본): `git fetch --prune`, `git status --porcelain=v2 --branch` (앞섬 · 뒤처짐은 `# branch.ab` 줄에서), `git rev-parse --abbrev-ref origin/HEAD`, `git check-ignore -v .workflow-hub/env`, 셋업한 진입 파일마다 `git grep --no-index -h -e workflow-hub:begin -- <파일>`, 내 task 에 묶인 커밋마다 `git cat-file -e <sha>^{commit}`. 명령 결과는 `{이름: {rc, output}}` 객체 또는 `[{name, rc, output}]` 목록 (이름의 `:` · `.` 를 키로 싣지 못하는 하네스 — M-039 실측 Antigravity; 두 꼴은 같은 판정) — 요청하지 않은 이름 · 목록 안 중복 이름은 거절한다.
2. `repo_results` 를 실어 다시 → 대조 보고: 뒤처짐 → 'fast-forward 후 시작' · 갈라짐 / 미커밋 변경 → **'멈추고 묻기'** · `.gitignore` 규칙 빠짐 → 경고 · 내 task 의 묶인 sha 가 저장소에 없음 → 보고 (R10.4). 진입 파일 판을 모두 쟀고 하나로 같으면 그 판을 `guide_version_seen` 에 적는다 (R7.8 — §4.7 받은 판 기록).
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
- 승인 흐름: `hub_guide_propose` → `guide_proposal(open)` → 승인된 `human` 이 `hub_guide_decide` → `guide` 새 판. 승인된 `human` 의 제안은 바로 판이 오른다 (제안 줄은 `approved` · 결정자 = 본인으로 남는다, R7.7). `agent` · 승인 전 `human` 의 제안은 판을 바꾸지 않는다. 거절은 판 불변. 결정된 제안을 다시 결정하면 `already_decided` 409.
- 기준 판: 제안 · 승인 모두 `base_version` 이 지금 판과 같을 때만 — 그 사이 판이 오른 제안은 승인할 수 없고(409, 화면은 '낡음' 표시) 새 판 위에서 다시 낸다. 자동 병합하지 않는다.
- 예산: 새 판이 될 본문을 지원 하네스 넷 모두에 렌더해 본 뒤에만 판을 올린다 (`entry_budget_exceeded` 422) — `hub admin guide set` 도 같다. 넘는 판이 서면 그 뒤 모든 렌더 · 세션 시작이 깨진다.
- 콜사인이 받은 판은 셋업 확인 · 세션 시작 2단계에서 `callsign.guide_version_seen` 에 적는다 — 화면에 '옛 지침으로 도는 환경' (R7.8, §4.7).

### 6.6 1.x 전환 매핑 (요구 R14)

감지 목록(에이전트가 실행하는 명령의 결과로 허브가 판정): `ai-workflow/memory/active/*/` (브랜치 네임스페이스) · 그 안의 `state.json` · `session_handoff.md` · `backlog/tasks/*.md` · `sessions/` · `lessons.md` · `.compact/` · `ai-workflow/memory/active/roadmap/` · `ai-workflow/wiki/` · memory_index · 진입 파일의 kit 생성 블록 · `.claude-plugin` 등 kit 플러그인 · hook · stdio MCP 설정, 그리고 1.x kit 판.

| 1.x 원천 | 허브 | 규칙 |
|---|---|---|
| `active/<branch>/backlog/tasks/<ID>.md` · `archived/<branch>/backlog/tasks/<ID>.md` | `task` (+ `plan_md`, 아카이브 출처는 `branch = archived/<branch>`) | 같은 ID 여럿이면 그 파일을 마지막으로 바꾼 커밋 시각이 가장 늦은 것이 정본, 같으면 기본 브랜치 → 활성 브랜치 → 이름순 (Q1). 나머지는 그 task 의 `event` (`op=imported_variant`) |
| `active · archived/<branch>/` 의 `session_handoff.md` · `sessions/*` · `lessons.md` · `baselines.md` · 날짜별 `backlog/<날짜>.md` · `.archived.json` | `memory_note(kind=archive_1x)` — 원문 그대로 + `meta_json{branch, archived, path, commit, imported_at}` | 읽기 전용 (Q2). 전환한 콜사인의 `handoff` 는 **현재 브랜치** handoff 의 칸에서 시작 (R14.4) |
| `<branch>/plan_responses/<TASK>-<n>.md` (반영된 응답 — `inbox/` 은 반영 전이라 남김) | 지금 task 계획으로 자격이 있으면 `plan_response` (1.x 가 이미 계획 줄 상태를 고쳐 두었으므로 계획은 다시 쓰지 않는다), 없으면 `memory_note` 보관 + 사유 | 1.x `qualify` 그대로 — 결정 상태가 1.x 와 같다 |
| `docs/PROJECT_PROFILE.md` (없으면 `active/PROJECT_PROFILE.md`) · `active/PURPOSE.md` | `project_doc(name=profile · purpose)` — 판 9 · `hub_project_doc_get` · `hub_project_doc_put` (승인된 human) | 상태 요약을 만들 때 1.x 자리에 펼쳐 목적 · 프로젝트 칸이 1.x 와 같다 |
| `.compact/checkpoint.json` | `checkpoint` | 현재 브랜치 것만 |
| `roadmap/*.md` | `roadmap_doc` | 원문 그대로 (R9.1) |
| `ai-workflow/wiki/**` · `memory_index/entries/*.json` | `wiki_page` · `memory_entry` | 위키는 **디렉터리 무손실 운반** (`hub_wiki_import_dir` 와 같은 함수 — R8.6 소유자 결정 2026-11-21, 1.x `index.md` · `log.md` 원문은 보관 기록), 묶음 하나 = ingest 하나. memory_index 는 1.x 스키마로 검증 |
| 진입 파일 | 생성 블록은 버림 · 손 문단은 `guide_proposal` (초안, D11 승인 대상) | R14.5 |
| kit 플러그인 · hook · stdio MCP | 하네스별 교체 안내 · 삭제는 등록자 확인 뒤 | R14.9 · 4종 밖 하네스는 '지원 대상 아님' |

- **감지 (R14.1 · I1)** — `hub_migrate_plan()` 이 돌릴 명령을 낸다 (`hub/migrate1x.py` 의 `COMMANDS` 가 정본: 현재 · 기본 브랜치 · HEAD · `git ls-files` (추적 · 무시 파일) · 경로별 마지막 커밋(`git log --format=@%ct %H --name-only`) · 진입 파일의 kit 판 표식). 결과를 실어 다시 부르면 감지 보고(네임스페이스 · 현재 네임스페이스 · kit 판 · 종류별 수 · 하네스 흔적 · 4종 밖 하네스 · 못 돌린 명령 · **들이지 않고 저장소에 남기는 파일** `left_in_repo` (사유별 수 · 표본 — R14.2, 리허설 §16.5) · **커밋 안 된 파일** `uncommitted` (감지는 추적 파일만 본다 — 경고))와 전환 표 · 같은 ID 정본 · 하네스 안내를 내고 `MIG-NNNN` 으로 남긴다.
- **정본 (Q1)** — 같은 ID 는 그 파일을 마지막으로 바꾼 커밋 시각이 가장 늦은 네임스페이스, 같으면 기본 브랜치, 기본 브랜치도 없으면 이름순. 근거(네임스페이스 · 커밋 · 시각 · 사유)를 계획에 싣는다. 나머지는 그 task 의 `imported_variant` 이력 — 다시 보내도 한 번.
- **들여오기 (R14.2)** — 종류 `tasks` · `archive` · `handoff` · `roadmap` · `wiki` · `memory_index` · `checkpoint` · `guide_draft` 가운데 소유자가 고른 것만. 계획에 없는 경로 · 고르지 않은 종류의 파일은 거절. 한 파일이 여러 종류에 속할 수 있다 (현재 네임스페이스 handoff = 보관 + 콜사인 handoff). 이미 있는 것은 건너뛴다 — 묶음을 다시 보내도 같다. 응답의 `summary` 는 이번 묶음, `total` 은 누적. `final=true` 뒤에는 409.
- **task 칸** — 1.x 리더(`read_task_list_field` · `read_task_affected_documents`) 그대로, `## 🧭 Plan` 절은 원문 그대로 `plan_md`, 상태는 frontmatter 우선 (`done` 도 그대로 — 1.x 에서 이미 게이트를 거쳤다). 못 읽는 파일은 `failed` 로 보고한다 (조용히 버리지 않는다). handoff 의 진행 · 막힘 · 최근 완료는 `TASK-` 줄만 들이고 나머지 줄은 `dropped_lines` 로 보고.
- 진입 파일의 kit 생성 절 판정은 1.x `entry_diet` 의 '알려진 생성물' 해시 + `generated-from` 표식 — 손 문단만 `guide_proposal(open)` 초안이 된다 (승인된 사람이 보내도 판은 오르지 않는다).
- 들여오기는 묶음 전송. **실제 규모의 저장소는 선택 클라이언트가 운반한다** (`hub_client.py migrate`, §7 — 리허설에서 이 저장소의 감지만 ~430KB, task 600여 개의 내용은 MB 단위라 LLM 이 도구 인자로 실을 수 없다). 작은 저장소는 에이전트가 MCP 로 실어도 된다 (요청 상한 §4.3). 원본 파일은 지우지 않고 허브는 쓰기 지시도 내지 않는다.
- **'허브로 옮김' 표식 (R14.6 · DS9, WBS-38.2)** — 끝난 전환(`final` 뒤)에만 `hub_migrate_marker(action=issue)` 가 `ai-workflow/HUB_MIGRATED.json` 쓰기 지시(`sha256_after`)와 커밋 명령(`op: run`)을 낸다. 본문은 `{format: "workflow-hub-migrated/1", hub, project_id, migration_id, migrated_at(전환이 끝난 시각), kit_version, from_kit_versions, note}` — 같은 전환이면 언제 내도 같은 바이트다. 쓴 뒤 `action=confirm(sha256)` 으로 대조한다 (다르면 미확인 + 이유). 1.x 쪽 판정은 `workflow_kit/common/hub_marker.py` 하나다 (경로 상수의 정본 — 허브도 이것을 쓴다): `python -m workflow_kit <명령>` 입구에서 워크플로우 상태를 쓰는 명령(`GUARDED_COMMANDS`)은 표식을 위로 찾아 있으면 `hub_migrated` 로 거절하고(종료 코드 3 · 허브 주소, MCP `plan_import` 도 같은 입구), `session-start` 는 기준선을 복원하지 않고 허브를 가리킨 뒤 정상 종료한다. 모든 명령은 막음 / 면제(사유)로 분류돼 있고 미분류는 `check_hub_marker_1x` 가 red 로 본다. 모듈 직접 실행(`python -m workflow_kit.tools.X`)은 이 입구를 지나지 않는다. 2.0 안내 한 줄 · README · EOL 은 1.x 안내 판(R16.4) 발행 때.
- **되돌리기 (R14.7)** — `action=revert` 가 삭제 지시(`op: delete`)와 확인 명령(`git ls-files -- <표식>` → 빈 출력)을 내고, `action=confirm_revert(check)` 가 그 결과로 판정한다 (아직 추적되면 미확인). 허브 쪽 기록은 지우지도 옮기지도 않는다. 되돌린 뒤 1.x 에서 바뀐 것은 다시 전환해도 '이미 있음' 으로 건너뛰므로, 응답이 그 주의를 싣는다 (다시 전환하기 전의 정리 방법은 후속).

### 6.7 위키 lint (요구 R8.3 · 실측 §16.2)

허브가 페이지를 임시 디렉터리에 `ai-workflow/wiki/…` 배치로 펼치고(생성 `index.md` · `log.md` 포함), 1.x 검사와 **같은 함수** — `workflow_kit/common/wiki_rules.py` 의 `check_canonical_location`(V-1 정위치) · `validate_index`(V-4) — 와 새 lint `classify_wikilinks`(깨진 위키 링크)를 돈다. 1.x `check_wiki_location` · `check_wiki_index_structure` 는 같은 함수를 부르는 얇은 껍데기다 (금지 위치 규칙은 저장소 배치 규칙이라 1.x 검사에만 남는다).

- **위키 링크** `[[대상]]` 은 `<wiki>/<대상>.md` 로 푼다 (코드 펜스 · 인라인 코드 안은 링크가 아니다). `.md` 로 끝나는 대상은 위키 페이지가 아니라 **저장소 참조**로 따로 센다 (이 저장소 위키 527 링크 중 3건 — 깨짐으로 세면 위양성).
- **index · log 는 생성물** — index 는 첫 디렉터리(SCHEMA 종류)를 절로, anchor 는 파일 이름(겹치면 경로 전체 slug). log 는 ingest 기록에서 오래된 것부터.
- **양방향 링크 (E5, WBS-36.2)** — memory entry 를 같은 임시 디렉터리의 `ai-workflow/memory/active/memory_index/entries/` 에 펼쳐 1.x `audit_bidirectional_links` 를 그대로 부른다. 비대칭이 있으면 `ok: false`. (1.x 결함 — 위키 언급이 없는 entry 에서 `UnboundLocalError` 또는 앞 entry id 로 거짓 비대칭 — 은 실측 §16.2 대로 고쳤다, `release/1.x` 에도.)
- **출처 (R8.4)** — ingest 페이지의 `source{repo_key, sha}`. `repo_key` 는 이 프로젝트의 등록 키(주 키 · 별칭)여야 한다. 출처 없이 다시 쓰면 출처를 지운다 — 옛 sha 가 새 본문의 출처인 척하지 않게.
- **원격 읽기 (R8.4 · E3, `hub/wiki_remote.py`)** — 소유자가 켜면 lint 때 `git clone --bare --filter=blob:none` 을 임시 디렉터리에 받아(트리 · 커밋만, 끝나면 지움, 시간 상한 120초) 잰다: 저장소 참조가 기본 브랜치 머리 트리에 있는가(`missing`) · 출처 sha 가 있는가(`unknown`) · freshness — 출처 sha 이후 frontmatter `last_ingested_from` 의 경로가 바뀌었는가(`stale`, 대상 = sha 와 경로가 둘 다 있는 페이지 수 `targets`). 셋은 `ok` 에 넣지 않고 따로 보인다.
- **미측정** — 원격 읽기가 꺼졌거나 받기에 실패하면 셋 다 `status: unmeasured` + 이유 (freshness `targets: 0`) — 통과 0건. 빈 위키는 `ok: null` · `status: empty` — 잴 것이 없음은 통과가 아니다.
- **운반 (R8.6, WBS-36.3)** — `hub_wiki_import_dir` 는 위키 뿌리 상대 파일을 받아 `.md` 페이지를 바이트 그대로 ingest 묶음 하나로, `index.md` · `log.md` 원문은 `memory_note` (`archive_1x`) 로 보관, `.md` 아닌 파일(`.gitkeep` 등)은 `skipped_non_page` 로 보인다. `overwrite` 가 아니면 있는 페이지는 409. 요청 상한 때문에 큰 위키는 여러 번 — 한 번이 ingest 하나.
- 점수 함수(coverage · cross_ref · discoverability · lifecycle)는 M-036 WBS 에 없다 — 1.x 함수가 저장소 상수 · kit 선언에 묶여 있어(실측 §16.2) 인자화가 따로 필요하다. 후속 후보. operational · trend 는 돌지 않는다.

## 7. 선택 클라이언트 (요구 R2.7 · R11.3 · R12)

`GET /v1/bootstrap/hub_client.py` (토큰 없이 — 비밀이 없다)가 내려주는 `workflow_kit/hub/client/hub_client.py` 한 파일, 표준 라이브러리만. 저장소 뿌리의 `.workflow-hub/hub_client.py` 로 두고 `.workflow-hub/env` 의 `WORKFLOW_HUB_URL` · `WORKFLOW_HUB_TOKEN` 을 읽는다. 모든 호출은 `POST /v1/tools/<name>` — MCP 도구와 같은 함수다. 하는 일은 셋 — ① hook 에서 체크포인트 올리기 · compact 직후 재주입 (아직 — 후속) ② 오프라인 보낼편지함 ③ 마지막 브리핑 캐시. 첫 판은 M-036 WBS-36.3 (②③).

| 명령 | 하는 일 |
|---|---|
| `call <tool> [json]` | 부른다. 허브에 닿지 않으면 **쓰기**(`QUEUEABLE` — `request_id` 를 받는 도구만)는 `.workflow-hub/outbox/<ns 시각>-<난수>.json` 에 `request_id` 를 붙여 쌓고 exit 3, 읽기 · 그 밖은 쌓지 않고 exit 2 (낡은 답을 지금 답처럼 내지 않게) |
| `flush` | 보낼편지함을 **오래된 것부터** 보낸다. 성공은 지운다 · 같은 항목을 두 번 보내도 `request_id` 로 한 번만 반영 · **409 는 자동 병합하지 않고 남긴 채 보고** (D4 · R12.2) · 그 밖 오류도 남긴다 · 닿지 않으면 멈춘다 |
| `status` | 남은 항목 수 · 목록 · 캐시 시각 |
| `move <대상 주소> <초대 코드>` | 허브 간 이전 (§3.5) — 소유자 환경에서 봉인 · 뜨기 · 대상에 들이기 · env 주소 바꾸기, 실패하면 이 실행이 건 봉인만 푼다 |
| `bootstrap <허브 주소> --harness <h> --callsign <c> [--kind] [--name]` | 빈 환경 부트스트랩 (§6.1 7) — env 없이 HTTP 로 등록(원격 없으면 로컬 키) · 합류 · 셋업 지시 실행 · 확인. 토큰 비출력, `for_agent` · `pending` 으로 하네스 안전 장치 단계를 넘김. 종료 코드 0 complete · 3 partial · 1 멈춤 · 2 닿지 않음 |
| `migrate plan` · `migrate import <MIG> <종류,…\|all>` | 1.x 전환의 대량 운반 (소유자 2026-11-21, 리허설 §16.5) — 허브가 낸 감지 명령을 저장소 뿌리에서 돌려 보내고 계획 요약을 낸다 (전체는 `.workflow-hub/cache/migrate-<MIG>.json`). import 는 계획의 파일을 읽어 2MiB 묶음으로 보내고 마지막 묶음에 `final`. 에이전트(LLM)는 요약을 사람에게 보이고 고른 종류만 넘긴다 — 큰 출력 · 파일 내용이 모델 컨텍스트를 지나지 않는다. 다시 돌려도 허브가 있는 것을 건너뛰고, 끝난 전환은 409 |
| `session-start [json]` | `hub_session_start(client={version, outbox_pending})` — 허브 보고 `hub.local_client` 에 남은 수가 실린다 (R12.3). 응답을 `.workflow-hub/cache/session_start.json` 에 둔다. 허브가 꺼졌으면 캐시로 열고 `허브 미확인 · 캐시 (<시각>)`, 캐시도 없으면 `허브 미확인 · 캐시 없음` (R12.1) |

- `client` 인자 없이 부른 세션 시작은 `local_client.status: none` — 클라이언트 없는 환경(원격 MCP 만)이다. 0건으로 치지 않는다.
- `QUEUEABLE` 은 허브 도구 표에서 `request_id` 를 받는 도구의 부분집합이어야 한다 — `check_hub_client` case 1 이 내려받은 원문과 도구 표를 대조한다.

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
