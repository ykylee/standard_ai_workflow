---
version: alpha
name: Product Name
description: 한 줄 — 누가 무엇을 하려고 쓰는 화면인가.
colors:
  primary: "#1f2430"
  secondary: "#5b6476"
  tertiary: "#3d5afe"
  neutral: "#f6f7f9"
  on-tertiary: "#ffffff"
  surface: "#ffffff"
  danger: "#c62839"
typography:
  headline-lg:
    fontFamily: system-ui
    fontSize: 1.75rem
    fontWeight: 700
    lineHeight: 1.25
  body-md:
    fontFamily: system-ui
    fontSize: 1rem
    lineHeight: 1.55
  label-sm:
    fontFamily: system-ui
    fontSize: 0.8rem
    fontWeight: 600
rounded:
  sm: 6px
  md: 12px
spacing:
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
  caption:
    textColor: "{colors.secondary}"
    typography: "{typography.label-sm}"
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.on-tertiary}"
    rounded: "{rounded.sm}"
    padding: 10px
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.on-tertiary}"
    rounded: "{rounded.sm}"
    padding: 10px
  title:
    textColor: "{colors.primary}"
    typography: "{typography.headline-lg}"
---

## Overview

이 화면이 주는 인상 한두 문장과 그 이유. 에이전트는 토큰(위 YAML)을 값으로, 이 글을 판단 근거로 읽는다.

## Colors

- **Primary:** 본문 글자 · 제목.
- **Secondary:** 보조 글 · 테두리.
- **Tertiary:** 주 동작 하나에만 — 한 화면에 여러 곳 쓰지 않는다.
- **Danger:** 되돌릴 수 없는 동작에만.

## Typography

제목 · 본문 · 라벨 세 단계만 쓴다.

## Layout

간격은 spacing 토큰의 배수. 좁은 폭(390px)에서 가로 스크롤이 없어야 한다.

## Components

- **card** — 화면의 기본 덩어리.
- **button-primary** — 카드 하나에 하나.

## Do's and Don'ts

- Do: 글자 대비 WCAG AA 이상, 상태는 색과 글자로 함께 말한다.
- Don't: 보라-파랑 그라디언트, 카드 안의 카드, 아이콘 타일을 모든 제목 위에.
