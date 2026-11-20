---
id: TASK-2026-11-20-claude-workflow-hub-concept-009
status: done
created_at: 2026-11-20
source_anchor: generic-task-2026-11-20-claude-workflow-hub-concept-009
source_path: backlog/2026-11-20.md
kind: generic
wbs: M-031/WBS-31.1
---

# TASK-2026-11-20-claude-workflow-hub-concept-009 — requirements 소유자 결정 반영 — Q1~Q5 권고안, Q4 는 arcturus 과제 대시보드 방식(화면 콜사인 · Bearer · 공용 web 토큰)

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-20
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `docs/planning/workflow-hub-requirements-2026-11.md`

- Description: 소유자 2026-11-20: Q1~Q5 권고안대로, Q4 는 arcturus 과제 대시보드 참조. arcturus-port@8d24fcd7 portal: 화면 로그인 없음, 브라우저가 콜사인 등록 → 토큰 localStorage → Bearer, 토큰 없는 요청에 프록시가 web 역할 토큰.
- Completion criteria: requirements §20 이 결정 기록이고 Q1~Q5 가 해당 R 에 반영됐다
- Completion criteria: Q4 요구가 arcturus 근거 경로를 단다

## 🧭 Plan

- Claims: C1 Q1~Q5 가 결정으로 기록되고 해당 요구(R14.3 · R14.4 · R7.7 · R13.2 · R10.1)가 결정 문구로 바뀐다
- Claims: C2 Q4 요구가 arcturus 실물(파일 · 커밋)을 근거로 적힌다
- Files that change: docs/planning/workflow-hub-requirements-2026-11.md
- Order of work: arcturus 방식 확인
- Order of work: 문서 반영
- Order of work: 검사
- Order of work: 커밋 · push
- Plan risks: arcturus 의 공개 노출(P7)까지 옮겨 오면 loopback 기본(R13.1)과 충돌 — 공용 web 토큰은 켤 때만
- Proof: §20 결정 표 · sign-off 기록 · 바뀐 R 대조 · --changed green

## 🛠️ Implementation / Content

- Progress: `2026-11-20 22:58` 커밋 · push
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: §20 결정 표(Q1~Q5 확정 · Q6 열림) · R13.2 역할(web/editor/admin, Bearer 만) · R13.2a 화면 = arcturus 방식(공용 web 토큰 기본 꺼짐 · CSP) · R7.7 human 승인 · R14.3/R14.4 · R10.1 · §24 sign-off
- Verification: arcturus-port@8d24fcd7 실물 확인(Caddyfile 익명 요청에 web 토큰 · callsign.go CanRegister/1회 토큰/409 · index.astro localStorage Bearer, 401 문구 원문 대조 후 정정) · 문서 대조: 추적 43/43 · R 96 전부 [검증] · 미정의 참조 0 · --changed 106/108 (check_entry_points --help 10s timeout · check_wiki_trend 60s timeout, load 14~15) → 둘 단독 러너 재실행 green · verifier 생략(검증 간소화 기간)
- Follow-up: check_entry_points 의 --help 하위 프로세스 timeout=10s 가 부하에서 red — 오늘 2회
