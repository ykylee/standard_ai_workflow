---
id: TASK-2026-11-17-claude-remote-sync-check-234c32-004
status: in_progress
created_at: 2026-11-17
source_anchor: generic-task-2026-11-17-claude-remote-sync-check-234c32-004
source_path: backlog/2026-11-17.md
kind: generic
wbs: M-007/WBS-7.1
---

# TASK-2026-11-17-claude-remote-sync-check-234c32-004 — iPad Chrome(CriOS 156 · iPadOS 27)에서 워크벤치 폼 제출이 서버에 닿지 않는다 — 응답 보내기 · todo 추가 전부

## 📝 Description

- Status: in_progress
- Priority: high
- Request date: 2026-11-17
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: 소유자 보고(2026-11-17). 진단 서버 실측: 탭→pointer→click→submit(prevented=false) 까지 정상인데 서버엔 접속 0 (TLS · 깨진 요청도 0), CSP 위반 이벤트 0. 같은 페이지의 fetch GET · fetch POST(…/respond 303)는 도착 — 폼 페이지 이동(POST navigation)만 브라우저가 조용히 막는다. Chrome 데스크톱 iPad 에뮬레이션은 정상. 곁가지 결함 2: (a) 경로 표 밖 POST 가 본문을 안 읽고 keep-alive 를 유지해 다음 요청이 'probe=1GET …' 로 오염(404) (b) 비 loopback --bind 서버를 workbench --stop 이 '워크벤치로 답하지 않는다'로 못 내린다
- Completion criteria: [C1] 워크벤치 화면 스크립트가 respond · todo 폼 제출을 fetch POST 로 보내고 결과(303 뒤 화면 · 오류 본문)를 그대로 보여 준다 — 스크립트가 없으면 기존 폼 제출 그대로
- Completion criteria: [C2] 실제 iPad(CriOS)에서 응답 보내기 · todo 추가가 서버 로그에 POST 로 남고 화면이 결과로 바뀐다 (소유자 확인)
- Completion criteria: [C3] 경로 표 밖 · 거절된 POST 가 본문을 비우거나 연결을 닫아 다음 요청을 오염시키지 않는다 — 검사 case
- Completion criteria: [C4] 비 loopback 바인드 서버를 --stop 이 내린다 — 검사 case
- Completion criteria: [C5] 워크벤치 검사 전부 PASS + 새 case 되주입 red

## 🧭 Plan

- Files that change: workflow-source/workflow_kit/workbench/static/workbench.js — POST 폼 submit → fetch
- Files that change: workflow-source/workflow_kit/workbench/server.py — _dispatch POST 연결 닫기
- Files that change: workflow-source/workflow_kit/tools/workbench.py — write_record bind · _probe_healthz 탐침 순서
- Files that change: tests/check_workbench_submit.py (신규) · check_workbench_auth.py 기록 키 · core/plan_workbench_spec.md §3 · §4.5
- Order of work: 1 진단(진단 서버 · 이벤트 신호) → 2 JS fetch 제출 → 3 서버 연결 닫기 · --stop 탐침 → 4 검사 · 되주입 → 5 Chrome iPad 에뮬 e2e → 6 실제 iPad 소유자 확인
- Plan risks: fetch 제출이 서버의 Origin · CSRF 검사와 어긋남 → e2e 에서 303 · 403 화면 확인
- Proof: check_workbench_submit 4/4 + 되주입 red · 워크벤치 검사 전부 · 헤드리스 Chrome CDP e2e(navigation POST 0) · 실제 iPad: 응답 보내기 + todo 추가가 서버 로그에 POST 로 남고 소유자가 화면 결과 확인 — 소유자 답을 이 task Result 에 기록

## 🛠️ Implementation / Content

- Progress: `2026-11-17 04:48` verifier: C1 · C3 · C4 PASS, C2 todo 추가 미측정(소유자 iPad 대기), C5 는 -005 진행분 때문에 red — -005 마친 뒤 재측정
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: 수리: workbench.js 가 POST 폼 submit 을 fetch POST 로(action 속성 · 리다이렉트 따라감 · 오류 화면은 main 에) · server._dispatch 가 POST 뒤 연결 닫기 · 실행 기록 bind 상시 · --stop 탐침 bind → public_url 호스트 → 127.0.0.1. 검사 check_workbench_submit 4/4 (되주입 5건 red: 연결 닫기 · 탐침 · bind 기록 · preventDefault · form.action) · check_workbench_auth 기록 키 계약 갱신 · 워크벤치 검사 13종 PASS. Chrome iPad 에뮬 e2e: todo 303 · 낡은 csrf 403 화면 · 응답 303, navigation POST 0 · fetch 3. 실제 iPad(CriOS 156 · iPadOS 27) 04:21:07 'POST …-003/respond 303 owner'. --stop 실측: tailscale 바인드 옛 기록 서버 stopped=true.
- Verification: check_workbench_submit 4/4 · run_all_checks --filter=workbench 13종 PASS · 실제 iPad 제출 서버 로그
- Follow-up:
