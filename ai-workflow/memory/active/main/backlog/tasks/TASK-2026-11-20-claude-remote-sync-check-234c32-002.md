---
merged_from: claude/remote-sync-check-234c32
id: TASK-2026-11-20-claude-remote-sync-check-234c32-002
status: done
created_at: 2026-11-20
source_anchor: release-task-2026-11-20-claude-remote-sync-check-234c32-002
source_path: backlog/2026-11-20.md
kind: release
wbs: M-007/WBS-7.4
---

# TASK-2026-11-20-claude-remote-sync-check-234c32-002 — v1.28.0 발행 — 호스트 역할(소비자 push 차단) · 재사용 브랜치 재합류 수리

## 📝 Description

- Status: done
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

- Progress: `2026-11-20 01:38` done — 발행 · §2.8 · verifier 완료, 완료 커밋
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: 태그 v1.28.0 = 8786cc4d = origin/main · 게이트 증거 8786cc4d native · slash 332×2 rc 0(첫 게이트 256d36d0 은 check_workbench_multi 포트 충돌 red → 8786cc4d 수리) · dist --apply(wheel · sdist · plugin ZIP 3, twine ok) · release --dry-run 사전 점검 전부 ok · release --apply rc 0 → GitHub Release v1.28.0 Latest draft=false prerelease=false asset 5 · post-step 산출물 5파일(완료 커밋에 싣는다). §2.8: claude update 1.27.0→1.28.0 · codex 재설치(plugin root …/1.28.0) · grok 재설치 · agy 재설치 · minimax sync 1.27.0→1.28.0 → doctor behind=[] disabled=[]. 재시작 필요: claude 34204 · 2109009, codex 34444 · 3319321.
- Result: verifier: 기준 1 PASS(리터럴 · 노트 절 · 게이트 증거 8786cc4d native · slash 332 · main 선형 ff) · 기준 3 PASS(태그 = origin/main = 8786cc4d, Release Latest asset 5 · 로컬 dist 와 sha256 일치, doctor behind=[] disabled=[] 5채널 1.28.0) · 기준 2 dist PASS, dry-run ready 는 발행 전 기록으로 대신: release --dry-run 출력(사전 점검 packaging · doctor · state · git · mypy · plugin_payload · gate · smoke_count 전부 ok) + release --apply summary 'local_mypy=ok, ready=true'. 소유자 확인: '좋아 발행까지 진행해'(2026-11-20). verifier 가 짚은 노트 수치 2건(메모리 커밋 4→5 · 게이트 실행 커밋) 정정 → 저장소 노트 + gh release edit 반영.
- Verification: verifier: 기준 1 PASS(리터럴 · 노트 절 · 게이트 증거 8786cc4d native · slash 332 · main 선형 ff) · 기준 3 PASS(태그 = origin/main = 8786cc4d, Release Latest asset 5 · 로컬 dist 와 sha256 일치, doctor behind=[] disabled=[] 5채널 1.28.0) · 기준 2 dist PASS, dry-run ready 는 발행 전 기록으로 대신: release --dry-run 출력(사전 점검 packaging · doctor · state · git · mypy · plugin_payload · gate · smoke_count 전부 ok) + release --apply summary 'local_mypy=ok, ready=true'. 소유자 확인: '좋아 발행까지 진행해'(2026-11-20). verifier 가 짚은 노트 수치 2건(메모리 커밋 4→5 · 게이트 실행 커밋) 정정 → 저장소 노트 + gh release edit 반영.
- Follow-up:
