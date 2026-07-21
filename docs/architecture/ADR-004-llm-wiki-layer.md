# ADR-004: LLM Wiki Layer 도입

- 문서 목적: standard_ai_workflow 의 `ai-workflow/wiki/` layer 도입 결정 rationale 와 운영 impact 를 정식 기록. Karpathy LLM Wiki (2026-04 gist) 패턴을 우리 3-Layer Runtime layer 안에 흡수한 결정.
- 범위: wiki 위치·git 추적 정책·ingest 트리거·7개 규칙 (R1~R7)·4개 안티패턴 (A1~A4)·8개 검증 (V-1~V-8)·4개 마이그레이션 phase (P1~P4)·alternatives considered.
- 대상 독자: maintainer, Mavis consumer, 위키 운영자, 다음 마일스톤 설계자.
- 상태: Accepted (v0.6.0, P1 prototype implemented)
- 최종 수정일: 2026-07-21
- 관련 문서: [`./README.md`](./README.md), [`./ADR-001-source-state-knowledge-3-layer-separation.md`](./ADR-001-source-state-knowledge-3-layer-separation.md), [`../../.omo/plans/v0.5.11-plus-llm-wiki-distributed-rules.md`](../../.omo/plans/v0.5.11-plus-llm-wiki-distributed-rules.md), [`../../.omo/plans/llm-wiki-convergence-design.md`](../../.omo/plans/llm-wiki-convergence-design.md), [`../../workflow-source/MEMORY_GOVERNANCE.md`](../../workflow-source/MEMORY_GOVERNANCE.md)

- **Status**: Accepted (v0.6.0, P1 prototype implemented)
- **Date**: 2026-06-12
- **Accepted in**: v0.6.0
- **Supersedes**: —
- **Superseded by**: —

## Context

Karpathy LLM Wiki (2026-04) 패턴 분석 결과, 우리 `ai-workflow/memory/` 는 운영 state 로는 우수하나 지식 위키로는 빈약. 지식 누적·합성·재사용을 위한 별도 layer 필요. `memory/` 의 gitignore 정책과 의도적으로 분리된 durable knowledge layer 가 요구됨.

기존 인프라 (3-Layer 분리, Contract v1, 52+ smoke test, 6 하네스 overlay, `MEMORY_GOVERNANCE.md`) 를 활용하면서 회귀 위험 0 으로 지식 layer 만 추가하는 방향 (방향 A) 이 검토됨. 방향 B (메모리 대체) 는 11개 스킬 + 6개 하네스 오버레이 재설계가 필요해 위험 대비 효과 불명.

`memory/` 의 gitignore 정책과 의도적으로 분리된 durable knowledge layer 가 요구됨. ADR-001 §3 의 Runtime layer 안에 흡수하여 Project docs 침범을 피함. git 추적 (memory/ 와 분리) + ingest-first (per-session) + release-freeze (자동 파생) 의 3축 정책으로 운영.

**Implementation**: P1 prototype at `ai-workflow/wiki/` (SCHEMA + index + log + 2 concept pages). 위 분산 규칙 (R1~R7) + 안티패턴 (A1~A4) + 검증 (V-1~V-8) 의 1차 프로토타입 구현 완료. v0.6.0 release 시점에 accepted.

## Decision

`ai-workflow/wiki/` 신설. git 추적. ingest-first (per-session) + release-freeze (자동 파생). 7개 규칙 (R1~R7) + 4개 안티패턴 (A1~A4) + 8개 검증 (V-1~V-8) 적용.

### 결정 3 종 (D1·D2·D3)

| ID | 결정 | 근거 |
|---|---|---|
| **D1** | wiki 위치 = `ai-workflow/wiki/` (Runtime layer) | ADR-001 §3 의 Runtime layer 안에 흡수. Project docs 와 분리 유지. `docs/wiki/` 는 Project docs 침범, `workflow-source/wiki/` 는 Source layer 침범 → 둘 다 거부 |
| **D2** | wiki 추적 = **git 추적** (memory/ 는 gitignore 유지) | 분산·merge·history 의 전제. memory (volatile session state) 와 wiki (durable knowledge) 를 별도 정책으로 운용. ADR-001 의 spirit 보존 (layer 분리) |
| **D3** | ingest 트리거 = **per-session** (session 종료 시) | M1 모드. M3 (release-freeze) 는 자동 파생 (release 스냅샷이 wiki/ 까지 포함) |

### 7 rules (R1~R7) — 영구 ID, 본 ADR 의 일부로 정식 채택

