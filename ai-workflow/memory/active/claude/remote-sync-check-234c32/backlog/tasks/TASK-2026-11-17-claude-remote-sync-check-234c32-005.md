---
id: TASK-2026-11-17-claude-remote-sync-check-234c32-005
status: done
created_at: 2026-11-17
source_anchor: generic-task-2026-11-17-claude-remote-sync-check-234c32-005
source_path: backlog/2026-11-17.md
kind: generic
wbs: M-007/WBS-7.4
---

# TASK-2026-11-17-claude-remote-sync-check-234c32-005 — 한 호스트에 워크벤치 여러 개 — 포트 분배 + 화면에 저장소 · 브랜치 표시

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-17
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: 소유자 지시(2026-11-17): 여러 세션(worktree · 저장소)이 동시에 작업하면 워크벤치가 여러 개 뜬다 — 기본 포트 8766 고정이라 둘째부터 충돌한다. 포트를 분배하고 화면 · 탭 제목에 저장소명 · 브랜치명을 싣는다.
- Completion criteria: [C1] 같은 호스트의 두 checkout 이 --port 없이 워크벤치를 띄우면 서로 다른 포트를 받고 둘 다 뜬다 (자동 기동 포함)
- Completion criteria: [C2] 진척 · 계획 화면 머리와 <title> 에 저장소명 · 브랜치명이 보인다
- Completion criteria: [C3] session-start 보고 · --status 가 그 checkout 의 실제 URL 을 낸다
- Completion criteria: [C4] 검사 + 되주입 red, 워크벤치 검사 전부 PASS

## 🧭 Plan

- Claims: C1 --port 없이 띄우면 checkout 경로 해시로 정한 포트(8766~8865), 차 있으면 다음 빈 포트 — 같은 호스트의 checkout 들이 충돌 없이 뜬다
- Claims: C2 화면 머리 · <title> 에 저장소명 · 브랜치명
- Claims: C3 호스트 공용 기록 + workbench --list 로 떠 있는 워크벤치들(저장소 · 브랜치 · URL)을 본다
- Decisions: D1 [C1] 포트 분배 방식 | default: hash | options: hash = checkout 경로 해시로 8766~8865 고정 + 차 있으면 다음 빈 포트; sequential = 8766 부터 첫 빈 포트; os = 포트 0 | state: answered:hash
- Decisions: D2 [C3] 여러 워크벤치 목록 | default: list | options: list = 호스트 공용 기록 + workbench --list; none = 목록 없음 | state: answered:list
- Files that change: workflow-source/workflow_kit/workbench/registry.py (신규) — 포트 해시 · 저장소 이름 · HEAD 브랜치 · 호스트 공용 목록
- Files that change: tools/workbench.py — --port 생략 시 자동 분배 · --list · 등록/해제 · views.py/server.py 머리 · <title>
- Files that change: tests/check_workbench_multi.py (신규) · _workbench_fixture.py 목록 위치 임시 디렉터리 · core/plan_workbench_spec.md §3.2
- Order of work:
- Plan risks:
- Proof: check_workbench_multi 5/5 + 되주입 7건 red · 워크벤치 검사 14종 · 실제 서버: 해시 포트 8847 · --list · 머리/title 확인

## 🛠️ Implementation / Content

- Progress: `2026-11-17 05:04` done — verifier 지적(R2 · R1 · 해제) 보강 후 재측정
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: 0c23165f + 검사 보강. --port 생략 → checkout 경로 해시 8766~8865, 차 있으면 다음 빈 포트(명시 포트는 넘어가지 않음 · 0 은 OS) · 화면 머리 · <title> 에 저장소(worktree 는 공통 .git 이름) · 브랜치 · 호스트 공용 목록 + workbench --list(죽은 기록 청소, --stop · 정상 종료가 지움) · 검사는 임시 목록 위치. 알려 둘 것: main worktree 자동 기동 인자에 --port 가 없어 kit 갱신 뒤 8766 → 8863 으로 뜬다(유지하려면 --autostart on … --port 8766). 옛 버전으로 떠 있는 서버(main :8766)는 등록 전이라 --list 에 안 보인다.
- Verification: verifier: C1 (수동 · 자동 기동 · 차 있을 때 다음 포트 8790→8791) · C2 (실서버 머리 · title) · C3 (session-start 보고 · --status · --list) PASS, C4 는 되주입 R2 가 TIME_WAIT 로 5회 중 1회 green → 검사 보강 후 재측정: R2 5/5 red · 해시 고정 R1 red · 해제 R8+R9 red · multi 5/5 ×3 · 워크벤치 검사 14종 PASS
- Follow-up:
