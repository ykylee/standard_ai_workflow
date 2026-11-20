# Beta v1.28.0 (2026-11-20)

> **상태: 릴리스 준비.** package `1.28.0`, runtime `__version__ = 1.28.0`, tag `v1.28.0`.
> **minor release** — 이 저장소의 호스트 역할(읽기 전용 소비자 클론의 push 차단) · 재사용된 브랜치의 재합류 수리.
>
> 등급 근거 (§1.5): v1.27.0 이후 코드 커밋 4 — feat 1 · fix 1 · docs 1 · test 1, breaking 0 — **minor**.
> 공개 Python API 시그니처 제거 0, 진입점 제거 0. `gate_evidence.host_role` · `check_consumer_push` 는 **추가**다.
> **동작이 바뀌는 곳 하나**: 이 저장소의 `.githooks/pre-push` 가 `git config workflow.role consumer` 인 클론의 push 를 게이트 기록과 무관하게 막는다.
> 역할을 선언하지 않은 클론 · `contributor` 는 이전 판정 그대로다. 킷을 설치해 쓰는 다른 프로젝트에는 영향이 없다(그쪽 hook 은 이 판정을 부르지 않는다).

## 0. 릴리스 판정

v1.27.0 이후 코드 4커밋(메모리 · 세션 커밋 제외)이다. 소유자 지시 — "이 저장소의 소비자는 개발 참여자와 읽기 전용 소비자 둘이고,
소비자가 워크플로우 코드를 수정해 반영하려는 경우가 있다 — 소비자는 로컬 환경 맞추기 · 버전 업데이트만 하도록" — 와
134차(macOS 호스트)가 찾아 고친 재합류 결함을 넣었다.

## 1. 릴리스 요약

- 범위: `v1.27.0..` **4 commit** — feat 1 · fix 1 · docs 1 · test 1 (+ 메모리 · 세션 커밋 4 · 발행 준비 1).
- 누적 smoke **332/332 PASS** (로컬 `--branch-context=all` = 332 × native/slash, 발행 준비 커밋에서 실행).
- 검사 파일 수 332 → 332 (새 파일 없음 — 기존 검사에 case 추가: `check_pre_push_gate` 3 → 4, `check_branch_join_reflect` 7 → 10).

## 2. 소비자에게 보이는 변화

### 2.1 호스트 역할 — 읽기 전용 소비자 클론은 push 하지 않는다 (`1fdcddc5` · `289e2124`, `docs/HOST_ROLES.md`)

- **이 저장소(워크플로우 킷 원본) 한정**이다. 클론마다 `git config workflow.role consumer|contributor` 로 역할을 선언한다 —
  `.git/config` 에만 남아 커밋 · push 되지 않는다.
- 소비자는 fast-forward pull · 로컬 환경 맞추기(`.venv` · `core.hooksPath`) · 버전 업데이트(RELEASE §2.8 채널 재적용 · `doctor` 확인)만 한다.
  고칠 것은 이 클론에서 고치지 않고 `docs/FEEDBACK.md` 의 GitHub Issue 로 보낸다(제안 diff 는 본문 텍스트, 이미 고쳤으면 patch 사본 → `git stash`).
- `CLAUDE.md` · `AGENTS.md`: 세션 시작 · pull · 업데이트 전에 `git config --get workflow.role` 을 먼저 본다. 비어 있으면 멈추고 소유자에게 묻는다.
- `.githooks/pre-push` → `gate_evidence.check_consumer_push`: `consumer` 면 올리려는 ref 마다 거절하고 가이드 · 이슈 경로를 알린다.
  값은 대소문자를 가리지 않는다. 그 밖의 값 · 미선언 · `contributor` 는 게이트 기록 판정 그대로다.

### 2.2 재사용된 브랜치의 재합류가 반영 없이 막히고 '이동했다' 로 보고되던 결함 (`7df480f9`)

- `session-start` 의 합류 반영 보고가 archive 도구의 계획이 아니라 **실행 결과**를 말한다 — 옮긴 것만 '이동했다', 못 옮긴 것은 '옮기지 못했다 + 사유'.
- `archived/<branch>/` 가 이미 있으면(같은 브랜치 이름의 두 번째 합류) 오류로 건너뛰던 것을 파일 단위 병합으로 바꿨다. 내용이 갈린 옛 파일은
  같은 디렉터리에 `superseded-<옛 날짜>.<이름>` 으로 남는다(소실 0). `.archived.json` 이 `previous_archived_at` 을 잇는다.
