# 워크플로우 허브 운영 가이드 (2.x · 3.x pilot)

- 문서 목적: 2.0 워크플로우 허브를 설치하고 띄우고 지키는 법 — 사람(허브 관리자)이 읽는다
- 범위: 설치 · SQLite/PostgreSQL 선택 · 띄우기 · 노출과 공개 주소 · 토큰 · 프로젝트 셋업 안내 · 지침 · 백업과 복원 · 판 올리기 · 허브 간 이전 · 점검
- 대상 독자: 허브 관리자, 저장소 관리자
- 상태: beta
- 최종 수정일: 2026-11-25
- 관련 문서: [`../workflow-source/core/hub_spec.md`](../workflow-source/core/hub_spec.md) (계약 정본), [`planning/workflow-hub-requirements-2026-11.md`](./planning/workflow-hub-requirements-2026-11.md) (요구 · 실측 §16), [`RELEASE.md`](./RELEASE.md)

허브는 **프로세스 하나와 SQLite 파일 또는 PostgreSQL 데이터베이스 하나**다. SQLite는 기본·테스트 저장소이고,
PostgreSQL은 Go와 Python 런타임이 함께 지원하는 서버 저장소다. 작업 환경(저장소 · 하네스)은 kit 을 깔지 않는다 — 허브 주소 하나로
참여한다. 하네스는 허브의 원격 MCP(`/mcp`)로 붙고, 셋업이 쓰는 파일은 `.gitignore` 한 줄 · 진입 파일 영역 ·
하네스 설정 · 토큰 파일(`.workflow-hub/env`, git 제외) 뿐이다.

버전 표시는 런타임 판과 kit 계약판을 구분한다. 현재 Go 허브 pilot과 Python wheel은 모두 **3.5.0**이며, 두 런타임이 구현하는
kit 호환 계약은 **2.1.0**이다. 허브 `/healthz` 의 `hub_version`은 런타임, `kit_version`은 호환 계약 판이다.
`X-Hub-Version` 과 `X-Hub-Kit` 응답 헤더도 같은 구분을 따른다.

## 1. 설치

허브를 돌릴 기계에만 깐다. Python 3.10 이상.

```sh
python3 -m venv ~/workflow-hub/venv
~/workflow-hub/venv/bin/python -m pip install "<GitHub Release 의 workflow_kit wheel 경로>[hub]"
```

- `[hub]` 추가 의존이 허브 서버 몫(`uvicorn` · `starlette`)을 깐다. 없으면 `hub serve` 가
  `허브 의존이 없다 — pip install 'workflow_kit[hub]'` 로 멈춘다.
- Python 허브를 PostgreSQL에 연결할 때는 `[hub,hub-postgres]`를 설치한다. Go 실행 파일은 PostgreSQL 드라이버를 포함한다.
- 배포는 GitHub Releases 하나다 (PyPI 에 올리지 않는다 — [`RELEASE.md`](./RELEASE.md) §1 각주 0).

## 2. 띄우기

```sh
python -m workflow_kit hub serve --db ~/workflow-hub/hub.db [--bind 127.0.0.1] [--port 8770] \
    [--public-url https://hub.example.org] [--web-token-name screen]
```

- 시작할 때 DB 를 최신 판으로 이관한다. 이관이 있으면 먼저 `hub.db.pre-v<판>-<시각>` 사본을 만들고 그 경로를
  알린다. 첫 줄 출력: `{"status": "serving", "url", "public_url", "db_version"}`.
- 앞에서(foreground) 돈다. 상시로 두려면 서비스 관리자(systemd 등)에 맡긴다 — 이 kit 은 배치 자동화를 내지
  않는다 (PURPOSE 제외 영역).
- 이 저장소의 테스트베드 예: `~/workflow-hub-testbed/start.sh` (loopback `:8770`, requirements §16.6).

### 2.1 PostgreSQL 연결과 SQLite 데이터 복사

`--db`에 `postgresql://` 또는 `postgres://` URL을 주면 PostgreSQL에 연결한다. 연결 시 각 런타임이 schema version을
읽고 advisory lock 아래 빠진 판을 트랜잭션으로 적용한다. 테스트·개발은 계속 SQLite를 기본으로 쓴다.

```sh
python -m pip install 'standard_ai_workflow[hub,hub-postgres]'
python -m workflow_kit hub serve --db 'postgresql://hub_user@db.example.org/workflow_hub' --bind 127.0.0.1
workflow-hub serve --db 'postgresql://hub_user@db.example.org/workflow_hub' --bind 127.0.0.1
```

기존 SQLite 데이터 복사는 자동 시작 동작과 분리된 명시적 작업이다. 원본의 일관된 스냅샷을 임시 파일에서 최신 판으로
올린 뒤, 빈 PostgreSQL 대상에 전체 표를 복사한다. 모든 표의 행 수와 digest를 대조하며 실패하면 대상 트랜잭션을
롤백한다. SQLite 원본은 수정하지 않는다. 같은 명령을 다시 실행하면 이미 데이터가 있는 대상을 거절한다.

```sh
python -m workflow_kit hub migrate --from-sqlite ~/workflow-hub/hub.db \
  --to-postgres 'postgresql://hub_user@db.example.org/workflow_hub'
workflow-hub migrate --from-sqlite ~/workflow-hub/hub.db \
  --to-postgres 'postgresql://hub_user@db.example.org/workflow_hub'
```

PostgreSQL URL의 자격 증명을 셸 기록·서비스 로그에 남기지 않도록 비밀번호는 URL에 직접 넣지 말고 libpq 환경/서비스
secret 설정을 사용한다. PostgreSQL 백업과 복원은 서버 운영 절차(`pg_dump`, 관리형 snapshot 등)를 따른다.
Python 허브의 프로젝트 묶음 export/import도 PostgreSQL에서 동작한다. import 전에 서버 운영 백업을 별도로 남기며, import 자체는 단일 transaction이다.

## 3. 노출과 공개 주소

- **기본은 loopback** (`127.0.0.1`). loopback 이 아닌 주소에 bind 하면 경고한다 — 허브에 닿는 누구나 프로젝트를
  등록할 수 있다 (요구 R3.4 · R13.3). 바깥 노출은 **TLS 를 거는 리버스 프록시 뒤**에서 하고 허브는 loopback 에 둔다.
- **`--public-url` = 사람과 하네스가 쓰는 바깥 주소**. 셋업이 쓰는 `.workflow-hub/env` · `.mcp.json` · Codex 등록
  명령, 안내 페이지(`/`), 에이전트용 절차(`/setup.md`) 의 주소가 모두 이 값에서 나온다. 추측하지 않는다 — 프록시
  뒤라면 반드시 준다. 바꾸면 이미 셋업한 환경은 셋업을 다시 돌려(`hub_setup_plan`) 주소를 고친다.
- 화면(`/ui/`)의 링크 · API 호출은 상대 경로라 접두사 프록시(`https://host/hub/`) 뒤에서도 돈다 (R13.4).
  MCP 주소는 `<public-url>/mcp` 다.
- `GET /healthz` 의 `exposure` (`loopback` / `non-loopback`) 로 지금 노출을 확인한다.

## 4. 토큰

| 토큰 | 누가 · 어떻게 | 권한 | 거두기 |
|---|---|---|---|
| 콜사인 (`wfh_…`) | 프로젝트 등록 · 합류 때 허브가 **한 번만** 준다. 작업 환경의 `.workflow-hub/env` (600, git 제외) 에만 | 그 프로젝트의 도구 · 화면. 결정 답 · 지침 판 올리기 · 원격 묶기는 **승인된 human** 만 | `hub admin --db … callsign revoke --project <ID> --callsign <c>` |
| 화면 공용 `web` | `hub admin --db … token issue --role web --name screen` → `hub serve … --web-token-name screen` | 토큰 없는 화면 요청이 **읽기 · 콜사인 등록** 권한으로 돈다 (기본 꺼짐) | `token revoke --name screen` — 즉시 꺼진다 |
| `admin` | `token issue --role admin --name <이름>` | 웹 허브에서 모든 프로젝트 읽기 · 콜사인 등록 · 하네스 제보 검토 · 별도 사람 명부 관리 (MCP 승인 도구 없음) | `token revoke --name <이름>` |

웹 화면의 **관리자 모드**는 `/ui/` 상단의 `관리자 모드` 또는 첫 화면의 `허브 전체 관리`에서 연다. 로그인 토큰은 허브 서버에 로컬로 발급한다.

```sh
python -m workflow_kit hub admin --db <DB 경로> token issue --role admin --name <이름>
workflow-hub admin --db <DB 경로> token issue --role admin --name <이름>
```

발급된 토큰은 로그인한 브라우저의 해당 허브 주소에 저장된다. 토큰을 잊었거나 만료했으면 서버에서 다시 발급하고, 공유 기기에서는 사용 후 관리자 화면에서 토큰을 지운다. `web` 공용 토큰과 프로젝트 콜사인 토큰은 관리자 권한을 대신하지 않는다.

- `hub admin` 은 DB 파일에 직접 접근하는 **로컬 명령**이다 — 네트워크로 열지 않는다. 토큰 값은 발급 출력에서
  한 번만 보인다. DB 에는 해시만 있다.
- Antigravity 는 MCP 헤더의 환경 변수 참조를 확장하지 않아, 그 하네스의 토큰은 사용자 범위
  `~/.gemini/config/mcp_config.json` 에 평문으로 남는다 (R2.5a) — 그 파일을 공유하지 않게 알린다.

## 5. 프로젝트 셋업 안내 (사용자에게 줄 말)

가장 쉬운 길 — 작업 환경의 에이전트에게 한 줄:

> `<public-url>/setup.md` 를 읽고 이 저장소를 셋업해. 콜사인은 `<이름>`, 나는 사람(human)이다.

에이전트가 허브의 선택 클라이언트로 등록(또는 합류) · `.gitignore` 확인 · 토큰 파일 · 진입 파일 · 하네스 설정을
하고, 하네스의 안전 장치가 걸린 단계(Claude Code 의 `.mcp.json` 승인, Codex 샌드박스, Antigravity 평문 토큰)는
사람에게 넘긴다. 끝나면 `.workflow-hub/env` 의 토큰을 하네스 환경에 올리고 하네스를 다시 시작한다. 실측: 4 하네스
모두 빈 폴더에서 페이지만 읽고 셋업을 마쳤다 (requirements §16.7).

- 하네스별 등록 명령과 사람 몫은 안내 페이지 `<public-url>/` 에 있다.
- git 원격이 없는 저장소는 로컬 키로 등록된다 — 원격을 만든 뒤 소유자가 `hub_project_bind_remote` 로 묶어야
  다른 환경이 주소로 찾아 합류한다.
- 새로 합류한 `human` 콜사인은 소유자가 승인하기 전까지 `agent` 권한이다 — 화면의 콜사인 표 또는
  `hub_callsign_approve`.

### 사람용 허브 계정

사람은 브라우저의 프로젝트별 토큰 저장 대신 허브 계정으로 로그인한다. `/ui/`의 **새 계정 만들기**에서 토큰 없이
가입한다. 가입만으로는 어떤 프로젝트도 열리지 않는다 — 로그인한 뒤 프로젝트 ID나 git 주소로 **참여 요청**을 하면 승인 전 사람
콜사인이 생기고, 프로젝트 소유자가 콜사인 화면에서 승인한다. 이관 같은 실행 승인은 프로젝트 소유자만 한다. 이미 승인된
human 콜사인 토큰이 있으면 가입할 때 함께 넣어 바로 연결한다. 토큰 없는 가입은 허브 전체에서 시간당 30건까지다.
이 토큰은 계정 연결에만 쓰이고 브라우저 저장소에는 보관되지 않는다. 다른 프로젝트도 맡고 있다면 로그인한
상태에서 해당 프로젝트의 승인된 human 콜사인 토큰을 **콜사인 연결**에 넣는다. 허브는 비밀번호 원문이 아닌
PBKDF2 해시, 세션 토큰 원문이 아닌 해시를 저장하며, 세션 쿠키는 HttpOnly·SameSite Strict로 제한된다.
비밀번호는 8자 이상이다. 리버스 프록시 뒤에서는 허브의 `--public-url`이 브라우저 주소와 같아야 로그인된다.
세션은 30일 뒤 만료되고, 로그아웃하면 즉시 폐기된다. 잘못된 비밀번호를 15분 안에 8회 입력하면 잠시
로그인을 제한한다. 에이전트 MCP는 계속 프로젝트 콜사인 토큰을 `Authorization: Bearer`로 사용한다.

### 미등록 하네스 제보

세션을 시작할 때 `hub_session_start`에 현재 하네스 이름을 실으면 응답의
`hub.harness_support.status`가 `unknown`인지 확인할 수 있다. 이 경우 클라이언트가
`hub_harness_report`에 하네스 ID·표시 이름·버전·플랫폼·MCP transport/설정 형식·진입 파일
후보·공식 HTTPS 문서 주소·짧은 메모를 보내 검토를 요청한다. 전체 설정 파일, 로그, 절대 경로,
환경 변수나 토큰은 보내지 않는다.

자동 셋업 프로필을 함께 등록하려면 제보에 `config_formats: [mcp-http-json-v1]`,
`mcp_transports: [streamable-http]`, 진입 파일 후보, `.json` MCP 설정 후보를 포함한다.
제보 상태는 해당 프로젝트의 `hub_harness_report_list`에서 확인한다. 사람의 검토는 MCP에서 하지 않는다.
허브 관리자 토큰으로 웹 화면 `/ui/#/harnesses`에 로그인해 전역 대기열을 검토한다. 담당자는 하네스와
별도로 사람 명부에 먼저 등록하고, 승인 화면에서 하네스별로 한 명 이상 지정한다. 관리자는 두 후보 경로와
호환 정보를 확인하고 명시적으로 셋업 지원 프로필을 활성화한다. 승인 프로필은 표준 진입 안내와
`mcpServers.workflow-hub` JSON 설정만 병합하고 토큰은 `${WORKFLOW_HUB_TOKEN}` 참조로 남긴다.
사람 명부 항목은
인증 계정이 아니라 책임자 메타데이터다. 승인하면 메타데이터와 담당자 연결이 허브 전역 등록부에 추가되고, 다른 프로젝트는
`hub_harness_registry_list`에서 볼 수 있다. 프로필이 승인된 하네스는 `setup_supported`로 보고되며, 승인 전
또는 호환 정보가 부족한 하네스의 `hub_setup_plan`은 파일을 변경하지 않고 제보·승인 흐름을 안내한다.
계약은 [`hub_harness_registry_spec.md`](../workflow-source/core/hub_harness_registry_spec.md)에 있다.

### task 목록 탐색

프로젝트 개요의 task 목록은 로드맵 연결 여부, 마일스톤, WBS, 카테고리 1~3단계로
필터할 수 있다. 목록은 최신 수정 순으로 페이지를 나누며, 필터와 페이지는 주소에 남는다.
표와 카드 보기는 언제든 바꿀 수 있고 현재 분류 조건을 유지한다. 로드맵 연결 여부는
task의 WBS 연결 유무를 기준으로 한다.

허브는 Python · Go 런타임 모두 `hub_setup_plan` 으로 단계별 파일 지시를 내고, `hub_guide_render` 로 현재
프로젝트 지침을 진입 파일에 렌더하며, `hub_guide_get` 으로 지침 본문 · 판 이력 · 제안 상태를 제공한다.
`hub_guide_propose` · `hub_guide_decide` 도 양쪽 런타임에서 같은 승인 경계를 적용한다 — 승인된 human 만 판을
올리고 제안을 승인 · 거절할 수 있다.
진입 파일의 허브 렌더 영역이 로컬에서 수정된 경우 덮어쓰지 않고 멈춘다. 이 세 도구는 두 런타임에서
같은 MCP 이름으로 제공된다.

### 작업 분류 · roadmap/WBS · 테스트

task `fields` 에 프로젝트가 정하는 3단계 `category: {level_1, level_2, level_3}` 를 기록한다. roadmap milestone/WBS 연결은 task의 `wbs` 를 사용하며 기존 roadmap_state v1 진척 계산을 유지한다. `tests` 는 `{id, name, required, runs:[{status, summary?, run_at?, commit_sha?}]}` 배열로 정의와 실행 이력을 함께 관리한다. 세션이 로컬에서 실제 테스트를 실행하고 결과를 `hub_task_update` 로 기록한다. 허브는 명령을 실행하지 않는다. task 종료 시 필수 테스트의 가장 최근 실행이 모두 `passed` 여야 하며, 선택 테스트는 완료 게이트에 포함되지 않는다.

### 1.x 저장소의 전환

1.x kit 를 쓰던 저장소는 셋업이 `legacy_1x` 로 알린다 — 셋업만으로는 1.x 기록이 허브에 들어오지 않는다.

```sh
python3 .workflow-hub/hub_client.py migrate plan                 # 계획 — 종류별 파일 수 · 충돌 · 남는 파일
python3 .workflow-hub/hub_client.py migrate import <MIG> all     # 고른 종류를 묶음으로 보낸다
```

들여온 뒤 사람이 확인하고 `hub_migrate_marker(action='issue')` 로 '허브로 옮김' 표식을 커밋하면 그 저장소의 1.x
쓰기 명령이 거절된다(종료 코드 3). **표식을 커밋한 뒤 같은 bootstrap 셋업을 다시 실행**하면 진입 파일의 표준 1.x 세션 시작
안내를 `hub_session_start` 경로로 갱신한다. 표준 문안이 수정돼 있으면 자동 변경하지 않고 사람 검토를 요청한다. 표식을 지우면 되돌아간다.
상세: hub_spec §6.6.

다시 이관하면 이미 있는 항목은 건너뛰고 새 항목만 들인다. 허브에 있는 task의 바뀐 상태를 덮어쓰지 않는다.

### 이관 승인 — 에이전트 요청, 사람 로그인 승인

소유자 토큰을 에이전트에 주지 않고 이관할 수 있다. 사람은 §계정 절차로 허브 계정을 만들어 둔다.

1. 에이전트: `hub_client.py migrate plan` → `hub_client.py migrate request <MIG> <종류,…|all>`. 승인 화면 주소와 A2A Task ID가 나온다.
2. 사람: 계정으로 로그인해 프로젝트의 **확인 요청**에서 허브가 계산한 실행 내용(이관 ID·종류별 파일 수·브랜치·HEAD·미커밋 수)을 보고 승인·거절한다.
3. 에이전트: `hub_client.py migrate import <MIG> <종류,…|all> <Task ID>`. Task가 승인되면 아티팩트의 `approval_id`를 꺼내 쓴다.

승인은 요청한 콜사인, 그 이관, 그 종류에만 듣는다. 24시간 뒤 만료되고 이관이 끝나면 소진된다. 소유자 콜사인 토큰으로는 승인할 수 없다 —
에이전트도 들고 있을 수 있어서다. `hub_approval_request(action={type: migrate_marker, …})`로 '허브로 옮김' 표식도 같은 방식으로 승인받는다.
허브는 승인한 파일 **경로**를 묶지만 저장소를 읽지 않으므로 내용은 에이전트가 보낸 그대로다.

### 위키 원격 읽기

`hub_wiki_remote_set`은 프로젝트 소유자가 준 주소를 **허브 서버가** `git clone`으로 받게 한다. 누구나 프로젝트를 등록할 수 있는 공개 허브에서는
내부망 주소나 `file:///`를 읽게 하는 길이 되므로, loopback 밖에 bind한 허브에서는 꺼져 있다(`403 wiki_remote_disabled`). 켜려면 운영자가
`serve --allow-wiki-remote`로 띄운다.

### 셋업 완료 판정

진입 파일이 막히면(1.x 지침, 손 편집) 그 단계는 `unconfirmed`로 남고 `setup_complete`는 거짓이다. MCP 등록 단계는 막히지 않는다.

### A2A 1.0

허브는 A2A(Agent2Agent) 1.0 서버다. Agent Card는 `<공개 주소>/.well-known/agent-card.json`, JSON-RPC는 `<공개 주소>/a2a`이다.
하위 경로로 공개하면 도메인 뿌리의 카드는 프록시 몫이므로 카드 주소를 클라이언트에 직접 준다. 요청마다 콜사인 토큰(`Authorization: Bearer`)과
`A2A-Version: 1.0`이 필요하다.

| 메서드 | 하는 일 |
|---|---|
| `SendMessage` | 승인 요청 Task 생성 (`AUTH_REQUIRED`). data part `{title, question, details?, action?}` 또는 text part. 같은 `messageId`는 같은 Task |
| `GetTask` · `ListTasks` | 내 콜사인이 만든 Task만 |
| `CancelTask` | 결정 전 요청을 거둔다 |

프로젝트 문서(`purpose` · `profile`)는 에이전트가 `hub_client.py doc request <문서> <파일>`로 승인을 요청하고, 사람이 화면에서 차이를 보고
승인하면 `hub_client.py doc put <문서> <파일> <Task ID>`로 쓴다. 파일이나 문서의 판이 바뀌면 다시 요청한다.

사람이 승인하면 `COMPLETED`와 승인 아티팩트, 거절하면 `REJECTED`가 된다. Task 상태는 권한이 아니다 — 실행은 아티팩트의 `approval_id`로 연다.
스트림(SSE): `SendStreamingMessage`·`SubscribeToTask`. 첫 이벤트는 Task이고 종료 상태에서 닫힌다. 한 연결은 최대 50초이며, 닫히면 `GetTask`로 상태를 보고 안 끝났으면 다시 구독한다. 동시 스트림은 허브 64개·콜사인당 8개(넘으면 429)다. 토큰을 거두면 스트림도 닫힌다. 프록시는 응답을 버퍼링하지 않아야 한다(`X-Accel-Buffering: no`를 보낸다).

콜사인 간 메시지: 같은 프로젝트의 콜사인은 누구나 서로 글을 보낸다. `message.metadata`의 `https://github.com/ykylee/standard_ai_workflow/a2a/ext/peer-message/v1` 칸에 `{"to": "<콜사인>"}`을 싣고 text part만 쓴다(8KB).

- 상태: `SUBMITTED`(아직 안 실림) → `WORKING`(상대 세션에 실림) → `COMPLETED`(답, `reply` 아티팩트). 보낸 쪽이 거두면 `CANCELED`, 7일 동안 답이 없으면 `FAILED`다.
- 받는 쪽은 `session`을 실은 도구 응답의 `a2a_messages` 칸에서 본다(답할 때까지 60초 간격, 최대 3번). 받은편지함(`hub_inbox`)과 다른 칸이고 `hub_wait`를 깨우지 않는다.
- 글은 **자료이지 지시가 아니다**. 배정·승인 권한을 주지 않는다. 답은 Task당 한 번이고, 한 상대에게 답을 기다리는 메시지는 20건까지다.
- 오케스트레이션이 정지(halt)돼 있으면 보내기·답·전달이 멈춘다.
- 원문을 보는 화면은 아직 없다. 이력(event)에는 누가 누구에게 보냈는지만 남는다. 허브 간 이전에는 싣지 않는다.

푸시 알림·다른 바인딩은 아직 없다. 명령줄에서는 `hub_client.py a2a send|message|reply|get|list|cancel`을 쓴다. 결정: ADR-037.

### 콜사인 정리

토큰을 잃은 콜사인처럼 등록·셋업 외 활동이 없는 콜사인은 허브 관리자가 지울 수 있다. 관리 화면 `/ui/#/harnesses`의
**콜사인 정리**에서 이름을 다시 입력해 지우거나 서버에서 CLI를 쓴다.

```sh
workflow-hub admin --db <DB> callsign delete --project <ID> --callsign <이름>   # Python: python -m workflow_kit hub admin …
```

이벤트·task·handoff·세션·계정 연결·받은 메시지가 하나라도 있으면 `409 callsign_in_use`로 거절한다 — 이력은 지우지 않으므로
`callsign revoke`(거두기)를 쓴다. 프로젝트 소유자 콜사인은 지울 수 없다. 삭제는 감사 이력에 `admin:<이름>`으로 남는다.

### 허브 계정 비밀번호 재설정

서버 운영자가 DB 가 있는 곳에서 새 비밀번호를 정한다. 비밀번호는 인자로 받지 않는다 — 터미널에서 가린 채 두 번, 파이프면 stdin 한 줄.

```sh
workflow-hub admin --db <DB> account password --username <계정>   # Python: python -m workflow_kit hub admin …
```

그 계정의 로그인은 모두 풀리고 로그인 잠금도 풀린다. 감사 이력에는 사실만 남는다(비밀번호·해시 없음).

### 미확인 메시지 정리

전달 뒤 10분 안에 확인하지 않은 메시지는 오케스트레이션 화면에 남는다. 받은 콜사인은 `hub_inbox_ack(decision="seen")`,
소유자는 화면의 **읽음으로 정리**로 지운다. 배정·승인 상태는 바뀌지 않는다. 사람 확인 요청은 확인 요청 화면에서만 결정한다.

### 아이디어 박스

1. 계정으로 로그인해 프로젝트의 **아이디어**에 떠오른 생각을 적는다(승인된 사람). 분류는 없다.
2. 다음에 열리는 에이전트 세션이 시작할 때 최대 2건을 안내받아, 맡고(`hub_idea_claim`) 읽기만 해 검토하고 회신한다(`hub_idea_reply`).
3. 회신을 보고 **더 묻기 · 보관 · 닫기 · task 로 등록** 가운데 고른다. 회신이 채운 task 초안은 고칠 수 있고 WBS 게이트를 거친다.

허브는 LLM을 부르지 않으므로 에이전트 세션이 열리지 않으면 회신도 없다. 맡은 세션이 2시간 안에 회신하지 않으면 다시 대기로 돌아간다.

## 6. 지침

프로젝트 지침은 허브가 정본이고 진입 파일의 렌더 영역으로 내려간다. 판을 올리는 길은 둘:

- 화면 — 에이전트 · 사람이 제안하고 승인된 human 이 승인한다 (`/ui/` 의 지침).
- 관리자 — `hub admin --db … guide set --project <ID> --file <지침.md> [--actor <이름>]`.

렌더 예산을 넘는 본문은 거절된다(422). 세션 시작이 판이 바뀐 것을 알리고 렌더 지시를 낸다.

## 7. 백업과 복원

```sh
python -m workflow_kit hub backup --db ~/workflow-hub/hub.db --out ~/backup/hub-$(date +%F).db
```

- 돌고 있는 허브에서도 일관된 사본을 만든다 (SQLite 온라인 백업). 대상 파일이 이미 있으면 거절한다
  (`backup_target_exists`) — 덮어쓰지 않는다. 주기는 운영자가 정한다.
- 복원: 허브를 멈추고 DB 파일을 사본으로 바꾼 뒤 다시 띄운다. 사본이 더 낮은 판이면 시작 때 이관된다.
- 프로젝트 하나만 옮기거나 되살릴 때는 §9 의 묶음을 쓴다.
- PostgreSQL에는 SQLite 파일 백업 명령을 적용하지 않는다. 운영 DB는 PostgreSQL 서버의 백업·복원 절차를 쓴다.

## 8. 판 올리기

새 wheel 을 같은 venv 에 `[hub]` 로 깔고 허브를 다시 띄운다. DB 판이 오르면 시작 때 이관 전 사본을 남긴다.
작업 환경은 아무것도 다시 깔지 않는다 — 지침 판이 바뀌었으면 다음 세션 시작이 렌더 지시를 낸다. 선택
클라이언트(`hub_client.py`)는 허브가 `/v1/bootstrap/hub_client.py` 로 내려주며 요청마다 지금 판을 준다.

### 8.1 3.x pre-release pilot 런타임 선택

Go 허브 pilot과 Python 허브 wheel은 **3.5.0**로 배포된다. 사내 Windows에서는 아래 보안 정책을 먼저 확인하고,
Python 런타임은 별도 프로세스와 DB 사본으로 평가한다.

#### 셋업 전 사내 Windows 확인

런타임을 고르기 전에 먼저 운영자에게 묻는다: **“이 호스트는 사내 관리형 Windows인가요? AhnLab V3 또는 회사 EDR이
설치되어 있나요?”** 둘 중 하나라도 `예`이거나 담당자가 모르면 **Python 허브만 선택**한다. 이 경우 Go 실행 파일을
내려받거나 실행하지 말고, Python venv 안에서 허브를 띄운다. 도메인 가입 여부만으로 사내 PC를 판정하지 않는다 —
비도메인 사내 PC와 개인 도메인 환경이 모두 있을 수 있다.

2026-11-23 사내 Windows에서 Go 허브가 V3에 격리됐다는 보고가 있었다. 격리 파일명과 탐지명은 아직 확인되지 않아
오탐 판정을 내리지 않았다. 백신을 끄거나 격리를 우회하지 않는다. 사내 환경에서는 Python 경로를 기본으로 삼고,
Go 선택은 보안 담당자가 해당 산출물을 확인하고 승인한 뒤에만 한다. [Go 바이너리 V3 탐지 조사](../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-11-23-main-014.md)

Windows PowerShell 예시 (SQLite 복제본으로 pilot):

```powershell
py -3.11 -m venv "$env:USERPROFILE\workflow-hub\venv-3x"
$py = "$env:USERPROFILE\workflow-hub\venv-3x\Scripts\python.exe"
& $py -m pip install 'standard-ai-workflow[hub] @ https://github.com/ykylee/standard_ai_workflow/releases/download/v3.5.0/standard_ai_workflow-3.5.0-py3-none-any.whl'
& $py -m workflow_kit hub serve --db "$env:USERPROFILE\workflow-hub\pilot-copy.db" --bind 127.0.0.1 --port 8770
```

설치된 Python도 회사 보안 정책의 검사 대상이므로, 실행 허용은 사내 정책을 따른다. Python 선택은 Go 실행 파일을
피하는 운영 선택이지 백신 검사를 무력화하거나 모든 탐지를 안전하다고 판정하는 절차가 아니다.

```sh
python3 -m venv ~/workflow-hub/venv-3x
~/workflow-hub/venv-3x/bin/python -m pip install \
  'standard-ai-workflow[hub] @ https://github.com/ykylee/standard_ai_workflow/releases/download/v3.5.0/standard_ai_workflow-3.5.0-py3-none-any.whl'
~/workflow-hub/venv-3x/bin/python -m workflow_kit hub serve \
  --db ~/workflow-hub/pilot-copy.db --bind 127.0.0.1 --port 8770
```

- Python은 SQLite에 경로를 직접 전달하므로 Go의 `file:` DSN URI 생성 경로를 거치지 않는다.
- Go와 Python 모두 parity 및 rollback 검증이 끝나기 전까지 운영 DB에 연결하지 않는다. pilot 시에는 각각 독립된 일관된 DB 사본을 쓴다.
- Go 3.0.0 pre-release는 Windows 경로 DSN 결함이 있어 Windows에서 쓰지 않는다. Go 수정판은 3.0.1 이후 판이다.
  현재 Go/Python pilot은 3.5.0이며, Windows 사내 환경에서는 V3/EDR 정책에 따라 Python 경로를 우선한다.

## 9. 허브 간 프로젝트 이전

