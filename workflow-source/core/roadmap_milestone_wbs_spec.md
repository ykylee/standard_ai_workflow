# Roadmap · Milestone · WBS 진척 관리 스펙

- 문서 목적: 워크플로우에 로드맵 수립 → 마일스톤 → WBS 기반 작업 진척 관리 흐름과, 온보딩 단계의 SDLC 기본 순서(컨셉 → 요구사항 → 설계 → 구현)를 정본 계약으로 정의한다.
- 범위: 문서 계층과 배치, roadmap SSOT 형식, SDLC 단계 어휘, task 연결 계약, 게이트 계약, 생성물(roadmap_state.json), skill/CLI 배선, 검사 계약, 단계별 구현 계획
- 대상 독자: workflow 설계자, 구현자, AI agent (session-start / backlog-update), 프로젝트 온보딩 담당자
- 상태: draft (ADR-027 accepted, 구현 전 — §10 의 M-002 부터가 구현이다)
- 최종 수정일: 2026-08-28
- 관련 문서: `../../ai-workflow/wiki/decisions/adr-027-roadmap-wbs-sdlc.md`, `./llm_wiki_concept_purpose_spec.md`, `./workflow_adoption_entrypoints.md`, `./existing_project_onboarding_contract.md`, `./global_workflow_standard.md`

> **결정 근거는 ADR-027 에 있다** (2026-08-25 소유자 결정 3건: 문서 형태 =
> 디렉터리 SSOT + 스키마 JSON 생성물 혼합 · 강제 = 게이트 · 산출물 순서 =
> ADR/스펙 확정 후 단계 구현). 이 문서는 *계약* 만 적는다.

## 1. 문제와 목표

`PURPOSE.md`(왜)와 backlog task(오늘 무엇을) 사이에 **무엇을 어떤 순서로,
어디까지 왔는가** 를 말하는 층이 없다. 그 결과:

- 다음 작업 축 선정이 매번 소유자 판단 대기로 남는다 (구조가 후보를 못 낸다).
- 진척이 task 개수로만 보이고 산출물 단위로 안 보인다.
- 온보딩이 문서 세트만 깔고 **일하는 순서**를 말하지 않아, 컨셉 정리 전에
  구현 task 가 쌓이는 것을 막을 장치가 없다.

목표: 로드맵 층을 신설하되 **기존 SSOT(backlog task)를 대체하지 않고 위에
얹는다.** 진척은 손으로 적지 않고 task 상태에서 파생한다. 로드맵이 없는
프로젝트는 아무것도 달라지지 않는다 (additive).

## 2. 문서 계층과 배치

```
ai-workflow/memory/active/PURPOSE.md            왜 (4-element)          — 기존
ai-workflow/memory/active/roadmap/              무엇을 어떤 순서로       — 신설 SSOT
├── index.md                                    로드맵 개요 + 마일스톤 목록
├── M-001-<slug>.md                             마일스톤 파일 (1 파일 = 1 마일스톤)
├── M-002-<slug>.md
└── roadmap_state.json                          기계 정본 (생성물 — 손편집 금지)
ai-workflow/memory/active/<branch>/backlog/tasks/TASK-*.md   오늘 (기존 SSOT + wbs 링크)
```

- `roadmap/` 는 **브랜치 무관 공유 위치**다 (`PURPOSE.md` 와 동급). 로드맵은
  프로젝트 전체의 것이지 브랜치의 것이 아니다 — 브랜치별로 두면 slash 브랜치
  컨텍스트에서 존재하지 않는 경로 문제(15연속 red 의 뿌리)를 재생산한다.
- `roadmap_state.json` 은 `state.json` 과 같은 계약이다: **생성물이며 손으로
  고치지 않는다.** SSOT 는 마일스톤 파일 + task frontmatter 이고, 재생성은
  `wk refresh-state` 가 함께 수행한다 (§7).

## 3. Roadmap SSOT 형식

### 3.1 index.md

사람이 읽는 개요 + 마일스톤 순서 선언. task daily index 와 같은 역할이다.

```markdown
# Roadmap — <프로젝트 이름>

- (표준 메타데이터 블록)

## Milestones

- **M-001** [concept] 컨셉 정리 — status: done
  - path: [`./M-001-concept.md`](./M-001-concept.md)
- **M-002** [requirements] 요구사항 정리 — status: in_progress
  - path: [`./M-002-requirements.md`](./M-002-requirements.md)
```

목록의 **순서가 곧 SDLC 순서 선언**이다 (§6 게이트가 이 순서를 읽는다).
status 는 파생 값의 사본이 아니라 선언이다 — 파생 롤업과 어긋나면 검사가
지목한다 (§8, "산문이 SSOT 를 복제하면 갈라진다" 를 검사로 막는다).

### 3.2 마일스톤 파일 (M-NNN-<slug>.md)

```markdown
---
id: M-002
title: 요구사항 정리
sdlc_phase: requirements        # §4 어휘
status: in_progress             # planned / in_progress / blocked / done
order: 2                        # index.md 순서와 일치 (검사 대조)
parallel_allowed: []            # 함께 열려도 되는 마일스톤 id 목록 (§6 게이트 우회는 여기 선언)
deliverables:                   # 수용 기준 — 산출물 경로 (완료 판정의 근거)
  - docs/REQUIREMENTS.md
---

# M-002 — 요구사항 정리

(목표·수용 기준 산문)

## WBS

- **WBS-2.1** 이해관계자 요구 수집 — 산출물: docs/REQUIREMENTS.md §1
- **WBS-2.2** 기능 요구 정리 — 산출물: docs/REQUIREMENTS.md §2
  - **WBS-2.2.1** 우선순위 매김
- **WBS-2.3** 비기능 요구 정리 — 산출물: docs/REQUIREMENTS.md §3
```

- WBS id 는 `WBS-<마일스톤번호>.<n>(.<n>)*`. **leaf 노드만 task 와 연결**된다.
- WBS 노드에는 status 를 **적지 않는다** — leaf 의 상태는 연결된 task 들에서
  파생하고, 중간 노드는 자식에서 롤업한다 (§7.2). 손으로 적는 순간 두 정본이
  생긴다.

## 4. SDLC 단계 어휘

`sdlc_phase` 는 다음 6개 중 하나다 (전수 버킷 — 어휘 밖은 검사 red,
어휘 안은 반드시 어딘가에 담긴다):

| phase | 기본 산출물 (bootstrap 씨앗의 deliverables) |
|---|---|
| `concept` | `PURPOSE.md` 4-element 완성 (placeholder 소거) + 컨셉 노트 |
| `requirements` | 요구사항 문서 (`docs/REQUIREMENTS.md` 기본) |
| `design` | 설계 문서 / ADR (`docs/architecture/` 또는 wiki decisions) |
| `implementation` | 동작하는 산출물 + 검증 결과 |
| `stabilization` | 검사/게이트 green + 알려진 결함 목록 |
| `release` | 릴리스 노트 + 배포 산출물 |

- 같은 phase 의 마일스톤을 여러 번 선언해도 된다 (iterative 프로젝트는
  design→implementation 을 반복 선언한다 — waterfall 강제는 어휘가 아니라
  **선언한 순서**가 한다).
- **온보딩 기본**: 신규 프로젝트는 `concept → requirements → design →
  implementation` 4개 씨앗으로 시작하고 M-001(concept) 이 `in_progress` 다.
  컨셉부터 정리하는 것이 기본 흐름이라는 소유자 결정이 이 씨앗에 실린다.

## 5. Task 연결 계약

task frontmatter 에 optional key 하나를 더한다 (additive — 기존 파서는
모르는 키를 무시한다):

```yaml
wbs: M-002/WBS-2.2        # 마일스톤 id / WBS leaf id
# 또는, 게이트 예외를 선언할 때:
wbs: exempt
wbs_exempt_reason: 로드맵 밖 긴급 수리 — CI red
```

- `wk backlog-update` 에 `--wbs <id>` / `--wbs exempt --wbs-exempt-reason <사유>`
  를 추가한다.
- 링크는 **task → WBS 단방향**이다. WBS 쪽에 task 목록을 적지 않는다
  (양쪽에 적으면 갈라진다). 역방향은 생성물(§7)이 계산한다.

## 6. 게이트 계약 (소유자 결정: 게이트까지)

로드맵(`roadmap/index.md`)이 **존재하는** 프로젝트에서만 성립한다. 없으면
아래 전부 해당 없음 — 기존 동작 그대로다.

