---
version: alpha
name: Workflow Hub
description: 차분한 운영 콘솔 — 프로젝트 진척과 사람이 결정할 일을 먼저 보이는 허브 화면. 워크벤치 · PC 중계(VS Code)가 같은 값을 따른다.
colors:
  ground: "#f2f4f6"
  surface: "#ffffff"
  surface-2: "#f7f8fa"
  ink: "#17202b"
  ink-2: "#4f5b6b"
  line: "#d5dae1"
  field: "#7d8796"
  shell: "#14233a"
  shell-ink: "#e8edf4"
  shell-ink-2: "#a9b6c8"
  shell-line: "#2a3c55"
  primary: "#1d5fbf"
  accent-soft: "#e6eefa"
  on-accent: "#ffffff"
  ok: "#1a6b3c"
  ok-soft: "#e4f2e9"
  warn: "#8a4b00"
  warn-soft: "#fbefdc"
  bad: "#b3261e"
  bad-soft: "#fbe7e5"
  neutral: "#3e4a5a"
  neutral-soft: "#e8ebef"
  rail-done: "#1d5fbf"
  rail-open: "#c9d6ea"
  rail-ground: "#e8ebef"
typography:
  count:
    fontFamily: "system-ui, -apple-system, Segoe UI, Apple SD Gothic Neo, Malgun Gothic, Noto Sans KR, sans-serif"
    fontSize: 1.5rem
    fontWeight: 700
    lineHeight: 1.2
  headline:
    fontFamily: "system-ui, -apple-system, Segoe UI, Apple SD Gothic Neo, Malgun Gothic, Noto Sans KR, sans-serif"
    fontSize: 1.5rem
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: -0.01em
  title:
    fontFamily: "system-ui, -apple-system, Segoe UI, Apple SD Gothic Neo, Malgun Gothic, Noto Sans KR, sans-serif"
    fontSize: 1.1875rem
    fontWeight: 700
    lineHeight: 1.35
  body:
    fontFamily: "system-ui, -apple-system, Segoe UI, Apple SD Gothic Neo, Malgun Gothic, Noto Sans KR, sans-serif"
    fontSize: 0.9375rem
    fontWeight: 400
    lineHeight: 1.55
    fontFeature: "tnum"
  label:
    fontFamily: "system-ui, -apple-system, Segoe UI, Apple SD Gothic Neo, Malgun Gothic, Noto Sans KR, sans-serif"
    fontSize: 0.8125rem
    fontWeight: 600
    lineHeight: 1.5
  caption:
    fontFamily: "system-ui, -apple-system, Segoe UI, Apple SD Gothic Neo, Malgun Gothic, Noto Sans KR, sans-serif"
    fontSize: 0.75rem
    fontWeight: 400
  mono:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
    fontSize: 0.8125rem
    lineHeight: 1.5
rounded:
  hair: 2px
  sm: 4px
  md: 6px
  lg: 8px
spacing:
  sp-1: 4px
  sp-2: 8px
  sp-3: 12px
  sp-4: 16px
  sp-5: 24px
  sp-6: 32px
