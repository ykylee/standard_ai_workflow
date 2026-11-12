---
id: TASK-2026-11-12-claude-remote-sync-check-234c32-004
status: done
created_at: 2026-11-12
source_anchor: generic-task-2026-11-12-claude-remote-sync-check-234c32-004
source_path: backlog/2026-11-12.md
kind: generic
wbs: M-024/WBS-24.2
---

# TASK-2026-11-12-claude-remote-sync-check-234c32-004 — 워크벤치 concept 정정 — 접속 위치 무가정: 노출 경로 · 항상 인증 · viewer/approver 역할

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-12
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `docs/planning/plan-workbench-review-2026-11.md`
  - `ai-workflow/memory/active/roadmap/M-024-plan-workbench.md`
  - `ai-workflow/memory/active/roadmap/M-025-plan-workbench-requirements.md`

- Description: 소유자 지시(웹이 꼭 localhost 로 접속되는 것은 아니다)에 따라 워크벤치 검토 문서의 loopback 전제를 걷어내고, 노출 경로 · 인증 · 권한 설계와 소유자 선택지 W6 · W7 을 정정 절로 낸다
- Completion criteria: 검토 문서에 loopback 을 신뢰 근거로 쓰는 문장이 남지 않는다 (남은 것은 정정 표시 또는 안전한 기본값으로만)
- Completion criteria: 노출 경로(같은 호스트 · 포워딩/터널 · 리버스 프록시 · 직접 노출)별로 서버가 지킬 것이 적혀 있다
- Completion criteria: 인증 · 권한(항상 인증 · 역할 · 응답자 기록)과 M-022 결정(응답=데이터 · import 는 결정 상태만)이 어긋나지 않는다
- Completion criteria: W6 · W7 이 기본값과 함께 있다; check_docs 통과; roadmap issues 0

## 🧭 Plan

- Files that change: docs/planning/plan-workbench-review-2026-11.md
- Files that change: ai-workflow/memory/active/roadmap/M-024-plan-workbench.md
- Files that change: ai-workflow/memory/active/roadmap/M-025-plan-workbench-requirements.md
- Files that change: ai-workflow/memory/active/roadmap/index.md
- Files that change: ai-workflow/memory/active/claude/remote-sync-check-234c32/** (task · backlog · handoff · state.json)
- Order of work: loopback 전제 문장 식별 → §11 정정 절(노출 경로 · 인증 · 권한 · 받은편지함 변화 · W6/W7 · 미실측)
- Order of work: M-024 WBS-24.2 · M-025 불변 갱신 → 문서 검사 → refresh-state
- Plan risks: 확정된 전제(§1-5)를 뒤집는다 — 정정 절로 남기고 원문은 취소선으로 보존
- Proof: check_docs (77+ 문서), roadmap_state issues, 문서 내 loopback 문맥 grep, verifier

## 🛠️ Implementation / Content

- Progress: 2026-11-12 정정 종결 — 소유자 결정 W6 · W7 기본값(검토 문서 §11.7). verifier 4/4 PASS, 주의 1건(approver 충돌 시 import 범위) 문구 확정 — 응답 묶음 전체를 쓰지 않음(M-022 §5.5 와 같음), '로컬 웹' 이름 잔재 정리. M-024 done
- Next session starting point: M-023 requirements 먼저 (W4), 그 뒤 M-025 — §11.6 미실측(경로 접두사 프록시 · 클라우드 포트 공유 쿠키) 포함
- Remaining risks:

## ✅ Outcome

- Result: 검토 문서 §11 — 서버는 작업 공간 호스트, 브라우저는 어디서든. 노출 경로 4종별 서버 의무(public_url · 경로 접두사 · 신뢰 프록시 · 직접 노출은 명시 옵션 + TLS), 항상 인증(loopback 면제 없음) · viewer/approver · 이름 붙은 토큰 · 응답자 기록 · approver 충돌 시 닫힘. 소유자 결정 W6 · W7 기본값
- Verification: verifier(새 컨텍스트) 4/4 PASS — loopback 등장 12줄 분류(신뢰 근거 0), 노출 경로 4행 의무 확인, M-022 §5.4–5.6 · D4 · §10 · §11 대조, check_docs 77 문서 PASS, roadmap 재생성 issues [] · state 일치
- Follow-up:
