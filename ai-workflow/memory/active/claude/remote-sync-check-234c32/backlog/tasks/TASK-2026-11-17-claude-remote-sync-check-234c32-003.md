---
id: TASK-2026-11-17-claude-remote-sync-check-234c32-003
status: in_progress
created_at: 2026-11-17
source_anchor: generic-task-2026-11-17-claude-remote-sync-check-234c32-003
source_path: backlog/2026-11-17.md
kind: generic
wbs: M-007/WBS-7.4
---

# TASK-2026-11-17-claude-remote-sync-check-234c32-003 — 작업 중 워크벤치 진행 기록(--progress-note) 지침 강화 — 정본 · 모든 하네스 진입점으로

## 📝 Description

- Status: in_progress
- Priority: high
- Request date: 2026-11-17
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: 소유자 지시(2026-11-17): 작업 중 지속적으로 워크벤치를 갱신하도록 지침이 들어가야 한다. 현재 규칙은 이 저장소 CLAUDE.md 손글 섹션과 backlog-update 스킬 7단계에만 있다.
- Completion criteria: [C1] 진행 기록 규칙이 core/global_workflow_standard.md 정본에 있고 생성 블록(CLAUDE.md · AGENTS.md · 플러그인 rules · 스킬)에 재생성돼 실린다
- Completion criteria: [C2] 규칙 존재 검사가 정본 · 생성물 양쪽을 보고, 되주입(규칙 제거)에 red
- Completion criteria: [C3] run_all_checks --changed + smoke 통과

## 🧭 Plan

- Claims: C1 진행 기록 규칙(단계마다 --progress-note)이 정본 Working Principles 에 있어 모든 하네스 진입점 생성 블록에 실린다 — 지금은 이 저장소 CLAUDE.md 손글 섹션과 backlog-update 스킬 7단계에만 있다
- Claims: C2 (D1=hook 일 때) in_progress task 의 Progress 가 오래 안 바뀌면 작업 세션 hook 이 한 번 상기시킨다
- Decisions: D1 [C1] 지침을 어디까지 강화하나? | default: hook | options: rule = 정본 원칙 한 줄만(모든 진입점에 생성); hook = 원칙 한 줄 + PostToolUse hook 이 진행 기록이 N분 넘게 낡으면 한 번 상기; skill = 원칙 한 줄 + session-start 스킬 보고에 진행 기록 안내 추가 | state: answered:hook
- Decisions: D2 [C2] hook 상기 간격(분)은? | default: 15 | options: 10 = 10분; 15 = 15분; 30 = 30분 | state: answered:15
- Decisions: D3 [C1] 원칙 한 줄로 check_entry_diet case 1(옛 생성물 15% 이상 축소)이 red(11.8%) — 어떻게? | default: 10 | options: 10 = 기준을 10% 로; skill = 원칙은 스킬에만; merge = 기존 원칙 줄에 합치기 | state: answered:10
- Files that change: workflow-source/core/global_workflow_standard.md §1 원칙 한 줄 → standard_rules --apply 로 스냅샷 · 진입점 재생성
- Files that change: workflow-source/workflow_kit/tools/progress_nudge.py (신규) · common/tool_dispatch.py · pyproject.toml
- Files that change: workflow-source/workflow_kit/plugin_payload.py PostToolUse 두 번째 명령 → plugin hooks.json 재생성
- Files that change: core/plan_workbench_spec.md §4.6 · plugin/skills/backlog-update · CLAUDE.md 손글 중복 줄 정리 · tests/check_progress_nudge.py (신규) · check_workbench_progress
- Order of work: 1 progress_nudge 명령 + 검사 → 2 hook 셸(15분 표식 · ai-workflow/memory 없으면 무동작) → 3 정본 원칙 · 재생성 → 4 스펙 · 스킬 · 문서 → 5 --changed + smoke → verifier
- Plan risks: 물려받은 낡은 in_progress task(Windows 3건)가 매번 상기를 부른다 → 최근 12시간 안에 기록된 task 만 '작업 중' 으로 본다
- Plan risks: PostToolUse 마다 Python 기동 비용 → 셸이 확인 표식 mtime(15분) 으로 거른다
- Proof: check_progress_nudge 전 case + 되주입 red · hooks.json 명령 실제 bash 실행 · 이 세션에서 상기 문구 주입 관측

## 🛠️ Implementation / Content

- Progress: `2026-11-17 04:44` D1 answered:hook 재기록 — D3 추가로 계획 지문이 바뀌어 04:21 iPad 응답(opened yes, hook)의 자격이 풀려 proposed 로 돌아갔던 것(verifier -002 발견)
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result:
- Follow-up:
