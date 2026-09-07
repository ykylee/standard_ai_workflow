# Beta v1.9.3 (2026-09-07)

> **상태: 릴리스 준비.** package `1.9.3`, runtime `__version__ = 1.9.3`, tag `v1.9.3`.
> **patch release** — **소비자 배포처에서만 나던 모순**의 뿌리를 닫는다.
>
> 등급 근거 (§1.5): 공개 API 시그니처 변경 0 (기존 함수에 기본값 있는 keyword
> 인자만 추가 — `suggest_next_task_id(reserved_ids=)` · `next_task_id(reserved_ids=)`) ·
> 진입점 제거 0 · 산출물 형식 변경 0 (`TASK_ID_PATTERN` 불변, 기존 ID 계속 파싱) ·
> 외부 spec 무관. 새 심볼 5종은 전부 순증이다.
> `wk release-status` 파생도 patch (breaking 0 / feat 0 / fix 5).

## 0. 릴리스 판정

이 사이클의 주제는 **"이 저장소에서만 성립하는 전제"** 다.

소유자가 *"타 배포처에서 사용 시 자꾸 모순이 발생한다"* 고 보고했다. 조사해 보니
증상이 여럿이었는데 뿌리가 하나였다:

    Path(__file__).resolve().parents[3]

이 표현이 **배포 형태마다 다른 것을 가리킨다.** 소스 배치(이 저장소)에서는 저장소
루트라 맞는 답을 내지만, 설치본(uv tool / 플러그인 캐시)에서는 `…/lib/python3.13`
이라 git 저장소가 아니다. 그래서 브랜치 조회가 실패하고 답이 **오류가 아니라
그럴듯한 오답**(`"main"`)으로 조용히 떨어진다.

**그리고 이 저장소에서는 구조적으로 보이지 않는다.** 이 저장소가 곧 모듈의
저장소라서 틀린 해석기가 *우연히 맞는 답*을 낸다 — 282개 검사 전부 그 조건에서만
돌았다.

**이 릴리스에는 발행할 이유가 있다.** 고친 다섯 자리가 전부 *소비자 쪽에서만*
발현하는 결함이고, 소비자가 새 버전을 깔아야 효과가 있다.

## 1. 릴리스 요약

- 범위: `v1.9.2..HEAD` (8 commit). 이 중 3건은 memory 기록, 1건(`cde2d0ef`)은
  **v1.9.2 발행 마무리**가 태그 뒤에 착지한 것이라 실질 내용은 4 commit 이다.
- 누적 smoke **282/282 PASS** (전량 2축 · FAIL 0, 좁은 선언 0), mypy strict 0 errors
  (204 files)
- 검사 신설 2종 (`check_example_state_artifact` 5 cases ·
  `check_task_id_remote_uniqueness` 5 cases), 판정 확장 1종
  (`check_branch_resolver_agreement` 계약 4·5 추가 → 7 cases)
- 지원 하네스 12 (변동 없음), MCP 표면 13 (변동 없음)
- 공개 API **+5 심볼**, 제거 0 —
  `common.paths.workflow_handoff_path` · `common.paths.resolve_branch_for_workspace`
  (+`BranchResolution`) · `common.git.remote_known_task_ids` (+`RemoteTaskIds`) ·
  `common.normalize.normalize_constraint_values` ·
  `tools.release_pipeline.expected_smoke_count_for_note`

## 2. 소비자 가시 변경

### 2.1 fix(paths) — 설치본에서 증발하는 모듈 앵커 (`30d2804b`, main-007)

**이 릴리스의 중심이다.** `get_current_branch()` 가 모듈 앵커를 쓰므로 설치본에서는
늘 `"main"` 을 냈다. 그 결과 workspace 계열 해석기와 갈라졌다.

설치본 배치 + `feature/xyz` 소비자 실측:

| | 수리 전 | 수리 후 |
|---|---|---|
| 채번된 ID | `TASK-2026-09-07-main-001` | `TASK-2026-09-07-feature-xyz-001` |
| 파일이 사는 곳 | `active/feature/xyz/…` | `active/feature/xyz/…` |

