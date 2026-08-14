---
id: TASK-2026-08-14-docs-english-entrypoints-001
status: done
created_at: 2026-08-14
source_anchor: generic-task-2026-08-14-docs-english-entrypoints-001
source_path: backlog/2026-08-14.md
kind: generic
---

# TASK-2026-08-14-docs-english-entrypoints-001 — AI 진입점·SKILL.md 영어화

## 📝 Description

- 상태: done
- 요청일: 2026-08-14
- 담당: AI Agent
- 작업 내용: AI 가 주로 읽는 진입점·스킬 문서를 영어로 (소유자 지시) — 정본부터 옮기고 생성물은 재생성
- 범위 밖: docs/ 제품 문서(소유자가 읽는 결정 문서) / 메모리 기록의 한국어 / 대화·보고
- 완료 기준: (작성 필요 — 검증 방법을 구체적으로 적는다)

## 🛠️ Implementation / Content

- 진행 현황: `2026-08-14 05:54` 기준 AI 가 주로 읽는 진입점·스킬 문서를 영어로 (소유자 지시)

## ✅ Outcome

- 작업 결과: 소비자가 받는 진입점·스킬 문안을 3단계로 영어화. 상세는 브랜치 세션 기록
- 작업 결과: stage 1 — 규칙 정본 §1·§3·§8·§11 + 스냅샷/진입점 블록 재생성. 렌더러가 §11.1 을 한국어 키워드로 조회하던 5곳도 함께 이동
- 작업 결과: stage 2 — 스킬 원본 13개 (16,253 → 12,437 tok, −23%). check_maturity_registry 가 요구하는 `Usage` 절 규약 준수
- 작업 결과: stage 3 — harnesses/renderers.py 템플릿 625 → **0** / plugin_payload.py 소비자 문안 → **0** / bootstrap_lib/renderers.py 산문 완료
- 작업 결과: **경계를 확정했다** — 메모리 문서 필드 라벨(`- 상태:` 등)은 `project_docs.py` STATUS_RE 와 writer 4곳이 emit 하는 **파싱 계약**이라 텍스트 편집이 아니라 데이터 형식 마이그레이션이다. TASK-2026-08-14-main-008 로 넘겼다
- 작업 결과: 산문을 조회하던 **검출기 9곳이 함께 이동**했고 전부 red 로 스스로를 드러냈다. 그중 2곳(`(있으면)`/`(if present)`, 평가 문서 14 라벨)은 **양쪽 표기를 모두 받도록** 고쳤다 — 소비자 저장소에는 아직 한국어 산출물이 남아 있어 한쪽만 보면 조용히 실명한다
- 검증 결과: 전량 2축 256/256 ×2 green. 토큰 실측: global_workflow_standard.md 5,626→4,882(−13%) / CLAUDE.md 4,358→3,987(−9%) / SKILL.md 13개 16,253→12,437(−23%)
- 후속 작업: 메모리 문서 라벨 영어화는 TASK-2026-08-14-main-008(task SSOT 구조화)의 일부로
