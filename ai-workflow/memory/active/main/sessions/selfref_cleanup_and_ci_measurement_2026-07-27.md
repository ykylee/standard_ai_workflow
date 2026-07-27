# 세션 기록 — 남은 자기참조 해소 + CI red 원인 계측 (2026-07-27)

- 문서 목적: 이 세션이 무엇을 재고, 무엇을 틀렸고, 무엇을 남겼는지 다음 세션이 이어받게 한다.
- 범위: TASK-2026-07-27-main-003 / -004 (§2.35 (6)~(8), §2.36, §2.37)
- 대상 독자: AI agent, 저장소 관리자
- 상태: closed
- 최종 수정일: 2026-07-27
- 관련 문서: [state.json](../state.json), [session_handoff.md](../session_handoff.md),
  [TASK-2026-07-27-main-003](../backlog/tasks/TASK-2026-07-27-main-003.md),
  [TASK-2026-07-27-main-004](../backlog/tasks/TASK-2026-07-27-main-004.md),
  `workflow-source/releases/Beta-v1.0.0.md` §2.35~§2.37

## 1. 시작 지점

직전 세션이 남긴 시작 포인트는 *"푸시 후 CI 확인. 자기참조를 없앴으니 smoke 가 green 이어야
한다 — 아니면 다른 원인이다."* 였다. 실제로는 **다른 원인**이었고, 그 한 줄이 이 세션 전부다.

## 2. 한 일

| 커밋 | 내용 |
|---|---|
| `44b1b78` | §2.35 (6)(7) — `local_mypy=ok` 환경 의존 제거 + 실패 사유가 늘 잘려 나가던 excerpt |
| `fbca6d7` | §2.35 (8) — 같은 자기참조 2건 추가 해소 + 매트릭스 7행 주입 검증(case 4b) |
| `dac83e3` | §2.36 — CI red 원인 계측 확정 + (6) 의 틀린 서술 정정 |
| `2f20cb5` | memory close-out (TASK-2026-07-27-main-003 + 이 세션 기록) |
| `fbdc8f9` | §2.37 — backlog-update 결함 4건 + 정본 검사 구멍 |

**smoke 는 41회 red 끝에 green 이 됐다** (`dac83e3` 에서 확인). 이후 커밋의 CI 는
사용자 요청으로 확인을 중지했다 — §7 4번 참조.

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

## 6. 발견하고 **같은 세션에서 고친** 결함 — backlog-update (§2.37)

close-out 을 저장소 자체 skill 로 하려다 `backlog-update --apply` 가 **`state.json` 의
`recent_done_items` 를 10건 → 8건으로 줄이고 새 항목은 추가하지 않는 것**을 봤다.
`status: ok` 였다. 발견 계기는 결과를 믿지 않고 `git diff` 를 읽은 것 하나다.

근본 원인은 또 **규약 사본**이었다. `normalize.WORK_ITEM_ID_RE` 가 정본
`project_docs.WORK_ITEM_ID_PATTERN` 의 사본이고 문자 클래스가 대문자 전용이라,
branch-scoped ID 의 소문자 브랜치 segment 에서 매치가 끊겨 같은 날짜 task 가 전부 한
dedupe key 로 뭉개졌다. `state.json` 은 자기 내용이 다시 입력으로 도는 구조라 영구 소실이다.

§2.24 의 규약 단일 출처 검사가 이걸 잡았어야 했는데, 탐지 리터럴이 `TASK-` 문자열을 찾고
사본은 `(?:TASK|WF)-` 라 **교대 표기로 탐지를 빠져나갔다**. 리터럴을 넓히고, 면제 판정을
코드에서만 하도록(주석 언급으로 통과하던 구멍) 함께 고쳤다.

같은 실행에서 `written_paths` 미보고(4개 중 2개), `--validation-result` 유실, handoff 빈
bullet 누적도 나왔다. 마지막 건은 `- ` 가 strip 하면 `-` 라 `startswith("- ")` 를 통과하지
못해 **교체가 아니라 삽입**이 되던 것이고, 고치는 도중 빈 bullet 이 *우연한 방벽* 이었음이
드러나(다음 구간 라벨을 항목으로 삼킴) 종결 조건을 명시했다.

회귀 테스트는 `check_writer_reader_roundtrip` 에 pair 로 넣었고, 되주입 시 정확히 실패한다.
수정 후 **이 도구로 직접 close-out 을 다시 해서**(dogfood) 같은 날짜 task 4건이 모두
살아남는 것을 확인했다.

## 7. 남은 결함 (미조치)

1. **`recent_done_items` 는 파생물 + 10개 상한.** 손으로 쓴 긴 서술은 다음 실행에서 짧은
   형태로 재생성돼 사라진다 — 상세의 집은 task SSOT 와 릴리스 노트다. 정렬이 시간순이
   아니라 오래된 항목이 남고 최근 항목이 밀린다 (`TASK-2026-07-22-003` 이 밀려났다).
2. **슬래시(`/`) 가 들어간 브랜치**에서 `check_branch_scoped_memory` 와
   `check_self_application` 이 깨진다 (probe 브랜치에서 실측). main 에서는 안 드러난다.
3. 스케줄 workflow 2건(`consumer-metrics-digest`, `okf-validate`) 여전히 red — 별건.
4. `dac83e3` 이후 커밋의 CI 는 **확인하지 않았다** (사용자 요청으로 중지). 다음 세션이 먼저
   볼 것 — `gh run list --commit $(git rev-parse HEAD)`, **full SHA 필수**.

## 8. 남길 원칙

- **로컬 재현의 출력과 CI 의 출력은 다른 증거다.** 하나를 다른 하나로 적지 않는다.
- **`gh` 인증 유무는 verdict 를 바꾸는 1급 환경 변수다.** CI 에서는 `skipped`, 로컬에서는
  `ci_sanity`/`ci_stale`. verdict 를 보는 검사는 전부 집합 검사 + 주입 검증이어야 한다.
- **"전량 PASS" 는 언제 쟀는지까지가 사실이다.** 커밋 전에 잰 217/217 은 커밋 후에는 성립하지
  않았다. 게이트는 *push 직전 상태*에서 통과해야 의미가 있다.