**ID 의 slug 와 네임스페이스가 어긋났다.** 게다가 브랜치마다 같은 번호를 매겨서,
`MEMORY_GOVERNANCE.md` 가 slug 로 보장한다던 브랜치 간 유일성이 **소비자에서
통째로 무효**였다 — 두 브랜치를 병합하면 같은 ID 의 다른 task 두 개가 된다.

수리는 `resolve_branch_for_workspace()` 와 `BranchResolution(slug, source, detail)`
다. **답과 함께 출처를 돌려준다** — 조용히 떨어지는 것이 이 결함의 본체라, 출처가
수리의 핵심이다. 채번은 workspace 계열을 쓰고, 출처가 workspace 가 아니면 경고한다.

### 2.2 fix(paths) — handoff 경로에만 legacy fallback 이 없었다 (`f21838f4`, main-001)

디렉터리(backlog / tasks / sessions)는 전부 `_branch_scoped_dir` 를 지나
"branch-scoped 없으면 legacy" 로 떨어지는데, `session_handoff.md` **만** helper 가
없어 소비자마다 인라인 조립했고 그 조립에는 fallback 이 없었다. 관례도 둘로 갈려
`ingest.py` 는 브랜치를 아예 빼고 봤다 — 같은 저장소에 대해 두 소비자가 **다른
파일**을 가리켰다.

**평평한(미마이그레이션) layout 의 소비자가 직격이다.** handoff 파일이 **있는데도**
생성기가 못 찾아 `state.json` 의 `current_baseline` / `current_axis` /
`recent_done_items` 가 통째로 비었고, **경고가 없다** — 없으면 그냥 비고 정상으로
보인다. 정본 `workflow_handoff_path()` 신설 + 읽는 쪽 8곳 경유.

### 2.3 fix(state) — 거짓말하는 `cast` 가 제약을 한 글자씩 쪼갰다 (`f21838f4`, main-002)

`cast(list[str], handoff.get("constraints"))` 는 실제 `str | None` 인 값을 목록이라
**선언만** 한다. `cast` 는 변환하지 않는다 — 문자열을 iterate 해
`session.environment_constraints` 가 28개 글자가 됐다. handoff 에 `주요 제약` 줄을
가진 **모든** 프로젝트가 대상이다. `normalize_constraint_values()` 정본으로 두
소비자(state 생성기 · session-start)를 모았다.

### 2.4 fix(backlog) — task ID 채번이 원격을 함께 본다 (`67fd0776`, main-006)

`next_task_id` 가 브랜치 격리를 근거로 *동시 작업 호스트끼리도 겹치지 않는다* 고
**보증**했는데, 그것은 브랜치가 다를 때 성립하는 문장이었다. 같은 브랜치의 두
호스트는 각자 로컬만 보고 같은 번호를 낸다 — 2026-09-04 에 실제로 충돌했고 push
거절로만 알았다. `common.git.remote_known_task_ids` 가 **원격 추적 ref** 를 함께
읽는다(네트워크는 타지 않는다). 못 읽었으면 그 사실을 경고로 말한다.

### 2.5 fix(release) — 발행 게이트가 발행된 노트를 고치라고 요구하던 자리 (`f21838f4`, main-004)

v1.9.2 는 `check_smoke_trend_cross` case 2 만 '자기 시점' 규칙으로 고쳤고, **같은
규칙의 사본**이 `verify_release_note_smoke_count` 에 남아 태그를 안 보고 늘 현재
갯수와 쟀다. 그래서 검사 파일이 하나 늘자 case 2 는 PASS 인데 게이트만 red 였고,
green 으로 만드는 유일한 길이 **발행된 `Beta-v1.9.2.md` 를 고치는 것**이었다 —
v1.9.2 가 없앤 바로 그 왕복이다. 규칙을 kit 정본
`expected_smoke_count_for_note()` 하나로 모으고 게이트와 두 검사가 그것을 읽는다.

