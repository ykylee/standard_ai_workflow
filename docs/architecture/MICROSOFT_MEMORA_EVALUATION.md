# Microsoft Memora Evaluation

- 문서 목적: Microsoft Research의 `Memora` 개념과 공개 구현을 조사하고, `standard_ai_workflow` 에 적용 가능한지 검토한다.
- 범위: 공개 자료 요약, 현재 저장소와의 대응 관계, 도입 가능 범위, 권장 실험안
- 대상 독자: 워크플로우 설계자, 메모리 계층 설계자, 연구 프로토타입 검토자
- 상태: draft
- 최종 수정일: 2026-07-03
- 관련 문서: [./README.md](./README.md), [./ADR-001-source-state-knowledge-3-layer-separation.md](./ADR-001-source-state-knowledge-3-layer-separation.md), [../../workflow-source/MEMORY_GOVERNANCE.md](../../workflow-source/MEMORY_GOVERNANCE.md), [../../workflow-source/core/workflow_agent_topology.md](../../workflow-source/core/workflow_agent_topology.md), [../../workflow-source/core/orchestrator_subagent_contract_v1.md](../../workflow-source/core/orchestrator_subagent_contract_v1.md)

## 1. Executive Summary

`Memora` 는 Microsoft Research가 공개한 장기 에이전트 메모리 프레임워크다. 2026년 6월 29일 Microsoft Research 블로그와 함께 공개되었고, 논문과 GitHub 저장소가 함께 열려 있다.

핵심 아이디어는 간단하다.

- 저장 본문(`memory value`)과 검색 구조(`primary abstraction`, `cue anchors`)를 분리한다.
- 검색은 본문 전체를 직접 임베딩해 뒤지는 대신, 짧은 추상화와 다중 anchor를 따라간다.
- 그래서 세부 정보는 잃지 않으면서도, 시간이 지날수록 메모리가 파편화되는 문제를 줄이려 한다.

`standard_ai_workflow` 에는 이미 다음 기반이 있다.

- `ai-workflow/memory/` 의 상태 문서 계층
- `archive/` 중심의 freeze 및 ingest lifecycle
- `orchestrator + worker` 역할 분리
- wiki / docs / runtime 을 분리한 3-layer 구조

따라서 **Memora 전체를 그대로 이식하기보다는**, 우리 구조 위에 아래 3개 개념을 선택적으로 가져오는 것이 가장 현실적이다.

1. 메모리 본문과 검색용 추상화의 분리
2. 한 메모리에 여러 retrieval anchor를 부여하는 방식
3. semantic top-k 1회 검색 대신 단계적 retrieval policy를 두는 방식

결론적으로, **개념 차용 가치는 높고 즉시 실험도 가능하지만, 현재 저장소에 바로 full replacement로 넣을 단계는 아니다.**

## 2. What Memora Is

확인한 공개 자료 기준 사실:

- Microsoft Research 블로그 게시일: 2026-06-29
- arXiv 제출일: 2026-02-03
- 공개 코드 저장소: `microsoft/Memora`
- 라이선스: MIT

공개 설명 기준 Memora의 메모리 단위는 3요소다.

1. `memory value`
   전체 본문. 세부 맥락과 수치를 보존한다.
2. `primary abstraction`
   해당 메모리를 대표하는 canonical 요약. 갱신/병합의 기준점이 된다.
3. `cue anchors`
   같은 메모리에 접근할 수 있는 다중 semantic entry point. 사람, 일정, 주제, 사건 등 서로 다른 각도에서 같은 메모리로 이어지게 한다.

이 설계는 다음 문제를 겨냥한다.

- raw text RAG: 세부는 남지만 메모리 항목이 잘게 파편화됨
- summary-only memory: 압축은 되지만 중요한 수치/예외/맥락이 사라짐
- rigid KG memory: 구조는 강하지만 도메인별 스키마 의존성이 큼

Memora는 이를 "저장은 풍부하게, 검색은 가볍게"로 풀려는 접근이다.

## 3. Public Code Status

연구용 공개 소스코드는 실제로 존재한다.

- GitHub: [microsoft/Memora](https://github.com/microsoft/Memora)
- Paper: [Memora: A Harmonic Memory Representation Balancing Abstraction and Specificity](https://arxiv.org/abs/2602.03315)
- Microsoft Research blog: [Memora announcement](https://www.microsoft.com/en-us/research/blog/memora-a-harmonic-memory-representation-balancing-abstraction-and-specificity/)

2026-07-02 확인 시점 기준으로 저장소에서 보이는 성격은 다음과 같다.

- 연구 코드 중심 공개
- Python 기반
- `quickstart.py` 제공
- benchmark runner 포함
  - `app/locomo`
  - `app/longmemeval`
- 실험적 retrieval policy 학습 코드 포함
  - `memora.rl.*`
- 의존성 폭이 큼
  - `chromadb`, `redis`, `transformers`, `torch`, `langgraph`, `mem0ai` 등

즉, 바로 production dependency로 가져오기보다는 **연구 프로토타입 또는 reference implementation** 으로 보는 편이 안전하다.

## 4. Why It Matters For Our Workflow

현재 저장소의 메모리 구조는 강하다. 다만 retrieval 구조는 아직 상대적으로 얇다.

현재 강점:

- `ai-workflow/memory/active/` 가 세션 상태의 SSOT 역할을 한다.
- `archive/` 와 `release/` 가 lifecycle 및 provenance를 제공한다.
- wiki ingest 규칙이 있어 raw state 와 curated knowledge를 분리한다.
- orchestrator / worker contract 가 있어 누가 무엇을 읽고 쓰는지 경계가 선다.

현재 약점 또는 확장 여지:

- 메모리 문서가 "기록용 본문" 과 "검색용 추상화" 로 명시 분리되어 있지는 않다.
- handoff/backlog/state/wiki 간 연결은 있으나, 같은 사실을 여러 관점에서 재진입시키는 anchor 계층은 약하다.
- retrieval은 문서 선택과 링크 추적 중심이지, memory-unit 수준의 canonical merge 모델은 약하다.

Memora의 장점은 정확히 이 틈에 들어온다.

## 5. Mapping: Memora vs standard_ai_workflow

| Memora 개념 | 우리 저장소의 현재 대응물 | 갭 | 도입 난이도 |
| --- | --- | --- | --- |
| `memory value` | `session_handoff.md`, backlog task 문서, wiki source body | 이미 강함 | 낮음 |
| `primary abstraction` | `state.json` 요약, `purpose_digest`, 문서 제목/상태 요약 | canonical per-memory abstraction 부재 | 중간 |
| `cue anchors` | wiki 링크, tags, related docs, task id, file path | 다중 anchor 체계 부재 | 중간 |
| memory merge/update | backlog task 단위 업데이트, state 재생성 | 같은 주제의 장기 통합 메모리 없음 | 중간 |
| policy retrieval | session-start / doc-sync / wiki-query의 규칙 기반 읽기 | iterative retrieval policy 부재 | 높음 |
| shared memory space | `ai-workflow/memory/` + wiki | 에이전트별 접근 경계/공유 정책 더 필요 | 중간 |

핵심 해석:

- 우리는 raw memory와 provenance는 이미 잘한다.
- Memora는 retrieval-facing structure를 더 잘한다.
- 따라서 **보완 관계** 가 크고, 대체 관계는 작다.

## 6. What We Should Borrow

### 6.1 반드시 검토할 개념

- **본문과 검색 구조 분리**
  - 현재 문서 본문은 유지한다.
  - 대신 별도 추상화 필드를 붙인다.
- **다중 anchor**
  - 사람, 프로젝트, 태스크, 파일, 결정, 날짜 축으로 같은 메모리를 다시 찾을 수 있게 한다.
- **canonical memory entry**
  - 같은 주제의 후속 업데이트가 새 문서를 무한정 만들지 않고, 하나의 장기 메모리 엔트리로 축적되게 한다.

### 6.2 선택적으로 검토할 개념

- **iterative retrieval policy**
  - 먼저 간단한 heuristic + BM25/embedding 혼합으로 시작하고, 나중에 정책형 retrieval로 확장한다.
- **group/shared memory**
  - 우리 구조에서는 project/team/org boundary와 연결하기 좋다.
  - 다만 접근권한, provenance, redaction 규칙이 먼저 필요하다.

### 6.3 당장 가져오지 말아야 할 것

- RL/GRPO 기반 retrieval training
- 무거운 Python/ML dependency 세트 전체
- Memora repo 자체를 core runtime dependency로 직접 편입하는 것

## 7. Recommended Adoption Shape

가장 안전한 도입 방식은 `Memora-inspired metadata layer` 를 우리 memory layer 위에 얹는 것이다.

예시 구조:

```text
ai-workflow/memory/active/
  session_handoff.md
  work_backlog.md
  state.json
  memory_index/
    entries/
      MEM-2026-07-02-001.json
    anchors/
      by_task.json
      by_entity.json
      by_project.json
```

`MEM-*.json` 후보 필드:

```json
{
  "id": "MEM-2026-07-02-001",
  "source_paths": [
    "ai-workflow/memory/active/session_handoff.md",
    "ai-workflow/memory/active/backlog/2026-07-02.md"
  ],
  "primary_abstraction": "Memora evaluation for workflow memory retrieval",
  "cue_anchors": [
    "Microsoft Memora",
    "agent memory",
    "workflow retrieval",
    "research evaluation"
  ],
  "value_digest": "조사 결과와 도입 가능성 요약",
  "owners": ["session-orchestrator"],
  "scope": ["project"],
  "updated_at": "2026-07-02T00:00:00+09:00"
}
```

중요한 점은 다음이다.

- 본문 원문은 기존 문서에 남긴다.
- `memory_index` 는 검색과 연결만 담당한다.
- wiki ingest 는 계속 `archive/` 기준으로 유지한다.
- 3-layer 분리는 깨지지 않는다.

## 8. Proposed Experiment Plan

### Phase 1. Zero-risk metadata prototype

- 목표: 기존 workflow state 문서를 건드리지 않고 추상화/anchor만 별도 생성
- 구현:
  - `state.json` 생성 시 optional `memory_entries[]` 추가
  - 또는 `memory_index/entries/*.json` 생성
  - source path, task id, decision id, date, title에서 anchor 추출
- 기대효과:
  - session-start 와 wiki-query 가 더 적은 read로 관련 문서를 고를 수 있는지 측정 가능

### Phase 2. Canonical memory merge

- 목표: 같은 장기 주제에 대한 업데이트를 하나의 memory entry로 누적
- 구현:
  - `primary_abstraction` 유사도 + task lineage 기반으로 merge
  - 중복 상태 문서 대신 "same topic, new update" 연결
- 리스크:
  - 잘못 합쳐지면 provenance가 흐려질 수 있음

### Phase 3. Retrieval policy integration

- 목표: session-start / doc-sync / backlog-update 가 필요한 문서만 단계적으로 확장 검색
- 구현:
  - 1차: anchor exact match
  - 2차: BM25 or embedding fallback
  - 3차: linked entry expansion
- 리스크:
  - 복잡도 증가
  - worker execution latency 증가

## 9. Risks

- **state vs knowledge 경계 훼손**
  - memory abstraction이 wiki 역할을 먹어버리면 현재 3-layer 규칙이 흐려진다.
- **과도한 자동 병합**
  - canonical merge가 aggressive하면 사실 충돌과 시간축 변화가 뭉개진다.
- **과설계**
  - 현재 문제보다 retrieval 계층이 먼저 커지면 유지비만 늘 수 있다.
- **dependency 비대화**
  - Memora 원본 스택을 그대로 들여오면 지금 저장소의 경량성/문서 중심 구조와 맞지 않는다.

## 10. Recommendation

권장 판단은 다음과 같다.

1. **Memora 개념은 채택 가치가 높다.**
   특히 `primary abstraction` + `cue anchors` 는 우리 workflow memory에 잘 맞는다.
2. **원본 구현은 바로 도입하지 않는다.**
   현재 공개 코드는 연구용 reference implementation 성격이 강하다.
3. **우리 구조에서는 metadata overlay 방식이 적합하다.**
   기존 `ai-workflow/memory/` 와 wiki ingest 규칙을 유지한 채, retrieval layer 만 강화하는 방향이 안전하다.
4. **첫 실험은 state 생성기 또는 session-start 쪽에서 시작하는 것이 가장 싸다.**
   메모리 본문 저장 포맷을 바꾸지 않고도 효과를 측정할 수 있다.

## 11. Suggested Next Step

가장 실용적인 다음 단계는 둘 중 하나다.

- `A.` 설계 전용 후속 문서 작성
  - `Memora-inspired memory index`의 스키마, merge rule, retrieval flow를 ADR 또는 spec으로 정리
- `B.` 작은 프로토타입 구현
  - `state.json` 또는 별도 `memory_index/*.json` 에 `primary_abstraction` / `cue_anchors` 를 생성하는 실험 코드 추가

이 저장소에는 `A -> B` 순서가 더 잘 맞는다.

## 12. References

- Microsoft Research Blog, "Memora: A Harmonic Memory Representation Balancing Abstraction and Specificity", published 2026-06-29  
  https://www.microsoft.com/en-us/research/blog/memora-a-harmonic-memory-representation-balancing-abstraction-and-specificity/
- arXiv, "Memora: A Harmonic Memory Representation Balancing Abstraction and Specificity", submitted 2026-02-03  
  https://arxiv.org/abs/2602.03315
- GitHub, `microsoft/Memora`  
  https://github.com/microsoft/Memora
