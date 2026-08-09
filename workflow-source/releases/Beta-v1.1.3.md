# Beta v1.1.3 (2026-08-09)

> **상태: 릴리스 준비.** `tool_version = v1.1.3-beta`, tag `v1.1.3-beta`.
> **patch release** — v1.1.2 발행 *도중과 직후* 에 드러난 것들을 닫는다.
> 신규 기능은 telemetry 윈도 지표 하나이고, 나머지는 **도구·검사·문서가 실제와
> 어긋나 있던 자리** 를 맞춘 것이다.
>
> PyPI 배포는 정책상 미실행 (릴리스 채널 = GitHub Releases).

## 0. 릴리스 판정

v1.1.2 는 "가려져 있던 사실의 노출" 이었다. 본 릴리스는 그 노출이 **릴리스 절차
자체까지 이어진** 결과다 — 발행 도중에 릴리스 도구 결함 2건이 터졌고, 발행 직후에
Phase 13 로드맵 문서가 코드와 대조된 적이 없다는 것이 드러났다.

이번 사이클에서 확인된 것:

- **릴리스 도구는 릴리스 때만 실행되므로 평소 검사에 안 걸린다.** `release-bump` 의
  post-step 과 `release-verify` 가 각각 깨져 있었는데
  `check_release_pipeline_lib` 9 case 는 green 이었다.
- **`phase_13_followup.md` 의 P0-2 와 P1 3건이 전부 실제와 달랐다.** 대부분 "이미
  되어 있었다" 였다 — 문서가 로드맵을 적어 두고 실행 상태를 따라오지 못했다.
- **검사가 하드코딩에 갇히면 새 사실을 못 본다.** harness SSOT 검사는 10개 고정
  목록과만 비교해, `grok-build` / `mavis` 가 늘어나는 동안 6/6 PASS 였다.
- 반대 사례도 하나 있었다 — `check_smoke_trend_cross` 는 **검사가 맞았고 이쪽이
  오독** 했다. 차이는 *git 이력을 봤는가* 였다 (§2.7).

## 1. 릴리스 요약

- **릴리스 도구 결함 2건 close** + 릴리스 없이 잡히는 회귀 검사 신설.
- **Phase 13 P0-2 / P1 3건 close** — 전부 문서 정정이 본체였다.
- **telemetry 윈도 지표** (신규) — AC2 가 *지속적 사용* 을 재게 됐다.
- **skill 14/14 stable** — `memory-index-query` 승격으로 잔여 beta 0.
- **릴리스 절차에 노트 누적 수치 검증 자리** 신설.
- breaking change: ❌ (모든 추가는 additive)

## 2. deliverable

### 2.1 릴리스 도구 결함 2건 (TASK-009)

v1.1.2 **발행 도중** 터졌다.

| 결함 | 원인 |
|---|---|
| `release-bump` post-step 의 `git add` 실패 | `REPO_ROOT` 가 이름과 달리 `workflow-source/` 인데 `git status --porcelain` 은 *저장소 루트* 기준 경로를 준다 → `workflow-source/workflow-source/…` |
| `release-verify` 의 `AttributeError: 'dry_run'` | `_make_args()` 가 `dry_run` 을 안 채웠는데 `cmd_verify` 는 그걸 읽는다 |

`_git_toplevel()` 을 신설해 git 경로를 다루는 세 자리(status / add / amend)가 그것을
cwd 로 쓰게 했다. `REPO_ROOT` 이름은 그대로 두고 함정을 주석으로 남겼다 — 다른
용도로는 그 값이 맞아서 이름만 고치면 변경면이 커진다.

**`check_release_wrapper_args.py` (10 case, 신규)** 가 이 부류를 릴리스 없이 잡는다:
`_make_args` ↔ 각 `cmd_*` 의 `args.X` 참조를 **AST 로 대조**하고, dirty path 를 두
cwd 에서 `git add --dry-run` 해 **버그 자체를 회귀로 고정** 한다 (toplevel 성공 /
`workflow-source/` 실패).

### 2.2 Phase 13 P0-2 — telemetry source 다양성 (TASK-010)

문서가 두 군데 틀려 있었다:

- "현 1 source: **dispatcher**" → 실제 1 source 는 **`session-start`** (132 calls).
  `dispatcher` 는 `--command=memory-index-query` 호출 시에만 쌓이는데 아무도 부른
  적이 없었다.