> 이 수리는 **이번 사이클에서 첫 실전으로 물었다**: 검사 파일이 280 → 282 로
> 두 번 늘었는데 발행된 노트를 고치라는 요구가 **한 번도** 없었다.

### 2.6 docs — `INSTALLATION_AND_USAGE §7.0.2` grok 복구 열 (`14422cc2`, main-005)

복구 열이 `uninstall` → `install` 로만 적혀 있어, 왼쪽 열이 정의한
`plugin-<hash>` id 를 주는 것으로 읽혔다. 실제로는 **플러그인 이름**을 받는다.
함정은 `grok plugin list` 의 출력 형식이다 — `plugin-da9172c3: standard-ai-workflow`
처럼 id 를 먼저 찍어서 "list 에 보이는 이름" 이라는 안내가 오히려 id 를 가리키는
것처럼 읽힌다. **명령에 주는 값은 콜론 뒤다.**

## 3. 판정 (회귀 방지)

이 사이클의 결함들은 **재는 자리가 없어서** 살아남았다. 그래서 판정을 세 방향으로
넓혔다.

- **`check_example_state_artifact` 신설 (5 cases)** — 체크인된 예제 `state.json` 을
  생성기 출력과 **대조**한다. 기존 두 검사는 tmpdir 로 새로 생성해 느슨한 속성만
  보고 체크인본을 읽지 않았다. 2.2 와 2.3 이 여기서 살아남았다.
- **`check_task_id_remote_uniqueness` 신설 (5 cases)** — 원격 조회, 모름 ≠ 안전,
  경로 계산의 소재, 거짓 보증 문구의 재등장 금지.
- **`check_branch_resolver_agreement` 확장 (5 → 7 cases)** — 채번 slug 가
  네임스페이스와 같은지, 그리고 **설치본 배치**(모듈 앵커가 git 저장소가 아닌 곳)
  에서도 workspace 기준이 유지되는지. 설치본 흉내는 패키지를 저장소 아닌 곳으로
  **실제 복사**한다 — symlink 은 `resolve()` 가 되짚어 흉내가 되지 않는다.

되주입 실증은 **9종**이고 전부 의도한 case 에서 red 였다. 그중 하나가 비대칭을
드러냈다: workspace 해석을 되돌리면 **설치본 축의 case 만** 잡는다. 소스 배치에서는
통과한다 — *배포 형태 축이 없으면 못 본다*는 증거다.

`audit_root_anchors` 의 R3 어휘도 넓혔다. `get_current_branch` 하나뿐이라 이
사이클이 만든 새 fallback(`_resolve_module_branch`)을 못 봤다 — 규칙의 어휘가
좁아지면 규칙이 조용히 사라진다.

## 4. 남은 리스크

- `get_current_branch()` **자체는 여전히 모듈 앵커를 본다** (sandbox caller 를 위한
  의도된 동작). 새 호출자가 workspace 를 알면서 그것을 쓰면 재발하며, audit R3 +
  resolver 검사만이 그것을 막는다.
- 원격 추적 ref 는 마지막 fetch 시점에 멈춰 있다. **fetch 없이는 task ID 유일성이
  로컬 안에서만 성립하고**, 도구는 그 사실을 경고로만 말한다.
- `INSTALLATION §7.0.2` 의 grok 항목은 **정적 판정으로 못 닫는다** — CLI 인자
  의미론이라 검사가 고정할 수 없다. 실측 기록으로만 지켜진다.

## 5. 업그레이드

소비자 채널은 재적용이 필요하다 (`INSTALLATION_AND_USAGE §7.0.2` 의 복구 열).
**이 릴리스의 수리는 전부 소비자 쪽에서 발현하므로, 깔지 않으면 효과가 없다.**

## Reference

- 이전 release note: `Beta-v1.9.2.md`
- task: `TASK-2026-09-07-main-001` ~ `main-007`
- 정본 문서: `MEMORY_GOVERNANCE.md` (§task ID 형식) · `docs/RELEASE.md` §2.3

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-09-07T03:52:11Z)_

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
