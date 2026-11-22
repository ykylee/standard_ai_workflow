# 2.x 전면 Go 전환 — requirements

- 문서 목적: M-049 결정(소유자 2026-11-22 — R1 = D 전면 Go)을 요구 R 과 검증 방법으로 옮긴다. Go 판이 **바꾸면 안 되는 계약**과 **같은 답 기준**을 먼저 고정해, design 이 언어만 바꾸고 동작은 바꾸지 않게 한다 (M-050).
- 범위: 계약 표면 실측 인벤토리 (§1 — WBS-50.1), 요구 R25~R35 (§2 — WBS-50.1 · 50.2), 추적표 (§3), 정할 것 Q1~Q6 (§4), 미측정 (§5). ADR 초안은 [`adr-035-go-runtime`](../../ai-workflow/wiki/decisions/adr-035-go-runtime.md) (WBS-50.3)
- 대상 독자: 소유자, 구현자 (M-051~)
- 상태: draft — §1~§5 작성, 정할 것 Q1~Q6 소유자 대기
- 최종 수정일: 2026-11-22
- 관련 문서: [`runtime-port-review-2026-11.md`](./runtime-port-review-2026-11.md) (concept — "concept §n"), [`M-050`](../../ai-workflow/memory/active/roadmap/M-050-go-port-requirements.md), [`hub_spec.md`](../../workflow-source/core/hub_spec.md) (2.0 계약 — "2.0 §n"), [`hub_orchestration_spec.md`](../../workflow-source/core/hub_orchestration_spec.md) (2.1 계약 — "2.1 §n"), [`RELEASE.md`](../RELEASE.md) §1.5 (판 등급)

## 0. 요약

Go 판의 성공 기준은 하나다 — **사용자 · 하네스 · 기존 DB 입장에서 아무것도 바뀌지 않는다.** 도구 74개의 이름 · 인자 · 응답 칸,
HTTP 경로, DB 판 12 의 표 32개, 1.x 생성물 형식, 판정 결과가 Python 판과 같아야 한다. 그래서 요구의 축은 셋이다:

1. **계약 불변** (R25 · R26 · R29) — 바뀌면 안 되는 것을 목록으로 고정한다 (§1 실측).
2. **같은 답** (R27 · R28) — 판정은 차분 검사(같은 입력 → Python · Go 결과 대조), 허브 전체는 기존 허브 검사를 두 구현에 돌리는 적합성 검사.
3. **단계 이행** (R30~R35) — 중계 → 허브(그림자 운영) → 전환 → Python 판 은퇴. 1.x(`release/1.x`, 2028-07-20 까지)는 Python 판정을 그대로 쓴다.

## 1. 계약 표면 실측 (2026-11-22, `main` = v2.1.0 + main-022)

코드에서 직접 뽑은 값이다 (`workflow_kit.hub.tools.TOOLS` · `db.open_db` 로 만든 빈 DB · `app.py` / `ui.py` 의 `Route`).

| 표면 | 실측 | 정본 |
|---|---|---|
| MCP 도구 | **74** — 부트스트랩 묶음 6 (토큰 없이: `hub_project_lookup` · `hub_project_register` · `hub_callsign_register` · `hub_setup_plan` · `hub_setup_confirm` · `hub_project_import`) + 토큰 묶음 68 | 2.0 §4.4 · §4.5, 2.1 §5 |
| HTTP 경로 (허브) | **9** — `/` · `/healthz` · `/setup.md` · `/v1/bootstrap/hub_client.py` · `POST /v1/tools/{name}` · `/v1/relay/{register,poll,result}` · `/mcp` (GET · POST · DELETE) | 2.0 §4.1, 2.1 §9.2 |
| HTTP 경로 (화면) | `/ui` · `/ui/` · `/ui/{name}` + `/api/…` **16** | 2.0 §4.7 |
| 화면 정적 파일 | 4개 (`index.html` · `hub.js` · `hub.css` · `favicon.svg`), 44 KB | `hub/static/` |
| 응답 머리 | `X-Hub-Kit` · `X-Hub-Contract` · `X-Hub-Db`, 화면 CSP · `Referrer-Policy` | 2.0 §4.1 · §4.7 |
| 오류 형식 | `{error_code, message, detail}` + HTTP 상태 | 2.0 §4.3 · 2.1 §12 |
| MCP 전송 | streamable HTTP · stateless · JSON 응답, SDK `mcp>=1.27,<3` (2.3.0 실측 — main-022) | 2.0 §2.3 |
| DB | 판 **12** · 표 **32** · 인덱스 36 · 트리거 0 — 시작 때 이관 · 이관 전 사본 · `version` 대조 쓰기 | 2.0 §3 · 2.1 §4 |
| 판정 입구 (`hub/judge.py`) | 7종 — 계획 파싱 · 린트 / 응답 자격 · 결정 상태 / done 게이트 / WBS 게이트 / 로드맵 파싱 · 진척 / 상태 생성 / handoff 파싱 | 2.0 §2.2 표 |
| 판정이 딸고 오는 코드 | 허브 7.0k 줄 + 공유 kit 19.3k 줄 (`common` 14.9k · `backlog_update` 1.6k · OKF 2.0k · 경로 · 진입 파일 0.7k) | concept §3 |
| 1.x 생성물 형식 | `state.json` `schema_version` "1" · `roadmap_state` v1 · `workbench-state/1` · `workflow-kit-plan-response/1` | 2.0 §1-1 |
| 진입 파일 렌더 영역 | 표준 규칙 사본(`_standard_snapshot.py`) + 하네스별 진입 파일 생성기 · sha 표식 · 예산 | 2.0 §5.2 |
| 선택 클라이언트 | `hub_client.py` 554 줄 · 표준 라이브러리만 · `/v1/bootstrap` 이 원문을 내려준다 | 2.0 §7 |
| 관리 CLI | `hub serve` · `backup` · `admin` (token · callsign · project export/import/seal/unseal/invite) · `hub relay` (init · allow · serve · pause · resume · status) | 2.0 §2.1 · 2.1 §9.1 |
| 허브 검사 | 14 파일 (12 개가 실제 허브 프로세스에 HTTP · MCP 호출, 전부 kit 내부도 import) + 중계 · VS Code | `tests/check_hub_*.py` |

## 2. 요구

### R25 — 바깥 계약 불변

- **R25.1** 도구 74개(그리고 그 뒤에 더해질 도구)의 이름 · 묶음 · 입력 스키마(필수 · 거절 규칙 포함) · 응답 칸 · 오류 코드가 Python 판과 같다. 모르는 필드 · 판은 거절한다 (2.0 §1-5).
- **R25.2** HTTP 경로 · 메서드 · 인증(Bearer · 화면 토큰 · 출처 대조) · 응답 머리 · `healthz` 칸이 같다. `X-Hub-Kit` 은 Go 판의 판을 싣는다.
- **R25.3** MCP 는 streamable HTTP · stateless · JSON 응답으로 열고, Python 판이 지원하는 규격 판(2025-11-25 · 2026-07-28)을 모두 받는다. Go 공식 SDK(`go-sdk`, concept §2.1)를 쓴다.
- **R25.4** 화면(`/ui/` · `/api/…`)은 정적 파일 4개를 **그대로** 실어 내보낸다 (바이너리에 포함). `/api` 응답 JSON 이 같다.
- **R25.5** 진입 파일 렌더 영역의 바이트가 같다 — 같은 프로젝트 · 같은 지침 판이면 Python 판과 Go 판이 같은 sha 를 낸다 (작업 환경이 '손 편집 감지' 로 오인하지 않게).

### R26 — 데이터 불변

- **R26.1** Go 허브는 Python 허브가 만든 DB(판 ≤ 12)를 **그대로 연다**. 판 13 이상의 이관은 Go 판에서 이어서 정의하고, 이관 전 사본 규칙(2.0 §3.4)을 지킨다.
- **R26.2** 표 · 칸 · 인덱스 이름과 의미를 바꾸지 않는다. 시각 · JSON 칸의 문자열 형식(ISO-8601 UTC · 키 순서 무관 JSON)이 같다.
- **R26.3** 백업(`hub backup`) · 허브 간 이전 묶음(`project export` / `import` · 봉인 · 초대)의 형식이 두 판 사이에서 서로 읽힌다 — Python 허브에서 낸 묶음을 Go 허브가 들이고, 그 반대도 된다 (이행 기간 되돌리기 경로).
- **R26.4** 비밀은 지금처럼 DB 에 해시만 — 토큰 원문 · 비밀 검사(`secret_in_payload`, 2.0 §1-4)가 같다.

### R27 — 판정 동일성 (차분 검사)

- **R27.1** 판정 입구 7종(§1)과 그 아래 함수가 Go 로 옮겨지고, **같은 입력에 같은 출력**을 낸다. 출력은 JSON 으로 정규화해 비교한다 (키 순서 · 숫자 표기만 무시).
- **R27.2** **차분 검사** — 같은 입력을 Python 판정과 Go 판정에 넣어 결과를 대조하는 검사를 게이트에 둔다. 입력 묶음(corpus)은 ① 기존 검사 fixture, ② 이 저장소의 실제 1.x 데이터(들여오기 리허설 실측: task 646 · 보관 281, 2.0 requirements §16.5), ③ 각 판정 규칙의 경계 사례. **불일치 0** 이 전환 조건이다.
- **R27.3** 시각은 지금처럼 인자로 주입한다 (2.0 §1-7). Go 판정 함수도 시계를 읽지 않는다 — 차분 검사가 같은 시각을 두 구현에 넣을 수 있어야 한다.
- **R27.4** 1.x(`release/1.x`) 결함 수리 중 판정에 닿는 것은 **Go 판에도 같이 반영**하고, 그 사례를 corpus 에 더한다. 한쪽만 고친 상태를 차분 검사가 red 로 잡는다.
- **R27.5** '미측정' 은 통과가 아니다 — 판정이 재지 못한 칸(예: L5 줄 수)을 Go 판도 같은 표식으로 낸다 (2.0 §1-9).

### R28 — 적합성 검사 (허브 전체)

- **R28.1** 허브 검사(`check_hub_*`)가 띄우는 허브를 **명령 하나로 갈아 끼울 수 있다** (예: 환경 변수로 Python 판 · Go 판). 같은 검사가 두 구현에서 통과해야 한다.
- **R28.2** 허브 검사 안의 kit 내부 import(DB 직접 확인 · fixture 생성)는 HTTP · DB 파일 확인으로 바꾸거나 구현 중립 도우미로 옮긴다 — 검사가 Python 허브의 내부에 묶이지 않게.
- **R28.3** 실제 하네스 실측(Claude Code · Codex · MiniMax Code · Antigravity — 2.0 §16.4 · 16.7 방식)을 Go 허브로 다시 한다. 셋업(`/setup.md`) 완주가 포함된다.

### R29 — 생성물 불변

- **R29.1** 1.x 생성물 형식(§1)을 Go 판도 그대로 낸다. `state.json` 등은 Python 판 결과와 의미상 같다(R27.1 정규화 비교).
- **R29.2** git 내보내기 · 위키 index/log · memory_index 생성물이 같다.

### R30 — 단계 이행

- **R30.1 S1 중계** — PC 중계를 먼저 Go 로 (판정 없음 · 909줄 · 닫힘, concept §3). 중계 HTTP 계약(`/v1/relay/*`)과 어댑터 실측(2.1 요구 §1.5)을 Go 판으로 다시 한다.
- **R30.2 S2 허브 그림자 운영** — Go 허브를 Python 허브 옆에 띄우고, 같은 요청을 둘에 보내 응답 · DB 결과를 대조하는 기간을 둔다 (테스트베드 허브 · 이 저장소 데이터 사본). 불일치 0 과 R28 통과가 다음 단계 조건이다.
- **R30.3 S3 전환** — 상시 허브를 Go 판으로. 되돌리기는 R26.3 의 묶음 · 같은 DB 로 Python 판을 다시 띄우는 것.
- **R30.4 S4 은퇴** — Python 허브 · 중계를 deprecation 정책([`v0_9_0_deprecation_policy_spec.md`](../../workflow-source/core/v0_9_0_deprecation_policy_spec.md))으로 내린다. 은퇴 전까지 두 판에 결함 수리가 들어간다.

### R31 — 배포

- **R31.1** 허브 · 중계는 OS별 단일 바이너리(linux · darwin · windows × amd64 · arm64)로 GitHub Releases 에 낸다. 체크섬을 함께 싣는다. PyPI 는 지금처럼 쓰지 않는다.
- **R31.2** 서명 · 공증은 결정 R4(concept §11) — Windows · macOS 실측 뒤 정한다. 그 전까지 Windows 는 Python 판을 병행한다.
- **R31.3** 바이너리는 `--version` 과 `healthz.kit_version` 으로 판을 말하고, 판 번호 규칙은 지금과 같다(정수 X.Y.Z, 베타 표기는 노트로).

### R32 — 게이트 · 개발 환경

- **R32.1** Go 도구 사슬의 판을 고정한다 (예: `go.mod` 의 `go`/`toolchain` 줄). 개발 호스트 요구에 Go 를 더한다.
- **R32.2** Go 의 빌드 · `go vet` · `go test` · 크로스 빌드를 `check_*.py` 하나 이상으로 감싸 기존 러너(`run_all_checks.py`)에 넣는다 — 게이트 정본은 하나로 남는다. Go 가 없는 호스트에서는 '미측정' 으로 보고한다 (통과로 세지 않는다).
- **R32.3** 발행 게이트(게이트 증거 · 노트 수치)가 Go 산출물(바이너리 · 체크섬)도 본다.

### R33 — 1.x · Python 공존

- **R33.1** `release/1.x` 는 Python 그대로다 — 이 전환과 무관하게 2028-07-20 까지 결함 수리만.
- **R33.2** `main` 의 Python 패키지(1.x 공개 API · `python -m workflow_kit` 명령)를 언제까지 내는지 정한다 (Q2).
- **R33.3** 한 판정 규칙이 두 언어에 있는 동안, 규칙 문서(스펙)가 정본이고 두 구현은 그것을 따른다. 규칙을 바꾸는 변경은 두 구현과 corpus 를 같은 커밋에서 바꾼다.

### R34 — 선택 클라이언트

- **R34.1** `hub_client.py`(표준 라이브러리 · 작업 환경에서 에이전트가 돌림)의 처리를 정한다 (Q3). 어느 쪽이든 `/v1/bootstrap` 계약(원문 · 판 머리 · sha 머리, 2.0 §4.1)은 유지한다.

### R35 — 결정 문서 개정

- **R35.1** ADR-035 — PURPOSE 제외 영역(Python 외 런타임)의 예외를 2.x 런타임(Go)으로 넓힌다 (concept R3). hub_spec R0.3('허브 · 클라이언트 · 부트스트랩 원문은 Python') 개정.
- **R35.2** PURPOSE 3.0판(또는 개정)에 반영 — 소유자 승인 뒤.

## 3. 추적표 — concept → 요구

| concept (runtime-port-review) | 요구 |
|---|---|
| §11-1 판정 두 벌 · 차분 검사 | R27 · R33.3 |
| §11-2 허브 검사를 적합성 검사로 | R28 |
| §11-3 이행 순서 · 단계별 같은 답 | R30 |
| §11-4 생성물 · DB · 도구 · 경로 불변 | R25 · R26 · R29 |
| §11-5 검사 하네스 언어 · `go test` | R32 |
| §11-6 배포 (OS별 바이너리) | R31 |
| R3 PURPOSE 예외 ADR | R35 |
| R4 서명은 실측 뒤 | R31.2 |
| §2.1 `go-sdk` v1.8.0 · 규격 2026-07-28 | R25.3 |

## 4. 정할 것 (소유자)

| ID | 질문 | 기본값 (권고) | 선택지 · 근거 |
|---|---|---|---|
| Q1 | Go 판의 판 번호 | **3.0.0** | 3.0.0 · 2.x minor. RELEASE §1.5: 진입점(`python -m workflow_kit hub …` · `pip install …[hub]`)이 **사라지면 major**. 계약(도구 · DB)은 같아도 설치 · 실행 방법이 바뀐다 |
| Q2 | `main` 의 Python 패키지 | **S4 까지 wheel 을 함께 내고, S4 에서 Python 허브 · 중계를 은퇴. 1.x 공개 API 는 `release/1.x` 에만 남김** | ① 위 권고 ② 3.0 부터 바이너리만 ③ 1.x API 를 main 에 계속 (판정 두 벌이 main 안에 상주) |
| Q3 | `hub_client.py` | **Python 한 파일 유지** — Go 허브가 원문을 내장해 `/v1/bootstrap` 으로 내려준다. 판정 없음 · 작업 환경 쪽이라 언어를 바꿀 이유가 약하다. Go 클라이언트는 후속 | Python 유지 · Go 바이너리 클라이언트 · 둘 다 |
| Q4 | SQLite 드라이버 | **`modernc.org/sqlite` (순수 Go)** — cgo 없이 크로스 빌드 (concept §2.2 실측 v1.62.0) | modernc · `mattn/go-sqlite3`(cgo, C 도구 사슬 필요) |
| Q5 | 저장소 배치 | **이 저장소의 `hub-go/`** (모듈 `github.com/ykylee/standard_ai_workflow/hub-go`) — 스펙 · corpus · 검사가 한 커밋에 묶인다 (R33.3) | 하위 디렉터리 · 별도 저장소 |
| Q6 | 차분 검사 corpus 에 이 저장소 실데이터를 쓰나 | **예** — 실데이터가 fixture 가 못 잡는 모양을 잡는다 (리허설 실측). 커밋할 때는 `.gitignore` 된 사본이 아니라 저장소 이력에서 매번 만든다 | 예 · fixture 만 |

## 5. 미측정 (통과로 세지 않는다)

- `go-sdk` 로 74 도구 · 긴 대기(`hub_wait`, 50초 상한) · 화면 정적 파일 · 화면 인증의 실제 동작 — 탐침은 도구 1개였다 (concept §7)
- Go 판정 구현의 실제 이식량 · 기간 (줄 수는 Python 기준)
- Windows · macOS 바이너리 실행 · 백신 · Gatekeeper (R31.2)
- MiniMax Code · Antigravity 의 Go 허브 연결 (R28.3)
