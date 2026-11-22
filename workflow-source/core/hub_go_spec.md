# 허브 Go 판 설계 (3.0)

- 문서 목적: 2.x 허브 · 공유 판정 · PC 중계를 Go 로 옮기는 **구조 · 검증 · 이행** 설계 — `hub-go/` 배치, Python 모듈 대응, DB 와 분리한 순수 판정 입구, 언어 중립 판정 CLI 프로토콜, 차분 검사 · 적합성 검사, 게이트 감싸기, S1 중계 · 빌드 · 배포 — 를 정한다.
- 범위: **언어만 바꾼다.** 도구 · HTTP 경로 · DB · 생성물 · 판정 결과는 `hub_spec.md` · `hub_orchestration_spec.md` 그대로 (요구 R25 · R26 · R29). 여기에는 그 계약을 Go 로 지키는 방법만 적는다.
- 대상 독자: 구현자 (M-052~), 소유자 (DG 결정)
- 상태: draft (M-051, 2026-11-22) — design 결정 DG1~DG5 **소유자 확정 (권고안 전부)** · ADR-035 Accepted. 구현은 M-052~ (S1 중계부터)
- 최종 수정일: 2026-11-22
- 관련 문서: `../../docs/planning/go-port-requirements-2026-11.md` (요구 R25~R35 · 결정 Q1~Q6 — 아래 "요구 R…" · "Q…"), `../../docs/planning/runtime-port-review-2026-11.md` (concept), `./hub_spec.md` (2.0 계약), `./hub_orchestration_spec.md` (2.1 계약), `../../ai-workflow/wiki/decisions/adr-035-go-runtime.md`

## 1. 불변 조건

1. 바깥 계약은 Python 판이 정본이다 — Go 판은 그것을 **재현**한다. 둘이 다르면 Go 판의 결함이다 (S3 전환 전까지).
2. 판정 규칙의 정본은 스펙 문서다. 규칙 변경은 Python 구현 · Go 구현 · corpus 를 **같은 커밋**에서 바꾼다 (요구 R33.3).
3. Go 판정 함수는 시계 · 파일 시스템 · 환경 변수를 읽지 않는다 — 시각 · 파일 존재 · 줄 수는 **입력 데이터**로 받는다 (요구 R27.3). 그래야 같은 입력을 두 구현에 넣을 수 있다.
4. 재지 못한 것은 '미측정' — Go 가 없는 호스트의 Go 검사, 판정이 재지 못한 칸 모두 (요구 R27.5 · R32.2).
5. 모르는 필드는 거절한다 — 판정 CLI 입력도 마찬가지다.

## 2. 배치 — `hub-go/` (Q5)

```
hub-go/
  go.mod                      module github.com/ykylee/standard_ai_workflow/hub-go · go/toolchain 줄 고정 (R32.1)
  cmd/workflow-hub/           바이너리 하나 — serve · backup · admin · relay · judge (§4)
  internal/
    db/        스키마 · 이관(판 1~12 SQL 은 Python `hub/db.py` MIGRATIONS 를 그대로) · 백업 · 판 대조 쓰기
    store/     Ctx · 인증 · 비밀 검사 · 이력 (Python `hub/store.py`)
    tools/     도구 74 — 스키마 · 묶음 · 처리기 (Python `hub/tools.py` · `session.py` · `orchestration.py` · `relay.py` · `setup.py` · `transfer.py` · `migrate1x.py` · `guide.py` · `memory.py` · `wiki.py` · `wiki_remote.py`)
    judge/     순수 판정 — §3. DB 를 모른다
    judgedb/   DB → 판정 입력 조립 (Python `hub/judge.py` 의 DB 쪽 절반)
    render/    진입 파일 렌더 영역 (Python `hub/render.py` + `bootstrap_lib/harnesses` 의 생성기)
    httpapi/   `/healthz` · `/v1/tools` · `/v1/relay` · `/` · `/setup.md` · `/v1/bootstrap` · 머리 · 오류 형식
    mcpserver/ `go-sdk` streamable HTTP · stateless · JSON (요구 R25.3)
    ui/        `/ui/` 정적 파일 · `/api/…` 16 (Python `hub/ui.py`)
    relay/     PC 중계 (Python `workflow_kit/relay/` — S1, §6)
    assets/    내장 자산 (§2.1)
```

### 2.1 자산 내장과 단일 출처

`go:embed` 는 모듈 밖(`../workflow-source/…`)을 못 읽는다. 내장할 자산은 넷이다 — 화면 정적 파일 4개, `hub_client.py`(Q3),
표준 규칙 사본(`_standard_snapshot.py` 의 블록), 하네스 진입 파일 템플릿.

- **S4 전까지 정본은 Python 쪽**이다. `go generate` 가 정본을 `internal/assets/` 로 복사하고, 사본은 커밋한다 (Go 만으로 빌드되게).
- 검사 `check_go_assets_sync` 가 사본과 정본의 바이트를 대조한다 — 다르면 red (1.x `_standard_snapshot` 과 같은 방식, `check_hub_bootstrap`).
- S4 에서 정본을 `hub-go/` 로 옮기고 방향을 뒤집는다.

## 3. 순수 판정 입구 — DB 와 분리

Python `hub/judge.py` 의 `Judge` 는 DB 연결을 받아 판정 입력을 모으고 판정 함수를 부른다. Go 판은 이를 둘로 나눈다:
`judgedb`(DB → 입력) 와 `judge`(입력 → 결과, 순수). 차분 검사는 `judge` 만 대조한다.

| op | 입력 (JSON) | 출력 | Python 정본 |
|---|---|---|---|
| `plan.lint` | `plan_md` · `criteria[]` · `line_counts{path: int}` (없으면 L5 '미측정') | `issues[]` · `has_error` | `plan_claims.parse_plan` · `lint_plan` · `has_error_rules` |
| `plan.states` | `plan_md` · `task_id` · `responses[{name, bytes_b64}]` | 응답별 `verdict` · `states{D: state}` · `open[]` | `plan_responses.parse_response` · `qualify` → `plan_claims.compute_states` (순서 고정) |
| `task.status` | `requested_status` · `validation_result` · `operation_type` · `current_status` · `recorded_validation` | `status` · `warnings[]` | `planning.determine_conservative_task_status` |
| `wbs.gate` | `roadmap_docs{path: text}` · `is_draft` · `wbs` · `exempt_reason` | verdict | `state.roadmap.judge_wbs` |
| `roadmap.derive` | `roadmap_docs{path: text}` · `links[]` · `deliverables{path: bool}` · `generated_at` | `roadmap_state` v1 · `issues[]` | `parse_index_text` · `parse_milestone_text` · `derive_state` |
| `state.build` | `files{relpath: text}` (1.x 배치) · `generated_at` | `state.json` (`schema_version` "1") | `state.builder.build_workflow_state_payload` (임시 디렉터리에 펼쳐 부름 — 지금 허브와 같다) |
| `handoff.parse` | `text` | 구조 | `project_docs.HandoffParser` |

- 콜백(`file_line_count` · `deliverable_exists`)은 **맵 입력**으로 바꾼다. 맵에 없는 키는 콜백이 `None` 을 낸 것과 같다 ('미측정').
- 출력은 정규화 JSON(키 정렬 · UTF-8 · 정수는 정수)으로 낸다. 차분 비교는 바이트 비교다 (요구 R27.1).
- op 표는 닫혀 있지 않다 — Go 로 옮기는 판정이 늘면 op 를 더한다. op 없이 옮긴 판정은 차분 검사 밖이라 **금지**한다.

## 4. 판정 CLI 프로토콜 (두 언어 공통)

```
python -m workflow_kit.judgecli <op>     # Python 정본 (새 모듈 — 위 표의 함수를 부르는 얇은 입구)
workflow-hub judge <op>                  # Go 판
```

- 입력: 표준 입력 JSON `{"protocol": "judge/1", "input": {...}}`. 출력: 표준 출력 정규화 JSON `{"protocol": "judge/1", "op": ..., "result": ...}`.
- 오류: 종료 코드 2 + `{"protocol": "judge/1", "error_code": ..., "message": ...}` — 모르는 op · 모르는 필드 · 프로토콜 판 불일치.
- 한 프로세스가 여러 입력을 받는 묶음 모드 `--batch` (JSON Lines) — corpus 수천 건을 프로세스 기동 비용 없이 돌린다.

## 5. 검증

### 5.1 차분 검사 `check_judge_parity` (요구 R27)

- corpus 를 만든다 (§5.2) → 두 CLI 에 같은 입력을 `--batch` 로 넣는다 → 출력 바이트 대조.
- 보고: op 별 건수 · 일치 · 불일치(첫 3건의 입력 요약과 두 출력의 차이) · Go 미측정. **불일치 1건이라도 red**.
- 되주입 case: Go 판정 결과 하나를 바꾸면 red, Python 쪽 하나를 바꾸면 red — 비교가 살아 있는지 잰다.

### 5.2 corpus (Q6)

| 출처 | 만드는 법 | 커밋 |
|---|---|---|
| 기존 검사 fixture | 판정 검사(`check_plan_*` · `check_roadmap_*` · `check_backlog_update` 등)의 입력을 op 입력으로 옮긴 파일 | `hub-go/testdata/corpus/fixture/` |
| 이 저장소 실데이터 | 검사 시점에 `git ls-files` 의 task · 로드맵 · handoff 와 `git show <rev>:` 이력 판으로 op 입력을 **매번 생성** | 안 함 (저장소 자체가 corpus) |
| 경계 사례 | 규칙마다 손으로 쓴 최소 입력 (L1~L8 각각 · 결정 상태 6종 · done 경계 · WBS exempt) | `hub-go/testdata/corpus/edge/` |

### 5.3 적합성 검사 (요구 R28)

- 허브 검사 11개가 `check_hub_core.Hub` 한 곳에서 허브를 띄운다 (실측). 그 한 곳에 스위치를 둔다:
  `WORKFLOW_HUB_IMPL=python`(기본) · `go`, `go` 면 `WORKFLOW_HUB_BIN`(기본 `hub-go/bin/workflow-hub`)을 같은 인자로 띄운다.
- 검사 안의 kit 내부 import(DB 확인 · fixture)는 `tests/_hub_probe.py`(구현 중립 도우미 — sqlite3 로 DB 파일만 읽고 HTTP 만 부른다)로 옮긴다 (요구 R28.2).
- 게이트: 기본 러너는 Python 판으로 돈다. `check_hub_conformance_go` 가 같은 검사들을 `WORKFLOW_HUB_IMPL=go` 로 다시 돌린다 — Go 바이너리가 없으면 '미측정'.

### 5.4 게이트 감싸기 (요구 R32)

| 검사 | 하는 일 |
|---|---|
| `check_go_build` | `go vet ./...` · `go test ./...` · 6 대상 크로스 빌드 (`CGO_ENABLED=0`) — `go` 가 없거나 `go.mod` 판과 다르면 '미측정' |
| `check_go_assets_sync` | §2.1 자산 사본 = 정본 |
| `check_judge_parity` | §5.1 |
| `check_hub_conformance_go` | §5.3 |

네 검사는 `WATCHES` 로 `hub-go/*` 와 관련 Python 정본을 선언해 `--changed` 가 고른다.

## 6. S1 — PC 중계 Go 판 (요구 R30.1)

- 범위: Python `workflow_kit/relay/` 전체 — CLI(init · allow · serve · pause · resume · status), 설정 자리 · 토큰 600 파일, 긴 폴링, 어댑터(claude-code · codex · fake), 로컬 화면(`127.0.0.1`, CSP · 출처 규칙 포함 — main-016 실측값).
- 설정 파일 형식(`relay.json` · 허용 목록 · `relay-state.json`)이 같다 — Python 중계 설정 디렉터리를 Go 중계가 그대로 읽는다.
- 검증: `check_hub_relay` 를 중계 구현 스위치(`WORKFLOW_RELAY_IMPL=python|go|both`)로 실제 자식 프로세스 + 로컬 화면 HTTP 로 두 구현에 돌린다 (python 11/11 · go 11/11 · both 22/22, 되주입 `config.go` 변조 → `[go] case 4` FAIL 확인). 실제 어댑터 실측(2.1 요구 §1.5 — Linux 호스트 Go 중계 `workflow-hub relay` 기준): **Claude Code 2.1.330**(L1 `5.1s` · L2 `14.8s` `next_turn` · `done-cc.txt=OK` · L3 `1.0s` `ended`) · **Codex 0.171.0**(L1 `12.3s` · L2 `24.5s` `steer` · `done-cx.txt=OK` · `workspaceWrite` sandbox + `writableRoots` `git commit` · L3 `1.0s` `ended`).
- Codex 어댑터의 쓰기 루트(main-014 — git dir · common dir)와 VS Code 화면 정책(main-016)을 그대로 옮긴다.

## 7. 빌드 · 배포 (요구 R31)

- 대상 6: linux · darwin · windows × amd64 · arm64, `CGO_ENABLED=0 -trimpath -ldflags "-s -w -X main.version=<판>"`. 판은 `workflow-source/pyproject.toml` 의 판과 같다 (S4 전까지 판 정본 하나).
- 산출물: `workflow-hub-<판>-<os>-<arch>[.exe]` + `SHA256SUMS`. 발행 도구(`release_pipeline`)의 `dist` 가 Go 빌드를 부르고, `release` 가 asset 으로 싣는다. 발행 게이트는 바이너리 · 체크섬 존재를 본다 (요구 R32.3).
- 서명 · 공증은 concept R4 대로 실측 뒤 (요구 R31.2).

## 8. 단계별 완료 기준

| 단계 | 완료 기준 |
|---|---|
| S1 중계 | `check_hub_relay` 두 구현 green · 실제 어댑터 실측 · 6 대상 빌드 — **완료 (M-052 · TASK-2026-11-22-main-031~033)** |
| S2 허브 그림자 | 적합성 검사 전부 두 구현 green · 차분 검사 불일치 0 (fixture + 실데이터 + 경계) · 테스트베드에서 같은 요청을 두 허브에 보낸 결과 대조 차이 0 · 하네스 4종 실측 |
| S3 전환 | 상시 허브를 Go 판으로, 되돌리기 리허설(같은 DB 로 Python 판 기동) 성공 |
| S4 은퇴 | deprecation 정책대로 Python 허브 · 중계 제거, 자산 정본 이동(§2.1) — 3.x 의 다음 판 |

## 9. design 결정 (DG — 소유자 2026-11-22 확정: 권고안 전부)

| ID | 질문 | 결정 (= 권고) | 선택지 |
|---|---|---|---|
| DG1 | 판정 입구 | **순수 판정 op + JSON CLI (§3 · §4)** — 차분 검사의 전제 | op CLI · Go 테스트에서 Python 을 직접 부름(cgo · 임베드) |
| DG2 | HTTP 라우터 | **표준 라이브러리 `net/http` ServeMux** (Go 1.22+ 경로 패턴) — 의존 0 | 표준 라이브러리 · chi 등 |
| DG3 | 적합성 스위치 | **환경 변수 `WORKFLOW_HUB_IMPL` · `WORKFLOW_HUB_BIN`** (§5.3) | 환경 변수 · 러너 인자 |
| DG4 | 빌드 · 발행 도구 | **`release_pipeline` 이 `go build` 를 직접 부름** — 새 도구 0 | 직접 · goreleaser |
| DG5 | 이관 SQL | **Python `MIGRATIONS` 의 SQL 문자열을 그대로 복사하고 `check_go_assets_sync` 가 대조** — 같은 DB 를 만든다는 가장 강한 근거 | 복사 + 대조 · Go 에서 다시 씀 |