- **R1: Wiki Location** — wiki 는 `ai-workflow/wiki/` 에 둔다. 다른 위치 사용 금지.
- **R2: Page Atomicity** — 1 commit = 1 ingest (5~15 페이지 동시 갱신). 페이지 = primary record atomic unit.
- **R3: Pull-Before-Push** — wiki push 직전 `git fetch && git rebase origin/main` 필수. 자동 push / force push 금지.
- **R4: Index Structure** — `wiki/index.md` 는 anchor 기반 구조화, 자유 산문 금지.
- **R5: Additive Merge** — 충돌 시 양쪽 결합, 폐기 금지. LLM reviewer 가 canonical 선택.
- **R6: Topic-Branch Mode** — 큰 탐색 phase 만 `wiki/topic/<name>` 브랜치 사용. PR promote 로 main 통합.
- **R7: Merge-Resolution Extension** — `merge-doc-reconcile` skill 을 wiki 전용으로 확장. conflict type 별 resolution 명시.

상세 rule schema·validation·lifecycle: [`.omo/plans/v0.5.11-plus-llm-wiki-distributed-rules.md`](../../.omo/plans/v0.5.11-plus-llm-wiki-distributed-rules.md) §4-§5.

### 마이그레이션 4 phase (P1~P4)

- **P1 (1~2주)** — `ai-workflow/wiki/` 디렉토리 + SCHEMA + index.md + 1~2 concept page 수동 작성. wiki git 추적 정책 적용. lint 스킬 1차 프로토타입. **v0.6.0 에서 implemented.**
- **P2 (2~4주)** — `wiki-ingest` skill (session 종료 트리거, 자동 ingest), `wiki-lint` skill (릴리스 전 실행), 5+ 페이지 누적. R2·R3·R5 적용.
- **P3 (1~2월)** — `wiki-query` skill (session-start retrieval), `merge-doc-reconcile` wiki 확장 (R7), topic branch 모드 (R6) PoC. R4·R6·R7 적용.
- **P4 (3월+)** — 하네스 overlay 6종 wiki 동기화, federated sync (multi-project) 평가.

## Consequences

### Positive

- **지식 누적·합성·재사용 가능** (RAG 대비 ~70x 토큰 효율, 500KB 이내)
- **ADR-001 3-Layer 정신 유지** — Runtime layer 안에 흡수, project docs 침범 안 함
- **기존 인프라 활용** — bootstrap_lib, contract_v1, 6 harness overlay, merge-doc-reconcile
- **LLM Wiki = LLM-friendly 문서 작성 방식** 으로 agent 의 wiki 활용도 극대화

### Negative / Trade-offs

- **위키 운영 헌법 (SCHEMA) · lint 스킬 · ingest 스킬 등 신규 컴포넌트 필요** (P1~P3 진행)
- **`merge-doc-reconcile` 위키 확장 (R7) 필요** — 기존 skill 의 wiki 전용 모드
- **`.gitignore` carve-out 정책 변경 (D2)** — memory/ 와 분리 정책 명시
- **6 harness overlay wiki/ 동기화 작업 (P4)** — 각 하네스별 emit 정책 추가

## Alternatives considered

| Option | Reason rejected |
|---|---|
| 메모리 대체 (방향 B, `.omo/plans/llm-wiki-convergence-design.md` §3) | 11개 스킬 + 6 하네스 재설계 필요. 위험 대비 효과 불명 |
| Federated Wiki (Ward Cunningham) | federation discovery 가 scale 안 됨 (2018 archived). 우리 1인 dev 환경엔 과설계 |
| CRDT (Yjs, Automerge) | tombstone overhead + 의미적 모순 미감지 + 1인 dev 에선 과설계 |
| `docs/wiki/` (Project docs) | ADR-001 의 Runtime/Project docs 경계 침범. bootstrap/exclude 정책 충돌 |
| `workflow-source/wiki/` (Source) | Source layer 는 템플릿·거버넌스 정의만. 운영 상태 불가 |

## References

- Karpathy LLM Wiki gist (2026-04): https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Karpathy Sequoia Ascent 2026 talk 요약: https://karpathy.bearblog.dev/sequoia-ascent-2026/
- ADR-001: Source / State / Knowledge 3-layer 분리
- [`.omo/plans/v0.5.11-plus-llm-wiki-distributed-rules.md`](../../.omo/plans/v0.5.11-plus-llm-wiki-distributed-rules.md) — 7 rules + 4 anti-patterns + 8 validation + 4 phases 본문
- [`.omo/plans/llm-wiki-convergence-design.md`](../../.omo/plans/llm-wiki-convergence-design.md) — Karpathy LLM Wiki 검토 + 방향 A 권고 + 3-Phase 로드맵
- `workflow-source/MEMORY_GOVERNANCE.md` — 메모리 쓰기 규칙 (wiki 와 분리 운용)
- `workflow-source/core/workflow_state_vs_project_docs.md` — state vs project docs 경계
- `workflow-source/core/merge_doc_reconcile_skill_spec.md` — wiki 확장 (R7) 의 기반
