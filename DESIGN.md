---
version: alpha
name: Workflow Hub
description: 프로젝트 소유자와 AI 에이전트가 task · 계획 · 승인 · 세션을 함께 보는 운영 화면 — 허브 · 워크벤치 · PC 중계(VS Code 안).
colors:
  primary: "#161a23"
  secondary: "#677085"
  tertiary: "#4f5bd5"
  on-tertiary: "#ffffff"
  tertiary-soft: "#eceefe"
  neutral: "#f4f6fa"
  surface: "#ffffff"
  surface-2: "#f8f9fc"
  line: "#e2e6ef"
  neutral-soft: "#eef0f5"
  ok: "#17804a"
  ok-soft: "#e3f5ea"
  info: "#1d6fd1"
  info-soft: "#e3effc"
  warn: "#a15c00"
  warn-soft: "#fdf1dc"
  danger: "#c2283c"
  danger-soft: "#fde6e9"
typography:
  headline-lg:
    fontFamily: system-ui
    fontSize: 1.45rem
    fontWeight: 700
    lineHeight: 1.25
  headline-sm:
    fontFamily: system-ui
    fontSize: 1.05rem
    fontWeight: 700
    lineHeight: 1.35
  body-md:
    fontFamily: system-ui
    fontSize: 15px
    lineHeight: 1.55
  label-sm:
    fontFamily: system-ui
    fontSize: 0.82rem
    fontWeight: 600
  mono-sm:
    fontFamily: ui-monospace
    fontSize: 0.85rem
rounded:
  sm: 8px
  md: 14px
  full: 999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
components:
  page:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    typography: "{typography.body-md}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 16px
  card-inset:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 12px
  divider:
    backgroundColor: "{colors.line}"
  caption:
    textColor: "{colors.secondary}"
    typography: "{typography.label-sm}"
  title:
    textColor: "{colors.primary}"
    typography: "{typography.headline-lg}"
  section-title:
    textColor: "{colors.primary}"
    typography: "{typography.headline-sm}"
  code:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.primary}"
    typography: "{typography.mono-sm}"
    rounded: "{rounded.sm}"
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.on-tertiary}"
    rounded: "{rounded.sm}"
    padding: 8px
  button-ghost:
    backgroundColor: "{colors.neutral-soft}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: 8px
  button-danger:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger}"
    rounded: "{rounded.sm}"
    padding: 8px
  nav-chip-on:
    backgroundColor: "{colors.tertiary-soft}"
    textColor: "{colors.tertiary}"
    rounded: "{rounded.full}"
  chip-neutral:
    backgroundColor: "{colors.neutral-soft}"
    textColor: "{colors.primary}"
    rounded: "{rounded.full}"
  chip-ok:
    backgroundColor: "{colors.ok-soft}"
    textColor: "{colors.ok}"
    rounded: "{rounded.full}"
  chip-info:
    backgroundColor: "{colors.info-soft}"
    textColor: "{colors.info}"
    rounded: "{rounded.full}"
  chip-warn:
    backgroundColor: "{colors.warn-soft}"
    textColor: "{colors.warn}"
    rounded: "{rounded.full}"
  chip-danger:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger}"
    rounded: "{rounded.full}"
---

## Overview

운영자가 매일 여는 도구다 — 마케팅 페이지가 아니다. 한눈에 "지금 무엇이 막혀 있고 무엇을 내가 결정해야 하는가"가 보여야 하고, 그다음이 세부다. 차분하고 조밀하게, 상태는 색과 글자로 함께 말한다.

이 문서는 2026-11-26 현재 세 화면이 실제로 쓰는 값을 받아 적은 **기준선**이다 (`workflow-source/workflow_kit/hub/static/hub.css` · `workflow-source/workflow_kit/workbench/static/workbench.css` · `workflow-source/workflow_kit/relay/ui.py` 의 CSS 변수). 재정비 task 가 이 값을 고친다 — 고칠 때는 이 파일을 먼저 고치고 화면을 따라 고친다.

화면 셋:

- **허브** (`/ui/`) — task · 로드맵 · 계획 · 승인 · 오케스트레이션 · 위키. Python 허브와 Go 허브가 같은 정적 파일을 쓴다 (`hub-go/internal/assets/static/` 는 사본, `check_go_assets_sync` 가 묶는다).
- **워크벤치** — 1.x 로컬 계획 검토 화면.
- **PC 중계** — 한 PC 에서 띄운 세션 목록 · 허용 경로 · 로그. VS Code 확장은 이 화면을 webview iframe 으로 담을 뿐이다 (`editors/vscode/extension.js`).

## Colors

- **Primary (`#161a23`):** 본문 글자 · 제목.
- **Secondary (`#677085`):** 보조 글 · 표 머리 · 메타. 흰 바탕 대비 4.9:1.
- **Tertiary (`#4f5bd5`):** 주 동작 · 링크 · 선택된 탐색. 주 동작 단추는 한 구역에 하나.
- **Ok / Info / Warn / Danger:** 상태 전용. 각 색은 `-soft` 바탕 위의 글자로만 쓴다(칩 · 알림). 상태 이름을 글자로 같이 쓴다.
- **Danger:** 되돌릴 수 없는 동작과 실패에만.

어두운 모드는 같은 이름의 값을 바꿔 넣는다 (`prefers-color-scheme: dark`): neutral `#0f1218`, surface `#171b24`, primary `#e7eaf2`, secondary `#9aa3b8`, tertiary `#8b95ff`.

## Typography

시스템 글꼴(한글: Apple SD Gothic Neo · Malgun Gothic · Noto Sans KR). 본문 15px, 제목 두 단계(1.45rem · 1.05rem), 라벨 0.82rem. ID · 경로 · 명령은 mono.

## Layout

본문 최대 폭 76rem, 카드 사이 16px. 390px 폭에서 가로 스크롤이 없어야 한다 — 넓은 표는 `.table-wrap` 안에서만 스크롤한다. 긴 ID · 경로는 박스 안에서 줄을 바꾼다(`overflow-wrap: anywhere`, flex · grid 자식 `min-width: 0`).

외부 자원(글꼴 · CDN)을 쓰지 않는다 — 허브는 CSP `style-src 'self'` 라 인라인 style 도 쓰지 않는다.

## Components

- **card** — 화면의 기본 덩어리. 카드 안에 카드를 겹치지 않는다(안쪽은 `card-inset`).
- **chip-*** — 상태 하나. 알약 모양, soft 바탕 + 진한 글자.
- **button-primary** — 구역마다 하나. 나머지는 ghost.
- **button-danger** — 거절 · 정지 · 삭제.

## Do's and Don'ts

- Do: 글자 대비 WCAG AA(4.5:1) 이상 — 작은 칩 글자도.
- Do: 입력마다 보이는 라벨이나 `aria-label`.
- Do: 자동 갱신은 사용자가 입력 중이면 포커스 · 입력값을 지킨다.
- Don't: 보라-파랑 그라디언트, 카드 안의 카드, 한쪽만 두꺼운 테두리 + 둥근 모서리 조합.
- Don't: 상태를 색만으로 말하기.
