# 로컬 게이트 운영

- 문서 목적: 이 저장소의 개발 환경 · 검사 실행 단계 · push 게이트 · 매트릭스 축의 **근거와 실측**을 보존한다. `CLAUDE.md` 에는 명령과 규칙 한 줄씩만 남는다.
- 범위: `.venv` 개발 환경, 전량/선택 실행, 게이트 통과 기록과 pre-push hook, SDK·브랜치·해석기 매트릭스, 경고 게이트
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-09-28
- 관련 문서: [`../CLAUDE.md`](../CLAUDE.md), [`RELEASE.md`](./RELEASE.md), [ADR-029](../ai-workflow/wiki/decisions/adr-029-session-context-budget.md)

> **이관 기록** (ADR-029, TASK-2026-09-28-main-013). 아래 절은 `CLAUDE.md` 의
> `## 프로젝트 실행 기본값` 절을 **바이트 그대로** 옮긴 것이다. `CLAUDE.md` 는 대화마다
> 실려 필독 중 바이트당 비용이 가장 크고, 근거 산문은 명령을 쓸 때만 필요하다.
> 수치는 각 문단이 적은 실측일 기준이다 — 예: "시간을 쓰는 8개" 는 2026-09-23 기준이고,
> 그 뒤 main-007·008 이 release 계열·러너·CLI 검사를 크게 줄였다
> ([처리량 검토](./planning/local-gate-throughput-review-2026-09.md) §9·§10).

## 프로젝트 실행 기본값

**개발 환경은 저장소 `.venv` 다.** 시스템 python3(homebrew)는 PEP 668
(`externally-managed-environment`)로 pip install 을 거부하고, 설치가 됐더라도 dev
의존성(mypy/jsonschema/mcp)이 없어 **전량 검사가 의존성 부재로 무더기 오탐**을 낸다
(2026-08-14 실측: homebrew python3 로 전량 2축을 돌려 9건 red — 전부 미설치였고 코드
결함은 0건). 아래 명령은 활성화 없이 그대로 복사해 실행 가능한 형태다.
기존 `.venv` 가 uv 로 만들어져 pip 이 없으면(`No module named pip`)
`.venv/bin/python3 -m ensurepip --upgrade` 한 번으로 채운다 (2026-08-14 이 호스트 실측).

- **install**: `python3 -m venv .venv && .venv/bin/python3 -m pip install -r requirements.txt -r requirements-dev.txt && .venv/bin/python3 -m pip install -e "./workflow-source[dev,release,mcp-sdk]"`
- **run**: `PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.workflow_kit_cli --command=dashboard --format=json`
- **quick test**: `.venv/bin/python3 workflow-source/tests/run_all_checks.py --filter=<이름조각> --tmp-dir=<실디스크경로>`
- **isolated test**: `.venv/bin/python3 workflow-source/tests/run_all_checks.py --tmp-dir=<실디스크경로>` (격리 venv 에서 전량)

> 전량 검사는 **기본이 병렬**이다 (v1.1.7, `--jobs auto`). 345s → 85s 로 줄었다.
> 재현이 필요하거나 실패를 분리해 보고 싶을 때만 `--jobs 1` 로 순차 실행한다.
> 저장소 전역 상태를 관찰하는 check (`REQUIRES_QUIET_REPO = True` 를 선언한 것들)
> 는 병렬 구간이 끝난 뒤 **정숙 구간**에서 직렬로 돈다 — 새로 그런 check 를 만들면
> 그 선언을 파일 안에 넣어야 한다. 안 넣으면 병렬에서 오탐이 난다.
> 단독 실행이 ~25s 를 넘는 무거운 check 는 `CHECK_TIMEOUT_S = 150` 을 파일 안에
> 선언한다 (v1.1.7+) — 기본 60s 상한은 병렬 부하에서 2배로 늘어진 실행을 죽인다.
> 선언은 CLI `--timeout` 과 max 로 합쳐져 상한을 **늘릴 수만** 있다.
> 전량 runner 는 **워킹 트리 배타 락**을 잡는다 (v1.1.7+, `.git/run_all_checks.lock`).
> 다른 runner 가 돌고 있으면 보유자 정보를 찍고 즉시 실패한다 — 동시 실행된 전량의
> 결과는 PASS 도 FAIL 도 근거가 못 된다. 같은 워킹 트리에서 두 에이전트가 전량을
> 돌려야 하면 락을 우회(`--no-lock`)하지 말고 **worktree 를 분리**한다.
- **smoke check**: `.venv/bin/python3 workflow-source/tests/check_self_application.py`

### 전량은 게이트지 확인 수단이 아니다 (2026-08-14 실측)

**편집할 때마다 전량을 돌리지 않는다.** 축당 벽시계 ~195s 이고 2축이면 ~6.5분이라,
반복 편집 중에 돌리면 그것만으로 세션이 간다 (2026-08-14 세션: 전량 2축 5회 =
약 33분 중 게이트로서 의미 있던 것은 push 직전 1회뿐).

| 단계 | 명령 | 언제 |
|---|---|---|
| 편집 중 | `run_all_checks.py --filter=<이름조각>` | 방금 건드린 것과 그 이웃만. 초 단위로 끝난다 |
| 커밋 전 | `run_all_checks.py --changed` + `check_self_application.py` | 관련 검사를 사람이 고르지 않는다 — 검사의 `WATCHES` 선언이 고른다 (v1.7.0, meta-watch 가 선언의 좁음을 게이트에서 잡는다). `--filter` 는 여전히 편집 루프용 |
| **push 직전 1회** | 커밋 후 깨끗한 트리에서 `run_all_checks.py --branch-context=all` | **이것이 게이트다.** 여기만 2축 전량. 통과하면 HEAD sha 의 **게이트 통과 기록**이 남고 `release --apply` 와 **pre-push hook** 이 그것을 요구한다 |
| 발행 전 / 해당 코드를 건드렸을 때 | `interpreter_matrix --run-local` · `sdk_matrix --run-local` | 아래 두 절. CI 가 덮던 축이라 이제 로컬 말고는 아무도 안 돈다 |

> **기록 없는 커밋은 push 되지 않는다** (TASK-2026-09-23-main-009). `.githooks/pre-push` 가
> push 하는 각 ref 의 sha 에 게이트 통과 기록(컨텍스트 전부)을 요구한다. 새 클론·호스트에서는
> 한 번 `git config core.hooksPath .githooks` 로 켠다. 게이트를 돈 **뒤** 편집하면 그 커밋은
> 기록이 없어 막힌다 — 86차 `f4504818` 이 정확히 그렇게 게이트 밖에서 push 됐다. 우회는
> `git push --no-verify` (그 push 는 게이트 근거가 없다).

> **GitHub Actions 테스트 workflow 는 없다** (2026-09-23 소유자 결정, TASK-2026-09-23-main-022).
> 느렸고, 어차피 push 전에 로컬 게이트를 돈다. 남은 workflow 는 `mkdocs`(문서 배포)와
> `consumer-metrics-digest`(주간 집계)뿐이다. **로컬로 옮기지 못한 축**이 셋 있다 —
> Windows/macOS 소비자 설치 경로(`os-matrix`), MCP Inspector 실동작(`mcp-inspector`,
> Node 필요), 외부 URL 온라인 검증(`okf-validate`). 이 셋은 지금 아무도 재지 않는다.

> 게이트의 **조건부 1축 생략은 검토 후 기각**했다 (TASK-2026-08-14-main-004, 재론 방지).
> '민감 경로' 판정이 건전하게 성립하지 않는다 — 15연속 CI red 의 결함은 kit 코드가
> 아니라 **검사 자신**에 있었고, 이 저장소의 push 는 memory 갱신을 실어 거의 항상
> 브랜치 컨텍스트에 민감하다. 절감은 push 당 ~106s, 오판 1회의 실측 비용은 10일이었다.
> 한 축만 볼 일이 있으면 `--branch-context=slash` 를 **명시적으로** 지정한다.

