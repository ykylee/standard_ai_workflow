# Beta v1.14.2 (2026-09-29)

> **상태: 릴리스 준비.** package `1.14.2`, runtime `__version__ = 1.14.2`, tag `v1.14.2`.
> **patch release** — **codex 가 쓴 공유 `AGENTS.md` 때문에 opencode 가 "적용된 하네스" 로
> 판정돼, 세션 시작이 요청하지 않은 opencode 오버레이를 만들던 결함 수리.**
>
> 등급 근거 (§1.5): `wk release-status` 는 fix 1 · feat 0 · breaking 0 으로 **1.14.2 (patch)** 를
> 제안하고 그대로 따른다. 공개 Python API 시그니처 변경 0, 진입점 증감 0.

## 0. 릴리스 판정

v1.14.1 발행 wheel 로 GitHub #29 시나리오를 격리 실측하던 중 발견했다. codex + minimax-code
로 도입한 프로젝트에서 첫 `wk session-start` 가 `opencode.json` 과 `.opencode/` 6건을 "부재
진입점" 으로 생성했다. #29 를 보고한 프로젝트처럼 codex 와 다른 하네스를 함께 쓰는 소비자에게
요청하지 않은 파일이 생기므로 바로 발행한다.

## 1. 릴리스 요약

- 범위: `v1.14.1..` 발행 준비 직전까지 **2 commit**. 이 중 1건(`151fa7ac`)은 **v1.14.1 발행
  마무리**가 태그 뒤에 착지한 것이라 실질은 **1 commit** 이다.
- 누적 smoke **296/296 PASS** (로컬 `--branch-context=all` = 296 × native/slash).
- 검사 **296 → 296** (신설·은퇴 없음 — 기존 검사에 case 추가).

## 2. 소비자에게 보이는 변화

### 2.1 공유 진입 파일의 마커로 다른 하네스를 적용 판정하지 않는다 (`bd78a2ad`, TASK-2026-09-29-main-004)

"어느 하네스가 적용됐는가" 는 "선언 파일 중 하나라도 kit 버전 마커가 있으면 적용" 이었다.
`AGENTS.md` 는 codex · opencode · pi-dev 가 함께 선언한 공유 파일이라, codex 가 쓴 마커 하나가
opencode 까지 적용으로 만들었다. 같은 규칙이 `wk ensure-entrypoints` 와 `wk doctor` 에 따로
복제돼 있었다.

이제 판정 정본은 `workflow_kit.common.harness_presence` 하나이고 두 도구가 함께 읽는다.

- 그 하네스만 선언한 **고유 파일**에 마커가 있으면 적용이다. 확장자상 마커를 달 수 없는 고유
  파일(`.codex/config.toml.example`, `opencode.json` 등)은 존재를 증거로 센다.
- 공유 파일의 마커는 고유 파일로 적용이 확인된 하네스의 몫이다. 확인된 하네스가 없을 때만
  고유 파일이 없는 하네스(pi-dev)를 적용으로 본다.

**적용**: kit 을 1.14.2 로 올리면 다음 세션부터 opencode 오버레이가 생기지 않는다. 이미 생긴
`opencode.json` · `.opencode/` 는 자동으로 지우지 않는다 — opencode 를 쓰지 않으면 손으로
지운다. `wk doctor` 의 `applied_harnesses` 가 바뀔 수 있다: 공유 파일로만 잡히던 하네스는
`candidate_harnesses` 로, 마커 없는 `.codex/config.toml.example` 이 있는 프로젝트는 codex 가
적용으로 옮긴다.

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- `check_ensure_entrypoints` case 8: codex 단독 → 적용 `[codex]` · 부재 0 · `--apply` 가 opencode
  생성 0 · `AGENTS.md` 삭제 시 codex 의 부재로 잡음 · `wk doctor` 같은 판정, pi-dev 단독 →
  적용 `[pi-dev]`. 되주입 3종(옛 규칙 / 마커 불가 파일의 존재 무시 / 고유 파일 없는 하네스
  fallback 제거) 각각 red
- `check_deploy_doctor` 52/52

## 4. 알려진 한계 (감추지 않는다)

- codex 와 pi-dev 를 함께 적용한 프로젝트에서 pi-dev 는 파일로 구별되지 않아 후보로 남는다.
  pi-dev 의 선언은 `AGENTS.md` 하나라 복구할 것도 없다.
- MiniMax Code CLI 가 프로젝트 로컬에서 어느 대소문자 경로를 읽는지는 여전히 미실측이다.
- **Windows 는 현재 미측정이다** (`TASK-2026-08-25-main-017` blocked).