components:
  page:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
  shell-bar:
    backgroundColor: "{colors.shell}"
    textColor: "{colors.shell-ink}"
    padding: 12px 24px
  shell-meta:
    backgroundColor: "{colors.shell}"
    textColor: "{colors.shell-ink-2}"
    typography: "{typography.label}"
  shell-button-hover:
    backgroundColor: "{colors.shell-line}"
    textColor: "{colors.shell-ink}"
    rounded: "{rounded.md}"
    padding: 4px 12px
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: 16px 24px
  card-meta:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-2}"
    typography: "{typography.label}"
  page-title:
    textColor: "{colors.ink}"
    typography: "{typography.headline}"
  section-title:
    textColor: "{colors.ink}"
    typography: "{typography.title}"
  divider:
    backgroundColor: "{colors.line}"
    height: 1px
  field-stroke:
    backgroundColor: "{colors.field}"
    height: 1px
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: 6px 8px
  row-hover:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
  code:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
    typography: "{typography.mono}"
    rounded: "{rounded.md}"
    padding: 12px
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-accent}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: 6px 16px
  button-ghost:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: 6px 16px
  button-danger:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.bad}"
    rounded: "{rounded.md}"
    padding: 6px 16px
  button-danger-hover:
    backgroundColor: "{colors.bad-soft}"
    textColor: "{colors.bad}"
  button-disabled:
    backgroundColor: "{colors.neutral-soft}"
    textColor: "{colors.ink-2}"
  tab:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-2}"
    typography: "{typography.label}"
    padding: 8px 12px
  tab-on:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    padding: 8px 12px
  filter-on:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 2px 12px
  decide-cell:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.count}"
    padding: 12px 16px
  decide-need:
    backgroundColor: "{colors.warn-soft}"
    textColor: "{colors.warn}"
    typography: "{typography.count}"
    padding: 12px 16px
  rail-track:
    backgroundColor: "{colors.rail-ground}"
    rounded: "{rounded.hair}"
    height: 10px
  rail-open:
    backgroundColor: "{colors.rail-open}"
    rounded: "{rounded.hair}"
    height: 10px
  rail-fill:
    backgroundColor: "{colors.rail-done}"
    height: 10px
  chip:
    backgroundColor: "{colors.neutral-soft}"
    textColor: "{colors.neutral}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: 1px 6px
  chip-progress:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: 1px 6px
  chip-need:
    backgroundColor: "{colors.warn-soft}"
    textColor: "{colors.warn}"
    rounded: "{rounded.sm}"
    padding: 1px 6px
  chip-done:
    backgroundColor: "{colors.ok-soft}"
    textColor: "{colors.ok}"
    rounded: "{rounded.sm}"
    padding: 1px 6px
  chip-fail:
    backgroundColor: "{colors.bad-soft}"
    textColor: "{colors.bad}"
    rounded: "{rounded.sm}"
    padding: 1px 6px
  alert-info:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 8px 12px
  alert-ok:
    backgroundColor: "{colors.ok-soft}"
    textColor: "{colors.ok}"
    rounded: "{rounded.md}"
    padding: 8px 12px
  alert-warn:
    backgroundColor: "{colors.warn-soft}"
    textColor: "{colors.warn}"
    rounded: "{rounded.md}"
    padding: 8px 12px
  alert-bad:
    backgroundColor: "{colors.bad-soft}"
    textColor: "{colors.bad}"
    rounded: "{rounded.md}"
    padding: 8px 12px
---

# Design System: Workflow Hub

## Overview

**Creative North Star: "차분한 운영 콘솔"**

팀이 매일 여는 운영 도구다. 첫 화면은 표가 아니라 "지금 어디까지 왔고, 사람이 무엇을 정해야 하나" 를 먼저 말한다 — 프로젝트 머리 → '사람이 결정할 일' 한 줄 → 마일스톤 진척 띠 → task 목록 순서. 짙은 남색 머리 막대가 화면을 붙잡고, 그 아래는 찬 회색 바탕 위 흰 판과 1px 선뿐이다. 그림자도 장식도 없다. 색은 상태를 말할 때만 쓰고, 상태는 언제나 한국어 낱말로 같이 쓴다.

이 문서는 2026-11-26 재정비가 끝난 허브 화면(`workflow-source/workflow_kit/hub/static/`)에서 받아 적었다. **값의 정본은 `hub.css` 의 `:root`** 다 — 값을 바꾸면 `hub.css` 와 이 파일을 같은 커밋에서 같이 고친다. 재정비 전 기준선 값은 git 이력과 허브 위키 보고(`queries/ui-baseline-2026-11-26.md`)에 남아 있다.

이 규약이 다스리는 화면 셋:

- **허브** (`/ui/`) — 이번 빌드. Python 허브와 Go 허브가 같은 정적 파일을 낸다. `hub-go/internal/assets/static/` 은 바이트 사본이다 (`check_go_assets_sync` 가 묶는다).
- **워크벤치** (`workflow-source/workflow_kit/workbench/static/`) — **동결**(2026-11-26, 정본은 허브). 재설계하지 않고 색 값만 이 토큰과 같게 맞췄다(변수 이름은 옛 것 그대로). 허브로 옮긴 저장소에서는 머리에 '정본은 허브' 안내를 달고 읽기 전용이다(응답 · 할 일 쓰기 없음, '허브에서 답한다' 링크). 강조 띠(4px 윗선 · 왼선)는 쓰지 않는다.
- **PC 중계 화면과 VS Code** (`workflow-source/workflow_kit/relay/static/`, Go `hub-go/internal/relay/static/` 은 바이트 사본, VS Code 확장은 iframe 으로 담을 뿐) — 이 토큰을 따른다(2026-11-26). `relay.css` 의 `:root` 값은 `hub.css` 와 같게 고친다. 어두운 테마는 확장이 넘긴 `?theme=` 가 정한다.

지킬 제약: 외부 자원 없음(글꼴 · CDN · 빌드 단계 없음), CSP `style-src 'self'` 라 인라인 `style` 속성을 쓰지 않는다 — 동적 폭도 클래스(`.pct-*`, `.w-*`)로 낸다.

**Key Characteristics:**
- 짙은 머리 막대 하나 + 찬 회색 바탕 + 흰 판 + 1px 선, 그림자 없음
- 강조색 하나(파랑), 주황은 사람이 필요한 것에만
- 상태 꼬리표는 각진 작은 표(4px)이고 글자가 상태를 말한다
- 시그니처는 마일스톤 진척 띠
- 시스템 글꼴 하나, 숫자는 tabular

## Colors

찬 회색 바탕 위의 남색 잉크, 파랑 하나, 상태색 넷. 모든 상태색은 자기 `-soft` 바탕 위 글자로만 쓴다.

### Primary
- **Console Blue** (`#1d5fbf`, frontmatter `primary` = CSS `--accent`): 주 동작 단추 · 현재 탭 밑줄 · 현재 마일스톤 테두리 · 진척 채움 · 링크 · 포커스 고리 · '진행 중' 꼬리표. 바탕 `--accent-soft` (`#e6eefa`), 위 글자 `--on-accent` (`#ffffff`).

### Neutral
- **Shell Navy** (`#14233a`, `--shell`): 머리 막대만. 글자 `--shell-ink` (`#e8edf4`), 보조 `--shell-ink-2` (`#a9b6c8`), 선 · 단추 hover `--shell-line` (`#2a3c55`).
- **Cool Ground** (`#f2f4f6`, `--ground`): 페이지 바탕.
- **Surface** (`#ffffff`, `--surface`) · **Surface 2** (`#f7f8fa`, `--surface-2`): 판 · 줄 hover · `pre`.
- **Ink** (`#17202b`, `--ink`) · **Ink 2** (`#4f5b6b`, `--ink-2`): 본문 · 보조 글(메타, 표 머리, 꺼진 탭).
- **Line** (`#d5dae1`, `--line`): 판 테두리 · 구분선. **Field** (`#7d8796`, `--field`): 입력 · ghost 단추 테두리, hover 시 판 테두리(비글자 3:1 이상).
- **Neutral** (`#3e4a5a` on `#e8ebef`): '예정' 등 중립 꼬리표 · 꺼진 단추 바탕.

### 상태색
- **Ok** (`#1a6b3c` on `#e4f2e9`): 끝남 · 승인됨 · 답함.
- **Warn** (`#8a4b00` on `#fbefdc`): 막힘 · 열림 · 승인 대기 · 미확인 — 사람이 필요하다는 뜻.
- **Bad** (`#b3261e` on `#fbe7e5`): 실패 · 거절 · 정지 · 응답 없음, 되돌릴 수 없는 동작.

### 진척 띠
- **Rail Done** (`#1d5fbf`) 채움 · **Rail Open** (`#c9d6ea`) 진행 중 마일스톤의 빈칸 · **Rail Ground** (`#e8ebef`) 아직 열리지 않은 칸.

### 어두운 모드
`@media (prefers-color-scheme: dark)` 가 같은 이름의 값을 바꿔 넣는다 (`color-scheme: light dark`). 위 frontmatter 는 밝은 값이다. 토큰 이름은 CSS 변수 이름과 같다 — 단 하나, frontmatter `primary` 는 CSS `--accent` 다(형식 검사기가 `primary` 를 요구한다).

| 토큰 | 어두운 값 | 토큰 | 어두운 값 |
|---|---|---|---|
| ground | `#0e141b` | primary (`--accent`) | `#7fb0ff` |
| surface | `#151c25` | accent-soft | `#182a44` |
| surface-2 | `#1b2430` | on-accent | `#0e141b` |
| ink | `#e6ebf1` | ok / ok-soft | `#6fd39a` / `#13301f` |
| ink-2 | `#a3afbf` | warn / warn-soft | `#f0b860` / `#33260f` |
| line | `#2a3542` | bad / bad-soft | `#ff8a80` / `#3a1a18` |
| field | `#6f7b8c` | neutral / neutral-soft | `#c5cdd8` / `#222c38` |
| shell | `#0a1018` | rail-done | `#7fb0ff` |
| shell-ink | `#e6ebf1` | rail-open | `#2b3f5e` |
| shell-ink-2 | `#8f9cad` | rail-ground | `#222c38` |
| shell-line | `#1f2a38` | | |

두 모드 모두 글자 쌍은 4.5:1 이상이다 (밝은 모드 최저 ink-2 on neutral-soft 5.8, 어두운 모드 최저 accent on accent-soft 6.6).

### Named Rules
**The One Blue Rule.** 강조색은 파랑 하나다. 두 번째 강조색을 들이지 않는다.

**The Orange Means Human Rule.** 주황(warn)은 사람이 손대야 하는 것에만 쓴다 — 막힌 task, 승인 대기, 열린 결정, 탭의 대기 개수.

**The Soft Pair Rule.** 상태색은 자기 `-soft` 바탕 위 글자로만 쓴다. 흰 바탕 위 상태색 글자는 `button.danger` 하나뿐이다.

## Typography

**Body Font:** 시스템 글꼴 (`system-ui, -apple-system, "Segoe UI", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif`)
**Mono Font:** `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` — ID · 경로 · 명령 · 옵션 값

**Character:** 글꼴 하나로 굵기와 크기만 바꾼다. 한국어 운영 문구가 주인이고, 숫자는 `font-variant-numeric: tabular-nums` 로 줄을 맞춘다.

### Hierarchy
- **Count** (700, 1.5rem, 1.2): '사람이 결정할 일' 칸의 숫자. 좁은 폭에서 1.1875rem.
- **Headline** (700, 1.5rem, 1.3, -0.01em): 화면 제목 `h1` 하나.
- **Title** (700, 1.1875rem, 1.35): 판 제목 `h2`. `h3` 은 본문 크기 굵게.
- **Body** (400, 0.9375rem / 15px, 1.55): 본문 · 표 · 입력.
- **Label** (600, 0.8125rem): 표 머리 · 탭 · 꼬리표 · 필드 라벨 · 메타.
- **Caption** (400, 0.75rem): task 분류 · 띠 라벨 · 탭 개수.
- **Mono** (0.8125rem, 1.5): `pre` · `.mono` · `.t-id`.

크기 단계는 12 · 13 · 15 · 19 · 24px 다.

## Layout

- 본문 폭 최대 76rem, 가운데. 머리 막대 안쪽도 같은 폭. 판 사이 16px, 판 안쪽 16px 24px.
- 간격 단위 4 · 8 · 12 · 16 · 24 · 32px (`--sp-1`~`--sp-6`).
- 좁은 폭 경계 하나: `max-width: 48rem`. 거기서 머리 막대 · 판 안쪽이 줄고, 탭은 화면 아래 고정 막대(5칸 · 높이 56px · 오른손 엄지 영역, 더 보기는 오른쪽 끝에서 위로 열린다)가 되며 본문은 그만큼 아래 여백을 둔다. 결정 단추 줄(`.decide-actions`)은 탭 막대 바로 위에 붙고 거절 왼쪽 · 승인 오른쪽(넓게), 단추 · 입력 높이 44px 이상, '사람이 결정할 일' 은 3열 고정(칸 최소 높이 44px, 설명 줄 숨김), `table.stack` 표는 제목 + 상태가 한 줄인 쌓인 줄로 바뀌고 나머지 칸은 `data-label` 머리말을 달고 아래로 간다. 진척 띠는 현재 마일스톤 라벨만 남긴다.
- 390px 폭에서 페이지 가로 스크롤 없음. 넓은 표는 `.table-wrap` 안에서만 스크롤. 긴 ID · 경로는 `overflow-wrap: anywhere`, flex · grid 자식은 `min-width: 0`.
- 결정 제출 막대(`.submitbar`)는 판 바닥에 sticky.

## Elevation & Depth

그림자를 쓰지 않는다. 깊이는 세 겹의 면으로만 낸다: 짙은 머리 막대(sticky) → 찬 회색 바탕 → 1px 선을 두른 흰 판. hover 는 `surface-2` 로 바탕을 바꾸거나 테두리를 `field` 로 진하게 하거나 `filter: brightness(1.06)` 로 낸다.

**The Flat Panel Rule.** 판은 흰 면 + 1px `line` 테두리다. `box-shadow` 를 들이지 않는다.

## Shapes

모서리는 작고 일정하다: 판 · '사람이 결정할 일' 줄 8px, 단추 · 입력 · 알림 · 필터 · `pre` 6px, 상태 꼬리표 · 탭 개수 4px, 진척 띠 막대 2px. 알약(999px)은 쓰지 않는다. 판 안의 판은 상자가 아니라 위쪽 구분선 하나로 바뀐다(`.card .card` → 테두리 0, `border-top: 1px`).

## Components

### 머리 막대 (`header.top`)
짙은 남색 sticky 막대. 이름(굵게) · 위치(crumbs, `shell-ink-2`) · '관리자 모드' 외곽선 단추(`shell-line` 테두리, 6px) · 계정(오른쪽 끝). 포커스 고리는 `shell-ink`.

### 프로젝트 머리와 탭 (`.project-head`, `.nav-links`)
제목 `h1` → mono ID · 메타 → 탭 줄. 탭은 다섯 — 개요 · 결정(대기 수) · 오케스트레이션 · 로드맵 · 더 보기(아이디어 · 지식 · 지침 · 이력 · 결정 변경 기록 · 확인 요청 기록). 사람이 승인할 것(확인 요청 · 세션 승인 · DCR · 지침 제안)은 '결정' 한 큐에 같은 카드(`.dq` — 종류 꼬리표 · 누가 무엇을 · 때 · 근거 · 결정 메모 폼)로 모인다. 탭은 밑줄형: 꺼진 탭 `ink-2`, 켜진 탭 `ink` 650 + 2px `accent` 밑줄, 탭 줄 밑에 1px `line`. 대기 개수는 탭 옆 4px 주황 작은 표.

### 사람이 결정할 일 (`.decide`)
개요 맨 위 한 줄. 칸들이 1px `line` 틈으로 붙은 한 덩어리(8px, overflow hidden), 각 칸은 숫자(Count) + 이름 + 한 줄 설명이고 해당 화면으로 가는 링크다. 0 이 아닌 칸은 `.need` 로 `warn-soft` 바탕 + `warn` 글자. 모두 0 이면 `.decide-clear` 한 줄로 접힌다.

### 마일스톤 진척 띠 (`.rail`) — 시그니처
마일스톤마다 한 칸, 칸 폭 = WBS 수(`.w-1`~`.w-8` → `flex-grow`), 채움 = 끝난 비율(`.pct-0`~`.pct-100`, 10% 단위). 막대 높이 10px, 모서리 2px, 칸 사이 3px. 끝난 부분 `rail-done`, 진행 중 칸 바탕 `rail-open`, 아직 안 연 칸 `rail-ground`. 현재 마일스톤은 2px `accent` 외곽선(offset 1px) + 굵은 라벨. 라벨 아래 mono ID. 띠 아래 범례 한 줄(`.rail-legend`). 로드맵 화면의 `progress` 요소도 같은 색을 쓴다.

### 상태 꼬리표 (`.chip`)
각진 작은 표: 4px, `1px 6px`, Label 크기 600. 글자는 `STATUS_LABEL` 의 한국어 낱말이고 원래 값은 `title` 에 남는다. 진행 중 계열 파랑, 사람 필요 계열 주황, 끝남 계열 초록, 실패 계열 빨강, 그 밖(예정 · 대기 등)은 중립 회색.

### 표 (`table.tasks`, `table.stack`)
머리는 Label `ink-2`, 줄 사이 1px `line`, hover `surface-2`. task 제목이 첫 칸이고 굵게, ID 는 그 아래 mono Caption. 48rem 아래에서 `table.stack` 은 쌓인 줄(Layout 참고).

### 판 (`.card`)
흰 면, 1px `line`, 8px, 안쪽 16px 24px(좁은 폭 12px 16px), 그림자 없음. 판 안의 항목(`.decision`, 중첩 `.card`)은 위쪽 1px 구분선 줄이다. 열린 결정 줄만 위 구분선이 2px `warn`.

### 단추
- **Primary:** `accent` 바탕 · `on-accent` 글자 · 600 · 6px · `6px 16px`. hover `brightness(1.06)`.
- **Ghost:** `surface` 바탕 · `ink` 글자 · 1px `field` 테두리. hover `surface-2`.
- **Danger:** `surface` 바탕 · `bad` 글자 · 1px `bad` 테두리. hover `bad-soft`.
- **Disabled:** `neutral-soft` 바탕 · `ink-2` 글자 · `line` 테두리, `not-allowed`.
- 포커스: 모든 대화 요소 2px `accent` outline, offset 2px.

### 입력 · 라벨 (`label.field`)
라벨은 입력 위에 붙는 Label 크기 `ink-2` 600. 입력은 `surface` 바탕 · 1px `field` 테두리 · 6px · `6px 8px`, placeholder 는 `ink-2`. 결정 선택지(`label.option`)는 1px `line` 상자, 고르면 `accent` 테두리 + `accent-soft` 바탕.

### 필터 · 보기 전환 (`.filters`, `.view-switch`)
1px `line` 테두리 6px 작은 단추. 켜진 것은 `accent-soft` 바탕 + `accent` 테두리 · 글자 650.

### 알림 (`.alert`)
6px, `8px 12px`, soft 바탕 + 같은 계열 글자(info 는 파랑). 안의 링크는 같은 색 밑줄 굵게. `bad` 는 `role="alert"`, 나머지는 `role="status"`.

## Do's and Don'ts

### Do:
- **Do** 값을 `hub.css` `:root` 에서 고치고, 같은 커밋에서 이 파일과 Go 사본(`hub-go/internal/assets/static/`)을 같이 맞춘다.
- **Do** 상태를 색과 한국어 낱말로 함께 말한다 — 꼬리표 글자는 `STATUS_LABEL` 에서 온다.
- **Do** 글자 대비 WCAG AA 4.5:1 이상을 두 모드에서 지킨다 — 작은 꼬리표 글자도.
- **Do** 입력마다 보이는 라벨(`label.field`)이나 `aria-label` 을 단다.
- **Do** 판 안의 항목은 구분선 줄로 나눈다 (`.decision`, 중첩 `.card`).
- **Do** 동적 폭 · 비율은 클래스(`.pct-*`, `.w-*`)로 낸다 — CSP 가 인라인 style 을 막는다.
- **Do** 자동 갱신은 사용자가 입력 중이면 포커스 · 입력값을 지킨다.

### Don't:
- **Don't** 외부 글꼴 · CDN · 빌드 단계를 들인다.
- **Don't** `box-shadow` 나 그라디언트로 판을 띄운다.
- **Don't** 상태 꼬리표를 알약(999px)으로 만든다.
- **Don't** 주황을 사람이 필요하지 않은 상태에 쓴다.
- **Don't** 판 안에 테두리 상자 판을 겹친다.
- **Don't** 상태를 색만으로 말한다.
