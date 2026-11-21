---
id: TASK-2026-11-21-release-1.x-003
status: planned
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-release-1.x-003
source_path: backlog/2026-11-21.md
kind: generic
wbs: M-007/WBS-7.2
---

# TASK-2026-11-21-release-1.x-003 — okf_export 가 5종 디렉터리 밖 페이지를 빠뜨리고 pages_skipped 에 세지 않는다

## 📝 Description

- Status: planned
- Priority: medium
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: 2026-11-21 main 실측: export_wiki_to_okf 가 98 페이지 중 78 만 내고(topics/ 16 · sources/ 4 · 메타 2 는 _is_wiki_page 에서 제외) ExportReport.pages_skipped=0 — 빠진 20 페이지가 보고 어디에도 없다. R16.8 분류: ① 문서화된 동작과 다름(조용한 누락).
- Completion criteria: 디렉터리 밖으로 빠진 페이지를 pages_skipped(또는 별도 칸)에 수와 목록으로 싣는다
- Completion criteria: 회귀 case: topics/ 페이지가 있는 fixture 에서 보고 수 = 페이지 수 − 내보낸 수, 되주입에서 red

## 🧭 Plan

- Files that change:
- Order of work:
- Plan risks:
- Proof:

## 🛠️ Implementation / Content

- Progress: `2026-11-21 03:05` 기준 2026-11-21 main 실측: export_wiki_to_okf 가 98 페이지 중 78 만 내고(topics/ 16 · sources/ 4 · 메타 2 는 _is_wiki_page 에서 제외) ExportReport.pages_skipped=0 — 빠진 20 페이지가 보고 어디에도 없다. R16.8 분류: ① 문서화된 동작과 다름(조용한 누락).
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result:
- Follow-up:
