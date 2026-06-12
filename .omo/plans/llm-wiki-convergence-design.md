# LLM Wiki Layer Convergence — Karpathy 패턴 + 우리 워크플로우 진화 설계

- 문서 목적: Andrej Karpathy 의 LLM Wiki (2026-04 gist) 개념을 우리 `standard_ai_workflow` 의 메모리/지식 레이어에 수렴시키기 위한 검토 결과를 기록한다. 단순 리뷰가 아니라 Phase 1 도입을 위한 의사결정 근거 문서.
- 범위: Karpathy LLM Wiki 핵심 개념 압축, 우리 `memory/` 의 현재 한계 gap 분석, 진화 방향 2개 (병렬 추가 / 대체), 권장안 (방향 A: 병렬 추가), 구체 설계 (`wiki/` 디렉토리 구조 + 신규 스킬 3종 + Schema 강화), 마이그레이션 3-phase 로드맵.
- 대상 독자: Sisyphus (orchestrator), maintainer, 다음 마일스톤 (v0.5.11+ / v0.6+) 설계자.
- 상태: draft (Rev 0 — 분석 단계, 결정 전)
- 최종 수정일: 2026-06-12
- 관련 문서: `.omo/plans/v0.5.11-plus-roadmap.md` (직전 milestone), `workflow-source/MEMORY_GOVERNANCE.md` (메모리 쓰기 규칙), `docs/architecture/ADR-001-source-state-knowledge-3-layer-separation.md` (3-Layer ADR)
- **v0.6.0 wiki layer**: [`.omo/plans/v0.5.11-plus-llm-wiki-distributed-rules.md`](./v0.5.11-plus-llm-wiki-distributed-rules.md) (accepted, P1 implemented)
- 후속: §6 "분산 위키 규칙(commitor별 1차 기록 + merge 시 취합)" 별도 검토 — `v0.5.11-plus-llm-wiki-distributed-rules.md` 로 분리 예정
- 작성자: Sisyphus (orchestrator)
- 적용 대상: `standard_ai_workflow` 저장소 + 본 문서를 도입한 외부 프로젝트

---

## 0. Executive Summary

| 그룹 | 항목 | 우선순위 | 비고 |
|---|---|---|---|
| 권고 | `ai-workflow/wiki/` 병렬 신설 (방향 A) | P0 | 기존 `memory/` 무변경, 회귀 위험 0 |
| 신규 | `wiki-ingest` / `wiki-query` / `wiki-lint` 스킬 3종 | P0 | Karpathy Ingest/Query/Lint 운영 매핑 |
| 강화 | `MEMORY_GOVERNANCE.md` 에 `wiki/` 헌법(SCHEMA) 절 추가 | P0 | 페이지 타입 frontmatter, Ingest/Query/Lint 워크플로 |
| 보강 | `backlog-update` 에 ingest hint 추가 | P1 | 작업 완료 시 위키 갱신 후보 자동 플래그 |
| 보강 | `workflow-linter` 에 wiki-lint 검사 통합 | P1 | 모순/스테일/고아/누락 자동 감지 |
| 후속 | 분산 위키 규칙 (commitor별 1차 기록 + merge 시 취합) | P1 | 별도 문서 — 현재 진행 중 |

**핵심 결정** (검토 결론):
- 우리 `memory/` 는 "운영 state" 로서는 우수. "지식 위키" 로서는 빈약.
- Karpathy LLM Wiki 패턴을 **병렬로 추가** (방향 A) 하는 것이 정공법. 기존 인프라 (3-Layer, Contract v1, 52 smoke test, 6 하네스 overlay, `MEMORY_GOVERNANCE.md`) 가 그대로 활용 가능.
- 전면 대체 (방향 B) 는 11개 스킬 + 6개 하네스 오버레이 재설계 필요 → 위험 대비 효과 불명.

---

## 1. Karpathy LLM Wiki 핵심 개념 (2026-04 gist)

### 1.1 문제 인식

> "Most people's experience with LLMs and documents looks like RAG: you upload a collection of files, the LLM retrieves relevant chunks at query time, and generates an answer. This works, but the LLM is rediscovering knowledge from scratch on every question. There's no accumulation."

핵심: **RAG 는 매 쿼리마다 재유도. 지식은 축적되어야 한다.**

### 1.2 컴파일러 vs 인터프리터

| 차원 | RAG (인터프리터) | LLM Wiki (컴파일러) |
|---|---|---|
| 처리 시점 | 쿼리 시 (매번) | 인제스트 시 (소스당 1번) |
| 교차참조 | 즉석에서 발견 | 미리 구축·유지 |
| 모순 처리 | 놓치기 쉬움 | 인제스트 중 명시 플래그 |
| 지식 축적 | 없음 | 소스 + 쿼리 양쪽 |
| 출력 형식 | 채팅 (휘발) | 마크다운 (지속) |
| 인간 역할 | 업로드/쿼리 | 큐레이션·탐색·질문 |
| 회수 신뢰도 | ~90% (청킹 깨짐) | 100% (전체 파일) |
| 효율 (RAG 대비) | 1x | ~70x (500KB 이내) |

> "Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase."

### 1.3 3-Layer 아키텍처

- **`raw/`** — 불변 소스 (article, paper, transcript, asset). LLM 은 읽기만, 절대 수정 X.
- **`wiki/`** — LLM 소유, 구조화·교차링크 마크다운 (entities / concepts / comparisons / queries / `index.md` / `log.md`). 한 소스가 10~15 페이지 갱신.
- **`SCHEMA.md`** (= `CLAUDE.md` / `AGENTS.md`) — 위키 운영 헌법. **가장 중요한 파일.**

### 1.4 3가지 운영

- **Ingest**: 소스 → 다중 페이지 갱신 + `log.md` append + 모순 플래그.
- **Query**: `index.md` 먼저 → 관련 페이지 → 답변 → file-back 판단.
- **Lint**: 주기적 — 모순, 스테일, 고아, 누락 교차참조, 누락 중요 개념.

### 1.5 Software 3.0 / Anterograde Amnesia 프레이밍

> "LLMs are a bit like a coworker with Anterograde amnesia — they don't consolidate or build long-running knowledge or expertise once training is over."

LLM Wiki 는 이 "전방위 기억상실 동료"에게 persistent scratchpad 를 주는 것. Sequoia Ascent 2026 강연의 Software 3.0 프레임워크 안에 위치.

### 1.6 인용 모음 (설계 근거)

- "The wiki is a persistent, compounding artifact."
- "Humans abandon wikis because the maintenance burden grows faster than the value. LLMs don't get bored, don't forget to update a cross-reference, and can touch 15 files in one pass."
- "The part [Vannevar Bush] couldn't solve was who does the maintenance. The LLM handles that."
- "Good answers can be filed back into the wiki as new pages. ... your explorations compound in the knowledge base just like ingested sources do."

---

## 2. 우리 워크플로우 메모리 현재 상태 (Gap 분석)

### 2.1 현재 메모리 = Task Tracker (지식 위키 아님)

| 위치 | 역할 | 한계 |
|---|---|---|
| `state.json` (16줄) | 세션 캐시 | 순수 운영 state. 지식 없음. |
| `session_handoff.md` | 다음 세션 인계 | "지금 뭐 하나"만. "X에 대해 뭘 아나" 없음. |
| `work_backlog.md` | 마스터 백로그 인덱스 | 작업 목록. 개념·결정·패턴 없음. |
| `backlog/YYYY-MM-DD.md` | 일일 작업 로그 | 작업 단위. 교차 작업 합성 없음. |
| `PROJECT_PROFILE.md` | 프로젝트 컨텍스트 | 정적. 작업 중 발견 흡수 안 함. |
| `repository_assessment.md` | 초기 코드 분석 | 도입 1회. 누적 안 됨. |
| `release/v0.5.X/` | 릴리스 스냅샷 | 히스토리. 검색·합성용 아님. |
| `MEMORY_GOVERNANCE.md` | 쓰기 규칙 | 운영 규칙. 지식 구조 정의 없음. |

### 2.2 격차 매트릭스 (Karpathy LLM Wiki 대비)

| Karpathy 개념 | 우리 상태 | 격차 |
|---|---|---|
| `raw/` 불변 소스 | 없음 (세션 종료 후 휘발) | **#1 격차** |
| `wiki/` 개념·엔티티 페이지 | 없음 | **#2 격차** |
| `SCHEMA.md` 헌법 | `global_workflow_standard.md` 부분 대응 | 부분 — 명시적 위키 운영 규칙 부재 |
| `index.md` 카탈로그 | `state.json` (16줄) | 너무 빈약 |
| `log.md` 작업 로그 | `backlog/YYYY-MM-DD.md` | 형식만, 의미적 시계열 아님 |
| Ingest 운영 | `backlog-update` | 소스 → 다중 페이지 갱신 패턴 없음 |
| Query 운영 | `session-start` (linear read) | 인덱스 기반 retrieval 없음 |
| Lint 운영 | `workflow-linter` (링크/메타) | 모순·스테일·고아 감지 없음 |
| File-back 답변 | 없음 | **#3 격차** — 좋은 답변도 휘발 |

### 2.3 우리 시스템의 강점 (그대로 활용)

1. **3-Layer 분리 (ADR-001)** — Source / Runtime / Project Docs. Karpathy 의 raw/wiki/schema 분리보다 정교.
2. **Contract v1** — 멀티 에이전트가 위키를 동시에 갱신할 때 충돌 방지 규약 가능.
3. **52개 smoke test + state cache builder** — 신규 컴포넌트 (wiki lint, backlink index) 검증 인프라 준비됨.
4. **6개 하네스 배포** — 위키 layer 도 동일 overlay 패턴 적용 가능.
5. **`MEMORY_GOVERNANCE.md` 존재** — 위키 운영 규칙을 여기에 더 얹으면 됨.
6. **브랜치별 메모리 분리** (`memory/codex/phase6/`, `memory/gemini/phase10/` 등) — 이미 분산 기록의 물리적 토대가 있음.

---

## 3. 진화 방향 비교

### 3.1 방향 A: 병렬 추가 (권장) ✅

- `memory/` 옆에 `wiki/` layer 신설
- 운영 state (handoff, backlog) 그대로 유지
- 지식만 위기에 격리
- 점진적 도입, 회귀 위험 0
- 첫 페이지 타입: `Concept`, `Decision`, `Pattern`, `Component`

### 3.2 방향 B: 메모리 대체 (비권장) ❌

- `memory/` 전체를 LLM Wiki 로 대체
- 작업 추적까지 위기에 흡수
- 11개 스킬 + 6개 하네스 오버레이 재설계 필요
- 전면 재작업, 회귀 위험 高

**권고: 방향 A.**

---

## 4. 구체 설계 (방향 A 기준)

### 4.1 `wiki/` 디렉토리 구조

```
ai-workflow/
├── memory/                            # 기존 그대로 (작업 state)
│   ├── state.json
│   ├── session_handoff.md
│   ├── work_backlog.md
│   ├── backlog/YYYY-MM-DD.md
│   ├── PROJECT_PROFILE.md
│   └── ...
└── wiki/                              # 신규 — LLM Wiki (지식)
    ├── index.md                       # 페이지 카탈로그 + 1줄 요약
    ├── log.md                         # 인제스트/쿼리 작업 로그
    ├── entities/                      # 엔티티 (Component/Service/API/Person)
    │   └── workflow-kits/
    │       └── contract-v1.md
    ├── concepts/                      # 개념 (MCP/Skill/Orchestrator/Pydantic)
    │   ├── mcp-transport.md
    │   ├── orchestrator-subagent-pattern.md
    │   └── session-continuity.md
    ├── decisions/                     # ADR 형식
    │   ├── ADR-001-source-state-knowledge-3-layer.md
    │   └── ADR-004-wiki-layer-introduced.md
    ├── patterns/                      # 재사용 패턴
    │   ├── harness-overlay-pattern.md
    │   └── memory-write-merge-pattern.md
    └── queries/                       # file-back된 답변
        └── why-mcp-sdk-transport-closed-regression.md
```

### 4.2 신규/확장 스킬 3종

| 스킬 | 트리거 | 동작 | Karpathy 매핑 |
|---|---|---|---|
| **`wiki-ingest`** (신규) | 세션 종료, 마일스톤, 사용자 명시 | handoff+backlog → 관련 위키 5~15페이지 갱신, `log.md` append, 모순 플래그 | Ingest 운영 |
| **`wiki-query`** (신규, 또는 `session-start` 강화) | "X에 대해 뭐 아는가?" / 세션 시작 | `index.md` → 관련 페이지 → 답변 → file-back 판단 | Query 운영 |
| **`wiki-lint`** (신규, 또는 `workflow-linter` 확장) | 주기적 (릴리스 전, 주 1회) | 모순·스테일·고아·누락 교차참조 감지 | Lint 운영 |
| `backlog-update` (확장) | 작업 완료 시 | (기존) + 작업 중 발견한 개념/패턴 후보 플래그 | Ingest hint |

### 4.3 `wiki/SCHEMA.md` (= 우리 확장판)

기존 `MEMORY_GOVERNANCE.md` 를 보완하는 위키 운영 헌법:

```markdown
# Wiki 운영 헌법

## 페이지 타입별 frontmatter
- entities/  →  type, status, last_ingested_from, related_pages
- concepts/  →  type, status, source_count, contradictions
- decisions/ →  type, status, decided_at, alternatives_considered
- patterns/  →  type, status, used_in, related_components
- queries/   →  type, asked_at, sources, answer_synthesis

## Ingest 워크플로우
1. 세션 종료 시 handoff+backlog 읽기
2. 언급된 엔티티/개념 식별
3. 관련 페이지 다중 갱신 (10~15개)
4. 모순 발견 시 [CONTRADICTION] 태그 + 양쪽 페이지에 명시
5. log.md에 append (## [YYYY-MM-DD] ingest | session-summary)

## Query 워크플로우
1. index.md 먼저 로드
2. 관련 페이지 식별 (3~7개)
3. 답변 산출 + 페이지 citation
4. 30줄 초과 또는 합성 결과 → queries/ 페이지로 file-back

## Lint 체크리스트
- [ ] 모순 페이지 ([CONTRADICTION] 태그 검색)
- [ ] 90일 이상 미갱신 페이지 (스테일)
- [ ] 인바운드 링크 0인 페이지 (고아)
- [ ] 언급은 많지만 페이지 없는 개념 (누락)
- [ ] 양방향 링크가 단방향인 경우
```

### 4.4 3-Layer 에서 위키 위치

`docs/architecture/ADR-001-source-state-knowledge-3-layer-separation.md` 의 3-Layer 정의에 따르면:

- **Source Layer** (`workflow-source/`) — 템플릿·거버넌스 정의. **위키 운영 헌법 (`wiki/SCHEMA.md` template)도 여기에 둠.**
- **Runtime Layer** (`ai-workflow/`) — 활성 세션 state. **`ai-workflow/wiki/` 도 여기에 둠 (= 각 프로젝트 인스턴스).**
- **Project Docs Layer** (`docs/`, project root) — 실제 프로젝트 문서. **위키는 여기 속하지 않음** (지식 베이지 운영 state).

→ 위키는 Runtime layer 의 일부. Project docs 와 경계 명확.

---

## 5. 마이그레이션 로드맵

### Phase 1 (1~2주, 검증 가능)

- `ai-workflow/wiki/` 디렉토리 신설
- `SCHEMA.md` + `index.md` + `log.md` 부트스트랩
- `wiki-ingest` 스킬 프로토타입 (수동 트리거)
- 기존 `memory/` 무변경
- 1개 개념 페이지 (예: `concepts/mcp-transport.md`) 실전 작성

### Phase 2 (1개월)

- `backlog-update` 에 ingest hint 추가
- 릴리스마다 자동 `wiki-lint` 실행
- 인덱스 카드 검색 CLI (BM25) — `workflow_kit` 에 추가
- 5개 이상 페이지 누적 시 lint 실효성 검증

### Phase 3 (3개월)

- 세션 종료 시 `wiki-ingest` 반자동 트리거
- file-back 답변의 자동 감지·승인
- 하네스 overlay 6종에 `wiki/` 디렉토리 추가
- 카탈로그/문서 README 에 "second brain" 섹션 추가
- 분산 위키 규칙 (commitor별 1차 기록 + merge 시 취합) 정식 도입 — 별도 plan 문서

---

## 6. 분산 위키 규칙 (별도 plan 으로 분리 — 작성 완료)

**제안된 규칙** (사용자):
- commitor 마다 wiki 의 1차 기록이 이루어지고
- 브랜치 간 merge / pull 로 동기화 수행 시 1차 기록을 합쳐서 전체의 기록으로 취합

**검토 결과 → 결정**: 옵션 A, A, A (D1=ai-workflow/wiki/, D2=git 추적, D3=per-session ingest). AI-optimized 문서 작성 방식 적용.

**별도 plan 문서 작성 완료**:
- 경로: [`.omo/plans/v0.5.11-plus-llm-wiki-distributed-rules.md`](./v0.5.11-plus-llm-wiki-distributed-rules.md)
- 내용: 7 rules (R1~R7, 영구 ID) + 4 anti-patterns (A1~A4) + 8 validation (V-1~V-8) + 4 phases (P1~P4) + ADR-004 draft
- 형식: AI-optimized (YAML frontmatter, stable anchors, 영구 ID, cross-reference index)
- 버전: 0.1.0 (2026-06-12)

**§6 항목 해결 상태**:
- ✅ 우리 저장소 multi-harness 매핑: R6 topic-branch mode + index anchor 구조
- ✅ 1차 기록 단위: R2 page atomicity (1 commit = 1 ingest = 5~15 페이지)
- ✅ merge 충돌 해결: R5 additive + R7 merge-doc-reconcile 위키 확장 (4 conflict type)
- ✅ 인덱스 일관성: R4 anchor 기반 구조화 (R5·R7 과 결합)
- ✅ CRDT / federated wiki: ADR-004 §"Alternatives considered" 에서 검토·기각 근거 명시

---

## 7. 다음에 읽을 문서

- 직전 milestone: [`.omo/plans/v0.5.11-plus-roadmap.md`](./v0.5.11-plus-roadmap.md)
- 메모리 쓰기 규칙: [`../workflow-source/MEMORY_GOVERNANCE.md`](../../workflow-source/MEMORY_GOVERNANCE.md)
- 3-Layer ADR: [`../docs/architecture/ADR-001-source-state-knowledge-3-layer-separation.md`](../../docs/architecture/ADR-001-source-state-knowledge-3-layer-separation.md)
- Karpathy 원본 gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Karpathy Sequoia Ascent 2026 talk 요약: https://karpathy.bearblog.dev/sequoia-ascent-2026/

---

## 8. Revision History

- **Rev 0 (2026-06-12)** — 초안 작성. Karpathy LLM Wiki 검토, 우리 워크플로우 gap 분석, 방향 A (병렬 추가) 권고, Phase 1~3 로드맵, §6 분산 규칙은 후속 plan 으로 분리.
- **Rev 1 (2026-06-12)** — P1 wiki layer prototype implemented. ADR-004 accepted. v0.6.0 release. See follow-up plan.
