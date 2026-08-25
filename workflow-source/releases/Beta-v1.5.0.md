# Beta v1.5.0 (2026-08-25)

> **상태: 릴리스 준비.** package `1.5.0`, runtime `__version__ = 1.5.0`, tag `v1.5.0`.
> **minor release** — 60차 세션 한 사이클. 새 층 하나가 통째로 들어왔다:
> **ADR-027 로드맵·마일스톤·WBS 층 + SDLC 온보딩 기본 흐름**.
>
> `feat(roadmap)!` 이 있지만 **major 가 아니다.** `docs/RELEASE.md` §1.5 4문항:
> ①공개 Python API 시그니처 변경 **0** — 은퇴한 `common.milestones` 는 동결
> 표면(v0.8.0 stable freeze) 밖의 데모 휴리스틱이다. ②진입점 제거 **0** —
> MCP `assess_milestone_progress` 스크립트는 남아 있고, **옛 인자
> (`--matrix-path`/`--backlog-path`)도 계속 받아 rc=0** 으로 왜 무시되는지
> 말한다 (v1.3.0 선례 그대로). ③소비자가 잃는 것 **0** — 출력의 기존 key
> (milestone_id/progress_percentage/done_count/total_count/suggestion) 유지,
> roadmap 없는 프로젝트는 **모든 동작이 그대로다** (additive). ④외부 spec 무관.
> 그 `!` 가 가리키는 것은 "진척의 SSOT 가 roadmap 층으로 바뀌었다" 는 의미
> 전환이지 우리 공개 API 가 아니다.

## 0. 릴리스 판정

이 사이클의 주제는 **"계층이 비어 있으면 판단이 매번 사람에게 돌아온다"** 다.
PURPOSE(왜)와 backlog task(오늘) 사이에 '무엇을 어떤 순서로' 를 말하는 자리가
없어서, 다음 작업 축 선정이 매번 소유자 판단 대기로 남았다 — 그 자리를
로드맵 층이 채운다. 그리고 이 기능의 구현 자체가 그 로드맵의 첫 사용자였다
(M-001~M-006 자기 적용).

- **진척은 손으로 적지 않는다.** WBS leaf ← task 상태 파생, 분모는 선언한
  leaf 수 — 링크를 지울수록 진척이 오르는 왜곡을 막는다. done 은 WBS 완료 +
  deliverable 실재 **둘 다**다.
- **우회는 침묵이 아니라 선언이다.** 게이트 예외는 `--wbs exempt` + 사유가
  frontmatter 에 남아 생성물이 센다. 순서 게이트의 병행 허용도 코드가 아니라
  로드맵의 `parallel_allowed` **선언**이 결정한다.
- **추정을 확정으로 적지 않는다.** 기존 프로젝트 온보딩 초안은 전부 planned +
  draft 이고, **draft 는 게이트를 발동시키지 않는다** — 소유자가 확정하면 그
  자리에서 선다.
- **위양성을 내는 검사는 무시당한다.** 씨앗 직후의 "in_progress 선언 + task 0"
  이 불일치로 보고되던 것을 done 경계 판정으로 좁혔다.

## 1. 릴리스 요약

- 범위: `v1.4.0..HEAD` (17 commit — feat 3 · fix 6 · chore 6 · docs 1 · release 1)
- 검사 **268 → 274**, 전량 2축 274/274 PASS, mypy strict 0 errors (201 files),
  SDK 매트릭스 3버전(1.27.0/1.29.0/2.0.0) PASS
- ADR-027 로드맵 층 신설(M-001~M-005) · overlay 위임 선언 신설 ·
  session-start 자기 복구(v1.4.0 발행 직후 커밋) 포함

## 2. deliverable

### 2.1 로드맵·마일스톤·WBS 층 (ADR-027, M-001~M-002)

`ai-workflow/memory/active/roadmap/` 디렉터리가 SSOT(index + 마일스톤별 파일 +
WBS 트리), `roadmap_state.json` 이 기계 정본(생성물 — 손편집은
`check_roadmap_state_generated` 가 잡는다)이다. 마일스톤은 SDLC 6단계 어휘
(concept/requirements/design/implementation/stabilization/release)를 선언하고,
task 는 frontmatter `wbs: M-NNN/WBS-N.N` 으로 leaf 에 연결된다.

