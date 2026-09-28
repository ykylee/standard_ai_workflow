# Beta v1.12.0 (2026-09-28)

> **상태: 릴리스 준비.** package `1.12.0`, runtime `__version__ = 1.12.0`, tag `v1.12.0`.
> **minor release** — **CI 를 걷고 로컬 게이트를 근거로 세운 사이클 + 세션 시작 컨텍스트 예산.**
>
> 등급 근거 (§1.5): `wk release-status` 는 `!` 커밋 2건을 근거로 **2.0.0** 을 제안하고
> `requires_decision` 을 세웠다. 소유자 결정(2026-09-28)은 **minor + 은퇴 shim** 이다.
> 판정과 반대 근거는 §0.1 에 있다.

## 0. 릴리스 판정

이 사이클의 주제는 **"재는 곳을 옮기면, 옛 자리에 기대던 것을 전부 옮겨야 한다"** 다.

GitHub Actions 테스트 workflow 를 폐지하고(2026-09-23 소유자 결정) 발행 게이트의 근거를
CI 조회에서 **로컬 게이트 통과 기록**으로 옮겼다. 그 이동이 남긴 자리가 이 사이클에서
하나씩 드러났다 — 늘 `skipped` 를 내던 `ci_mypy` 칸, 게이트 기록 없이 나가던 push,
그리고 이번 발행 준비에서 드러난 **유예 없이 지워진 공개 API 2종**.

### 0.1 `!` 2건에 §1.5 적용 → minor (소유자 결정)

| 커밋 | 무엇이 깨지나 | 판정 |
|---|---|---|
| `534e3a8d` ci! | `release_pipeline.verify_required_ci` · `REQUIRED_CI_WORKFLOWS` 제거 — **동결 표면** (`tools/`, v0.8.0 spec §3.3). v1.9.0 노트가 "공개 API 추가" 로 적은 두 이름이다 | **이 발행에서 되살렸다** — 은퇴 shim (§3). 제거는 v1.13.0 |
| `534e3a8d` ci! | branch/interpreter/sdk matrix 모듈의 `--github-matrix` 류 CLI 제거 | `workflow_kit.common.*` — 보장 밖 (stable_guarantee §1.2) |
| `53a3e152` refactor! | `release` · `release-status` JSON 의 `ci_mypy` 필드와 summary 의 `ci_mypy=` 토큰 제거 | 생성 스키마(`schemas/`)에 없는 필드. CI 폐지 뒤 늘 `skipped` 였다. 옛 플래그(`--skip-cross-verify` · `--strict-cross-verify`)는 경고와 함께 no-op 으로 계속 받는다 — **호출자는 죽지 않는다** |

**반대 근거 (감추지 않는다)**:

1. **공개 API 제거가 실제로 있었다.** shim 이 없었다면 §1.5 표로는 major 다. 지운 채 minor 로
   내면 deprecation 정책(1 release 경고 → 다음 release 제거)을 어기고, major 로 올리면
   v0.8.0 → v2.0.0 **2년 보장을 스스로 끝낸다**. 셋째 길 — 한 발행 동안 되살려 정책을
   지키는 것 — 을 택했다.
2. **`ci_mypy` 를 읽던 소비자는 키를 잃는다.** 스키마 계약 밖이고 늘 `skipped` 인 칸이었지만,
   JSON 을 키로 읽던 스크립트는 `KeyError` 를 본다.
3. **`state.json` 의 `memory_entries` 형식이 바뀌었다** (`10c166cd`, v2). 전문 대신
   `{id, primary_abstraction, path}` 포인터만 싣는다 — 옛 전문 필드를 읽던 소비자는 그
   키를 잃는다. 저장소 안에서 이 필드를 읽는 코드는 **0** 이었고
   `MEMORY_ENTRIES_SCHEMA_VERSION = "2"` 로 형식이 선언된다. `state.json` 은 생성 산출물이며
   stable_guarantee §5.2 가 보장의 한계로 적는 영역이다.
4. **모르는 인자를 이제 거절한다** (`8ee16bdc`). 손수 파싱하던 커맨드 37개가 모르는 플래그를
   조용히 버리고 rc 0 을 내던 것을 rc 2 로 바꿨다. 오타 난 플래그로 부르던 호출은 이제
   실패한다 — 그 호출은 **요청과 다른 일을 하고 성공을 보고하고 있었다** (v1.11.0 준비에서
   `--version` 이 버려져 1.10.1 로 올라가고 직전 커밋이 amend 됐다).

## 1. 릴리스 요약

- 범위: `v1.11.0..` 발행 준비 직전까지 **45 commit**. 이 중 13건은 memory 기록이고 1건
  (`14f10cfc`)은 **v1.11.0 발행 마무리**가 태그 뒤에 착지한 것이라 실질은 **31 commit** 이다.
- 누적 smoke **296/296 PASS** (로컬 `--branch-context=all` = 296 × native/slash).
- 검사 **292 → 296** — 신설 6 (`check_cli_unknown_flags` · `check_mypy_ci_cross_verify_retired` ·
  `check_pre_push_gate` · `check_release_gate_evidence` · `check_session_context_budget` ·
  `check_validate_source_coverage`), 은퇴·개명 2 (`check_mypy_ci_cross_verify_v0_11_13` ·
  `check_release_ci_gate`).

## 2. 소비자에게 보이는 변화

### 2.1 발행 게이트의 근거가 로컬 게이트 통과 기록이다

`release --apply` 는 **HEAD sha 의 게이트 통과 기록**이 없으면 태그 생성 전에 멈춘다
(`534e3a8d`). 기록은 `run_all_checks.py --branch-context=all` 을 커밋 후 깨끗한 트리에서
필터 없이 돌려 exit 0 일 때만 `<git common dir>/gate_evidence/<sha>.json` 에 남는다.
`.githooks/pre-push` 가 같은 기록을 push 에도 요구한다 (`33e58fdd`, `core.hooksPath=.githooks`).

**로컬로 못 옮긴 축은 이제 아무도 재지 않는다** — Windows/macOS 소비자 설치 경로 ·
MCP Inspector 실동작 · 외부 URL 온라인 검증.

### 2.2 세션 시작 컨텍스트 예산 (ADR-029, M-013 → M-017)

세션 시작 때 읽는 문서가 계속 불어났다. 예산을 정본 모듈로 선언하고 출구를 만들었다.

- `common/context_budget.py` — 예산 정본. `wk refresh-state` 가 넘치면 출구 명령과 함께 경고 (`ec21152a`)
- `state.json` `memory_entries` v2 — 전문 대신 포인터 (`10c166cd`, 반대 근거 §0.1-3)
- `wk rollover-handoff-notes` — handoff §5 누적형 절을 `lessons.md` · `sessions/` 로 옮긴다 (`0292d421`)
- `CLAUDE.md` 운영 절 → `docs/LOCAL_GATE.md` (`e1ef118b`, 19.6KB → 11.3KB)
- 이 저장소 게이트가 예산 초과를 red 로 (`8b7119de`, 필독 195KB → 111KB)

### 2.3 `wk doctor` 가 더 많이 잰다

- **플러그인 MCP 가 실제로 띄우는 해석기**의 kit 출처·버전을 설치본과 대조한다 (`5631f059`, `mcp_interpreter` 절)
- **설치본이 정본보다 낮은 버전**이면 뒤처짐으로 따로 낸다 (`22653225`, `content_drift.behind`).
  발행 절차에 이 호스트의 채널 재적용이 `RELEASE.md` §2.8 로 들어갔다

### 2.4 모르는 인자를 거절한다

손수 파싱하던 커맨드 37개가 모르는 플래그에 rc 2 와 **받는 목록**을 낸다 (`8ee16bdc`).
`--help` 는 이제 부수효과 없이 도움말만 낸다 (예전에는 dry-run 을 실행했다).

### 2.5 대시보드

- Panel 1 `phase` 를 로드맵 정본에서 파생 — v0.15 에 멈춘 상수였다 (`6253791c`)
- 멀티에이전트 충돌 지표가 task ID 충돌을 센다, `session-start` warning 으로도 낸다 (`4c8cd252` · `dd9a004e`)
- telemetry 를 대시보드당 스냅샷 1회로 — Panel 3·8 hit_rate 경합 (`e5d2c6f4`)

### 2.6 게이트 처리량

병렬 구간 LPT 제출 + `--jobs auto` (`5b96ebb6`), release 계열 검사의 mypy 반복 제거
(`5e0d0043`, 44.2 → 28.3s), 러너·CLI 검사의 무거운 fixture·네트워크 제거
(`bf1417d5`, 46.9 → 12.3s).

## 3. Deprecation — v1.12.0 cycle

| Symbol | module | replacement | removal |
|---|---|---|---|
| `verify_required_ci` | `workflow_kit.tools.release_pipeline` | `release_pipeline.verify_gate_evidence` | v1.13.0 |
| `REQUIRED_CI_WORKFLOWS` | `workflow_kit.tools.release_pipeline` | (없음 — 필수 CI 가 없다) | v1.13.0 |

shim 은 **옛 질문에 새 근거로 답한다**. 조회할 CI 가 없으므로 늘 통과도 늘 차단도 거짓이다 —
`verify_required_ci` 는 `verify_gate_evidence` 의 판정을 그대로 따르고 옛 반환 키
(`ok` · `required` · `workflows` · `blocking` · `error`)를 유지한다. 쓰이지 않는 CI 입력
(`repo` · `runs` · `fetch_error`)은 `ignored_inputs` 에 이름을 남긴다. `REQUIRED_CI_WORKFLOWS`
는 **빈 tuple** 이다 — 옛 4종을 돌려주면 없는 워크플로를 필수라 말하게 된다.
정본: `core/v0_9_0_deprecation_policy_spec.md` §3.7.

## 4. 새 심볼 (순증)

- `release_pipeline.verify_gate_evidence` · `workflow_kit.common.gate_evidence`
- `workflow_kit.common.context_budget`
- `wk rollover-handoff-notes`

## 5. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- shim: `check_release_gate_evidence` case 10 · `check_v0_9_1_deprecation_contract` whitelist.
  되주입 3종(늘 통과 · 경고 제거 · 옛 4종 반환) 각각 red
- `wk release-status`: unreleased 45, 제안 2.0.0 → 소유자 결정 1.12.0

## 6. 알려진 한계 (감추지 않는다)

- **Windows 는 현재 미측정이다.** `TASK-2026-08-25-main-017`(MCP emit `python3`)은 코드 수리 후
  Windows 실측만 남아 blocked 다.
- **해석기·SDK 매트릭스는 게이트가 강제하지 않는다** — 발행 전 `--run-local` 이 유일한 수단이다.
- `behind` 판정의 기준은 **그 호스트의 kit 정본**이다. GitHub Releases 최신 태그를 조회하지 않는다.