- action item "3 skill 의 retrieval 호출 **활성화** 필요" → **이미 v0.15.21+ 에서
  세 skill 모두 자동 활성** 이었다.

남아 있던 것은 wiring 이 아니라 **그 skill 들이 실행된 적이 없다는 사실** 이었고,
확인 수단도 코드 읽기가 아니라 **한 번 돌려보는 것** 이었다. 세 경로를 실제 용도로
한 번씩 돌리자 즉시 4 source 가 됐다.

### 2.3 telemetry 윈도 지표 (TASK-011, 신규 기능)

전체 기간 `by_source` 는 **각 경로를 한 번씩만 돌려도** 4 source 가 찬다 —
위 P0-2 가 실제로 그렇게 충족됐다. `summarize_telemetry(window_days=30)` 이
최근 N일 지표를 함께 낸다 (`window_source_count` / `window_hit_rate` /
`window_by_source`). 방치하면 윈도 밖으로 빠져나가므로 값이 떨어진다.

AC2 의 실질 지표를 `window_source_count` 로 바꿨다. `check_telemetry_window.py`
(8 case) 의 핵심은 **case 4** — *오래된 4 source + 최근 1 source* 로
"전체는 4, 윈도는 1" 을 확인한다.

### 2.4 Phase 13 P1 3건 (TASK-012)

셋 다 실제와 달랐다:

| 항목 | 문서 | 실제 |
|---|---|---|
| P1-1 changelog-gen | "pre-step **부재**" | v0.15.21+ 에 이미 있음 |
| P1-2 automated-repro-scaffold | "stable 승격 필요" | **이미 stable** (v0.11.24) |
| P1-3 git-conflict-resolver | "alpha → **beta**" | **이미 stable** — beta 를 건너뜀 |

P1-1 에서 실제로 남아 있던 것은 (a) 최근 3 release 가 `cmd_release` 를 타지 않아
CHANGELOG 가 v0.15.21 에서 멈춘 것, (b) `RELEASE_RE` 가 `(v3.0)` / `(v3.0.1)` 을
release 로 오인해 **`[3.0.1]` 이 최신 자리에** 앉은 것이었다. 후자는
`NON_RELEASE_VERSIONS` 선언된 예외로 제외했다 (git tag 대조는 불가 — 0.15.x 대
다수가 tag 없이 릴리스돼 진짜 release 를 대량으로 지운다).

### 2.5 문서 전반 실측 대조 + harness 정의 (TASK-013)

정합 5건 / 정정 3건. harness 는 숫자가 아니라 **정의** 가 문제였다:

`maturity_matrix.harnesses.supported` 는 *overlay 를 배포하는* harness 목록이고
파일시스템의 `harnesses/<name>/` 과 1:1 이다. `HARNESS_SPECS` 13 개 중 둘은 그
정의 밖이다 — `custom` (어댑터 템플릿) 과 `mavis` (**project-local 산출물 0**,
글로벌 `mcp.json` merge 만). 그래서 11 이 맞다.

검사도 고쳤다. `test_case_5_harness_supported_ssot_alignment` 는 이름과 달리
**10개 하드코딩 목록** 과만 비교해 새 harness 를 몰랐다. 기대값을
`HARNESS_SPECS − NON_OVERLAY_HARNESSES` 로 정본에서 유도하게 했고, 제외 항목에
이유가 없으면 그 자체를 실패로 본다.

### 2.6 memory-index-query beta → stable (TASK-014)

`skill_beta_criteria.md` §3.1 6 조건 중 2 미충족이었다.

- **error_code 3종** (`invalid_query_tokens` / `missing_required_document` /
  `memory_index_query_runtime_error`) — 이전에는 stderr 문자열 + rc 2 뿐이라
  caller 가 실패 *종류* 를 구분할 수 없었다. `ErrorOutput` 을 **stdout 에** emit 한다.
- **SKILL.md 실행 예시 절**.

**skill stage 14 stable / 0 beta.**

### 2.7 smoke_trend 오독 정정 (TASK-015)

`case_2_ratio_sanity` 가 릴리스 후 smoke 추가 시 red 나는 것을 "정상적인 성장을
결함으로 본다" 고 읽고 판정을 느슨하게 바꿨다가 **되돌렸다.**

그 수치는 릴리스 시점 스냅샷이 아니라 **살아있는 지표** 다. smoke 가 늘면 최신
note 의 그 줄을 함께 갱신해 온 관행이 있다 (커밋 메시지 `(전량 205/205)`,
`Beta-v1.0.0.md` 는 199 → … → 234). 태그 시점 실측으로 확인:

| 태그 | 파일 | 노트 |
|---|---|---|
| `v1.0.0-beta` | 199 | 199/199 ✅ |
| `v1.1.0-beta` | 251 | **표기 없음** ❌ |
| `v1.1.2-beta` | 257 | 257/257 ✅ |

red 구간은 v1.1.0 / v1.1.1 이 **표기를 빠뜨린** 탓이었다. 검사가 맞았다.

### 2.8 릴리스 절차에 누적 수치 검증 자리 (TASK-016)

위 §2.7 이 "검사가 아니라 **절차** 문제" 로 짚은 자리. `cmd_release` 에 **step 3.4**
를 넣어 note 부재 / 표기 부재 / 수치 불일치를 각각 잡고 조치를 안내한다
(`--skip-smoke-count-check` escape hatch).

**자동으로 채우지 않는다** — 그 줄은 *전량 PASS 했다* 는 **주장** 이고, 실제로
전량을 돌린 사람만 할 수 있는 말이다. 회귀 case 9b 가 그 원칙을 고정한다
(함수가 파일을 쓰면 red).

## 3. smoke 회귀

누적 smoke test **259/259 PASS** (2026-08-09, `dev,release,mcp-sdk` extra 를 깐
격리 venv, `--tmp-dir` 실디스크). 이 줄은 릴리스 시점 스냅샷이 아니라 *최신 전량
결과* 를 반영하는 살아있는 지표다 (§2.7 / §2.8).

신규 smoke:

| smoke | case | 상태 |
|---|---|---|
| `check_release_wrapper_args.py` | 10 | ✅ |
| `check_telemetry_window.py` | 8 | ✅ |

기존 smoke 갱신: `check_release_pipeline_changelog_gen`(+1, 오탐 예외) /
`check_memory_index`(+1, error_code) / `check_drift_prevention_v0_11_23`(정본 유도) /
`check_smoke_trend_cross_v0_15_5`(관행 기록) / `check_release_pipeline_lib`(dist 전제).

## 4. 1차 출처 (cross-ref)

- `core/phase_13_followup.md` — AC2 / AC5 / P0-2 / P1 (전면 실측 대조)
- `core/skill_beta_criteria.md` — 최종 batch (14/14 stable)
- `tools/release_pipeline.py` — `_git_toplevel` / `NON_RELEASE_VERSIONS` /
  `verify_release_note_smoke_count`
- `workflow_kit/common/state/memory_index.py` — 윈도 지표
- `ai-workflow/memory/active/main/sessions/cli_dispatcher_and_rotation_2026-08-09.md`

## 5. 후속

- **branch protection** — 저장소 소유자 결정 (v1.1.2 의 도구는 판정만 한다).
- **`v1.1.0` / `v1.1.1` 노트의 누적 표기** — 사후에 넣으면 *그때* 의 전량 결과가
  아니다. 파서는 최신 노트만 보므로 동작 지장은 없고, v1.1.3 부터는 절차(§2.8)가
  막는다. 넣을지는 별도 판단.
- **registry HTTP server 실환경 검증** — loopback 왕복만 실측했다.
- **title drift 임계 0.6** — 운영 데이터로 고른 값이 아니다.

## 6. compatibility

- breaking change: ❌
- `summarize_telemetry` 의 `window_*` 필드 — additive (전체 기간 필드 불변)
- `MemoryIndexQueryOutput` — 변경 없음. 실패 시 `ErrorOutput` 을 stdout 에 내보내는
  것이 추가됐다 (이전에는 stderr + rc 2 뿐이라 **읽을 것이 없었다**).
- `cmd_release` 에 step 3.4 추가 — 기존 릴리스 절차에 **검증 단계가 하나 늘었다**.
  노트에 누적 수치가 없으면 막힌다 (`--skip-smoke-count-check` 로 우회 가능).
- MCP server 변경 ❌
