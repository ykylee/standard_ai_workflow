# Beta v1.9.2 (2026-09-04)

> **상태: 릴리스 준비.** package `1.9.2`, runtime `__version__ = 1.9.2`, tag `v1.9.2`.
> **patch release** — 발행 절차에서 사람이 매번 손으로 고치던 두 자리를 없앤다.
>
> 등급 근거 (§1.5): 공개 API 시그니처 변경 0 · 진입점 제거 0 · 산출물 형식 변경 0
> (`_fix_readme_header_version` 의 결과 dict 에 `literals` 키가 **추가**됐을 뿐,
> 기존 키는 그대로다). 새 모듈 `common/readme_version.py` 는 순증이다.
> `wk release-status` 파생도 patch (breaking 0 / feat 0 / fix 1).

## 0. 릴리스 판정

이 사이클의 주제는 **"자동 수리가 닿지 않는 자리에 판정도 없으면 조용히 썩는다"** 다.

v1.7.0 ~ v1.9.1 의 **네 사이클 연속**, 발행 준비 게이트는 같은 두 자리를 사람에게
넘겼다. 매번 "버전 bump 파생이니 손으로 고치면 된다" 로 처리했고, 그래서 네 번
반복되는 동안 아무도 그것을 결함으로 열지 않았다. 조사해 보니 둘 다 결함이었고,
모양이 서로 달랐다.

- **README 꼬리**는 자동 수리의 사각이 아니라 **판정의 공백**이었다. 넷 중 둘은
  어떤 검사도 보지 않았다 — 사람 눈에 걸린 것은 그것이 *검사가 보는 리터럴 옆에*
  있었기 때문이다.
- **누적 smoke 수치**는 검사가 **거짓 주장을 유도**하고 있었다. 이미 발행된
  릴리스 노트를 현재 값에 맞추라고 요구했고, 그 편집은 전량을 돌리지 않은 사람이
  쓰게 된다.

**이 릴리스에는 발행할 이유가 있다.** 둘 다 *발행 절차 자체*의 결함이라, 소비자가
이 킷으로 자기 릴리스를 돌리는 동안 같은 손질이 그대로 반복된다.

## 1. 릴리스 요약

- 범위: `v1.9.1..HEAD` (4 commit). 이 중 2건은 memory 기록, 1건(`10f41465`)은
  **v1.9.1 발행 마무리**가 태그 뒤에 착지한 것이라 실질 내용은 1 commit 이다.
- 누적 smoke **280/280 PASS** (전량 2축 · case 합계 560, FAIL 0, 좁은 선언 0),
  mypy strict 0 errors
- 검사 case 신설 1종 (`check_smoke_trend_cross` case 6), 판정 확장 2종
  (`check_drift_prevention` case 4 · `check_readme_cross` case 3)
- 지원 하네스 12 (변동 없음), MCP 표면 13 (변동 없음)
- 공개 API **+1 모듈** (`common.readme_version` — `header_line` · `found_versions` ·
  `mismatches` · `sync` · `LITERALS`), 제거 0

## 2. 소비자 가시 변경

### 2.1 fix(release) — self-recover 가 README 헤더 줄의 버전 리터럴 4개를 모두 고친다 (`bb55ccd5`)

README 헤더 `- 버전:` 줄에는 같은 버전이 **네 번** 적힌다:

```
- 버전: v1.9.2 (… ; package: standard-ai-workflow 1.9.2,
  runtime `__version__` = 1.9.2, latest tag **v1.9.2**)
```

`_fix_readme_header_version` 은 맨 앞 하나만 고쳤다. 나머지 셋 중
``runtime `__version__` `` 과 `latest tag **v…**` 는 **어떤 검사도 보지 않았다** —
`check_readme_cross` 가 보던 것은 `package:` 하나뿐이고, 두 자리는 그 옆에 붙어
있었던 덕에 사람 눈에 걸렸을 뿐이다.

되주입이 그것을 그대로 보여 준다. 두 자리를 옛 버전으로 되돌리자 **옛 판정은
4/4 PASS** 였다 — 아무것도 못 봤다.

**수리**: 패턴 정본 `workflow_kit/common/readme_version.py` 를 두고 **수리와 판정이
같은 것을 읽는다**. 범위는 헤더 **줄 하나**다 — README 아래쪽 changelog 에는 같은
모양 문자열이 *역사 기록*으로 남아 있어(v0.9.0 항목의
``runtime `__version__` = v0.9.1-beta``) 문서 전체 치환은 역사를 덮어쓴다.

이 릴리스 자신이 첫 실전이었다: bump 직후 self-recover 가
`literals: [header, package, runtime, latest_tag]` 를 한 번에 고쳤고
`manual_required` 는 0 이었다.

### 2.2 fix(checks) — 릴리스 노트의 누적 smoke 수치를 '그 노트의 시점' 과 대조한다 (`bb55ccd5`)

`check_smoke_trend_cross` case 2 는 `가장 최근 노트의 수치 >= 현재 check 파일 수`
를 요구했다. 그래서 사이클 중에 검사가 하나라도 늘면 **이미 발행된 노트**를 올려
red 를 끄고, 다음 발행 준비에서 그것을 되돌려야 했다. `Beta-v1.9.0.md` 의
`279 → 280 → 279` 왕복이 git 이력에 그대로 남아 있다.

뿌리는 판정 기준이 아니라 **분모**였다. 그 수치는 *그 릴리스가 나가던 순간의
주장*이다. 발행된 뒤에도 현재와 맞추라고 요구하면 역사 기록이 가변이 되고,
그 편집은 전량을 돌리지 않은 사람이 쓰게 된다.

**수리**: 노트마다 자기 시점과 대조한다.

| 노트 | 대조 대상 |
|---|---|
| 발행된 노트 (같은 이름의 태그가 있다) | `git ls-tree` 로 잰 **그 태그 시점**의 `check_*.py` 갯수 |
| 아직 태그가 없는 노트 (발행 준비 ~ 태그 push) | **현재** 갯수 — 발행 게이트의 `verify_release_note_smoke_count` 와 같은 규칙 |

발행된 값이 얼어붙으므로 왕복이 사라지고, 과거 노트를 몰래 고치면 오히려 red 가
난다. git 을 못 읽으면 통과가 아니라 **FAIL** 이다 (`_doc_stamp.py` 와 같은 규약 —
모름은 안전이 아니다).

**표기 누락 커버리지는 `case 6` 신설로 유지**했다. 파서는 수치 줄이 없는 노트를
**조용히 건너뛴다** — v1.1.0 / v1.1.1 에서 그렇게 빠뜨렸을 때 dashboard 는 옛
노트(v1.0.0 의 234)를 최신으로 읽었다. case 6 은 '파일 기준 최신' 과 '파싱 기준
최신' 을 직접 대조해 그 상황에서 case 2 가 엉뚱한 노트를 재지 않도록 막는다.

**그 줄은 여전히 사람의 주장이다** — 도구가 대신 채우지 않는다. 전량을 돌린 뒤
적고, 발행 게이트가 그 주장을 필수 CI 결과와 대조한다.

## 3. 업그레이드

전역 설치본은 재설치해야 이 수리가 반영된다. `wk doctor` 의 `kit 사본` 줄이
돌고 있는 사본과 저장소 소스의 정합을 말해 준다.

```bash
uv tool install --force \
  "standard-ai-workflow @ https://github.com/ykylee/standard_ai_workflow/releases/download/v1.9.2/standard_ai_workflow-1.9.2-py3-none-any.whl"
wk doctor | head -12
```

산출물 형식 변경은 없다 — 마이그레이션 불필요. 자기 저장소에서 릴리스 노트의
누적 수치를 **현재 파일 수에 맞춰 과거 노트까지 갱신해 오던 관행**이 있었다면,
이제 그 편집이 red 를 낸다. 발행된 노트는 그 시점 값으로 두면 된다.

## 4. 검증

- 전량 2축 **280/280 ×2 PASS** (`--branch-context=all`, RUNNER_EXIT=0,
  native 132.4s / slash 128.1s, 좁은 선언 0)
- mypy strict **0 errors** (204 source files)
- CI `bb55ccd5` 필수 4종 전부 success (`smoke` · `mypy-strict` · `os-matrix` ·
  `mcp-sdk-matrix`) + `mkdocs` success
- 되주입 red 실증 (README): `runtime` / `latest_tag` 를 옛 버전으로 → 옛 판정
  4/4 PASS, 새 판정 case 3 FAIL (두 자리를 이름까지 지목). 이어 self-recover 가
  고쳐 README 가 바이트 단위로 원복
- 되주입 red 실증 (누적 smoke) **3종**: 발행된 노트 280→281 → case 2 FAIL /
  최신 노트의 수치 줄 삭제 → case 6 FAIL (case 2 는 직전 노트를 자기 태그와 재어
  PASS — 설계된 분업) / check 파일 1개 추가 → case 2 **PASS** (옛 규칙이면 FAIL)
- meta-watch 가 좁은 선언을 red 로 잡아 `check_readme_cross` 의 `WATCHES` 를
  넓혔다 (국소 176 → 177)

## 5. Commit

| Hash | Subject |
|---|---|
| `bb55ccd5` | fix(release): 발행마다 손이 가던 두 자리를 파생과 판정으로 닫는다 (main-003·004) |
| `96f5f386` | chore(memory): v1.9.1 소비 채널 배포 기록 |
| `2e57ad45` | chore(memory): 74차 세션 종료 — 잦던 불일치 보고를 도구 결함으로 확정·수리·발행·적용 |
| `10f41465` | release(v1.9.1): 발행 완료 — 태그 push + GitHub Release(asset 4종) + post-step 정합 |

## 6. Reference

- 이전 release note: `Beta-v1.9.1.md`
- task SSOT: `TASK-2026-09-03-main-003` · `TASK-2026-09-03-main-004`
- 리터럴 정본: `workflow_kit/common/readme_version.py`
- 누적 수치 판정: `workflow-source/tests/check_smoke_trend_cross_v0_15_5.py` (case 2 · 6)
- 절차 문서: `docs/RELEASE.md` §2.3

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-09-04T05:46:22Z)_

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
