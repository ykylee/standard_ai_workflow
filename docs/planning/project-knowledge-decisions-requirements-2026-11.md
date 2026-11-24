# 프로젝트 지식·결정 공유 시스템 — requirements

- 문서 목적: concept의 권고안과 소유자 결정(D1~D3)을 검증 가능한 요구로 옮겨 DB·API·MCP·UI 설계 입력을 제공한다 (TASK-2026-11-24-main-002, M-059/WBS-59.1).
- 범위: source/authority, catalog·search, provenance·revision, DCR/ADR lifecycle, authorization, export, session integration, parity/operations.
- 대상 독자: owner, design/implementation 담당자
- 상태: D1~D3 확정 (2026-11-24), 구현 요구 — M-059/WBS-59.3~59.4
- 최종 수정일: 2026-11-24
- 관련 문서: [`project-knowledge-decisions-concept-2026-11.md`](./project-knowledge-decisions-concept-2026-11.md), [`hub_knowledge_decisions_spec.md`](../../workflow-source/core/hub_knowledge_decisions_spec.md), [`ADR-036`](../../ai-workflow/wiki/decisions/adr-036-project-knowledge-decisions.md)

## 1. 기능 요구

### R1 — source 등록과 authority

- **R1.1** 프로젝트 source는 고유 ID, 표시명, `kind`, `authority`, remote identity, include path allowlist, indexed revision을 가진다.
- **R1.2** source authority는 `git` 또는 `hub` 중 하나이며 신규 source에는 명시적으로 설정한다. 프로젝트 밖에서 읽을 수 있는 visibility 설정은 기본 비공개다.
- **R1.3** Git source sync는 등록 remote key와 allowlist 안의 일반 파일만 읽는다. `.git`, symbolic link escape, 상한 초과 파일, 거부 경로는 index하지 않고 이유를 보고한다.
- **R1.4** Git snapshot에는 commit SHA, canonical path, content SHA-256, last indexed time을 기록한다. 같은 source SHA에서 반복 sync는 결과를 멱등하게 유지한다.
- **R1.5** Git source가 움직였거나 파일이 삭제되면 현재 projection을 갱신하되 이전 revision을 보존한다. 자동 반영 실패나 partial sync는 성공처럼 표시하지 않는다.
- **R1.6** 기존 `wiki_page`와 `memory_entry` 데이터는 migration 뒤에도 유지된다. source/import history는 버리지 않는다.

### R2 — catalog와 검색

- **R2.1** 검색은 Wiki, 설계 문서, requirements/spec, ADR, DCR, Memory Index를 종류·상태·source·경로·task link로 필터한다.
- **R2.2** 검색 결과는 프로젝트 범위로 제한되며 provenance, canonical ref, revision/SHA, authority, lifecycle status, updated time, excerpt를 담는다.
- **R2.3** `get`은 현재판 또는 명시된 immutable revision을 반환한다. 현재판이 바뀌면 호출자는 stale 여부를 판단할 수 있다.
- **R2.4** superseded ADR, pending DCR, stale projection을 숨기지 않고 현재 상태와 relation을 분명히 표시한다.
- **R2.5** 같은 source document를 Hub Wiki import와 Git projection에서 동시에 가져도 두 결과를 출처를 제거해 하나로 합치지 않는다. 중복 group은 보조 정보다.
- **R2.6** session/task relation이 있는 knowledge만 session start briefing에 선택적으로 노출한다. 원문 전체를 자동 주입하지 않는다.

### R3 — DCR/ADR

- **R3.1** DCR에는 ID, 제목, 요약, 변경 사유, 대상 문서/ADR 및 기준 revision, 제안 내용, 영향 문서, 대안, 검증 계획, author, 상태가 필요하다.
- **R3.2** DCR 생성/수정은 프로젝트 writer 권한을 따른다. 수락·거절·철회 권한과 규칙은 별도 명시하며 승인된 `human`만 결정을 내린다.
- **R3.3** 결정에는 reviewer, timestamp, outcome, rationale, decision payload, request id를 기록하고 append-only event를 남긴다.
- **R3.4** 기준 ADR/source revision이 바뀐 DCR은 자동 수락하지 않고 `stale` 또는 409 conflict로 되돌린다.
- **R3.5** DCR 수락은 accepted decision record/ADR과 양방향 relation을 갖는다. 기존 ADR을 지우거나 결정 이력을 잃어서는 안 된다.
- **R3.6** Git authority ADR에 대한 결과는 source SHA 검증이 가능한 export instruction으로 제공한다. Hub 서버는 Git 원격에 쓰지 않는다.
- **R3.7** 동일 `request_id` 재시도는 중복 DCR이나 결정을 만들지 않는다.

### R4 — 보안·무결성

- **R4.1** 콜사인 토큰은 본인 프로젝트 범위만 읽고 쓴다. hub-wide 검색은 별도 합의 및 명시적 접근 모델 없이는 제공하지 않는다.
- **R4.2** web token은 기본 읽기/등록 역할을 유지하며 DCR 승인, ADR 결정, source 등록 권한을 갖지 않는다.
- **R4.3** human 승인 요건은 승인된 human callsign으로 확인한다. payload의 author/reviewer 문자열을 권한 증거로 삼지 않는다.
- **R4.4** content snapshot의 secrets 검사, 크기 제한, safe path/remote 검증은 기존 허브 입력 규칙을 따른다.
- **R4.5** DB write와 event는 하나의 transaction이다. expected version과 idempotency를 사용해 lost update와 중복 요청을 막는다.

### R5 — 인터페이스와 운영

- **R5.1** Python·Go hub는 같은 tool/API names, arguments, response keys, status transitions, error/status codes, DB migration 결과를 제공한다.
- **R5.2** MCP와 HTTP UI는 공통 service function 및 authorization decision을 공유한다.
- **R5.3** source sync 상태(성공, stale, partial, rejected, last SHA)를 운영자가 조회할 수 있다.
- **R5.4** 문서 import/export는 기존 파일 내용을 자동 덮어쓰지 않고 version/hash check가 붙은 write instruction을 제공한다.
- **R5.5** 운영 문서에 source 추가, sync, DCR review/decision, ADR export, backup/recovery 절차를 설명한다.
- **R5.6** 프로젝트 pilot은 docs, wiki, design/spec, ADR 조회와 DCR create/review/decision flow를 실제 hub MCP로 확인한다.

## 2. 결정 추적

| 요구 | Concept / 결정 | 검증 근거 |
|---|---|---|
| R1 | §3.1, D1 | source allowlist·SHA·authority roundtrip 및 sync/stale 사례 |
| R2 | §3.2, D1·D3 | source 종류·상태 필터, revision 조회, project boundary |
| R3 | §3.3, D2 | lifecycle table, 권한 조합, stale conflict, idempotency, relation audit |
| R4 | §3.1~3.3, D3 | cross-project access denied, web token cannot decide, secret/path probes |
| R5 | §3.4, §4 | Python/Go response diff, UI/MCP parity, backup restore/pilot transcript |

## 3. design 진입 조건

1. D1~D3 owner response를 task decision state에 기록한다.
2. ADR-036을 Proposed에서 Accepted로 바꾸기 전에 concept과 requirement가 상호 일치해야 한다.
3. authority·visibility·DCR decision permission을 database/API 설계 전에 확정한다.
4. 구현 순서는 source/catalog read path → DCR write/decision path → UI/export → parity/pilot이다.
