---
merged_from: claude/remote-sync-check-234c32@fc814642
id: TASK-2026-11-17-claude-remote-sync-check-234c32-003
status: done
created_at: 2026-11-17
source_anchor: generic-task-2026-11-17-claude-remote-sync-check-234c32-003
source_path: backlog/2026-11-17.md
kind: generic
wbs: M-007/WBS-7.4
---

# TASK-2026-11-17-claude-remote-sync-check-234c32-003 — 작업 중 워크벤치 진행 기록(--progress-note) 지침 강화 — 정본 · 모든 하네스 진입점으로

## 📝 Description

- Status: done
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

- Progress: `2026-11-17 05:01` done — verifier PASS 3/3
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: 0c23165f · 1b94a470. 정본 §1 원칙 → 스냅샷 · CLAUDE.md · AGENTS.md · 플러그인 rules · ai-workflow/core 사본 (스킬은 원칙 블록을 싣지 않는 구조 — backlog-update 스킬 7단계 손글 + hook 안내 문장으로 실림). progress-nudge --hook + Claude Code PostToolUse 두 번째 명령(15분 표식 · 12시간 작업 창 · 비 워크플로우 무동작 · 옛 kit 은 표식만). check_standard_single_source 가 원칙도 대조(명령만 보던 사각). check_entry_diet 기준 10%(D3). CLAUDE.md 손글 '작업 중:' 줄은 구체 명령 예시라 남긴다 — Plan 의 정리 항목은 걷음. 미측정: 이 세션 안의 상기 문구 실제 주입(완료 기준 밖).
- Result: 되주입 출처(노트 v1.27.0 §3 대조용): 작성 세션 progress-nudge 7건 — R1 ACTIVE_WINDOW 무시 · R1b STALE_AFTER 무시 · R2 iter_task_plans 로 회귀(계획 없는 task 누락) · R5 표식 파일명 · R3 셸 find 표식 게이트 제거 · R4 옛 kit 표식 touch 제거 · R6 커밋 hooks.json 을 HEAD 로(렌더러 불일치) — 7/7 red. 진입점 원칙 1건 — CLAUDE.md 원칙 줄 제거 → check_standard_single_source red. verifier 8판(정본 · 스냅샷 · CLAUDE.md · AGENTS.md · rules.md · core 사본 · hooks.json 둘).
- Verification: verifier PASS 3/3 — check_progress_nudge 5/5 · check_standard_single_source 11/11 · check_entry_diet 7/7 · check_workbench_progress 3/3 · check_agent_plugin_payload 23/23 · check_wk_dispatcher 11/11 · check_ensure_entrypoints 8/8 · smoke 8/8, 원칙 제거 되주입 8판 red. 전량 게이트는 push 전 작업 세션
- Follow-up:
