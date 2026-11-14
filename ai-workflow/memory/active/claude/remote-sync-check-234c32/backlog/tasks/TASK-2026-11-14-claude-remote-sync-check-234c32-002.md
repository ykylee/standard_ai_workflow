---
id: TASK-2026-11-14-claude-remote-sync-check-234c32-002
status: done
created_at: 2026-11-14
source_anchor: generic-task-2026-11-14-claude-remote-sync-check-234c32-002
source_path: backlog/2026-11-14.md
kind: generic
wbs: M-029/WBS-29.2
---

# TASK-2026-11-14-claude-remote-sync-check-234c32-002 — M-029 ② 워크벤치 서버 · 화면 · 검사 넷 · 스킬 (MCP 두 도구는 다음 task)

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-14
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/core/plan_workbench_spec.md`

- Description: plan_workbench_spec §2~§7 · §9 · §10 · §11 을 구현한다: python -m workflow_kit workbench (시작 거절 · .workbench/server.json · --status · --new-token), 인증(토큰 · 로그인 실패 제한 · 세션 쿠키 · §5.4 네 단계), 응답 쓰기(§6 — publish 로 받은편지함에만), 진척 · 계획 화면과 api/state(§7, 읽기 전용), 접두사 프록시 뒤 상대 경로, 정본 §11.1 한 줄 · 스킬 workbench · session-start 의 public_url 줄, 검사 넷.
- Completion criteria: [C1] workbench 명령이 §2 의 시작 거절(토큰 없음 · 32자 미만 · 모드 0600 초과 · 이름 문법/겹침 · 포트 사용 중 · TLS+http · 비loopback 평문 · 살아 있는 서버)을 rc 2 와 이유 한 줄로 내고, .workbench/server.json · 자기 무시 .gitignore · --status · --new-token 이 §2 · §3 대로 동작한다 — check_workbench_auth 의 case 로 잼
- Completion criteria: [C2] §4.1 밖 경로는 404, 모든 응답이 §4.2 머리를 갖고, 세션 없음 401/303 · viewer POST 403 · 로그인 5회 실패 429 · 질의 토큰 400 · §5.4 네 단계 각각의 어긋난 요청이 받은편지함을 바꾸지 않으며, 쿠키가 HttpOnly · SameSite=Lax · Path=public_url 경로 · https 면 Secure 다 — check_workbench_auth, 각 case 되주입 red
- Completion criteria: [C3] 서버가 쓴 응답이 plan-import 1~6 단계를 통과해 결정 상태에 들고, 동시 제출(스레드 · 프로세스) 유실 0 · 덜 쓰인 파일 비노출 · 413/422/409 전부 받은편지함 무변경 · answered 결정의 조작 값 무시 · 같은 응답자 received_at 단조 증가 — check_workbench_write, 각 case 되주입 red
- Completion criteria: [C4] 진척 · 계획 화면과 api/state 가 §7 의 원천 · 표시 규칙(선언≠파생 둘 다 · 잎 0 미측정 · 절대 경로 · 호스트 이름 없음 · 이스케이프)을 지키고, 서버가 받은편지함 밖을 쓰지 않으며(git status 전후 동일), 정적 자원이 wheel 에 실린다 — check_workbench_views, 각 case 되주입 red
- Completion criteria: [C5] 검사 안의 접두사를 벗기는 프록시 뒤에서 로그인 → 계획 → 제출 → 도착이 전부 접두사 안이고 쿠키 Path 가 접두사다 — check_workbench_proxy, 절대 Location · Path=/ 되주입 red
- Completion criteria: [C6] 정본 §11.1 에 workbench 한 줄, 스킬 workbench(+ bootstrap /workflow-workbench), session-start 가 살아 있는 서버의 public_url 한 줄을 싣고, check_plan_claims case 6 소비자 목록에 workbench/ 가 들며, --changed · smoke 가 green 이다

## 🧭 Plan

- Claims: C1 workbench 명령의 시작 · 수명이 스펙 §2 · §3 대로다
- Claims: C2 인증과 응답 머리가 스펙 §4 · §5 대로다
- Claims: C3 서버가 쓰는 것은 자격 있는 받은편지함 응답뿐이다
- Claims: C4 화면과 api/state 는 생성물 · task 파일의 값만 그린다
- Claims: C5 접두사 프록시 뒤에서도 경로 · 쿠키가 접두사 안에 머문다
- Claims: C6 사용자가 서버를 찾고 띄우는 길이 정본 · 스킬 · session-start 에 있다
- Files that change: workflow-source/workflow_kit/tools/workbench.py · workflow_kit/workbench/{server,auth,views,state_view,respond}.py · static/
- Files that change: workflow-source/workflow_kit/common/tool_dispatch.py · pyproject.toml · tools/session_start.py
- Files that change: workflow-source/tests/check_workbench_{auth,proxy,write,views}.py · check_plan_claims.py
- Files that change: workflow-source/core/global_workflow_standard.md §11.1 · skills/workbench · plan_workbench_spec.md
- Order of work: [C1][C2] 명령 · 인증 · 라우팅 · 머리
- Order of work: [C3] respond · publish 경로
- Order of work: [C4] state_view · views · static
- Order of work: [C5] 상대 경로 · 프록시 검사
- Order of work: [C6] 정본 · 스킬 · session-start → 되주입 → verifier
- Plan risks: [C3] 서버가 다른 파일을 쓰면 R0 위반 — git status 전후 비교와 쓰기 경로 grep 으로 확인한다
- Plan risks: [C2] 테스트가 서버를 스레드로 띄우면 포트 경합 · 종료 누락 — 포트 0 bind 와 finally shutdown
- Plan risks: [C4] 화면이 task 파일 글을 이스케이프하지 않으면 XSS — 조립 함수 한 곳에서만 escape
- Proof: 검사 넷의 case · case 마다 되주입 red · verifier

## 🛠️ Implementation / Content

- Progress: 2026-11-14 구현: workflow_kit/workbench/{auth,server,respond,state_view,views}.py + static 2 · tools/workbench.py(시작 거절 · .workbench/server.json · --status · --new-token) · session-start summary 의 public_url 줄 · 정본 §11.1 · 스킬 workbench(+ /workflow-workbench) · plan_responses.sweep_dead_temp_files · check_packaging 자원 실측 · 검사 넷(auth 10 · write 6 · views 7 · proxy 2) 전부 green, 되주입 진행 중
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: workflow_kit/workbench/ 서버 · tools/workbench.py · 검사 넷 · 스킬 workbench · session-start public_url 줄 · plan_responses.sweep_dead_temp_files · check_packaging 자원 실측
- Verification: verifier 7회 — 1차 C3 · C4 · C6 FAIL(§7.2 미측정 미구현 · 스킬 명령 실패 · 측정 구멍) → 2차 C2 · C3 FAIL(모르는 메서드 501 · 덜 쓰인 파일 감시가 fsync/open 에 묶임) → 3~6차 C3 FAIL(감시 우회 W8 · W11b · X1~X3 · Y4(계측의 flush 가 결함을 가림) · Z6 · Z7) → 7차 [C1]~[C6] PASS. 검사 auth 12 · write 6 · views 7 · proxy 2, --changed(base bba68693) 304/304 · smoke 8/8. 되주입: 작성자 77+ · verifier 34+13+8+8+12+13 건, 생존은 진술된 한계(mmap 쓰기 · 다른 프로세스의 밖 하드링크 별칭 · main 의 비loopback 경고 출력 배선)뿐
- Follow-up: M-029/WBS-29.2 나머지: MCP plan_inbox(read-only) · plan_import(write) + 체크인 생성물 (스펙 §8.3)
- Follow-up: 소유자 질문: check_entry_diet case 1 의 15% 기준이 근거 없이 경계(여유 13B) — 템플릿이 늘 때마다 막힌다
- Follow-up: 소유자 질문: 주장 없는 task 의 완료 기준 '미측정' 표식 · 검증 줄 표식 단위(task 단위)
- Follow-up: Windows 실측(포트 bind · 토큰 파일 모드 · 콘솔 인코딩, inotify 층 미측정) — WBS-28.3 과 같은 호스트
