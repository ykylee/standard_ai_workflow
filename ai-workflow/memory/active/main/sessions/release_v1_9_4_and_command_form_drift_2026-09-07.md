# 77차 세션 (후반) — v1.9.4 발행과 "성공했는데 틀린" 명령

- 문서 목적: 지표 수리를 소비자에게 보낸 발행 사이클과, 그 과정에서 드러난 문서/실제 명령 형태의 어긋남을 남긴다.
- 범위: TASK-2026-08-25-main-017(판정 보강) · main-011(발행) · main-012(문서 교정)
- 대상 독자: AI agent, 저장소 관리자
- 상태: stable
- 최종 수정일: 2026-09-07
- 관련 문서: [graph_insights 결함 기록](./graph_insights_metric_defects_2026-09-07.md), [session_handoff.md](../session_handoff.md), [Beta-v1.9.4.md](../../../../../workflow-source/releases/Beta-v1.9.4.md)

## 0. 이 기록이 남길 것

세 가지가 같은 모양이었다: **명령이 성공했는데 결과가 틀렸다.** rc=0 이,
"already installed" 가, PASS 가 전부 근거가 못 되는 자리를 연달아 밟았다.

## 1. 수리할 것이 없다는 것도 결론이다 — main-017

`TASK-2026-08-25-main-017`(Windows 에서 `python3` 를 못 찾는다)을 "수리 + 판정"
으로 열었는데, 실측해 보니 **62차가 이미 다 고쳐 두었다.** emit 지점 전수가 정본
`mcp_server_command` 를 지나고, `python3` 리터럴 전수 grep 에서 emit 경로에 남은
사본은 0건이었다.

없던 것은 **판정**이다. 기존 `check_bootstrap_mcp_roundtrip.unit_checks` 는 정본
함수를 *직접* 부를 뿐이고, 그 docstring 이 스스로 적어 두었다:

> smoke 는 이 호스트의 산출물만 밟는다.

즉 새 렌더러가 command 를 손으로 적어 정본을 우회해도 red 가 되지 않는다.
`check_mcp_emit_launcher_sweep.py` 는 함수가 아니라 **산출물**을 잰다 — 렌더러
6개를 돌려 emit 된 설정에서 command 를 꺼내고 플랫폼을 강제해 대조한다.

> **검사가 조용히 통과할 뻔했다.** 첫 판에서 `opencode` 가 command 0건인데
> PASS 였다 — 그 하네스만 command 가 **리스트**라 문자열 전용 추출이 아무것도
> 못 찾았고, 그 0건은 **위반 0건과 구분되지 않았다.** 추출을 고치고, 렌더러마다
> 최소 1건을 찾았는지와 모듈의 렌더러 전수가 사정권 안인지를 검사에 넣었다.
> *모름을 통과로 세지 않으려면 커버리지를 함께 재야 한다.*

Windows 실측(완료 기준 2)은 이 호스트에서 불가하므로 task 는 `in_progress` 로
남겼다. 판정이 보증하는 것은 command **이름**까지이고, 그 이름이 PATH 에 실재해
spawn 되는지는 그 다음 칸이다.

## 2. 등급은 도구가 파생하고 사람이 고른다 — main-011

`wk release-status` 가 patch(1.9.4)를 파생했다. §1.5 를 적용하면 공개 API **추가**
2종(`UNCLASSIFIED_WARNING_PREFIX` · `SurprisingResult.total_items`)이 있어 73차
선례로는 minor 로 읽을 여지가 있었다. 소유자가 도구 파생값을 택했다 — 두 추가는
수리를 가능하게 한 보조 장치이지 소비자용 기능이 아니라는 해석이고, **"손으로
등급을 덮지 않는다"** 는 저장소 규칙과도 맞는다.

## 3. 발행 직전, 수리가 안 먹은 것처럼 보였다

발행 전 `wk session-start` 를 돌렸더니 **옛 문구가 그대로** 나왔다. 하마터면
"수리 실패" 로 보고할 뻔했다. 원인은 전역 `wk` 가 발행본(= 수리 이전) 1.9.3 을
돌고 있어서였고, 탐침이 스스로 말해 주었다:

    kit 사본 : 1.9.3 — **버전은 같은데 내용이 다르다** (.py 3개 어긋남)

> **버전 문자열이 같은 것은 내용이 같다는 뜻이 아니다.** 소스에서 고친 것을
> 설치본으로 확인하면 안 된다 — 어느 사본이 도는지부터 본다.

그래서 발행 후 검증은 **격리 venv** 로 했다. GitHub Release 의 wheel 을 받아
`PYTHONPATH` 없이 깔고, 모듈 경로가 site-packages 임을 `assert` 한 뒤 쟀다:
`__version__` 1.9.4 · 새 접두사 · `total_items` 필드 · 단조성 `[50,50,50,50]`.
소스 트리가 새면 그 PASS 는 아무것도 증명하지 않는다.

## 4. 준비 게이트 12건 — 전부 버전 bump 파생

v1.9.3 사이클과 같은 수·같은 모양이었다. self-recover 가 README 리터럴 4종을
`manual_required=0` 으로 처리했고, 나머지는 생성기 재실행 3종 · 샘플 24개 ·
문서 리터럴 8줄이었다.

두 가지를 **일부러 하지 않았다**:

- **`docs/RELEASE.md:175` 은 남겼다.** `(v1.9.3, TASK-2026-09-07-main-004)` 는
  현재 상태가 아니라 **역사 인용**이다. 일괄 치환은 과거 기록을 거짓으로 만든다.
  문서에 남은 `1.9.3` 은 이 한 줄뿐이고 그게 맞다.
- **`doc-headers-update` 는 껐다.** 안 건드린 문서 77개를 오늘로 스탬프하는데,
  전량이 284/284 green 이라 어떤 검사도 그것을 요구하지 않는다.

생성기 3종은 **재생성 전에 대조**했다 — 차이가 정말 버전 문자열뿐인지(1·8·1건)
확인하고 나서 돌렸다. 다른 것이 섞여 있었다면 재생성이 덮었을 것이다.

> smoke 왕복은 이번에도 없었다. 검사가 282→284 로 늘었는데 **발행된 노트를
> 고치라는 요구는 0건**이었다 — main-004 수리가 두 사이클 연속 물었다.

## 5. 명령이 성공했는데 버전이 틀렸다 — main-012

채널 재적용에서 문서의 `marketplace remove → marketplace add → plugin add` 를
그대로 따랐다. 앞의 둘이 usage 오류로 죽었고, 그 상태에서 `codex plugin add` 가
**옛 marketplace 를 보고 1.9.3 을 다시 깔았다.**

    Installed plugin root: …/standard-ai-workflow/1.9.3

**명령은 성공했고 버전만 틀렸다.** 성공 출력이라 눈으로 안 보면 지나친다.

뿌리는 맨 `marketplace …` 라는 최상위 명령이 **세 CLI 어디에도 없다**는 것이다.
전부 `plugin` 아래에 있고 갱신 동사도 갈린다:

| CLI | 정규 경로 | 갱신 동사 |
|---|---|---|
| claude | `claude plugin marketplace …` | `update` |
| codex | `codex plugin marketplace …` | **`upgrade`** |
| grok | `grok plugin marketplace …` | `update` |

같은 문서 282행은 **이미 올바른 형태**였다 — 처음부터 틀린 게 아니라 문서 안에서
사본이 갈린 것이다.

### 5.1 rc 로 못 가르는 채널이 있다

codex·grok 은 맨 형태에서 rc 2 로 죽는데 **claude 는 rc 0 을 낸다.** 명령으로
실행돼서가 아니라 `"marketplace list"` 가 **프롬프트로 먹혀 모델이 산문으로
답했기** 때문이다.

> **이 채널에서 rc=0 은 명령이 동작했다는 근거가 못 된다.** 출력이 CLI 의 것인지
> 모델의 것인지 눈으로 갈라야 한다. rc 표만 믿었으면 "claude 는 맨 형태도 된다"
> 고 문서에 적을 뻔했다.

### 5.2 측정 방법 자체가 틀렸다

첫 시도에서 여러 단어 문자열을 `$c` 로 실행해 rc 를 쟀는데, 셸이 그것을 통째로
**명령명**으로 해석해 rc 가 전부 무의미했다(127 과 0 이 섞여 나왔다). 그 값으로
결론을 냈으면 전부 오답이었다. `probe() { "$@"; }` 로 고쳐 다시 쟀다.

> 측정값이 **예상과 다르게 깔끔할 때**(전부 같은 rc, 전부 0) 도구가 아니라
> 측정 장치를 먼저 의심한다.

## 6. 검증

- 전량 2축 **284/284 ×2 PASS** (native / slash, FAIL 0, `RUNNER_EXIT=0`, 좁은 선언 0)
- mypy strict **204 files, 0 errors**
- `required_ci` 필수 4종 success, `blocking=[]` · `smoke_count_check` expected 284, found [284, 284]
- 태그 `v1.9.4` → `51ab7cb2`, draft 아님, asset 4종 uploaded 실측
- 격리 venv 에서 발행본 실측 · `content_drift` 3채널 in-sync (대조 12·10·19)

커밋 `51ab7cb2`(준비) · `0facde38`(발행 완료) · `0bcd757e`(문서 교정).

## 7. 닫지 않은 것

- **`runtime_load` 낡은 호스트** — 재적용 뒤 claude 2 · codex 2 이고 **이 세션도
  포함된다**. 플러그인은 프로세스 시작 때 로드되므로 재시작해야 v1.9.4 가 노출된다.
- **§7.0.2 는 정적 판정으로 못 닫는다** — CLI 인자 의미론이라 검사가 고정할 수
  없고, 벤더가 명령 트리를 바꾸면 표가 다시 낡는다. 6번·7번 각주는 실측 기록으로만
  지켜지는 자리다.
- `graph_insights.scope_creep_warnings` 개명 (deprecation 사이클 후보).
- `TASK-2026-08-25-main-017` 완료 기준 2 (Windows 실측) — 이 호스트 불가.
