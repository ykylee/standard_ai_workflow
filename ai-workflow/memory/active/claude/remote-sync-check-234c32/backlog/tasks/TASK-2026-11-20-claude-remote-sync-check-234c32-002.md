---
id: TASK-2026-11-20-claude-remote-sync-check-234c32-002
status: in_progress
created_at: 2026-11-20
source_anchor: release-task-2026-11-20-claude-remote-sync-check-234c32-002
source_path: backlog/2026-11-20.md
kind: release
wbs: M-007/WBS-7.4
---

# TASK-2026-11-20-claude-remote-sync-check-234c32-002 — v1.28.0 발행 — 호스트 역할(소비자 push 차단) · 재사용 브랜치 재합류 수리

## 📝 Description

- Status: in_progress
- Priority: high
- Request date: 2026-11-20
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: 소유자 지시 '버전 올리고 배포준비하자'(2026-11-20). v1.27.0 이후 코드 커밋: fix 7df480f9(재합류) · feat 1fdcddc5(호스트 역할) · docs 289e2124. breaking 0 → minor.
- Completion criteria: 발행 준비 커밋: 버전 1.28.0 리터럴 전부 · releases/Beta-v1.28.0.md(등급 근거 · 소비자 변화 · 한계) · 전량 게이트 native · slash green · main ff push
- Completion criteria: dist --apply(wheel · sdist · plugin ZIP) · release --dry-run ready=true
- Completion criteria: release --apply 는 소유자 확인 뒤 — 태그 v1.28.0 · GitHub Release asset 5 · §2.8 재적용 doctor behind=[] disabled=[]

## 🧭 Plan

- Files that change: workflow-source/pyproject.toml
- Files that change: workflow-source/workflow_kit/__init__.py
- Files that change: workflow-source/releases/Beta-v1.28.0.md
- Order of work: version-bump --minor --skip-sync-hash
- Order of work: 노트 · 리터럴 · 생성물
- Order of work: --changed · smoke → 커밋 → 게이트 → main push
- Order of work: dist --apply · release --dry-run
- Order of work: 소유자 확인 → release --apply → §2.8
- Plan risks: release post-step 의 auto-amend · 스탬프 재삽입 — 실행 전 clean tree, 뒤에 diff 확인
- Proof: 게이트 증거 · release --dry-run ready=true · gh release view asset 5 · doctor --json

## 🛠️ Implementation / Content

- Progress: `2026-11-20 01:21` 게이트 red(check_workbench_multi 포트 충돌) 수리 — 재게이트
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result:
- Follow-up:
