# Beta v1.8.1 (2026-09-01)

> **상태: 릴리스 준비.** package `1.8.1`, runtime `__version__ = 1.8.1`, tag `v1.8.1`.
> **patch release** — v1.8.0 이 소비자에게 깨진 채 나간 것을 고치고, 그 결함족을
> 게이트에서 닫는다.
>
> 등급 근거 (§1.5): 공개 API 시그니처 변경 0 · 진입점 제거 0 · 산출물 형식 변경 0.
> 수리 2건뿐이라 patch 다. 다만 **하나는 v1.8.0 소비자에게 실제 고장이었다** (§2.1).

## 0. 릴리스 판정

이 사이클의 주제는 **"손으로 유지하는 목록"** 이다. v1.8.0 이 *침묵*을 걷었다면
v1.8.1 은 **사람의 기억에 의존하던 두 자리**를 걷는다. 둘 다 같은 모양이었다 —
선언과 사실이 갈라져도 아무도 red 를 내지 않고, 저장소에서는 영원히 green 이다.

**이 릴리스에는 반드시 발행해야 할 이유가 있다.** §2.1 의 결함은 v1.8.0 wheel 에
실려 나갔고, 그것을 설치한 소비자에게 `workflow_kit.cli` 가 **없다**. 저장소에서는
디렉터리가 실재하므로 로컬 검사로는 영원히 보이지 않는다.

## 1. 릴리스 요약

- 범위: `v1.8.0..HEAD` (4 commit). 이 중 1건(`236a6aa9`)은 **v1.8.0 발행 마무리**가
  태그 뒤에 착지한 것이라 실질 내용은 3 commit 이다.
- 누적 smoke **278/278 PASS** (전량 2축 · case 합계 556, FAIL 0, 좁은 선언 0),
  mypy strict 0 errors
- 검사 신설 1종(`check_doc_stamp_rule`) + `check_deployed_layout` case 5 추가
  (총 277 파일)
- 지원 하네스 12 (변동 없음), 공개 API 25 (변동 없음), MCP 표면 13 (변동 없음)

## 2. 소비자 가시 변경

### 2.1 fix(packaging) — `workflow_kit.cli` 가 wheel 에 실린다 (`12b9f311`)

**v1.8.0 이하를 wheel 로 설치한 소비자에게는 `workflow_kit.cli` 가 없었다.**
`python -m workflow_kit.cli.doctor` (7 baseline compliance) 가
`ModuleNotFoundError` 로 죽는다. 저장소 체크아웃에는 그 디렉터리가 실재하므로
로컬 검사·CI 어디에서도 보이지 않았다.

원인은 pyproject `[tool.setuptools] packages` **손 목록에서 빠진 것**이다.
(`__init__.py` 부재가 원인이라는 초기 추정은 반증됐다 — 형제 `workflow_kit.harness`
도 `__init__.py` 없이 선언만으로 정상 배포된다.)

**세 번째 발생이다**: `common.{state,contracts,schemas}` (v0.5.7.1 hotfix) ·
`tools` (v1.1.7) · `cli` (v1.8.0). 세 번 다 사람이 목록 갱신을 잊은 것이라,
사람에게 다시 부탁하는 대신 **디스크와 대조**한다.

- `tests/check_deployed_layout.py` **case 5** — 디스크의 하위 패키지와
  `packages` 선언을 **양방향** 대조한다 (미선언 → red, 실재하지 않는 선언 → red).
  wheel 을 안 만들므로 매 게이트마다 돈다.
- `check_packaging` 의 `REQUIRED_IMPORTS` 가 손 목록이 아니라 **소스 트리 파생**이다.
  커버리지 10 → 15 — `harness` · `server` · `common.modes` 는 그때까지 **한 번도
  검증된 적이 없었다**. 기준이 소스 트리인 이유: wheel 에서 파생하면 "wheel 이
  담은 것을 wheel 이 담았다" 는 동어반복이 된다.

같은 조사에서 **검증 자신을 무력화하던 침묵 둘**을 함께 걷었다:

- `check_packaging` 의 자식 프로세스가 부모 환경을 물려받아, 저장소 관례인
  `PYTHONPATH=workflow-source` 로 부르면 격리 venv 가 **소스 트리를 본다**. 게다가
  `standard_ai_workflow.egg-info` 때문에 pip 이 `already installed` 로 **wheel 설치를
  통째 건너뛴다**. 실측: `cli` 가 빠진 wheel 에 이전 판 검사가 `result: PASS`.
- pyproject 기반 설정은 `include_package_data` 가 **기본 True** 라, 이전 빌드가 남긴
  `build/` · `egg-info/SOURCES.txt` 가 있으면 **지금 선언되지 않은 파일까지 wheel 에
  실린다**. 로컬 산출물과 CI 산출물이 갈리는 자리다 —
  `wk release-pipeline dist --apply` 가 빌드 전에 둘을 지운다.

### 2.2 fix(checks) — 문서 스탬프 기대값이 리터럴에서 git 파생으로 (`09a9df21`)

소비자 표면 변화는 없다. 저장소 유지보수 결함이다.

`check_code_index_v0_15_17` · `check_document_index_v0_15_16` 이 인덱스 문서의
`최종 수정일` 기대값을 **리터럴**로 들고 있어, 발행 post-step(`doc-headers-update`)이
스탬프를 올릴 때마다 같은 커밋에서 손으로 맞춰야 했다 (v1.7.0 `4d7a78da` ·
v1.8.0 — **같은 자리 두 번**).

**'문서에서 파생' 은 채택하지 않았다** — 문서를 읽어 기대값으로 삼으면 동어반복이라
아무것도 못 잡는다 (§2.1 의 "wheel 에서 파생하면 안 된다" 와 같은 이유). 대신
지키려던 규약을 그대로 옮겨 **git 에서** 판정한다: `스탬프 >= 그 문서의 마지막
내용 변경일`. 워킹 트리가 더러우면 기준일은 오늘(UTC)·유예 0, 깨끗하면 마지막
커밋일(UTC)·유예 1일(스탬프를 찍은 날과 커밋이 착지한 날이 UTC 자정을 사이에 두고
갈리는 경계만 흡수).

정본은 `tests/_doc_stamp.py`, 규칙 자체는 신설 `check_doc_stamp_rule.py` **6 cases**
가 **날짜를 우리가 정하는 격리 git 저장소**에서 고정한다. 그 검사가 작성 중 결함
둘을 잡았다 — 둘 다 red 가 아니라 **green 으로 새는** 것이라 본 저장소에서는
원리적으로 안 보인다:

- `--date=format-local:` 이 실행 환경 TZ 를 쓰는데 TZ 를 고정하지 않아 **UTC 를
  자칭하며 로컬(KST) 날짜를 읽었다** — 없는 하루 어긋남을 만들었다.
- 자정 경계용 1일 유예를 **더러운 워킹 트리에도** 적용해, "어제 스탬프를 단 채 오늘
  내용을 고치는 것" 이 통과했다 — 이 판정이 잡으려는 바로 그 경우다.

## 3. 업그레이드

`v1.8.0` 에서 올라오는 데 필요한 조치는 **없다**. 공개 API · 진입점 · 산출물 형식이
모두 그대로다.

다만 v1.8.0 이하를 설치해 두고 `python -m workflow_kit.cli.doctor` 를 쓰던 경우,
그 명령은 **원래 동작하지 않았고** 이 버전부터 동작한다. 재설치가 필요하다:

```bash
pip install --force-reinstall standard_ai_workflow-1.8.1-py3-none-any.whl
# 또는 uv tool
uv tool install --force <wheel 경로>
```

설치본이 저장소 소스와 갈라졌는지는 `wk doctor` 의 `kit 사본` 줄이 말해 준다.

## 4. 검증

- 전량 2축 **277/277 ×2 PASS** (`--branch-context=all`, RUNNER_EXIT=0, 좁은 선언 0)
- mypy strict **0 errors**
- `check_self_application` 8/8 · `check_doc_stamp_rule` 6/6
- 되주입 red 실증 6건:
  - pyproject 에서 `workflow_kit.cli` 선언 제거 → `check_deployed_layout` case_5 FAIL
  - 잔재를 지운 트리에서 만든 결함 wheel → `check_packaging` 이
    `missing [workflow_kit.cli, workflow_kit.cli.doctor]` 로 FAIL
  - 같은 결함 wheel 에 이전 판 `check_packaging` 은 `result: PASS` (침묵 실증)
  - 인덱스 문서에 낡은 스탬프 + 내용 수정 → 인덱스 검사 2종 FAIL
  - `_doc_stamp` 의 TZ 고정 제거 → `check_doc_stamp_rule` case_2 FAIL
  - 유예를 더러운 트리에도 적용 → `check_doc_stamp_rule` case_4 FAIL
- 완료 기준 실측: 격리 venv 에 수리 wheel 설치 후 **임의 cwd** 에서
  `python -m workflow_kit.cli.doctor --json` rc=0

## 5. Commit

| Hash | Subject |
|---|---|
| `09a9df21` | fix(checks): 문서 스탬프 기대값을 리터럴에서 git 파생으로 (main-002) |
| `12b9f311` | fix(packaging): workflow_kit.cli 를 wheel 에 싣고, 손 목록을 디스크 대조로 대체 (main-001) |
| `bfd25c15` | chore(memory): 전역 wk 1.8.0 재설치 + 새 탐침이 패키징 결함 적발 (main-001 등록) |
| `236a6aa9` | release(v1.8.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + post-step 정합 (main-005) |

## 6. Reference

- 이전 release note: `Beta-v1.8.0.md`
- task SSOT: `TASK-2026-09-01-main-001` · `TASK-2026-09-01-main-002`
- 후속 (미착수): `TASK-2026-09-01-main-003` — `--validation-result` 없는 `done` 의
  조용한 강등이 handoff 의 완료 기록을 되돌린다

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-09-01T00:32:24Z)_

- total wiki pages: **95**
- total memory entries: **15**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