**시간을 쓰는 것은 개수가 아니라 8개다** (1축 실측: CPU 819s / 255 checks, 벽시계
196s, 160개는 1초 미만): `wiki_score` 68s(병렬 구간 임계경로) · `release_summary` 62s ·
`release_status_auto_bump` 57s · `release_status` 48s · `release_pipeline_lib` 44s ·
`mypy_config_actually_loaded` 41s · `no_repo_write` 39s(정숙 구간 61s 의 64%) ·
`branch_context_matrix` 45s(2026-09-23 실측 12회 42.8~46.2s — 기본 60s 상한에
> 닿아 `CHECK_TIMEOUT_S = 150` 을 선언했다). `--filter` 로 좁힐 때 이 이름들을 피하면 대개 즉시 끝난다.


### SDK 매트릭스는 push 전에 로컬에서 돌린다

```bash
PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.common.sdk_matrix --run-local
```

`mcp` SDK 를 쓰는 코드를 건드렸으면 **반드시** 이걸 먼저 돌린다. 개발 venv 는
`requirements-dev.txt` 가 깐 하한(1.27.0) 하나뿐이라, 2.x 에서만 갈라지는 코드가
**로컬 게이트를 통과하고도 2.x 에서 깨진다.** 실제로 2026-08-05 에
`CallToolResult.isError`(1.x 이름, 2.0.0 은 `is_error`) 때문에 그렇게 됐다 — 그때는
CI 의 `mcp-sdk-matrix` 가 잡았지만 **이제 CI 가 없으니 이 명령이 유일한 수단이다.**

버전 목록은 `workflow_kit/common/sdk_matrix.py` 의 `PINNED_VERSIONS` 가 정본이다.
venv 는 `.venv-sdk-matrix/` 에 캐시되므로 두 번째부터 빠르다.

### 브랜치 매트릭스도 push 전에 로컬에서 돌린다

```bash
.venv/bin/python3 workflow-source/tests/run_all_checks.py --branch-context=all --tmp-dir=<실디스크경로>
```

게이트는 전량을 **두 브랜치 컨텍스트**로 돌린다 (`native` / `slash`).
`ai-workflow/memory/active/<branch>/` 는 브랜치 이름으로 경로가 갈리고, 슬래시가 든
브랜치는 중첩 디렉터리가 되며 **그 브랜치의 `state.json` 은 존재하지 않는다** —
main 에서 재면 그 차이가 전부 0이다.

무인자 `run_all_checks.py` 는 `native` 하나만 밟는다 — 그래서 게이트 통과 기록은
`--branch-context=all` 로 돈 실행만 남기고, 발행 게이트는 기록에 컨텍스트가 전부 있는지
본다. 한 축만 밟은 green 이 무엇을 놓치는지는 2026-08-10 에 겪었다: 검사 하나가
브랜치의 `state.json` 존재를 전제해 `slash` 셀에서만 red 였고, **15연속 red 인
동안 로컬은 계속 green 이었으며 handoff 는 내내 "전량 검사 green" 을 기록했다.**
열흘 가까이 걸린 이유는 결함이 어려워서가 아니라 로컬에 그 축이 없어서였다.

컨텍스트 목록은 `workflow_kit/common/branch_matrix.py` 의 `BRANCH_CONTEXTS` 가
정본이다. 한 축만 볼 때는
`--branch-context=slash` 로 줄인다.

### 저장소 코드가 낸 Python 경고는 게이트 red 다

`run_all_checks.py` 가 각 검사의 stdout+stderr 에서 Python 경고를 뽑아 **출처별로**
가른다. 저장소 코드가 낸 것(과 `<unknown>` — 문자열 compile 산물)은 검사 자신이
exit 0 이어도 게이트를 red 로 만들고, 서드파티는 보고만 한다.

이 축은 해석기 매트릭스가 종료 코드만 보던 구멍을 메운다 — 3.12+ 에서만 나는
`SyntaxWarning` 을 CI(3.11)가 통째로 못 보고 있었다. 전수 census(288검사 ×
2해석기)에서 갈린 2건은 **전부 서드파티**였고 원인도 해석기가 아니라 venv 의
의존성 해석 차이라, '셀 간 출력 차이' 대신 **출처**로 가른다.

deprecation 경로를 의도적으로 부를 때는 `check_warnings.call_deprecated` 를 쓴다
(삼키되 경고가 났는지 단언한다). 정본은
`workflow_kit/common/check_warnings.py`, 판정은 `check_warning_gate.py`.

**다만 실행 출력에서 줍는 것만으로는 부족하다** (2026-09-21, main-008). `SyntaxWarning`
류는 *컴파일 시점* 신호라 `.pyc` 가 유효하면 아예 나지 않는다 — 소스를 그대로 둔 채
1차 `exit 1` / 2차 `exit 0` 이 실측됐다. **고친 것 없이 재실행만으로 green** 이 되는
게이트였다. 또 runner 부모가 낸 경고는 수집 지점이 서브프로세스뿐이라 아무도 안 봤다
(kit 모듈 44/196 이 그 경로로 컴파일된다).

그래서 축이 둘이다. `check_source_compile_warnings` 가 저장소 Python 소스 **전수**
(566개, `python_floor.iter_sources` 파생 — git 추적 집합과 대조해 좁아지면 red)를
메모리에서 `compile()` 해 캐시와 무관하게 판정하고, runner 는 부모 프로세스 경고를
`PARENT_WARNINGS` 로 같은 출처 규율에 태운다.

### 해석기 매트릭스 — 발행 전에 로컬에서 돌린다

```bash
PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.common.interpreter_matrix --run-local
```

`--branch-context=all` 게이트는 당신이 가진 해석기 **하나로만** 돈다. 해석기 목록의
정본은 `workflow_kit/common/interpreter_matrix.py` 의 `GATE_INTERPRETERS` 이고, 위
명령이 선언된 해석기마다 전량을 돈다 (venv 는 `.venv-interpreter-matrix/<버전>` 에
캐시). 예전에는 CI 가 브랜치 2 × 해석기 2 = 4셀로 덮었지만 **CI 폐지(2026-09-23) 뒤로는
이 명령 말고는 아무도 이 축을 안 돈다.** 게이트마다 돌리면 전량이 해석기 수만큼 늘어
push 당 비용이 배가 되므로 **발행 전 1회 + 해석기에 민감한 코드(문법·경고·stdlib)를
건드렸을 때**로 정했다. 발행 게이트가 이것을 강제하지는 않는다 — 공백으로 안다.
한 버전만 볼 때는 `--only 3.11 --filter=<이름조각>`.

착수 시점 실측(2026-09-21)이 이 축을 정당화한다. 전량을 두 해석기로 대조하면
287/287 × 2 green 인데 **출력이 갈린 검사가 8건**이었고, 그중 다섯이 한 신호였다 —
3.12+ 에서만 나는 `SyntaxWarning: invalid escape sequence` 를 **3.13 만 보고
3.11(CI)은 완전히 침묵**했다. 반대 방향도 이미 겪었다 (81차: 로컬 3.13 green /
CI 3.11 red). 더 고약했던 것은 **3.13 커버리지가 선언이 아니라 우연**이었다는 점이다 —
`.venv` 를 3.11 로 다시 만들면 조용히 사라지고 아무 검사도 실패하지 않는다.

> `--tmp-dir` 를 실디스크 경로로 주는 이유: `TMPDIR` 가 tmpfs(RAM) 이면 temp 누수가
> 곧 OOM 이 된다.
