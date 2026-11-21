---
carried_over_to: TASK-2026-11-20-claude-workflow-hub-concept-010@main
id: TASK-2026-11-20-claude-workflow-hub-concept-010
status: done
created_at: 2026-11-20
source_anchor: generic-task-2026-11-20-claude-workflow-hub-concept-010
source_path: backlog/2026-11-20.md
kind: generic
wbs: M-031/WBS-31.2
---

# TASK-2026-11-20-claude-workflow-hub-concept-010 — 허브 design 전 실측 — S1 판정 함수 데이터 입구 · S2 위키 검사 펼친 디렉터리 · S3 하네스별 원격 MCP

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-20
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `docs/planning/workflow-hub-requirements-2026-11.md`

- Description: M-031/WBS-31.2. requirements §16 의 S1~S3 을 재고 결과를 §16 에 적는다. 미실측은 미실측으로.
- Completion criteria: S1 · S2 · S3 결과가 requirements §16 에 근거와 함께 있다
- Completion criteria: 미실측 항목은 미실측으로 표시되고 이유가 있다

## 🧭 Plan

- Claims: C1 S1: 판정 함수마다 입력이 경로인지 데이터인지와 '그대로 / 얇은 입구 / 리팩터' 판정이 근거(파일:줄)와 함께 있다
- Claims: C2 S2: 위키 검사 4종을 펼친 임시 디렉터리에서 돌린 결과와 경로 고정 지점이 실측으로 있다
- Claims: C3 S3: 이 호스트 하네스별 원격 MCP(HTTP) 지원이 실측 / 문서 근거 / 미실측으로 나뉘어 있다
- Files that change: docs/planning/workflow-hub-requirements-2026-11.md
- Order of work: S1 · S2 조사 위임 + S3 실측
- Order of work: 결과 검토 · 표본 재확인
- Order of work: §16 반영
- Order of work: 커밋 · push
- Plan risks: 위임 조사 결과의 오판 — 판정마다 표본을 직접 재확인한다
- Plan risks: 하네스 실측이 사용자 설정 · 자격 증명을 건드림 — 격리 설정 · 임시 디렉터리로만
- Proof: §16 표 세 개 · 근거 경로 · 표본 재확인 기록

## 🛠️ Implementation / Content

- Progress: `2026-11-20 23:21` 커밋 · push
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: requirements §16 — S1 판정 핵심은 그대로/얇은 입구, 리팩터는 입력 수집 층만 · S2 V-1/V-4/점수 인자화 필요, bidir_link 그대로, freshness 조용히 좁아지며 점수 상승 · S3 Claude Code/Codex/MiniMax 실측 지원, Grok 연결·인증만(모델 자격 없음), Antigravity ${VAR} 미확장 → Q7 신설. R2.5 · R5.5 · R8.3 보강
- Verification: S1 · S2 위임 조사 + 표본 재확인 3건(bidir_link entry_id_stem · _head_line_counter git · HandoffParser markdown_targets) 코드와 일치 · S2 결함 3개 사본 주입으로 경로 교체 효력 확인 · S3 탐침 서버(401 앞단) 5 하네스 양성/대조 실행, MiniMax 첫 대조가 토큰 파일 우회로 무효 → 토큰을 환경 변수에만 두고 재측정 · 산문 수치 측정 기록과 대조 정정 2건 · --changed 108/108 · verifier 생략(검증 간소화 기간)
- Follow-up: 1.x 결함: bidir_link.py entry_id_stem 미정의/잔존
- Follow-up: 1.x 결함: score_freshness 가 대상이 줄면 점수가 오른다 (미측정 아님)
- Follow-up: 소유자 결정 Q7
