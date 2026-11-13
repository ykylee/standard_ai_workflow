---
id: TASK-2026-11-13-claude-remote-sync-check-234c32-001
status: done
created_at: 2026-11-13
source_anchor: generic-task-2026-11-13-claude-remote-sync-check-234c32-001
source_path: backlog/2026-11-13.md
kind: generic
wbs: M-025/WBS-25.1
---

# TASK-2026-11-13-claude-remote-sync-check-234c32-001 — 계획·진척 워크벤치 requirements — 미실측 실측 + 서버 · 응답 쓰기 · 알림 · 진척 화면 요구 사항 · design 진입 조건 확정

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-13
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `docs/planning/plan-workbench-requirements-2026-11.md`
  - `ai-workflow/memory/active/roadmap/M-025-plan-workbench-requirements.md`
  - `docs/planning/plan-workbench-review-2026-11.md`
  - `docs/planning/claim-plan-requirements-2026-11.md`

- Description: M-024 concept(W1~W7)과 M-023 requirements(응답 형식 · 받은편지함 · plan-import)를 받아 워크벤치 서버의 requirements 문서를 낸다. 먼저 하네스별 프롬프트 직전 hook · 받은편지함 쓰기 경합 · 경로 접두사 프록시 뒤 쿠키 · 리다이렉트를 재고, 그 결과로 경로 · 응답 쓰기 · 토큰 · 본문 상한 · 열림 측정 · 진척 화면 표시 규칙 · MCP 도구 이름 · §11.1 명령 문구 · design 진입 조건을 확정한다
- Completion criteria: 프롬프트 직전 hook 표의 하네스 칸(Claude Code · Codex · Grok Build · Antigravity)이 각각 '이 호스트 실측 결과(명령 · 출력)' 또는 '이 호스트에서 잴 수 없는 이유' 로 채워져 있고, W1 ② 를 만들지 여부가 그 표에 판정 규칙(둘 이상 하네스에서 발화와 주입이 실측됨)을 적용한 결과로 적혀 있다
- Completion criteria: 받은편지함 응답 쓰기의 배타 생성과 번호 매기기가 동시 쓰기 경합(Linux, 프로토타입)에서 중복 · 덮어쓰기 0 임이 명령과 결과로 적혀 있다
- Completion criteria: 경로 접두사가 붙는 프록시 뒤에서 쿠키 경로 · 리다이렉트 · 폼 제출 · CSRF 출처 대조가 맞는지가 프로토타입 실측(명령 · 결과)으로 적혀 있고, 실측에 쓴 프록시의 종류와 nginx · Caddy 실물 미실측 여부가 명시돼 있다
- Completion criteria: M-025 의 '확정할 것' 9항목(경로 · 응답 형식 · 토큰 · 본문 상한 · 열림 측정 · 진척 화면 표시 규칙 · MCP 도구 이름 · §11.1 명령 문구 · design 진입 조건)이 각각 식별자 붙은 요구 사항으로 있고 W1~W7 · M-023 requirements(R5 · R6 · R8 · R9.2 · §12 Q1~Q7)와 어긋나지 않는다
- Completion criteria: check_docs 통과; roadmap issues 0; M-025 deliverables_missing 이 빈다

## 🧭 Plan

- Files that change: docs/planning/plan-workbench-requirements-2026-11.md
- Files that change: ai-workflow/memory/active/roadmap/M-025-plan-workbench-requirements.md
- Files that change: ai-workflow/memory/active/roadmap/index.md
- Files that change: ai-workflow/memory/active/roadmap/roadmap_state.json (생성물)
- Files that change: ai-workflow/memory/active/claude/remote-sync-check-234c32/** (task · backlog · handoff · state.json)
- Files that change: docs/planning/plan-workbench-review-2026-11.md (§11.3 에 Q1 갱신 주석 1줄)
- Files that change: docs/planning/claim-plan-requirements-2026-11.md (R8.1 배타 이동 + 잠금 · R5.1 received_at 소수 초 · R11-7 · R13 · 수정일)
- Files that change: ai-workflow/memory/active/roadmap/M-026-claim-plan-design.md (넘긴 항목)
- Order of work: 실측: 하네스별 프롬프트 직전 hook → 받은편지함 쓰기 경합 → 접두사 프록시 뒤 쿠키 · 리다이렉트 (프로토타입은 scratchpad, 저장소 밖)
- Order of work: 요구 사항 작성(서버 · 인증 · 응답 쓰기 · 열림 측정 · 진척 화면 · 알림 · MCP · 명령) → check_docs → refresh-state → verifier → 소유자 sign-off
- Plan risks: 하네스 hook 실측은 모델 호출 · 인증이 필요할 수 있다 — 못 재는 칸은 이유를 적고 ② 판정에서 '실측 안 됨' 으로 센다
- Plan risks: 프로토타입 코드를 저장소에 넣지 않는다 — 측정 명령과 결과만 문서에
- Plan risks: 한글 Windows · 클라우드 포트 공유는 이 호스트에서 못 잰다 — 남은 실측으로 넘긴다 (완료 기준 밖)
- Proof: 실측 스크립트 재실행으로 같은 결과, check_docs, roadmap_state issues, verifier(요구 사항끼리 모순은 문면 모델링으로)

## 🛠️ Implementation / Content

- Progress: 2026-11-13 종결 — sign-off Q1 · Q2 권고안(문서 §13). verifier 3회: 1차 기준 4 FAIL(server.json 위치), 2차 기준 4 FAIL(옮기는 쪽 둘에서 중복 보관 — 잠금으로 수리), 3차 5/5 PASS. M-025 done
- Next session starting point: M-026 design — 주장 트리 계획과 워크벤치를 한 ADR 묶음으로 낼지부터 (워크벤치 R12-③). design 전 실측: Codex UserPromptSubmit 주입 · nginx/Caddy 실물 + 실제 브라우저 · 진입점 블록 크기 · file_lock.py 로 import 잠금 재현
- Remaining risks:

## ✅ Outcome

- Result: docs/planning/plan-workbench-requirements-2026-11.md — 실측(hook 주입은 Claude Code 만 실측 → ② 보류 / 배타 생성 없으면 400 중 280건대 유실 · 다 쓴 뒤 공개 · rename 이동은 쓰는 쪽과 겹치면 유실 · 잠금 없는 배타 이동은 중복 → import 잠금 / 접두사 프록시 뒤 상대 경로 + 쿠키 Path) + R0~R12. 주장 requirements R8.1 · R5.1 · R11-7 수정
- Verification: verifier 3차(새 컨텍스트) 5/5 PASS — 스크립트를 읽고 재실행: 잠금 아래 옮기는 쪽 2 · 4 각 30회 중복 0 · 유실 0, 잠금 무력화 사본은 중복 5 · 8회(판정이 살아 있음), 잠금 대기 · 번호 재부여 발화 계측, A1~A4 표 일치, agy 문자열 대조, 소유자 결정 어긋남 0, 9항목 누락 0, check_docs 79 PASS, roadmap issues []
- Follow-up:
