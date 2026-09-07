# 77차 세션 — 오탐인 줄 알았던 지표가 결함이었다

- 문서 목적: session-start 가 매번 내던 `health 0` / `scope creep` 10건을 오탐으로 열었다가 지표 자체의 결함으로 확정하고 닫은 과정을 남긴다.
- 범위: TASK-2026-09-07-main-010 (수리) · main-009 (runtime_load 기록)
- 대상 독자: AI agent, 저장소 관리자
- 상태: stable
- 최종 수정일: 2026-09-07
- 관련 문서: [session_handoff.md](../session_handoff.md), [purpose_graph.py](../../../../../workflow-source/workflow_kit/common/purpose_graph.py), [check_graph_insights_health_monotonic.py](../../../../../workflow-source/tests/check_graph_insights_health_monotonic.py)

## 0. 이 세션이 남길 것

후보를 **"오탐 조사"** 라고 이름 붙여 열었다. 그 이름이 이미 결론을 담고 있었고,
틀렸다. 경고는 정확했던 적이 없지만 오탐도 아니었다 — **지표가 고장 나 있었다.**

## 1. 100% 발화하는 경고는 신호가 아니다

`recent_done_items` 10건이 **전부** `scope creep 의심` 으로 떴다. 이 비율 자체가
진단이다. 입력의 100% 에서 우는 경고는 정보량이 0이고, 그 상태가 여러 세션 지속됐다면
경고의 임계값이 아니라 **경고의 근거**를 의심해야 한다.

## 2. 점수가 일한 것을 벌하고 있었다

```
100 - uncovered*15 - scope_creep*10 + min(surprising*5, 25)
```

벌점은 항목 수에 **비례해 무한히** 커지는데 보너스는 25 에서 막힌다. goal 매칭 0 을
고정하고 완료 항목 수만 늘리면:

| 완료 항목 | raw | tier |
|---|---|---|
| 0건 | 40 | fair |
| 3건 | 25 | poor |
| 10건 | **−35 → 0 clamp** | poor |

표준이 recently-done 을 **10건으로 상한**하므로, 활발한 저장소는 영구히 바닥에 눌린다.
보고되던 `0` 은 "나쁘다" 가 아니라 **clamp 자국**이었다.

> **개수로 벌점을 매기고 보너스에 상한을 두면 지표는 규모의 함수가 된다.**
> 두 성분 모두 비율이어야 한다 — 그래야 "더 많이 재는 것" 이 "더 나쁜 것" 이 되지 않는다.

수리: `coverage 70*covered/goals + classification 30*(1-미분류/전체)`.
`SurprisingResult` 가 **분모(`total_items`)를 함께** 돌려주게 했다 — 호출자가
`len(surprising)` 로 비율을 내면 분모가 분자와 같아져 늘 1.0 이 된다.

## 3. 내 가설이 틀렸고, 측정이 그것을 죽였다

겹침이 0인 것을 보고 **한국어 조사** 탓이라고 판단했다 (`프로젝트에서` vs `프로젝트`).
그럴듯했다. 조사 제거기를 붙여 재측정했다 — **여전히 공집합**이었다. 부분문자열 포함까지
완화해도 회수되는 것은 `ai` 와 `처럼` 둘뿐이었다.

진짜 이유는 더 단순하고 더 깊다. **Goals 는 지향 문장이고 deliverable 은 결함 수리
제목이다.** "표준 워크플로우를 패키지로 제공" 과 "설치본에서 모듈 앵커가 증발해 브랜치
해석이 갈라진다" 가 낱말을 공유할 이유가 없다. 유지보수 저장소에서 이 지표는 **구조적으로**
0 을 낸다.

> 그럴듯한 원인 가설이 있으면 고치기 전에 그 가설을 **부정해 보는 측정**을 한 번 넣는다.
> 조사 제거를 "개선" 으로 커밋했다면 아무것도 안 고치고 코드만 늘렸을 것이다.

그래서 토크나이저를 정교화하는 길을 **기각**하고(임계값만 옮긴다) **주장을 좁혔다** —
이것이 재는 것은 어휘 겹침이지 건강도가 아니라는 것, 낮은 값은 "어휘가 겹치지 않는다" 로
읽는다는 것, 어떤 skill·harness 도 이것을 소비하지 않으므로(참조 0건, state.json 에도
미저장) 자동 판정의 근거로 쓰지 않는다는 것을 docstring 정본에 적었다.

## 4. 좋은 점수를 내는 유일한 자리가 항등식을 쟀다

지표가 늘 나쁘면 **좋게 나오는 fixture 를 먼저 본다.**

```python
Goals: **G1**: 표준 워크플로우          **G2**: skill 분리
done : "v0.1.0 (aaaaaaa): 표준 워크플로우 release"
       "v0.2.0 (bbbbbbb): skill 분리"
```

goal 문자열을 deliverable 에 **그대로 복사**해 두었다. coverage 100% 는 항등함수의 값이다.
게다가 형식이 `vX.Y.Z (hash):` — 표준이 `TASK-` 로 바꾼 뒤라 **살아 있는 10건은 전부
`version='unknown'`** 으로 떨어지고, 모든 항목이 공유하는 `task`/`2026`/`09`/`main` 이
키워드에 섞여 있었다.

**결함이 어려웠던 게 아니라 재는 자리가 없었다.** 76차 `main-002`(`examples/` 만이 그
필드를 가진 코퍼스인데 그 산출물을 보는 검사가 없었다)와 같은 모양이다.

## 5. 재생성하라는 지시를 따르기 전에 대조했다

게이트가 `check_state_json_generated` 를 이렇게 red 로 냈다:

> 이 저장소의 state.json 이 생성기 출력과 갈라졌다 — `wk refresh-state` 로 재생성하라.
> `drifted_keys=[]`

`drifted_keys=[]` 가 걸렸다 — 갈라졌다면서 **무엇이 다른지 못 댄다**. 체크인본과 재생성본을
평탄화해 대조하니 **차이 나는 키 0개**. payload 실측:

```
drift=false · drifted_keys=[] · roadmap_drift=true
```

도구는 두 산출물 중 **어느 쪽이 갈라져도** rc=1 인데, `case_5` 의 실패 문구가 **무조건
state.json 을 지목**하고 있었다. 시키는 대로 했으면 멀쩡한 산출물을 다시 쓰면서 진짜
원인(roadmap)을 지나쳤다. 문구가 payload 를 읽고 범인을 말하게 고쳤다.

> 오류 메시지가 **자기 근거를 못 대면**(`drifted_keys=[]`) 그 메시지의 지시를 따르기 전에
> 대조부터 한다. 산출물 재생성은 되돌리기 어렵고, 원인을 덮는다.

## 6. handoff 산문은 읽히는 시점에 이미 낡아 있다

76차 handoff ⑮ 는 "`runtime_load` 의 낡은 호스트에 **이 세션 자신이 포함된다**" 고 적었다.
그 세션에서는 참이었다. 이 세션에서 읽었을 때는 거짓이었다 — 이 세션은 설치(12:55:44)
뒤인 13:02:22 에 시작해 doctor 가 세는 "최신 호스트 1개" 가 곧 이 세션이었다.

낡은 3개는 전부 **이 저장소 밖**(pid 10649 claude @`~/repos/auto-trading` · 9096
`codex --yolo` @`~/repos/custom-harness` · 18642 codex app-server 데몬)이라, 다른 작업이
붙어 있을 수 있어 죽이지 않았다. doctor 가 "실제 호출로만 재진다" 고 남긴 노출 미측정
칸은 이 세션의 `/session-start` 가 1.9.3 스킬 경로에서 정상 실행돼 claude-code 채널에
한해 닫혔다.

> handoff 의 "이 세션" 은 **쓴 시점의 세션**이다. 읽는 쪽은 그것을 자기 자신으로 읽기
> 쉽다. 프로세스 사실은 산문을 믿지 말고 매번 재는 것이 맞다.

## 7. 판정으로 닫았다

`check_graph_insights_health_monotonic.py` (4 case):

| case | 재는 것 |
|---|---|
| 1 | 비율 고정 시 규모 1~30배에서 점수 불변 · 분류된 일 추가가 점수를 안 내림 · 최악=0/최선=100 이고 clamp 자국 없음 |
| 2 | 정반대 술어(`purpose_context` 제외영역 **매칭** ↔ `purpose_graph` **미매칭**)의 두 경고가 접두사를 공유하지 않음 |
| 3 | fixture 의 deliverable 이 goal 문자열의 복사가 아님 |
| 4 | `TASK-` 형식 인식 + ID 토큰 누출 0 (legacy 병행) |

되주입 4종(옛 산식 복원 / 접두사 통일 / fixture 항등식 복원 / `TASK-` 인식 제거) 전부
의도한 case 에서 red, 원복 green.

필드 이름 `scope_creep_warnings` 는 **건드리지 않았다** — 공개 schema 라 G3 SemVer
보증상 개명은 deprecation 사이클이 필요하다. 이름은 scope creep 인데 담기는 것은
미분류라는 사실을 schema docstring 에 후속 후보로 남겼다.

## 8. 검증

- 전량 2축 **283/283 ×2 PASS** (native / slash, FAIL 0, `RUNNER_EXIT=0`, 좁은 선언 0)
- mypy strict **204 files, 0 errors**
- `check_self_application` **8/8**
- 되주입 4종 red 실증
- smoke count 282→283 갱신은 `CODE_INDEX`·`INSTALLATION` 둘뿐 — **발행된 노트를 고치라는
  요구 0건** (76차 `main-004` 수리가 이번에도 물었다)

커밋 `878f0ae7`.

## 9. 닫지 않은 것

- **지표는 여전히 0 을 낸다.** 다만 이제 clamp 자국이 아니라 **정직한 읽기**다
  (coverage 0 + 전량 미분류). 어휘 겹침이라는 근거 자체를 바꾸려면 — 예컨대 task 의
  WBS·로드맵 링크를 쓰거나 goal 을 task 에 명시 선언하게 하려면 — ADR 이 필요해
  범위 밖으로 남겼다.
- `graph_insights.scope_creep_warnings` 개명 (deprecation 사이클 후보).
- `runtime_load` 낡은 호스트 3개 (`main-009`, planned) — 소유자 결정으로 기록만 남겼다.
  그 터미널을 재시작한 뒤 `wk doctor` 재측정으로 닫는다.