- `check_memory_index_cross_v0_15_7` case 5 대조군이 telemetry 누적량에 따라 반올림에 묻혀 red 가 되던 것을 고쳤다.

## 3. 검증

- **전량 게이트** `--branch-context=all` — native 332/332 · slash 332/332 · rc 0. 발행 준비 커밋의 clean tree 에서 실행하고,
  결과는 게이트 증거 파일(`<git common dir>/gate_evidence/<sha>.json`)에 남는다.
- **커밋 전** `--changed` 게이트 · **스모크** `check_self_application` 8/8 rc 0.
- 호스트 역할: 되주입 3건(hook 경로의 판정 건너뛰기 · 대소문자 정규화 제거 · 역할 무시하고 항상 거절)이 모두 red — 작성 세션과 verifier 가 각각 쟀다.
  verifier 는 역할(미선언 · contributor · consumer · 잘못된 값) × sha(게이트 기록 있음 · 없음)를 hook 으로 직접 실행해 기대 exit 와 맞는지 확인했고,
  그때 드러난 case 의 사각(미선언 · contributor 의 기록 없는 sha)을 case 에 넣었다. `contributor` 로 선언한 이 클론에서 실제 push 가 통과했다.
- 재합류 수리: `check_branch_join_reflect` 7 → 10 cases(수리 전 red 재현), verifier 3건 PASS(134차 기록).
- **게이트 간헐 red 수리 (test)**: 발행 준비 커밋의 첫 게이트에서 `check_workbench_multi` case 3 이 red — 이 호스트의 실제 워크벤치가
  쥔 포트(8766)가 fixture 의 해시 포트와 겹치면 '잴 수 없다' 로 끝났다(단독 3회 중 1회 재현). 막을 수 있는 해시 포트가 나올 때까지
  fixture 를 다시 만든다(최대 20회). 범위 100 중 43 포트를 쥔 채 잰 결과: 수리판 10회 중 red 0 · 재시도 1회(되주입) 10회 중 5회 red.
- 발행 호스트: Linux.

## 4. 알려진 한계 (감추지 않는다)

- **소비자 클론의 첫 pull 은 옛 `CLAUDE.md` 로 시작한다** — 역할 확인 규칙은 pull 뒤에야 보인다. 소유자가 그 호스트에 한 번 지시하거나
  `git config workflow.role consumer` 를 직접 선언해야 한다.
- push 차단은 `git config core.hooksPath .githooks` 가 켜진 클론에서만 걸린다(가이드 §3.3 이 켠다). `--no-verify` 는 막지 못한다.
- 소비자 클론에서도 하네스의 세션 시작 hook 이 생성물(`state.json` · `roadmap_state.json`)의 날짜를 다시 써 트리가 더러워질 수 있다 —
  가이드에 '알려진 잔여'로 적었다. `session-start` 가 `consumer` 면 쓰지 않게 할지는 소유자 결정 대기다.
- **브랜치 네임스페이스 자동 seed 가 `roadmap_state.json` 을 재생성하지 않는다** — seed 커밋 뒤 생성물 대조 검사 2건이 red 다(손으로 `refresh-state`).
  미수리, `TASK-2026-11-19-claude-remote-sync-check-234c32-002`.
- 합류 직후 seed 전 worktree 에서는 `check_branch_context_matrix` 가 native 에서도 7b SKIP 으로 red 가 난다(브랜치 `state.json` 부재를 전제로 둔 검사). 미등록 관찰.
- **Windows 실측은 이번 판에도 없다** (M-028/WBS-28.3).
- **case 수 선언 대조 축은 컨텍스트마다 83건이 미측정**이다(개수 선언 없음 79 · case 줄 없음 4, native · slash 합계 166) — 통과가 아니다.
- **PyPI 업로드는 하지 않는다**(§1 각주 0 — 2026-08-14 소유자 최종 결정). 배포는 GitHub Releases 하나다.
