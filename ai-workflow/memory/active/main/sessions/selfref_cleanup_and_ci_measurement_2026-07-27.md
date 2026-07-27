# 세션 기록 — 남은 자기참조 해소 + CI red 원인 계측 (2026-07-27)

- 문서 목적: 이 세션이 무엇을 재고, 무엇을 틀렸고, 무엇을 남겼는지 다음 세션이 이어받게 한다.
- 범위: TASK-2026-07-27-main-003 (§2.35 (6)~(8), §2.36)
- 대상 독자: AI agent, 저장소 관리자
- 상태: closed
- 최종 수정일: 2026-07-27
- 관련 문서: [state.json](../state.json), [session_handoff.md](../session_handoff.md),
  [TASK-2026-07-27-main-003](../backlog/tasks/TASK-2026-07-27-main-003.md),
  `workflow-source/releases/Beta-v1.0.0.md` §2.35~§2.36

## 1. 시작 지점

직전 세션이 남긴 시작 포인트는 *"푸시 후 CI 확인. 자기참조를 없앴으니 smoke 가 green 이어야
한다 — 아니면 다른 원인이다."* 였다. 실제로는 **다른 원인**이었고, 그 한 줄이 이 세션 전부다.

## 2. 한 일

| 커밋 | 내용 |
|---|---|
| `44b1b78` | §2.35 (6)(7) — `local_mypy=ok` 환경 의존 제거 + 실패 사유가 늘 잘려 나가던 excerpt |
| `fbca6d7` | §2.35 (8) — 같은 자기참조 2건 추가 해소 + 매트릭스 7행 주입 검증(case 4b) |
| `dac83e3` | §2.36 — CI red 원인 계측 확정 + (6) 의 틀린 서술 정정 |

**smoke 는 41회 red 끝에 green 이 됐고, 세 커밋 연속 유지된다.**

## 3. 무엇이 문제였나

`_cross_verify_ci_mypy` 의 verdict 를 보는 검사 4곳이 **매트릭스의 한 행만 정답으로
박아 두고** 있었다. `ci_sanity` 는 "최신 mypy-strict run 이 success 이고 그 headSha 가 HEAD 와
같다" 는 뜻이라, **커밋 직후부터 그 커밋이 CI 를 통과할 때까지는 반드시 `ci_stale`** 이다.
즉 push 직전 — 게이트가 정작 필요한 순간 — 에 구조적으로 통과할 수 없었다.

거울상도 있었다. CI 에서는 `gh` 인증이 없어 verdict 가 `skipped` 로 떨어지는데 그 값은
통과시키는 분기가 있어, **로컬에서만 red / CI 에서만 green** 인 조합이 만들어졌다. 그래서
아무도 못 봤다.

처방은 일관되게 하나다 — **관측한 값은 알려진 집합에 드는지만 보고, 매핑·매트릭스는 주입으로
검증한다.** 느슨하게 푸는 변경이므로 반대 방향(결함 주입 → FAIL)으로 확인했다.

## 4. 내가 틀린 것

§2.35 (6) 을 쓸 때 CI 실패 원인을 `local_mypy` 로 단정했다. **관측이 아니라 추측이었다.**
근거로 삼은 `local_mypy=FAIL` 문자열은 *내 로컬 시스템 python3* (mypy 없음) 의 출력이었고,
CI 의 실제 사유는 (7) 의 excerpt 결함 때문에 아무 데도 남아 있지 않았다.

계측해 보니 CI 에서 mypy 는 처음부터 정상이었다(`raw rc=0`, `_check_local_mypy` 3회 모두
`ok=True`). 진짜 변수는 `ci_mypy=skipped` 였다. 즉 **§2.35 (8) 의 처방이 이 red 를 고친
것은 맞지만, 그때 적어 둔 인과는 틀렸다. 그건 운이지 방법이 아니다.**

## 5. 계측 방법 (재사용 가능)

CI 안의 값을 봐야 하는데 로그에 안 남을 때:

1. `smoke.yml` 이 `branches: ["**"]` 에서 도는 성질을 이용해 **임시 브랜치**에 진단 probe 를 얹는다
2. probe 는 **실패 표지 줄**(`FAIL ...`)로 출력하고 항상 exit 1 — `_error_excerpt` 가 400자까지 싣는다
3. 예산이 모자라면 probe 를 **여러 개로 쪼갠다** (검사당 400자)
4. 아티팩트(`smoke-result.json`)를 받아 `error_excerpt` 를 읽고, **브랜치를 삭제한다**

(7) 의 excerpt 수정이 없었으면 이 계측 자체가 불가능했다. 관측성 수정은 그 자체로 값을 한다.

시간도 증거가 된다 — 실패 run 7.04초 vs 정상 36.1초. 정상이면 mypy 를 4회 부르므로,
소요 시간만으로 "어디까지 갔는지" 를 좁힐 수 있었다.

## 6. 이 세션에서 새로 발견한 결함 (미조치)

1. **`backlog-update --apply` 가 state.json 을 손상시킨다.** 긴 `recent_done_items` 2건을
   조용히 지우고 새 항목은 추가하지 않았다. `written_paths` 는 4개 중 2개만 보고하고,
   `--validation-result` 는 산출물에 렌더되지 않으며, handoff 의 in_progress/blocked 에는
   빈 bullet 을 계속 덧붙인다. **stable 선언 skill 이 상태 문서를 파괴하는 것이라 우선순위 높다.**
   이번 세션은 손으로 되돌려 갱신했다.
2. **슬래시(`/`) 가 들어간 브랜치**에서 `check_branch_scoped_memory` 와
   `check_self_application` 이 깨진다 (probe 브랜치에서 실측). main 에서는 안 드러난다.
3. 스케줄 workflow 2건(`consumer-metrics-digest`, `okf-validate`) 여전히 red — 별건.

## 7. 남길 원칙

- **로컬 재현의 출력과 CI 의 출력은 다른 증거다.** 하나를 다른 하나로 적지 않는다.
- **`gh` 인증 유무는 verdict 를 바꾸는 1급 환경 변수다.** CI 에서는 `skipped`, 로컬에서는
  `ci_sanity`/`ci_stale`. verdict 를 보는 검사는 전부 집합 검사 + 주입 검증이어야 한다.
- **"전량 PASS" 는 언제 쟀는지까지가 사실이다.** 커밋 전에 잰 217/217 은 커밋 후에는 성립하지
  않았다. 게이트는 *push 직전 상태*에서 통과해야 의미가 있다.