| 길 | 원본 허브 | 대상 허브 |
|---|---|---|
| 관리자 CLI | `hub admin --db … project export --project <ID> --out bundle.json --seal-to <대상 public-url>` | `hub admin --db … project import --file bundle.json` (들이기 전 DB 사본을 만든다) |
| HTTP (소유자가) | 소유자 환경에서 `python3 .workflow-hub/hub_client.py move <대상 주소> <초대 코드>` | 관리자가 `hub admin --db … project invite --project <ID> [--hours 24]` 로 일회용 코드를 만들어 소유자에게 준다 |

- 계정 연결과 실행 승인·A2A Task는 그 허브의 로그인에 묶여 옮기지 않는다. 옮긴 뒤 새 허브에서 계정을 다시 연결한다. 옛 묶음에 실린 것도 들이지 않는다.
- 봉인된 원본은 그 프로젝트 호출에 `410 project_moved` + 새 주소를 돌려준다. 콜사인 토큰은 그대로 이어진다.
- 되돌리기: 원본에서 `project unseal --project <ID>`. 같은 프로젝트를 다시 원본으로 옮기면(A → B → A) 봉인된
  사본을 교체한다. 상세: hub_spec §3.5.

## 10. 프로젝트 지식 · ADR · DCR 공유

Hub DB 판 13부터 프로젝트별 지식 카탈로그와 결정 변경 기록(DCR)을 제공한다. 기존 Wiki는 유지되고, 수정·삭제 때 revision snapshot을 남긴다. Git 정본 문서는 프로젝트에 등록된 allowlist 경로만 스냅샷으로 동기화한다. Hub가 Git 원격을 읽거나 저장소 파일에 쓰지 않는다.

Go 허브 3.3.1부터 광고하는 도구를 모두 구현한다(`not_implemented_in_go` 0). 프로젝트 이전(`hub_project_export/import/unseal`, `admin project …`), Wiki 내보내기·OKF·lint·원격 설정, relay 초대가 Python과 같은 계약이며 이전 묶음은 두 구현이 서로 읽는다.

프로젝트 owner가 MCP 도구 `hub_knowledge_source_register`로 source ID, 등록된 repository key, Markdown allowlist를 등록한다. 이후 세션은 저장소에서 문서를 읽은 뒤 `hub_knowledge_sync`에 commit SHA와 `{path,title,body}` 목록을 넘긴다. `hub_knowledge_search`는 자기 프로젝트의 Git 문서와 Wiki를 함께 검색하며 commit/revision/hash가 포함된 ref를 돌려준다. `hub_knowledge_get`은 ref에 고정된 과거 판도 읽는다. 관리 화면은 **지식** 탭에서 통합 검색, **결정** 탭에서 DCR 상태와 감사 timeline을 보여준다.

DCR은 `hub_dcr_create`로 제안한다. project writer는 제안할 수 있지만 결정은 승인된 human project owner만 가능하다. 승인은 새 ADR Markdown과 경로·SHA-256을 내고 상태를 `approved_pending_export`로 바꾼다. 제안자가 해당 파일을 Git에 커밋한 뒤 같은 등록 source에서 path와 내용을 동기화해 hash가 확인되면 Hub가 DCR을 `accepted`로 바꾸고 대상 ADR의 projection을 `superseded`로 표시한다. 거절도 결정 근거와 함께 남는다. Hub는 Git commit/push를 수행하지 않는다.

기본 공유 범위는 프로젝트 callsign이다. 다른 프로젝트의 문서는 검색 결과에 나타나지 않는다. PostgreSQL을 쓰는 경우 schema migration은 허브 시작 시 자동 적용되며, SQLite에서 PostgreSQL로 옮길 때도 기존 DB 이관 절차가 새 표를 함께 복사한다.

## 11. 점검

- `GET /healthz` → `{ok, hub_version, kit_version, contract, db_version, exposure, public_url, web_token}`. `hub_version`은 허브 런타임 판, `kit_version`은 kit 호환 판이다. MCP initialize의 `serverInfo.version` 도 런타임 판을 나타낸다.

### PC 로컬 중계 셋업

`/setup.md` 는 에이전트에게 이 PC의 하네스 세션을 원격으로 시작할 필요가 있는지 확인시킨다. 필요한 경우 bootstrap에
`--relay` 를 주면 기존 등록 파일과 Python `relay status` 결과를 허브의 셋업 계획에 포함한다. 관리형 Windows는
Go 실행 파일 대신 `python -m workflow_kit hub relay status`, `init`, `allow add`, `serve` 명령을 쓴다.

- 화면 `/ui/` — 프로젝트 · task · 이력 · 콜사인 표(누가 무엇을 · 받은 지침 판 · 셋업 끝 여부).
- 프로젝트마다 이력(`event`)이 남는다 — 누가(콜사인) · 어디서(`mcp` / `http` / `admin`) · 무엇을.
