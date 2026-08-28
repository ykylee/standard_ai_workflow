---
type: decision
status: accepted
adr_id: ADR-028
decided_at: 2026-08-28
alternatives_considered: [builtins-open-instrumentation, os-level-tracing, separate-meta-check-rerun]
related_pages: [decisions/adr-027-roadmap-wbs-sdlc]
created: 2026-08-28
updated: 2026-08-28
r9_skip: true
---

# ADR-028: WATCHES 선언 메타 검증 — audit hook 채취 + 러너 내장 전수

## Status

**Accepted** (2026-08-28, requirements sign-off 를 받은 design 단계 결정 —
TASK-2026-08-28-main-006, M-010/WBS-10.1). requirements 정본은
`docs/planning/test-impact-tiering-requirements-2026-08.md`, kit 계약 정본은
`workflow-source/core/test_impact_tiering_spec.md`. 이 페이지는 결정과 근거만
기록한다.

## Context

`--changed` 선택 실행(2026-08-14)은 검사의 `WATCHES` 선언과 git 변경 경로의
교집합으로 실행 대상을 고른다. 유일한 위험 실패 모드는 **좁은 선언** — 실제로
읽는 경로가 선언 밖이면 그 검사가 조용히 skip 된다 (requirements R3.1).
선언이 실제 입력 표면과 맞는지 재는 수단이 없으면 선언은 낡고, "조용히 안
도는 검사" 가 로컬 green + CI red 의 모양으로 돌아온다.

requirements sign-off 가 형태를 고정했다: 채취는 실측이어야 하고(R3.2, 정적
추정 금지), 상시 전수를 우선하되 실측이 상한을 넘으면 표본 순환으로
강등하며(R3.3), 좁은 선언만 red 다 (넓은 선언은 warn — R3.1).

## Decision

1. **채취 = Python `sys.addaudithook`.** 대상 이벤트는 `open` · `os.stat` ·
   `os.scandir` · `os.listdir` · `glob.glob` · `os.walk`. 저장소 밖 경로와
   인프라 경로(`.git` / `.venv*` / `__pycache__` / temp)는 채취에서 제외한다.
2. **주입 = 러너의 spawn 환경.** 러너가 검사 프로세스를 띄울 때
   `PYTHONPATH` 에 sitecustomize 디렉터리를 앞세우고 출력 경로를 env 로
   넘긴다 — 자식 **python** 프로세스까지 같은 훅이 전파된다 (실측 확인).
   비-python 자식(git 등)의 파일 접근은 채취 범위 밖이며, 이는 한계로
   문서화한다 (git 의 주 접근은 `.git` — 어차피 인프라 제외 대상).
3. **판정 = 러너 내장 전수.** 별도 메타 검사가 검사들을 재실행하는 것이
   아니라, **게이트 실행 자체가 채취를 겸한다** — 오버헤드 실측 <1% 라
   상시 전수가 성립한다. 게이트 종료 후 `WATCHES` 선언 검사에 대해
   (채취된 파일 접근) − (선언 glob ∪ 자기 파일 ∪ import 표면) 차집합이
   비어 있지 않으면 **red**, 역방향(선언했으나 접근 없음)은 **warn**.
4. **import 표면은 입력 표면이다.** `__pycache__/<m>.pyc` 접근은 `<m>.py` 로
   역매핑해 표면에 넣는다 — kit 모듈을 import 하는 검사는 그 모듈 경로를
   선언에 포함해야 한다 (`workflow-source/workflow_kit/*` 같은 넓은 glob 허용
   — 넓은 쪽 오차는 안전).
5. **전역 선언 리터럴 = `WATCHES_ALL_REASON = "<근거>"`.** (requirements
   R1.3 sign-off 형태의 리터럴 확정.) 이 선언이 있는 검사는 항상 실행하고
   메타 판정에서 제외한다. `WATCHES` 와 동시 선언은 모순 — 검사 저작 오류로
   red.
6. **전수/순환 판정 기준 = 게이트 벽시계 증가 5%.** 채취 활성 게이트가
   비활성 대비 5% 를 넘게 느려지는 것이 2회 연속 실측되면 표본 순환(회당
   1/N, N주기 안에 전 선언 검사 1회 보장)으로 강등한다. 현재 실측은 <1%
   (아래 표)라 상시 전수로 시작한다.

## Alternatives Considered

| 후보 | 포착 범위 | 오버헤드 | 크로스 플랫폼 | 판정 |
|---|---|---|---|---|
| **audit hook** (채택) | open/stat/scandir/listdir/glob/walk + python 자식(주입 시) — 실측: 0.05s 검사에서 52건, 2.3s 검사에서 201건 채취 | **실측 <1%** (2.28s 검사 3회 대조: 2.27–2.29 vs 2.28–2.29s) | CPython 3.8+ 표준, win32 포함 | ✅ |
| `builtins.open` 계측 | `open` 만 — `os.listdir`/`scandir`/`stat` 경유 접근을 구조적으로 놓친다 (archive 검사 실측 201건 중 다수가 scandir/stat) | 유사 | 가능 | ⛔ 포착 범위 열세 |
| OS 레벨 트레이스 (fs_usage/dtrace/strace) | 전 프로세스 (비-python 자식 포함) | 큼 (전 syscall) | ⛔ macOS 는 sudo 필수, Windows 대응물 부재 — kit 은 Windows 를 지원한다 (M-007/WBS-7.1 축 실측 중) | ⛔ 플랫폼 탈락 |
| 별도 메타 검사가 재실행 | audit hook 과 동일 | ⛔ 검사 전량 2회 실행 = 게이트 ~2배 | 가능 | ⛔ R3.3 상한 위반 |

## Consequences

- 러너가 채취 주입·수집·판정을 갖는다 — 구현은 M-011 (implementation) 로.
- **첫 채취 실측이 이미 좁은 선언 1건을 찾았다**: `check_handoff_next_steps`
  의 `WATCHES` 는 memory 경로 2개만 선언하는데, 채취는 kit 모듈 import
  (`workflow-source/workflow_kit/*`) 를 보였다 — kit 의 handoff 파서가 바뀌어도
  이 검사는 `--changed` 에서 skip 된다. 구현 시 이 선언부터 교정한다 (결정 4
  의 실증 사례).
- 판정 red 의 진단에는 차집합 경로가 실린다 ("불일치" 라고만 말하지 않는다 —
  requirements R3.5).
- 되주입 실증(일부러 좁힌 선언으로 red 확인)이 구현의 완료 기준에 들어간다.

## References

- `docs/planning/test-impact-tiering-review-2026-08.md` (concept, C안 결정)
- `docs/planning/test-impact-tiering-requirements-2026-08.md` (R0~R6 + sign-off)
- `workflow-source/core/test_impact_tiering_spec.md` (kit 계약 정본)
- TASK-2026-08-14-main-003 (`--changed` + `WATCHES` 구현) ·
  TASK-2026-08-14-main-004 (게이트 축소 기각 — 본 축의 불변 조건)