### 2.2 배선 (M-003)

- `wk refresh-state` 가 roadmap_state 를 **같은 호출**에서 재생성하고 `--check`
  는 roadmap drift 를 함께 판정한다 (별도 명령 없음).
- session-start 출력에 `roadmap_context` — 현재 마일스톤·SDLC 단계·다음 WBS
  후보·문서 단계 산출물 권고. roadmap 부재는 `present=false` 로 말한다.
- 데모 휴리스틱 `common/milestones.py` 는 **함수까지 은퇴** — MCP
  `assess_milestone_progress` 는 roadmap 층을 읽는다 (§1.5 판정은 상단).

### 2.3 task 생성 게이트 (M-004)

`evaluate_wbs_gate` **단일 판정 함수** — CLI(backlog-update)와 MCP
(create_backlog_entry)가 같은 함수를 거친다. 거부 7코드(wbs 미지정 · 사유 없는
exempt · 형식 위반 · dangling · 비-leaf · done 역행 · SDLC 순서) / 허용 4코드
(linked · exempt_declared · not_applicable · draft_roadmap). roadmap 없는
프로젝트는 기존 그대로다.

### 2.4 온보딩 SDLC 기본 (M-005)

bootstrap 이 SDLC 씨앗을 심는다 — 신규는 **concept 부터**(M-001 in_progress),
기존은 전부 planned + draft. 씨앗이 자기 파서·게이트를 첫날부터 통과하는지
`check_roadmap_bootstrap_seed` 가 고정한다. 재실행은 사용자 로드맵을 덮지
않는다 (`memory/active` 보존 경로).

### 2.5 overlay 위임 선언 (main-010)

진입 파일의 `standard-ai-workflow-kit-overlay: plugin-only` 선언이 있으면
overlay 파일 부재는 missing 이 아니라 **plugin_delegated** 다 — 자동 복구가
되살리지 않는다. 이 저장소가 첫 적용(프로젝트 overlay 5종 제거, 플러그인 단일
채널). 추측("플러그인이 있으니 로컬은 불필요")은 CI 처럼 플러그인 없는
호스트에서 틀린다 — 파일이 스스로 말하게 했다.

## 3. smoke 회귀

누적 smoke test **274/274 PASS** ×2축 (2026-08-25, `dev,release,mcp-sdk` extra 를
깐 격리 venv, `--tmp-dir` 실디스크). 이 줄은 릴리스 시점 스냅샷이 아니라 *최신
전량 결과* 를 반영하는 살아있는 지표다.

## 4. 1차 출처 (cross-ref)

- [ADR-027](../../ai-workflow/wiki/decisions/adr-027-roadmap-wbs-sdlc.md) (결정 기록)
- [로드맵·마일스톤·WBS 스펙](../core/roadmap_milestone_wbs_spec.md) (정본 계약)
- [릴리스 등급 판단 기준](../../docs/RELEASE.md) §1.5
- [설치·사용 가이드](../../docs/INSTALLATION_AND_USAGE.md)

## 5. 후속

- **mypy flake** ([TASK-2026-08-13-main-004]) — 격리(`19e40ac9`, 본 릴리스에
  포함) 이후 6 run 연속 green. close 기준은 33 run 연속(95% 신뢰) — 일상
  push 가 표본이다.
- **로드맵 상시 운용** — 이 저장소의 exempt 비율 관찰 시작 (스펙 §11). 비율이
  높게 유지되면 '운영 축' 상설 마일스톤 여부를 소유자에게 묻는다.
- **maturity_matrix.json 의 milestones 키** — 이 저장소 자신의 phase 추적
  레거시. roadmap 층으로의 이행은 별도 사이클 (ADR-027 §Consequences).
- **cross-host federation** — 두 번째 호스트(MacBook) 확보 시점.

## Self-recovery log

_자동 emit (Phase 13 AC3, 2026-08-25T02:02:43Z)_

### 자동 fix (1건)

- `test_case_4_readme_header_version_sync` → `_fix_readme_header_version`
  - new value: `1.5.0`
  - file: `README.md`

_re-check status: **pass** (pass=7/fail=0/total=6)_

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-08-25T02:02:43Z)_

- total wiki pages: **95**
- total memory entries: **15**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