**draft 는 게이트를 발동시키지 않는다** (M-005 에서 확정): 기존 프로젝트
온보딩 초안(index.md 메타데이터 `- 상태: draft`)은 소유자가 확정하기 전의
추정이다 — 추정이 강제를 발동시키면 draft 가 draft 가 아니다. 소유자가
상태를 active 로 바꾸고 현재 마일스톤을 선언하는 것이 확정이고, 그때부터
아래 게이트가 선다.

1. **WBS 링크 게이트**: `--mode create` 는 `--wbs` 없이 **실패한다**
   (경고가 아니라 거부). 우회는 침묵이 아니라 선언이다 — `--wbs exempt` 는
   사유가 필수이고 frontmatter 에 남으며, 검사가 exempt 수를 센다 (§8).
2. **SDLC 순서 게이트**: index.md 순서상 앞선 마일스톤이 `done` 이 아니면
   뒤 마일스톤의 WBS 로 task 를 **열 수 없다.** 병행이 필요하면 마일스톤
   파일의 `parallel_allowed` 에 선언한다 — **게이트를 코드가 아니라 로드맵
   선언이 결정한다** (코드 예외 분기를 늘리지 않는다).
3. **done 역행 게이트**: `done` 마일스톤의 WBS 에 새 task 를 열면 거부한다.
   그 일이 생겼다는 것은 마일스톤이 done 이 아니었다는 뜻이다 — 마일스톤
   status 를 먼저 되돌리고(선언 수정) task 를 연다.

게이트 판정은 **한 곳**에 둔다 (57차 main-006 규칙: 판정이 복제된 곳에 새
분류를 넣지 않는다). backlog-update 의 생성 경로가 유일한 진입점이므로 그
안의 단일 함수로 강제하고, MCP `create_backlog_entry` 도 같은 함수를 부른다.

## 7. 생성물: roadmap_state.json

### 7.1 계약

- Pydantic 스키마 (`workflow_kit/common/schemas/roadmap.py`, M-002 에서 신설)
  가 정본이다. `maturity_matrix.json` 의 `milestones` 키는 이 스키마로
  이행한다 (데모 휴리스틱 `milestones.py` 은퇴 — §9).
- 재생성: `wk refresh-state` 가 state.json 과 **함께** 재생성한다. 별도
  명령을 만들지 않는다 (진입점이 둘로 갈리면 `--help` 도 갈린다).
- 내용: 마일스톤별 { 선언 status, 파생 progress, WBS 트리(leaf←task 파생
  상태 + 연결 task id 역방향 목록), 선언-파생 불일치 목록, exempt task 목록 }.

### 7.2 진척 파생 규칙

- leaf 진척: 연결 task 전부 `done` → `done` / 하나라도 `in_progress` 또는
  `blocked` → 그 상태 / 연결 0건 → `planned`.
- 중간 노드·마일스톤: 자식 leaf 의 done 비율. **분모는 선언한 leaf 수다**
  (50차 규칙 — 연결된 task 수를 분모로 잡으면 링크를 지울수록 진척이 오른다).
- 마일스톤 완료 판정은 **두 개가 다 필요하다**: WBS 전부 done (파생) +
  `deliverables` 경로 실재. 진척 100% 여도 산출물 파일이 없으면 done 선언은
  불일치로 보고된다 (rc=0 은 무해의 증거가 아니다).
- 선언-파생 불일치는 **done 경계에서만** 보고한다 — "끝났는가" 가 갈릴 때가
  드리프트다. `in_progress` 선언 + 링크 0(파생 `planned`)은 "열었는데 아직
  task 가 없다" 는 정상 시작 상태이고, 씨앗(§9) 직후의 모든 프로젝트가 그
  모양이다 — 위양성을 내는 검사는 무시당한다.

## 8. 검사 계약 (M-002 에서 구현)

- `check_roadmap_format`: frontmatter 어휘 전수(sdlc_phase 6개·status 4개가
  각각 어딘가에 담긴다), index 순서 ↔ `order` 일치, WBS id 형식·중복.
- `check_roadmap_integrity`: task `wbs:` 가 실재 leaf 를 가리킴(dangling 0),
  done 마일스톤 아래 in_progress task 0, 선언 status ↔ 파생 롤업 불일치 보고,
  exempt 수·사유 실재.
- `check_roadmap_state_generated`: roadmap_state.json 이 손편집이 아니라
  생성물임을 대조 (check_state_json_generated 와 같은 방식).
- bootstrap 씨앗은 **자기 파서를 통과해야 한다** (56차 규칙 — 씨앗이 읽히는지
  확인하지 않으면 소비자는 첫날부터 파싱 안 되는 상태를 받는다): 씨앗 생성 →
  파싱 → 게이트 판정까지 한 case 로 고정한다.
- 되주입 red 실증은 각 게이트마다 1건 이상 (도달 불가능한 분기는 검사되지
  않은 분기다).

## 9. 배선 (skill / CLI / bootstrap)

| 지점 | 변경 |
|---|---|
| `session-start` | 현재 in_progress 마일스톤·sdlc_phase·다음 WBS 후보를 보고. concept/requirements/design 단계면 그 단계 deliverable 의 placeholder 잔존 여부를 재고 "다음 행동" 으로 권고. roadmap 부재 시 silent skip (기존 graceful 원칙) |
| `backlog-update` | §6 게이트 + `--wbs` 인자. scope creep 경고(PURPOSE 기반)는 그대로 유지 — 게이트와 별개 축 |
| `session-end` / `wk refresh-state` | roadmap_state.json 재생성 (§7) |
| bootstrap `--adoption-mode new` | roadmap/ 씨앗 (SDLC 4 마일스톤, M-001 concept = in_progress) |
| 기존 프로젝트 온보딩 | `repository_assessment` 기반으로 현재 단계 추정 초안 생성 — 추정을 확정으로 적지 않고 draft 표기 (모르는 정체를 지어내지 않는다) |
| MCP `assess_milestone_progress` | 새 정본 모듈을 부르도록 교체. 데모 휴리스틱 `milestones.py` 는 **함수까지 은퇴** (49차 규칙 — CLI 분기로만 막으면 다음 사람이 다시 부른다) |

하네스 채널(claude-code / codex / …) 스킬 문안 갱신은 기존 정본 파생 체계
(`check_standard_single_source`)를 그대로 탄다.

## 10. 단계별 구현 계획 — 이 계획이 이 저장소의 첫 roadmap 이 된다

M-002 완료 시점에 아래 표를 `ai-workflow/memory/active/roadmap/` 로 옮겨
심는다 (자기 적용 — 파서가 생기기 전에는 심을 수 없으므로 이 표가 임시 정본).

| id | phase | 내용 | 게이트 |
|---|---|---|---|
| M-001 | design | ADR-027 + 본 스펙 (이번 세션) | 문서 검사 green |
| M-002 | implementation | 스키마 + 파서 + roadmap_state 생성기 + 검사 3종 + 자기 적용 씨앗 | 전량 2축 green, 되주입 red 실증 |
| M-003 | implementation | `wk refresh-state` 통합 + session-start 배선 + milestones.py 은퇴 | 〃 |
| M-004 | implementation | backlog-update 게이트 + exempt 선언 + MCP 경로 동일 함수 | breaking 등급은 `RELEASE.md` §1.5 로 판정 |
| M-005 | implementation | bootstrap 씨앗 + 기존 프로젝트 온보딩 초안 + 채널 문안 | 씨앗이 자기 파서 통과 case |
| M-006 | release | 릴리스 + 소비 채널 재적용 + 이 저장소 roadmap 상시 운용 전환 | `wk doctor` drift 0 |

## 11. 미결 / 리스크

- **게이트와 기존 코퍼스**: 이 저장소가 roadmap 을 심는 순간(M-002) 게이트가
  성립한다. 로드맵 밖 일상 수리(flake 관찰, doctor 대응)는 exempt 선언이
  잦아질 수 있다 — exempt 비율을 생성물이 세므로, 비율이 높게 유지되면
  "운영 축" 마일스톤을 상설로 둘지 소유자에게 묻는다 (그때 결정, 지금 채번 ❌).
- **선언 status 와 파생의 이중성**: index.md 의 status 는 선언이고 파생과
  어긋날 수 있다. 검사가 불일치를 보고하되 자동 수정하지 않는다 — 갱신이
  상태를 나쁘게 만드는 조언(54차)을 재생산하지 않기 위해 사람이 닫는다.
- **task ↔ WBS 다대일의 한계**: task 하나가 여러 WBS 에 걸치는 경우는 지원하지
  않는다 (frontmatter 단일 키). 걸치면 task 를 쪼개는 것이 기본 처방이다.
