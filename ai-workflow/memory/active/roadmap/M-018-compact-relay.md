---
id: M-018
title: compact 중계 — 컨텍스트 압축을 워크플로우 메모리로 건너뛴다
sdlc_phase: concept
status: done
order: 18
parallel_allowed:
  - M-007
deliverables:
  - docs/planning/compact-relay-review-2026-09.md
goals: [G1, G2]
---

# M-018 — compact 중계

소유자 제기(2026-09-30, 107차): 워크플로우와 플러그인을 **compact 의 중계 재료**로
쓴다. 하네스가 컨텍스트를 압축(`/compact` · 자동 compact)하면 요약이 진행 중 task ·
검증된 사실과 미검증 사실의 구분 · 다음 한 걸음을 잃을 수 있다. 압축 **전**에 그것을
워크플로우 메모리에 적고, 압축 **뒤**에 다시 컨텍스트로 넣어 요약 하나에 기대지 않게 한다.

**소유자 결정 (착수 시)**:

- 범위 = **스킬 + hook 2종** — 수동 스킬(checkpoint 기록 + `/compact` 지시문 생성) +
  PreCompact 기계 checkpoint + compact 뒤 SessionStart 재주입.
- checkpoint 위치 = **별도 파일** (`session_handoff.md` 에 쓰지 않는다 — 생성기 입력이라
  세션 도중 쓰기는 형식 오염 위험).
- 진행 = SDLC 온보딩 기본 순서 (concept → requirements → design → implementation).

**전제 이력** (concept 검토가 대면할 것):

- 플러그인은 파생본이다 — 스킬·hook 은 `plugin_payload.py` 가 정본에서 생성하고,
  스킬은 정본 §11.1 명령과 1:1 이다. 새 스킬은 새 §11.1 명령을 전제한다.
- `hooks/hooks.json` 은 Claude 어댑터 훅의 동일 사본으로 Grok Build 도 읽는다 —
  새 이벤트(PreCompact, SessionStart matcher)가 Grok 에서 어떻게 해석되는지는 미실측.
- M-013~M-017 컨텍스트 예산 — 재주입 분량도 예산 안에 있어야 한다.
- 같은 브랜치에 세션이 둘 이상이면 checkpoint 가 서로를 덮는다 (branch-scoped 설계가
  task ID 충돌만 풀었다).

**종결 (2026-09-30)**: 소유자 결정 **안 B** (스킬 + hook 3종 + 요약 대조) · 위치
워크트리 로컬 gitignore · Grok 같은 사본 + 선언 · 재주입 예산 4KB 초안 (산출물 §9).
requirements 단계는 [`M-019`](./M-019-compact-relay-requirements.md) 로 이어진다.

## WBS

- **WBS-18.1** concept 검토 — 하네스별 compact 표면(명령 · hook · 재주입 경로) 실측,
  checkpoint 에 무엇을 싣는가, 파일 위치·수명·동시 세션, §11.1 명령 신설 여부,
  소유자 선택지 — 산출물: `docs/planning/compact-relay-review-2026-09.md`
  (TASK-2026-09-30-main-003)
