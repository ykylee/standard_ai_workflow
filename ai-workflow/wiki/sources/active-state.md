---
type: meta
status: draft
r9_skip: true
title: active-state
created: 2026-07-22
last_touched: 2026-08-20
---

# Active State (Derived View, 2026-08-20)

> L1 SSOT: `ai-workflow/memory/active/main/state.json` (479 lines)
> 본 L2 파생 뷰는 in-repo retrieval 용 압축 요약이다. 정본은 L1 SSOT 를 본다.
> 생성: `2026-08-20` by `workflow_kit.tools.refresh_wiki_memory --emit-l2`

## SSOT 요약

| 필드 | 값 |
|---|---|
| `purpose_digest` | 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 협업 워크플로우를 *독립 패키지 형태* 로 제공 |
| `session.current_focus` | TASK-2026-08-20-main-009 플러그인 스킬 4종이 인벤토리엔 있고 세션엔 없다 — in_sync 를 쓸 수 있음으로 읽던 자리 |
| `backlog.task_count` | 11 |
| `source_of_truth.latest_backlog_path` | ai-workflow/memory/active/main/backlog/2026-08-20.md |

## 진행 중

- TASK-2026-08-20-main-009 플러그인 스킬 4종이 인벤토리엔 있고 세션엔 없다 — in_sync 를 쓸 수 있음으로 읽던 자리
- TASK-2026-08-13-main-004 CI native 셀 mypy 게이트 flake — cmd_validate mypy 전역 스캔의 병렬 race 판정
- TASK-2026-08-14-main-009 task SSOT 4단계 — 본문 라벨 영어 전환 (release 경계)

## 차단

- (없음)

## 최근 완료

- TASK-2026-08-20-main-008 — session-end 가 bootstrap 채널에 없다 — 두 채널의 스킬 집합이 갈라져 있었다
- TASK-2026-08-20-main-007 — v1.3.0 릴리스 — 101 커밋 누적분 발행 + breaking 표기 판단 기준 문서화
- TASK-2026-08-20-main-006 — release-status 의 next_version 이 커밋을 읽지 않는다 — 개수는 세고 판정은 안 센다
- TASK-2026-08-20-main-005 — watch_transient_writer 의 고정 sleep 이 병렬 부하에서 깨진다 — 시간이 아니라 관측을 기다린다
- TASK-2026-08-20-main-004 — memory_index 3-tuple 관찰 — 저점 고착의 원인은 검색이 아니라 종료 절차 배선
- TASK-2026-08-20-main-003 — OKF v0.2 이행 — ADR-026 + status 어휘 매핑 + sources 필드
- TASK-2026-08-20-main-002 — 날짜 롤오버 때 열린 task 가 mismatch 로 잡힌다 — linter 가 SSOT 대신 하루치 index 를 본다
- TASK-2026-08-20-main-001 — wiki L2 계약을 memory 파생 4종으로 좁힌다 — L1→L2 경로 은퇴 + 지표 분모 재정의
- TASK-2026-08-18-main-006 — OKF 상호운용 실측 — 다른 생산자의 번들과 대조
- TASK-2026-08-18-main-005 — 드리프트 감지 — 마커가 아니라 페이로드 해시로 비교
