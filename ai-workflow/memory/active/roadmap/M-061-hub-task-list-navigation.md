---
id: M-061
title: 허브 task 목록 분류·페이지네이션·보기 전환
sdlc_phase: implementation
status: done
order: 61
parallel_allowed:
  - M-007
  - M-028
  - M-039
  - M-057
  - M-059
  - M-060
deliverables:
  - hub-go/internal/httpapi/
  - workflow-source/workflow_kit/hub/ui.py
  - workflow-source/workflow_kit/hub/static/
  - docs/HUB_OPERATIONS.md
goals: [G1, G3, G5]
---

# M-061 — 허브 task 목록 분류·페이지네이션·보기 전환

## 목적 및 완료 기준

허브 task 목록에서 roadmap, milestone, WBS, 3단계 카테고리를 기준으로 찾고,
페이지 단위로 탐색하며, 표와 카드 보기 사이를 바꿀 수 있게 한다. Python·Go
허브의 API와 정적 화면 동작을 맞춘다.

## WBS

- **WBS-61.1** task 목록 API 필터·페이지네이션 계약, Python·Go 웹 UI 구현 및 parity 검증 — 산출물: roadmap/milestone/WBS/category 필터, 안정 정렬·페이지 메타데이터, 표/카드 보기와 갱신된 운영 안내
