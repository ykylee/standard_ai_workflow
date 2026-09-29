# Beta v1.14.1 (2026-09-29)

> **상태: 릴리스 준비.** package `1.14.1`, runtime `__version__ = 1.14.1`, tag `v1.14.1`.
> **patch release** — **MiniMax Code 하네스를 쓰는 프로젝트에서 `wk session-start` 가 매 세션
> 빈 bootstrap task 를 만들던 결함 수리 (GitHub #29) + `wk backlog-update` 이월 표식 수리.**
>
> 등급 근거 (§1.5): `wk release-status` 는 fix 2 · feat 0 · breaking 0 으로 **1.14.1 (patch)** 을
> 제안하고 그대로 따른다. 공개 Python API 시그니처 변경 0, 진입점 증감 0.

## 0. 릴리스 판정

#29 는 이미 도입된 소비자 프로젝트에서 **거래일마다** 빈 `planned` task 와 daily index 줄이
생기고 `state.json` 이 바뀌는 결함이다. 소비자는 매 세션 정리 스크립트로 우회하고 있었다.
수리가 닿는 길은 새 kit 배포뿐이라 발행한다.

## 1. 릴리스 요약

- 범위: `v1.14.0..` 발행 준비 직전까지 **3 commit**. 이 중 1건(`8b434f4b`)은 **v1.14.0 발행
  마무리**가 태그 뒤에 착지한 것이라 실질은 **2 commit** 이다.
- 누적 smoke **296/296 PASS** (로컬 `--branch-context=all` = 296 × native/slash).
- 검사 **296 → 296** (신설·은퇴 없음 — 기존 검사에 case 추가).

## 2. 소비자에게 보이는 변화

### 2.1 `session-start` 가 빈 bootstrap task 를 만들지 않는다 (GitHub #29, TASK-2026-09-29-main-002)

사슬이 둘이었다.

1. **선언과 출력의 대소문자 불일치.** `HARNESS_SPECS["minimax-code"]` 는 `.minimax/agents/*`,
   `minimax_config_example.json` 을 선언했는데 렌더러는 `.MiniMax/agents/*`,
   `MiniMax_config.example.json` 에 썼다. 대소문자 구분 FS(Linux ext4 등)에서 6건이 **영구
   부재**로 분류됐다. macOS 기본(APFS, 비구분)에서는 드러나지 않는다. 선언을 실제 출력
   (`.MiniMax`)으로 맞췄다. 전 하네스를 전수 조사해 **grok-build · minimax-code 가 `AGENTS.md`
   를 선언만 하고 쓰지 않던 것**도 걷었다 — codex/opencode 채널이 쓰는 공유 파일이라 단독
   프로젝트에서 같은 반복을 냈다.
2. **부재 채우기가 bootstrap 전체를 돌렸다.** `wk ensure-entrypoints --apply`(세션 시작의 자기
   복구)가 `--create-missing-only` bootstrap 을 통째로 실행해, 도입일과 날짜가 다르면 오늘
   날짜의 초기 task · daily index 가 새로 생기고 `state.json` 이 다시 쓰였다. 이제 bootstrap 의
   새 `--only-paths` 로 **선언된 부재 파일만** 쓴다 — 상태 문서 · `state.json` ·
   `roadmap_state.json` 재생성은 그 범위 밖이다.

부수: bootstrap 매니페스트 `file_actions` 에 같은 경로가 두 번 실리던 것(13건)을 걷었다.

**적용**: kit 을 1.14.1 로 올리면 다음 세션부터 반복이 멈춘다. 이미 생긴 빈 task 파일과
daily index 줄은 자동으로 지우지 않는다(소비자 기록일 수 있다) — 손으로 정리한다. MiniMax
하네스 문서의 프로젝트 로컬 경로 표기도 `.MiniMax/` 로 맞췄다.

### 2.2 `wk backlog-update` 이월이 task 의 kind 를 따른다 (TASK-2026-09-29-main-001)

update 에서 `--kind` 를 생략하면 task frontmatter 의 kind 는 보존됐지만, 날짜 경계를 넘은
이월로 새 daily index 에 생기는 줄의 표식은 `[generic]` 이었다 — 같은 task 가 두 index 에서
다른 작업으로 보였다. 이제 `--kind` > frontmatter `kind` > `generic` 순으로 정한다.

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- #29: `check_ensure_entrypoints` case 5(전 하네스 선언 ↔ 단독 bootstrap 출력, 대소문자 정확
  비교) · case 6(부재 채우기가 선언된 파일 하나만 만들고 `state.json` 불변, 도입일을 과거로 둔
  fixture) · case 7(매니페스트 중복 0). 되주입 5종(소문자 선언 / grok `AGENTS.md` 선언 /
  `--only-paths` 제거 / 중복 제거 해제 / state.json 가드 해제) 각각 red
- 이월 kind: `check_backlog_carry_over` case 6(`kind: release` 이월 → `[release]`), 옛 줄
  되주입 시 red

## 4. 알려진 한계 (감추지 않는다)

- MiniMax Code CLI 가 프로젝트 로컬에서 **어느 대소문자 경로를 읽는지는 미실측**이다. `.MiniMax`
  는 이미 설치된 파일을 인정하는 쪽의 결정이다.
- Antigravity 에서 MCP 도구의 실제 **호출**은 여전히 재지 않았다 (v1.14.0 한계 그대로).
- **Windows 는 현재 미측정이다** (`TASK-2026-08-25-main-017` blocked).

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-09-29T02:21:59Z)_

- total wiki pages: **96**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
