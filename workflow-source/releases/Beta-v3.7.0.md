# Beta v3.7.0 — DCR 승인이 곧 확정 (2026-11-26)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- `hub_dcr_decide(approve)` 가 같은 트랜잭션에서 새 ADR 을 허브 위키 `decisions/adr-NNN-<slug>.md` 에 쓰고 DCR 을 `accepted` 로 바꾼다. 위키 decision frontmatter(type · status · adr_id · decided_at · alternatives_considered · related_pages)와 `supersedes` · `dcr` 를 싣는다. 응답에 `adr_id` · `wiki{path, version, ingest_id}` 가 오고 `instruction`(Git 커밋 지시)은 없어졌다.
- 대체되는 Git ADR 의 지식 projection 은 승인 때 `superseded` 로 표시한다. 옛 ADR 본문은 고치지 않는다.
- ADR 번호는 허브 위키와 Git 지식 원본의 ADR 을 모두 보고 매긴다.
- 3.6.1 이하에서 승인돼 `approved_pending_export` 에 남은 DCR 은 예전처럼 같은 내용을 source sync 하면 `accepted` 가 된다.
- 이유(소유자 2026-11-26): 허브 이관 뒤 위키의 정본은 허브이고 저장소 `ai-workflow/` 는 읽기 전용 기록이라, Git 커밋을 확정 조건으로 두면 온보딩한 저장소에서 승인만으로 결정이 끝나지 않았다. 계약 변경은 `hub_knowledge_decisions_spec.md` §DCR 에 적었다.

## 검증

- 누적 smoke **360/360 PASS**
- `check_hub_knowledge` 가 Python · Go 에서 각 20/20 — 승인 즉시 accepted · 위키 본문 = 응답 본문 · 위키 lint 위반 0 · 위키 ADR 까지 본 번호(050 → 051, 052 선점 → 053) · 예전 대기 DCR 의 sync. 되주입 5건(Python · Go 상태, Python · Go 번호, Python 위키 쓰기 생략)이 각 런타임의 해당 case 만 red.

## 운영 범위

- DB 판은 21 그대로다. 저장소에 ADR 파일이 필요하면 위키 내보내기(`hub_wiki_export`)를 쓴다.
- 사람 화면의 DCR 결정 단추는 아직 없다 — 결정은 MCP `hub_dcr_decide`(승인된 human owner).
