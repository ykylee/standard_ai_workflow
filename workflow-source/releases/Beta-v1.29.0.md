# Beta v1.29.0 (2026-11-20)

> **상태: 릴리스 준비.** package `1.29.0`, runtime `__version__ = 1.29.0`, tag `v1.29.0`.
> **minor release** — 읽기 전용 소비자 클론에서 `session-start` 가 저장소에 쓰지 않는다.
>
> 등급 근거 (§1.5): v1.28.0 이후 코드 커밋 1 — feat 1, breaking 0 — **minor**.
> 공개 Python API 시그니처 제거 0, 진입점 제거 0. `workflow_kit.common.host_role` 모듈은 **추가**다 — v1.28.0 의 `gate_evidence.host_role` 은 같은 함수를 다시 내보내 이름이 그대로 남는다.
> **동작이 바뀌는 곳 둘** (이 저장소 한정, 킷을 설치해 쓰는 다른 프로젝트에는 영향 없음):
> - `session-start` 가 `workflow.role=consumer` 인 클론에서 저장소에 쓰지 않는다(§2.1).
> - 역할 판정이 클론의 **로컬 설정(`git config --local`)만** 읽는다. v1.28.0 은 `git config --get` 이라 전역 `~/.gitconfig` 값도 읽었다 — 전역에만 `workflow.role` 을 둔 호스트는 이제 미선언으로 다뤄진다(push 차단도 걸리지 않는다). 클론마다 `git config --local workflow.role <역할>` 로 다시 선언한다.

## 0. 릴리스 판정

v1.28.0 이후 코드 1커밋(메모리 · 세션 커밋 제외)이다. 소유자 지시 — "소비자 클론이면 session-start 가 쓰지 않게 하자" — 로
v1.28.0 노트 §4 의 알려진 한계(소비자 클론에서도 세션 시작이 생성물을 다시 써 트리가 더러워질 수 있다)를 도구 쪽 방어로 바꿨다.

## 1. 릴리스 요약

- 범위: `v1.28.0..` **1 commit** — feat 1 (+ 메모리 · 세션 커밋 3 — v1.28.0 발행 완료 `b05dec29` 포함 · 발행 준비 1).
- 누적 smoke **333/333 PASS** (로컬 `--branch-context=all` = 333 × native/slash).
- 검사 파일 수 332 → 333 (`check_consumer_readonly_session_start` 6 cases 추가).

## 2. 소비자에게 보이는 변화

### 2.1 소비자 클론에서 `session-start` 는 저장소에 쓰지 않는다 (`cb31e317`, `docs/HOST_ROLES.md` §4)

- `workflow.role=consumer` 이면 쓰기 다섯 가지를 건너뛴다 — 브랜치 메모리 seed, 기본 브랜치의 합류 반영 · 아카이브
  (`--archive-stale-branches` 를 줘도), 부재 진입점 생성(조기 실패 경로 포함), 워크벤치 자동 기동, memory_index telemetry.
- 출력 `warnings` 첫 줄에 읽기 전용 클론임과 `docs/HOST_ROLES.md` §3 을 알린다. 기준선을 못 찾아 실패하는 경로에서도 같고,
  그때 `recovery_hint` 는 쓰기 명령을 권하지 않는다.
- 읽기(기준선 · 다음 작업 후보 보고)는 그대로다. 미선언 · `contributor` 클론은 이전 동작 그대로다.

### 2.2 역할 판정 정본 하나 — `workflow_kit.common.host_role`

- pre-push hook(`gate_evidence`)과 `session-start` 가 같은 함수를 쓴다. 값은 대소문자를 가리지 않는다.
- 로컬 설정만 읽는다 — 위 '동작이 바뀌는 곳' 참조. `CLAUDE.md` · `AGENTS.md` · `HOST_ROLES.md` 의 확인 명령도 `git config --local --get workflow.role` 로 맞췄다.

## 3. 검증

- **전량 게이트** `--branch-context=all` — native 333/333 · slash 333/333 · rc 0. 결과는 게이트 증거 파일(`<git common dir>/gate_evidence/<sha>.json`)에 남는다.
- **커밋 전** `--changed` 게이트 · **스모크** `check_self_application`.
- `check_consumer_readonly_session_start` 6 cases: 실행 전후 작업 트리 전체(git 무시 파일 포함)를 비교하고, 경로마다 역할 없이 돌린 대조군이 실제로 쓰는지 같이 잰다.
  수리 지점을 하나씩 되돌린 되주입 12건이 각각 red. verifier 2회 — 1차가 찾은 사각 3곳(조기 실패 경로의 진입점 생성 · `--archive-stale-branches` · 워크벤치 자동 기동)과
  오류 경로 안내 누락, 2차가 찾은 `recovery_hint` 사각을 고친 뒤 다시 red 를 확인했다.
- 이 저장소의 실제 클론에서 소비자로 선언하고 `session-start` 를 돌려 바뀐 파일 0 을 확인했다.
- 발행 호스트: Linux.

## 4. 알려진 한계 (감추지 않는다)

- **워크벤치 자동 기동 차단은 검사용 설정(기동이 곧 실패하는 argv)으로만 쟀다** — 서버가 실제로 뜨는 설정에서 소비자 클론을 잰 적은 없다.
- **소비자 클론의 첫 pull 은 옛 `CLAUDE.md` · 옛 킷으로 시작한다** — 이 판 이전 킷의 `session-start` 는 소비자 클론에도 쓴다. 소유자가 그 호스트에 한 번 지시하거나 역할을 직접 선언해야 한다.
- 하네스의 세션 시작 hook 이 `session-start` 를 거치지 않고 생성물을 쓰는 경로가 있다면 이 방어 밖이다(이번 판에서 별도로 재지 않았다).
- push 차단은 `git config core.hooksPath .githooks` 가 켜진 클론에서만 걸리고 `--no-verify` 는 막지 못한다.
- **브랜치 네임스페이스 자동 seed 가 `roadmap_state.json` 을 재생성하지 않는다** — 미수리, `TASK-2026-11-19-claude-remote-sync-check-234c32-002`.
- **Windows 실측은 이번 판에도 없다** (M-028/WBS-28.3).
- **PyPI 업로드는 하지 않는다**(§1 각주 0 — 2026-08-14 소유자 최종 결정). 배포는 GitHub Releases 하나다.
