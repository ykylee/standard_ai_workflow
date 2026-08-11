---
description: 표준 AI 워크플로우 백로그 갱신 — 오늘 날짜 backlog 에 task 를 등록/갱신하고 PURPOSE.md 제외 영역과 겹치면 scope creep 을 경고한다.
---

<!-- standard-ai-workflow-kit: v1.0.0-beta -->

# /workflow-backlog-update

> Claude Code slash command. 표준 AI 워크플로우 의 *backlog-update* 진입점.

## 역할

오늘 작업 항목을 `ai-workflow/memory/active/<branch>/backlog/<YYYY-MM-DD>.md` 에 등록/갱신.

## 실행

이 작업은 **도구를 거친다** — 문서를 손으로 고치면 파싱 계약이 조용히 깨진다 (정본 §11).

```bash
wk backlog-update --help
```

## 절차

1. `ai-workflow/memory/active/<branch>/backlog` 의 인덱스 anchor 확인
2. 오늘 날짜의 `backlog/YYYY-MM-DD.md` 파일:
   - 없으면 신규 작성
   - 있으면 기존 항목에 append
3. **in-scope check** (PURPOSE.md §3 Research Scope *제외 영역* 매칭):
   - `task_brief` + `affected_documents` vs 제외 영역 substring / 첫 2 token 매칭
   - 매칭 시 `scope_creep_warnings` 1줄 emit (hard warning)
4. 작업 상태: `planned` / `in_progress` / `blocked` / `done` 중 선택
5. priority + owner + acceptance criteria 명시

## PURPOSE.md 부재 시

scope_creep_warnings = `[]` (graceful skip). 본문 reference 불가, advisory 만.

## 다음에 읽을 문서

- `ai-workflow/memory/active/<branch>/backlog`
- (있으면) `ai-workflow/memory/active/PURPOSE.md`
- 영향 받을 document 들

## language 원칙

- 작업 보고, 상태 요약, 갱신 문안 = 한국어
- 코드, file path, 외부 시스템 명칭 = 원문
