# 세션 기록 — handoff 기준선 롤오프 (2026-08-14)

- 문서 목적: handoff §1 의 단조 증가를 끊은 방식과 그 과정에서 드러난 것을 남긴다.
- 범위: `rollover_handoff_baselines` 도구, `BASELINE_ITEMS_CAP`, 계약 검사, 린터 규칙
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 관련 문서: [task](../backlog/tasks/TASK-2026-08-14-perf-handoff-baseline-rolloff-001.md)

## 0. 자르는 것과 옮기는 것은 다른 처방이다

완료 목록에는 이미 상한이 있었다(`RECENT_DONE_ITEMS_CAP = 10`, writer 가 넘치는 줄을
**버린다**). 기준선에 같은 처방을 쓰면 안 된다:

| | SSOT | 넘치면 |
|---|---|---|
| 최근 완료 목록 | `backlog/tasks/` 에 따로 있다 | **버려도** 사실이 안 사라진다 |
| §1 기준선 줄 | **어디에도 없다** — 그 산문이 원본이다 | **옮겨야** 한다 |

그래서 `BASELINE_ITEMS_CAP = 4` 와 함께 `baselines.md` 이관을 만들었다. 검사의 중심
case 도 "줄었는가" 가 아니라 **"옮겨졌는가"** 다 (case 3) — 줄 수만 보는 검사는 자르는
구현을 통과시킨다.

## 1. 만든 것

- `project_docs.py` — `BASELINE_ITEMS_CAP` / `BASELINES_FILENAME` / `BASELINE_LABELS`
  (`RECENT_DONE_ITEMS_CAP` 과 같은 자리, 같은 idiom)
- `tools/rollover_handoff_baselines.py` + `wk rollover-baselines`
  (기본은 계획만, `--apply` 로 이관, 멱등, `--cap 0` 거부)
- `check_handoff_baseline_cap.py` (10 cases) — 유실 없음 / 포인터 잔존 / 라벨 재작성 /
  헤더 미적층 / 생성기 입력 불변 / 자기 적용
- `linter.py` 의 `handoff_baseline_bloat` — fix_suggestion 이 **도구를 가리킨다**.
  "지워라" 라고 적으면 사람이 지우고 그 세션 이력이 사라진다.
- 정본 §11.1 에 명령 한 줄 추가 + 파싱 계약에 "손으로 지우지 말 것" 한 줄

## 2. 되주입이 드러낸 검사 자신의 결함

이관을 생략한 구현(자르기만)을 심었더니 case 3 이 `FileNotFoundError` 로 **죽었다**.
`_run` 이 `AssertionError` 만 잡고 있어서 그 예외가 러너를 통째로 끝냈고, **case 4~10 이
아예 안 돌았다.** 출력은 traceback 하나뿐이라 어느 계약이 깨졌는지도 안 보였다.

`except Exception` 을 붙여 실패로 보고하게 고쳤다. 되주입은 "잡히는가" 만 보는 것이
아니라 **"어떻게 보고되는가"** 도 본다 — 첫 예외에서 죽는 검사는 나머지를 재지 않는다.

## 3. 행을 하나 늘리자 위치 가정이 깨졌다

`check_agent_plugin_payload` 가 §11.1 재생성 명령을 이렇게 찾고 있었다:

```python
refresh_cmd = rules.memory_commands[-1][1]   # 표의 마지막 행
```

§11.1 에 행을 추가하자 `wk rollover-baselines` 가 "재생성 명령" 이 됐다. 위치가 아니라
**목적**으로 찾도록 `find_memory_command(rules, "Regenerate state.json")` 로 바꿨다 —
렌더러가 이미 쓰던 정본 helper 다. 표에 행을 더할 때마다 깨질 자리가 하나 줄었다.

## 4. 순서 — main 의 handoff 는 main 에서만 고친다

새 린터 규칙이 main 의 handoff(기준선 37줄)를 즉시 지목했다. 그런데 작업 브랜치에서
`active/main/` 을 고치는 것은 `check_branch_memory_namespace` 가 막는 일이고 **그게
맞다**. 그래서 자기 적용 case 도 main 이 아니라 **현재 브랜치의 handoff** 를 본다.

실제 이관은 병합 후 main 에서 돌린다. 브랜치 단독 2축 게이트에는 그 한 건이 남아
있고, 그건 결함이 아니라 **아직 적용되지 않은 규칙**이다.
