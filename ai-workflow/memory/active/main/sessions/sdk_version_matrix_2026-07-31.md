# 세션 기록 — 커버리지가 넓은 것과 넓다고 말할 수 있는 것 (2026-07-31)

- 문서 목적: 이 세션이 무엇을 결정하고, 무엇을 재고, 무엇을 남겼는지 다음 세션이 이어받게 한다.
- 범위: TASK-2026-07-31-main-001 (§2.45)
- 대상 독자: AI agent, 저장소 관리자
- 상태: closed
- 최종 수정일: 2026-07-31
- 관련 문서: [state.json](../state.json), [session_handoff.md](../session_handoff.md),
  [TASK-2026-07-31-main-001](../backlog/tasks/TASK-2026-07-31-main-001.md),
  `workflow-source/releases/Beta-v1.0.0.md` §2.45,
  `workflow-source/workflow_kit/common/sdk_matrix.py`

## 1. 시작 지점

`ea1576c` 기준선에서 저장소 현황 파악부터. push CI 5종은 green 실측이었고, 열린 항목
8건 중 §2.43 이 남긴 첫 번째 — "핀 해제로 CI 가 두 major 를 동시에 밟는다. 커버리지는
넓어졌지만 여전히 설치 순서에 기댄 우연이다" — 를 열었다.

## 2. 결정

**우연을 없애는 대신 선언한다.** 세 job 의 버전이 서로 다른 것 자체는 좋다(하한과
최신을 동시에 밟는다). 문제는 그렇게 정한 사람이 없다는 것이었다. 그래서 버전을
바꾸지 않고 **정책을 적었다** — `pinned` / `floating` / `matrix`, 그리고 그 버전이
*어디서 오는지*.

**floating 을 없애지 않는다.** 상한 없는 설치가 mcp 2.0.0 을 CI 로 끌고 들어왔고 그래서
§2.41~§2.44 를 할 수 있었다. 나쁜 것은 부동인 것이 아니라 **부동인 줄 몰랐던 것**이다.
부동은 부동이라고 적고, 집힌 값을 step summary 첫 화면에 남긴다.

**yml 에 버전을 적지 않는다.** `prepare` job 이 registry 에서 목록을 뽑아 `fromJson`
으로 matrix 를 만든다. 복제가 없다는 것 자체를 검사가 본다.

## 3. 잰 것

- 격리 venv 3종(`1.27.0` / `1.29.0` / `2.0.0`): 요청=설치 일치, mcp subset 12/12,
  SDK 왕복 증거 2/2.
- smoke 의 설치 3줄을 **매 줄 관측**: `requirements.txt` 뒤 2.0.0 → `requirements-dev.txt`
  뒤 1.27.0 → editable install 뒤 1.27.0. 이 세 줄이 "우연" 의 실체다.
- mypy strict 121 files 0 errors (1.27.0 / 2.0.0, mypy 2.1.0, `--config-file` 명시).
- 전량 smoke **224/224** (`dev,release,mcp-sdk` venv, 누수 0, 워킹트리 변경 0).
- 되주입 7건이 각각 다른 신호로 실패. SDK 미설치 환경에서 `--assert-exercised` 는
  두 검사 모두 "증거가 없다" 로 실패.

## 4. 이 세션이 배운 것

**판정을 두 번 버렸다.** 처음엔 출력에서 "skip 처럼 보이는 말" 을 찾았는데 위양성이
났다 — `check_mcp_server_sdk_compat.py` 는 "둘 다 없을 때 fail-fast 하는가" 를
*의도적으로* 확인하느라 SDK 가 깔린 환경에서도 "SDK not installed" 를 출력한다. 다음엔
`run_all_checks --json` 의 `last_line` 에서 성공 메시지를 찾았는데, mcp 1.x 가 서버
로그를 stderr 로 뒤에 붙여서 성공한 검사의 마지막 줄이 성공 메시지가 아니었다.
결국 **판정이 자기 측정을 직접 하게** 했다. 남이 요약해 준 필드는 그 요약이 무엇을
버리는지 모른 채 쓰게 된다.

**matrix 가 만들자마자 실제 결함을 잡았다.** `check_read_only_mcp_sdk_stdio.py` 가 2.x
에서 깨져 있었다 — 서버는 §2.43 에서 이관했는데 **읽는 쪽은 범위 밖**이었다. §2.41 의
"이관 범위를 파일 하나로 잡았다" 와 같은 모양이 한 번 더 나왔다. 이번엔 고치기 전에
전수 sweep 부터 했고, 클라이언트 표면은 하나였다.

**수치에는 환경을 함께 적는다.** 같은 트리가 `release` extra 없는 venv 에서는 219/224
다. 이 중 2건은 `build` 부재, 3건은 문서가 아직 223 이라 적고 있어서였다.

## 5. 남긴 것

- 새 major 조기 경보는 **여전히 floating job 에 의존**한다. 의도한 설계지만, 그 job 이
  path 필터로 안 돌면 경보도 안 온다 (`mcp-inspector` 가 그렇다).
- `backlog-update` 가 handoff §4 에 상한을 적용하지 않는 문제가 **연속 2회 재발**했다.
  close-out 마다 손으로 1건 지우고 있다 — 도구 쪽에서 자르게 할지가 다음 후보다.
- CI 러너에서의 `mcp-sdk-matrix` 실행은 push 후 확인해야 한다.
