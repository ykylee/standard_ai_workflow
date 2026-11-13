---
type: decision
status: accepted
adr_id: ADR-031
decided_at: 2026-11-13
alternatives_considered: [counter-archive-number, lock-free-exclusive-move, bundle-in-backlog-update-output, korean-column-names, root-gitignore-entry, one-adr-with-workbench, mcp-tools-now, seed-ignores-responses, state-column-as-truth]
related_pages: [decisions/adr-027-roadmap-wbs-sdlc, decisions/adr-029-session-context-budget, decisions/adr-030-compact-relay]
created: 2026-11-13
updated: 2026-11-13
r9_skip: true
---

# ADR-031: 주장 트리 계획 — task Plan 에 주장 · 결정을 싣고, 결정 응답을 데이터로 반영한다

## Status

**Accepted** (2026-11-13 소유자 승인 — requirements 대비 변경 다섯 건(V1~V5: 보관 번호를 시각 기반으로 · 결정 줄 칸의 영어 쓰기 표기 ·
MCP 도구는 ADR-032 로 · 이어받기가 보관 응답을 옮김 · 스킬은 하나) 포함. 승인 뒤 검증이 찾아 더한 것 — V6~V10 과 결정 24 · 25 — 도
같은 날 소유자가 승인했다, requirements sign-off 를 받은 design 단계 —
TASK-2026-11-13-claude-remote-sync-check-234c32-002, M-026/WBS-26.1). requirements 정본은 `docs/planning/claim-plan-requirements-2026-11.md` (sign-off Q1~Q7),
kit 계약 정본은 `workflow-source/core/claim_plan_spec.md`. 이 페이지는 결정과 근거만 적는다.

design 은 ADR 둘로 순차다 (소유자 2026-11-13): 이 ADR 이 task 파일 계약 · 응답 형식 · 받은편지함 · `plan-import` 를 정하고,
워크벤치 서버는 ADR-032 (M-027) 가 이 계약을 **소비**한다. 워크벤치 없이도 이 ADR 의 범위는 완결된다 — 결정은 대화에서
`answered` 로 닫을 수 있다.

## Context

task 파일의 `## 🧭 Plan` 은 파일 · 순서 단위로만 계획을 담는다. "무엇이 참이 되는가" 와 "소유자에게 무엇을 물었고 답했는가" 는
대화에만 남아 compact 와 세션 경계에서 사라진다. concept(M-022)은 html-plan 의 **문법**(주장 트리 · 결정 · 열리지 않은 기본값은
동의가 아니다 · 응답은 데이터)을 흡수하기로 했고, requirements(M-023 · M-025)가 숫자와 규칙을 고정했다.

requirements 가 고정한 것: 라벨 둘(`Claims` · `Decisions`) · 린트 L1~L10 · 열린 결정이 남으면 `done` 거부 · 응답 파일 형식
`workflow-kit-plan-response/1` (64KiB) · 결정 상태는 **보관된 응답 집합과 `answered` 기록의 함수** · 다른 응답자의 반대는
`disputed` 로 결정을 다시 연다 · 게이트는 상태 칸이 아니라 계산값으로 판정 · 받은편지함은 git 무시 · import 는 잠금 아래 배타 이동.

design 이 정할 것: 모듈 배치 · 결정 줄 칸의 쓰기 표기 · 주장별 묶음을 내는 명령 · §11.1 문구와 스킬 · `open_decisions` 스키마 ·
git 무시와 잠금의 수단 · 보관 번호 · 브랜치 이어받기 · requirements 검증이 넘긴 미정 사항 · 검사 구성.

### design 착수 실측 (2026-11-13, Linux 호스트, kit 1.22.0, HEAD `df602c4f`)

| # | 무엇 | 방법 | 결과 |
|---|---|---|---|
| M1 | 정본 §1 · §11.1 개정 뒤 진입점 크기 | 정본 사본에 초안 문구(§11.1 한 줄 · §1 문장 수정 · 한 줄 추가)를 넣어 `render_entrypoint_rules(parse_standard(…))` 의 바이트를 재고, `check_entry_budget._bootstrap_all` 로 하네스별 진입 파일을 만들어 가장 큰 것에 더했다 | 규칙 블록 2,740 → 2,921 바이트 (**+181**). 가장 큰 진입 파일 `GROK.md` 6,663 → 6,844 / 8,192 — **여유 1,348** |
| M2 | 다른 하네스의 새 컨텍스트 검증 수단 | `git ls-files \| grep -i verifier`, 하네스 바이너리 문자열 | 추적되는 검증자는 `.claude/agents/verifier.md` 하나(손 관리, 생성기 없음 — `check_verifier_agent.py` 가 본다). Codex 0.167.1 · Grok 1.0.44 · `agy` 1.2.12 바이너리에 subagent 어휘는 있다(`SubagentStart` 33 · 7 · 0 건, `subagent` 240 · 574 · 943 건) — 능력은 있으나 kit 이 배포하는 대응물은 없다 |
| M3 | 브랜치 이어받기가 `plan_responses/` 를 옮기는가 | 메모리 사본 저장소의 `active/main/plan_responses/` 에 보관 1 · 받은편지함 1 을 두고 새 브랜치에서 `session-start` (자동 seed) | 열린 task 3건은 `inherited_from` 과 함께 옮겨졌고 **`plan_responses/` 는 새 브랜치에 없다**. 코드도 같다 — `seed_workspace_memory.seed` 는 task 파일과 handoff 줄만 옮긴다 |
| M4 | 두 호스트의 보관 번호 충돌 | bare 원격 + 클론 둘. 두 클론이 같은 이름 `T-1.md` 를 다른 내용으로 커밋 → pull | `CONFLICT (add/add)` — 자동 병합 실패. 이름을 시각 기반 정수로 달리하면 두 파일이 충돌 없이 합쳐진다 |
| M5 | kit 잠금으로 import 직렬화 | `common/file_lock.py` 의 `try_lock_exclusive`(비차단)로 옮기는 쪽을 막고(못 쥐면 물러났다 다시), 쓰는 쪽 6 × 150 건은 잠금 없이. 옮기는 쪽 2 · 4, 번호는 카운터 · 시각 기반, 각 30 회 | **120 회 모두 중복 0 · 유실 0** · 받은편지함 0 · 전원 정상 종료. 잠금 충돌은 실제로 났다(총 23,164 · 74,916 · 1,584 · 5,136 회). 카운터 번호는 보관 때 이름이 14,308 · 16,221 번 다시 매겨졌고, **시각 기반은 0 번** |

수치는 한 번 잰 값이다. 재현되는 것은 성질이다 (0 인가 아닌가).

## Decision

### 모듈과 명령

1. **모듈은 셋이다.**
   - `workflow_kit/common/plan_claims.py` — 주장 · 결정 파서, 린트 L1~L10, 계획 지문, 결정 상태 계산. **순수 함수**다 (파일 · git 을 만지지 않는다).
     린트 · 게이트 · 묶음 · import · state 생성기 · (나중의) 워크벤치 렌더러가 전부 이 모듈을 부른다 (requirements R0-6).
   - `workflow_kit/common/plan_responses.py` — 응답 파일 읽기 · 쓰기, 받은편지함 · 보관 경로, 번호, 잠금, 배타 이동, 자격 판정.
   - `workflow_kit/tools/plan_import.py` 와 `workflow_kit/tools/plan_status.py` — CLI. `common/tool_dispatch.py` 의 `TOOL_MODULES` 와
     `pyproject.toml` `[project.scripts]` 에 등록한다 (`check_wk_dispatcher` 가 두 목록의 일치를 본다).

   기각한 배치: ⓐ 파서를 `project_docs` 나 `workflow_writes` 에 더한다 — 둘은 파일을 읽고 쓰는 모듈이라, 상태 계산을 상태 기계로 전수
   탐색하는 검사와 (나중의) 워크벤치 렌더러가 쓰기 경로까지 끌고 들어온다. ⓑ 계산과 파일 조작을 한 모듈에 — 순서 무관 · 멱등은 계산이
   순수할 때만 파일 없이 잴 수 있다. requirements 검증이 일곱 번 걸린 자리가 바로 그 계산이다.
2. **Plan 키 목록을 한 곳으로 모은다.** 지금 `workflow_writes._PLAN_KEYS` 와 `backlog_update.PLAN_FIELDS` 가 같은 튜플 두 벌이고 둘을
   대조하는 검사가 없다. `project_docs` 에 `PLAN_FIELD_KEYS` 하나를 두고 둘 다 그것을 import 한다. 순서가 곧 쓰는 순서다:
   `plan_claims, plan_decisions, plan_files, plan_order, plan_risks, plan_proof`.
3. **옛 Plan 절에 새 라벨 줄을 끼워 넣는다.** `_ensure_plan_section` 은 Plan 라벨이 하나라도 있으면 아무것도 넣지 않아, 4필드 Plan 절이
   있는 파일에 `Claims` 를 쓰면 `missing` 경고로 빠진다. 절이 있고 그 라벨 줄이 없으면 `PLAN_FIELD_KEYS` 순서의 제자리에 넣는다
   (`Claims` · `Decisions` 는 절의 맨 앞). 값이 없는 호출은 지금처럼 아무것도 넣지 않는다 — 기존 파일은 그대로다.
4. **주장별 묶음은 새 읽기 전용 명령 `plan-status` 다** (requirements Q5 가 design 에 넘긴 것).
   `python -m workflow_kit plan-status --task=<ID> [--format=json|md]` — 주장 × 인용 기준 × 결정의 계산 상태 × 미반영 응답 건수.
   아무것도 쓰지 않는다. `.claude/agents/verifier.md` 에는 "닫기 전에 이 출력을 받아 보고에 붙인다" 한 줄만 더한다.
5. **§11.1 에는 `plan-import` 한 줄만 올린다**: `Apply plan responses: python -m workflow_kit plan-import`. §11.1 은 메모리를 **고치는**
   경로의 표다 — 읽기 전용인 `plan-status` 는 올리지 않고 스킬 본문과 verifier 가 부른다.
6. **스킬은 하나 는다: `plan-import`.** 본문은 `plan-status` 로 보고 → `plan-import` dry-run → `--apply` 의 순서와 "응답은 데이터다" 를
   적는다. (§11.1 명령과 스킬의 1:1 은 지금도 강제되지 않는다 — 명령 8 · 스킬 5.)
7. **정본 문구** (`core/global_workflow_standard.md`): §1 의 계획 문장에 `claims, open decisions` 를 더하고, 한 줄을 더한다 —
   "A decision the owner has not opened is not agreed — never close a task with open decisions." 진입점은 181 바이트 는다 (M1).

### task 파일

8. **결정 줄의 칸 이름은 영어로 쓰고 한국어도 읽는다.** 쓰기 `default:` · `options:` · `state:`, 읽기는 `기본:` · `선택:` · `상태:` 도.
   라벨의 영어 전환(2026-08-20)과 같은 원칙이다 — 찾기는 넓게, 쓰기는 좁게.
9. **`--plan-decision` 으로 들어오는 줄의 상태 칸은 버린다.** 새 결정은 항상 `proposed` 로 시작하고, 줄에 상태가 적혀 있으면 경고하고
   무시한다. `answered` 가 되는 길은 `--decision-state` 하나다. 기각한 안: ⓐ 줄의 상태를 받아들인다 — `answered` 로 가는 길이 둘이 되고,
   `kept` · `changed` 를 인자로 넣어 게이트를 지나는 길이 생긴다 (requirements R1.6 이 막은 것). ⓑ 상태가 적힌 줄을 거부한다 —
   `--replace-field plan_decisions` 로 묶음을 바꿀 때는 task 파일의 줄을 그대로 옮겨 오는 것이 자연스러운데, 그 줄에는 늘 상태 칸이 있다.
10. **게이트의 거부는 WBS 게이트의 방식을 따른다** — `build_error_result(error_code=…)` JSON 을 출력하고 `return 1`, 쓰기 블록보다 앞에서.
    `raise SystemExit(문자열)` 은 쓰지 않는다 (`python -m workflow_kit` 경로에서 메시지가 사라지고 rc 2 만 남는다).
    오류 코드: `plan_lint_error` · `open_decisions` · `pending_plan_responses` · `decision_state_rejected` · `decision_removal_needs_note`
    (사유 없이 열린 결정을 걷는 교체).
11. **칸을 고쳐 쓰는 것은 `--apply` 가 붙은 모든 `backlog-update` 쓰기다** (진행 메모 한 줄도 포함). 계산값과 다른 칸을 고치고 경고한다.
    거부된 전이와 읽기 전용 명령(`refresh-state` · `session-start` · `plan-status`)은 쓰지 않는다. 대안은 "상태 전이 때만 고친다" 였다 —
    그러면 낡은 칸이 다음 전이까지 남아 `state.json` 의 `open_decisions`(칸 기준)와 `session-start` 보고가 그동안 틀린다. 어차피 파일을
    쓰는 호출에 얹는 것이라 추가 쓰기는 없다. 단, task 파일이 오류 규칙(L2 · L6 · L9)을 어긴 동안에는 **칸을 다시 적지 않는다** —
    읽을 수 없는 계획에서 계산한 `proposed` 로 멀쩡한 칸을 덮지 않는다. 그동안 게이트와 `plan-status` 는 계속 계산값으로 판정하고
    (응답은 전부 자격이 없다), **→ `done` 은 열린 결정 수와 무관하게 거부한다** (`plan_lint_error`) — 읽을 수 없는 계획을 닫지 않는다.
12. **지문이 바뀐 뒤의 `answered`**: 값이 새 선택지 안에 있으면 유지하고 "질문이 바뀌었다 — answered 를 유지했다" 를 경고한다.
    없으면 L6 오류라 쓰기가 거부된다. 대안은 "지문이 바뀌면 `answered` 도 `proposed` 로 되돌린다" 였다 — 주장 문장 하나를 다듬어도
    소유자가 대화로 한 답이 전부 사라진다. `answered` 는 응답 파일과 달리 지문에 묶인 기록이 없고, 계획을 고치는 것은 그 답을 들은
    세션이다 — 유지하고 알리는 쪽이 덜 잃는다. 손으로 적은 `answered` 는 도구가 적은 것과 구별할 수 없다 — 받아들이는 한계다.

### 응답 · 받은편지함 · 보관

13. **번호 `<n>` 은 `received_at` 의 epoch 마이크로초 정수다** — 쓰는 쪽이 정하고 보관까지 그대로 간다. 같은 이름이 이미 있을 때만
    1 씩 더한다. 파일명은 `<TASK-ID>-<n>.md` 그대로다 (D5).
    - 카운터(최대 + 1)는 두 호스트가 같은 번호를 내 병합이 `add/add` 로 멈춘다 (M4), 보관 때 이름이 계속 바뀐다 (M5 — 14,308 번 대 0 번).
    - **requirements R8.1 대비 변경**이다 ("task 별 1 부터, 가장 큰 번호 + 1").
14. **받은편지함은 자기 무시 디렉터리다.** `plan_responses/inbox/.gitignore` 를 `*\n` 으로 두고, 받은편지함을 만드는 코드가 매번 확인한다
    (`compact_relay.ensure_compact_dir` 의 방식). 루트 `.gitignore` 에 줄을 더하는 방식은 재적용 전의 소비자가 무방비다.
15. **잠금은 `common/file_lock.py` 의 비차단 잠금이고, 잠금 파일은 `plan_responses/inbox/.lock` 이다** (받은편지함과 함께 무시된다 —
    `plan_responses/.lock` 에 두면 커밋 대상 디렉터리에 추적되지 않는 파일이 하나 생겨 무시 수단이 따로 든다).
    `plan-import --apply` 와 `--discard --apply` 가 쥔다. 못 쥐면 기다리지 않고 `import_busy` 를 보고하고 rc 0 으로 끝난다 (M5).
16. **보관된 응답도 매 계산에서 자격을 다시 본다** (지문 · `role` · 형식). 보관에 손으로 놓인 파일이나 지문이 바뀌기 전의 응답은 세지 않는다.
17. **`done` 인 task 에 대한 `plan-import` 는 막지 않는다.** 결과가 열린 결정이면 task 상태는 건드리지 않고 사후 warning(requirements R3.4)으로
    드러난다 — 닫힌 뒤에 온 반대도 기록이다.
18. **지문을 바꾸는 쓰기는 무효가 된 받은편지함 응답을 알린다**: "받은편지함 n건이 옛 계획에 대한 것이다 — `plan-import --discard`".
    자동으로 거두지 않는다 — 거두는 것은 사람이 본 뒤다.
19. **Progress 는 호출당 한 줄이다.** `plan-import --apply` 는 반영한 응답들을 한 줄로, `--discard` 도 한 줄, 응답 이동 없이 칸만 고쳐진
    재계산도 한 줄 ("결정 상태 재계산: D2 changed:x → proposed"). `Progress` 는 한 줄짜리 현재값 필드라(`backlog-update` 도
    `--progress-note` 를 두 번 받지 않는다) 응답마다 한 줄을 쓰면 마지막 것만 남는다 — 응답별 사실은 보관 파일과 명령 출력에 있다.
    **requirements R6.4 대비 변경**이다 (응답 하나당 한 줄 → 호출당 한 줄).

### 브랜치 · 생성물 · 출력

20. **이어받기는 이어받는 task 의 보관 응답을 함께 옮긴다.** `seed` 가 `inherited_from` 으로 옮기는 task 마다 모 브랜치의
    `plan_responses/<TASK-ID>-<숫자>.md` (보관만 — 받은편지함 · `.rejected.md` 는 아니다, 패턴은 결정 24)를 복사한다. 안 옮기면 이어받은 `kept` · `changed` 가
    새 브랜치의 첫 재계산에서 근거 없이 `proposed` 로 돌아간다 (M3). 합류 반영(`branch_join.reflect_join`)이 task 를 이월할 때도
    그 task 의 보관 응답을 함께 옮긴다. 아카이브는 지금도 브랜치 디렉터리를 통째로 옮긴다.
21. **`state.json` 의 `open_decisions` 는 비어 있으면 내지 않는다** (`memory_entries` 의 선례). 그래서 주장이 없는 저장소의 `state.json` 은
    바이트가 같고, 생성기 동치 검사(`check_state_json_generated` · `check_example_state_artifact`)는 재생성 없이 통과한다.
22. **`plan-import` · `plan-status` 는 출력 계약 family 를 등록한다** (`PYDANTIC_MODEL_REGISTRY` + `generated_output_schemas.json` 재생성).
    `validate_output_payload` 는 미등록 family 에 `Unknown family` 를 돌려준다 — 등록 없이 그 검증을 타는 명령은 성공 경로가 죽는다
    (main 의 TASK-2026-11-04-main-002 가 MCP 도구 넷에서 그 증상을 기록했다).
23. **MCP 도구(`plan_inbox` · `plan_import`)는 ADR-032 로 넘긴다.** 받은편지함에 응답이 생기는 것은 워크벤치가 있을 때뿐이고, 도구를
    더하면 체크인 생성물 넷과 하드코딩된 개수(`assert len(tools) == 13`)가 함께 움직인다 — 서버와 한 번에 한다. 그때까지 정본 경로는 CLI 다.

24. **번호는 접미사를 통틀어 유일하다.** 보관 · 거둠으로 옮길 때 그 task 에 `<TASK-ID>-<n>.md` **또는** `<TASK-ID>-<n>.rejected.md` 가
    있으면 번호에 1 을 더한다 — 배타 판정의 단위는 이름이 아니라 번호다. 이름으로만 보면 `-3.md` 와 `-3.rejected.md` 가 함께 생겨 번호 3 이
    두 응답을 가리킨다. 파일을 찾는 패턴도 `-<숫자>.md` · `-<숫자>.rejected.md` 로 좁힌다 (`<TASK-ID>-*` 는 접두가 겹치는 다른 task 를 잡는다).
25. **줄바꿈을 LF 로 고치는 것은 쓰는 쪽의 의무이고 ADR-032 로 넘긴다** (워크벤치 requirements R5.3-4). 읽는 쪽은 고치지 않는다 —
    CR 은 제어 문자라 자격 1 단계에서 떨어진다. 읽는 쪽이 조용히 고치면 쓰는 쪽의 결함이 가려지고, 지문 · sha256 동률 규칙이 보는
    바이트가 파일과 달라진다.

### 구현 순서와 검사

26. **두 단계로 낸다.** ① 라벨 · 파서 · 린트 · 게이트 · `--decision-state` · `plan-status` · `open_decisions` — 이것만으로 안 A 가
    완결되고 발행할 수 있다. ② 응답 형식 · 받은편지함 · `plan-import`. 리더와 라이터는 같은 릴리스다 (requirements §1.1).
27. **검사는 넷이다** (스펙 §12 가 case 를 적는다). 기각한 구성: ⓐ 기존 `check_task_plan_section.py` 에 얹는다 — 상태 기계 탐색과 다중
    프로세스 경합은 수십 초가 걸려 `CHECK_TIMEOUT_S` 와 `WATCHES` 가 그 검사 전체에 걸린다. ⓑ 하나로 묶는다 — 순수 계산(파일 없음)과
    실제 파일 · 잠금 · 프로세스를 쓰는 검사가 한 파일에 있으면 `--changed` 가 파서 한 줄 수정에도 경합 검사를 돌린다:
    - `check_plan_claims.py` — 파서 · 린트 L1~L10 · 지문 · 기존 task 파일 전수 무변화.
    - `check_plan_decision_state.py` — 상태 계산을 **상태 기계로 전수 탐색**한다: 도착 · import(일괄 / 하나씩) · discard · `answered` 적기 ·
      걷기 · 손 편집의 모든 끼워 넣기에서 끝 상태 1종 · 멱등 · `done` 판정의 순서 무관 · 다툼에 든 입장이 채택된 채 닫히는 경로 0.
      requirements 검증이 일곱 번 손으로 고쳐 닫은 규칙이다 — 탐색을 저장소에 고정한다.
    - `check_plan_gate.py` — `backlog-update` 의 린트 오류 거부 · 전이 게이트 · 칸 고쳐 쓰기 · 우회 검출 warning.
    - `check_plan_import.py` — 자격 판정 · 잠금 · 배타 이동 · 쓰는 쪽 × 옮기는 쪽 둘의 경합(중복 0 · 유실 0, 잠금을 무력화하면 red).
28. **argparse 접두 축약을 끈다** (`allow_abbrev=False`) — 새 CLI 둘에서. `backlog-update` 는 지금 켜져 있고 이 ADR 이 건드리지 않는다. requirements R6.1 이 "모르는 인자는 거절한다" 를 요구하는데,
    축약이 켜져 있으면 `--resp` 같은 조각이 조용히 `--response` 로 받아들여진다 (`backlog-update` 에서 `--task-na` 가 받아들여지는 것을 쟀다).
29. **design 은 ADR 둘로 순차다** (소유자 결정 2026-11-13). 이 ADR 이 응답 형식 · 받은편지함 · `plan-import` 계약을 정하고 ADR-032 가
    소비한다. 한 ADR 로 묶으면 워크벤치의 실물 프록시 · 브라우저 실측이 끝날 때까지 안 A 의 design 이 닫히지 않는다.

## Requirements 대비 변경

| # | requirements | 여기서 | 근거 |
|---|---|---|---|
| V1 | R8.1 (과 워크벤치 requirements R5.3-7) — `<n>` 은 task 별 1 부터, 받은편지함 ∪ 보관의 가장 큰 번호 + 1 | `received_at` 의 epoch 마이크로초, 충돌 시 +1 (결정 13 · 24) | M4 · M5 |
| V2 | R1.4 — 결정 줄의 칸 이름 예시가 한국어 (`기본:` · `선택:` · `상태:`) | 쓰기는 영어, 읽기는 둘 다 (결정 8). 그래서 지문의 입력도 칸 이름을 정본 표기로 고친 것이다 (R5.2 는 라벨 정규화만 적었다) | 라벨 영어 전환과 같은 원칙. R1.4 는 "쓰기는 한 표기로, design 에서 고른다" 로 넘겼다 |
| V3 | R10 — MCP 는 read-only `plan_inbox`, write `plan_import` | ADR-032 로 넘긴다 (결정 23) | 시점만 바뀐다 |
| V4 | R13 — 브랜치 이어받기가 `plan_responses/` 를 옮기는지 미정 | 옮긴다 (결정 20) | M3 |
| V5 | R10 — "`plan-import` 스킬이 늘고, 묶음이 새 명령이 되면 하나 더" | 스킬은 하나만 (결정 6) | `plan-status` 는 그 스킬의 한 단계다 |
| V6 | R6.4 — Progress 는 `plan 응답 <n> (<responder>): …` (응답 하나당 한 줄) | 호출당 한 줄 — `plan 응답 n건 (<응답자들>): …` (결정 19) | `Progress` 는 한 줄짜리 현재값 필드다 |
| V7 | R1.1 — 새 라벨이 `PLAN_FIELDS` · `_PLAN_KEYS` 에 "함께 들어간다" | 두 목록을 `PLAN_FIELD_KEYS` 하나로 접는다 (결정 2) | 두 벌을 대조하는 검사가 없다 |
| V8 | R6.3 — 유효 응답의 모집단은 "지금 지문과 맞는 보관 응답" | 자격(1~6 단계)을 다시 본 보관 응답 (결정 16) | 보관에 직접 놓인 `viewer` · 형식이 깨진 파일을 세지 않는다 |
| V9 | R6.3 — 통과한 상태 전이는 칸을 고쳐 쓴다; R2.2 — 오류 상태 파일의 전이는 R3 을 따른다; R3.2 — 결정이 없는 task 는 영향이 없다 | 오류 규칙을 어긴 동안에는 칸을 다시 적지 않고, → `done` 은 거부한다 — 주장만 있고 결정이 없는 task 도 (결정 11) | 읽을 수 없는 계획에서 계산한 값으로 칸을 덮지 않는다 · 닫지 않는다 |
| V10 | R10 — `backlog_update_skill_spec.md` 에 필드 · 린트 · 게이트 | 그 스펙에는 새 인자와 포인터만, 규칙의 정본은 `claim_plan_spec.md` (스펙 §11) | 같은 규칙을 두 문서에 적지 않는다 |

소유자 결정(D1~D5 · Q1~Q7)을 바꾸는 것은 없다. V1 은 D5 의 파일명 형식을 지킨다.

## Alternatives Considered

| 대안 | 기각 이유 |
|---|---|
| 보관 번호를 카운터로 (requirements 문면) | 두 호스트가 같은 번호를 내 병합이 멈춘다 (M4). 쓰는 쪽과 옮기는 쪽이 겹칠 때마다 이름이 바뀐다 (M5) |
| 잠금 없는 배타 이동 + "같은 파일인지" 규칙 | 30 회 중 중복 8 · 유실 3 (워크벤치 requirements §1.2 행 10). 잠금이 60 회 · 120 회 모두 닫았다 |
| 주장별 묶음을 `backlog-update` 출력 필드로 | 읽기만 하려는 검증자가 쓰기 명령을 부르게 된다. dry-run 이어도 인자(`--task-name`)가 필요하다 |
| 결정 줄 칸을 한국어로 쓰기 | 라벨은 영어인데 칸만 한국어가 된다. 영어권 소비자 저장소에서 읽히지 않는다 |
| 루트 `.gitignore` 에 `plan_responses/inbox/` 한 줄 | bootstrap 은 루트 gitignore 를 심지 않고(`ensure_gitignore_patterns` 는 별도 스크립트가 부른다), 재적용 전 소비자는 첫 응답을 커밋할 수 있다 |
| 워크벤치와 한 ADR 로 | 실물 프록시 · 브라우저 실측이 끝날 때까지 안 A 의 design 이 닫히지 않는다 (소유자 결정 — ADR 둘) |
| MCP 도구를 지금 | 응답을 쓰는 쪽이 아직 없다. 생성물 넷과 개수 단언이 따라 움직인다 |
| 이어받기가 응답을 옮기지 않음 (지금 동작) | 이어받은 결정이 첫 재계산에서 조용히 다시 열린다 (M3) |
| 상태 칸을 정본으로 (계산하지 않음) | requirements 검증 2~8차가 이 형태에서 매회 순서 의존을 찾았다. 칸은 계산 결과를 적어 둔 것이다 |

## Consequences

- `plan-import` 가 `Progress` 에 한 줄을 쓰면 세션이 적어 둔 진행 메모가 그 줄로 바뀐다 (`Progress` 는 현재값 필드다 — requirements R6.4 에서 온 성질).
  메모를 남기려면 import 뒤에 `--progress-note` 로 다시 적는다.
- 지문을 바꾼 뒤에는 `done` 판정이 import 시점에 달린다 — 바꾸기 전에 보관된 옛 응답은 조용히 자격을 잃고, 받은편지함에 남아 있던 같은
  응답은 `--discard` 할 때까지 `done` 을 막는다. 막는 쪽으로만 갈리고 결정 18 의 경고가 알린다.
- 진입점이 181 바이트 는다 — 가장 큰 진입 파일이 6,844 / 8,192 가 된다 (여유 1,348). 정본을 고치면 `ai-workflow/core/` 사본 ·
  규칙 스냅샷 · 플러그인 스킬 본문을 함께 재생성한다 (`check_standard_single_source`).
- 플러그인 스킬이 6종이 된다. `MINIMAX_EXAMPLE_QUERIES` 에 slug 를 더해야 한다 (없으면 KeyError).
- `backlog-update` 의 모든 `--apply` 쓰기가 주장이 있는 task 에서 상태를 다시 계산한다 — 보관 디렉터리를 읽는 비용이 든다. 주장이 없는
  task 는 읽지 않는다.
- 옛 kit 이 섞인 환경에서는 `done` 게이트가 우회된다 — 사후 warning 으로만 드러난다 (requirements Q3).
- 다른 하네스에는 검증자 대응물이 없다 (M2). `plan-status` 는 어느 하네스에서나 같은 표를 내지만, 새 컨텍스트에서 판정을 채우는 것은
  지금 Claude Code 의 verifier 뿐이다.
- 두 호스트가 같은 브랜치에서 각자 응답을 보관하면 파일은 충돌 없이 합쳐진다 (M4). 같은 결정에 다른 값이면 합친 뒤의 첫 재계산이
  `disputed` 로 연다 — 병합이 조용히 한쪽을 고르지 않는다.
- Windows(NTFS)에서의 `os.link` 공개 · 배타 이동 · 잠금은 재지 않았다. `file_lock` 은 Windows 백엔드가 있으나 이 조합은 미실측이다.

## Implementation Notes

**1단계 (2026-11-13, TASK-2026-11-13-claude-remote-sync-check-234c32-003, M-028/WBS-28.1)** — 결정 26 의 ①.

- 결정 1 의 모듈에 **`workflow_kit/common/plan_tasks.py` 가 하나 더 있다** — task 파일을 읽어 `plan_claims` 에 넘기는 얇은 I/O 층이다
  (게이트 · `plan-status` · state 생성기 · 우회 검출이 "task 파일을 어떻게 읽는가" 를 각자 정하지 않게). `plan_claims` 는 순수 함수로 남는다.
  보관 응답을 읽는 자리는 `plan_tasks.archived_responses` 하나로 모았고 1단계에서는 빈 목록이다 — 2단계가 그 함수만 채운다.
- 받은편지함 게이트(`pending_plan_responses`), 응답 자격, `plan-import`, 이어받기, §11.1 한 줄과 스킬은 2단계다.
  1단계의 상태 계산은 응답이 없으므로 `answered` 가 아닌 결정을 전부 `proposed` 로 본다.
- 정본 §1 개정은 1단계에 넣었다 (진입점 +181 바이트). 진입점 템플릿이 바뀌어 `harvest_entry_sections.py` 의 `DEFAULT_REFS` 에 그 커밋을 더했다.
- 검증(새 컨텍스트)이 스펙과 다른 동작 9건과 검사가 못 보던 되주입 24건을 찾았다 — 코드와 검사를 고쳤다: 사유는 명시한
  `--progress-note` 만(brief 로 채운 진행 줄은 사유가 아니다) · 결정 줄을 교체해도 `answered` 를 옮겨 적는다(결정 12) · 겹친 거부 사유를
  함께 싣는다 · 같은 상태를 다시 준 호출에는 린트 경고를 되풀이하지 않는다 · `refresh-state --check` 도 우회를 싣는다 ·
  `.claude/agents/verifier.md` 에 `plan-status` 한 줄(결정 4).
- 2차 검증이 판정 분기 단위로 넣은 되주입에서 린트 32건이 더 안 잡혔다 — 일부 규칙만 확인하던 검사를 "입력마다 나와야 하는
  (규칙, 강도, 대상) 전부" 를 대조하는 표(41 입력)로 바꿨다. 공백뿐인 `--progress-note` 가 사유로 통하던 길도 막았다.
- 3차 검증이 게이트를 지나는 길 둘을 더 찾았다: 같은 ID 로 task 를 다시 만드는 `create` 가 열린 결정을 덮어쓰고 닫는 것,
  폭 없는 문자뿐인 사유. 열린 결정을 없애는 쓰기는 경로와 무관하게 읽을 수 있는 사유를 요구하도록 고쳤다 (스펙 §2.5).
  읽을 수 없는 결정 줄의 지문은 원문 그대로(§5-2), 값 없는 라벨 줄은 묶음이 아니다(§2.1).
- 검증자가 넣은 되주입 432건(판정 분기 단위) 중 스펙의 판정을 바꾸는 것은 전부 red 다. 남은 green 은 다른 판정이 같은 규칙 · 강도 ·
  대상으로 잡는 동치이거나 스펙 밖(메시지 문구)이다. "N건 전부 red" 는 그 N건에 대한 말이다 — 표본을 넓힐 때마다 빈 곳이 나왔다.

**2단계 (2026-11-13, TASK-2026-11-13-claude-remote-sync-check-234c32-004, M-028/WBS-28.2)** — 결정 26 의 ②.

- 응답 파일의 형식 · 자격 · 디렉터리는 `workflow_kit/common/plan_responses.py` 한 곳이다 (읽기 · 1~6 단계 · 자기 무시 · 번호 · 공개 ·
  배타 이동 · 잠금). 상태 계산은 여전히 `plan_claims` 다. `plan_tasks.archived_responses` 가 자격을 다시 본 보관 응답을 돌려주고,
  게이트 · `plan-status` · 우회 검출이 그것으로 계산한다. **읽는 길은 디렉터리를 만들지 않는다** — 응답이 없는 저장소의 트리는 그대로다.
- 배타 이동은 `os.link`(있으면 실패) + `unlink` 다. 쓰는 쪽의 공개도 같은 호출이다 — 같은 `received_at` 으로 쓰는 쪽 넷 × 옮기는 쪽 둘에서
  중복 0 · 유실 0 (`check_plan_import` case 9).
- `backlog-update` 는 자격을 **쓰기 뒤의 계획**(초안의 지문)으로 본다 — 지문을 바꾸는 쓰기는 같은 쓰기에서 옛 응답을 잃는다.
- 판정 순서: 0 단계 → 잠금 → 쥔 뒤 task 와 받은편지함을 다시 읽는다 (design 검증이 넘긴 ①). dry-run 의 0 단계도 rc 1 이다 (②).
- 결정 20 에 한 가지를 더했다: 합류가 이어받은 task 를 원본 쪽에 **되돌려 적을 때도** 브랜치에서 보관한 응답을 함께 복사한다 —
  task 만 돌아가면 그 상태의 근거가 아카이브에만 남는다 (스펙 §11). 검증이 그 반대쪽 구멍을 찾았다 — 브랜치에서 **거둔** 응답이
  원본 쪽 보관에 `.md` 로 남아, 브랜치에서 `proposed` 로 되돌린 결정이 원본 쪽에서 다시 닫혔다 (결정 20 의 원래 문면에서도 생기는 길이다).
  되돌려 적기가 거둠도 나르게 했다: 내용이 같은 원본 쪽 보관 응답을 `.rejected.md` 로 옮긴다 — 브랜치가 같은 내용을 보관에도
  들고 있으면(거뒀다가 다시 받았다) 거두지 않는다. **결정 20 의 확장 — 소유자 승인 2026-11-13** (task -004 의 D1 = carry).
- 스킬 `plan-import` 는 bootstrap 채널의 slash command(`/workflow-plan-import`)로도 나간다 — 두 채널의 스킬 집합을 맞추는 기존 검사가 요구한다.
- 응답 파일 이름의 ID 는 작업 항목 ID 문법(`project_docs.WORK_ITEM_ID_PATTERN`)으로 읽는다 — 게이트가 세는 이름과 같은 집합이어야
  세어진 파일이 "알 수 없는 파일" 로도 나오는 어긋남이 없다 (검증이 `WF-…` ID 에서 찾았다).
- `received_at` 은 `datetime.fromisoformat` 에 맡기지 않고 스펙 §6 의 한 꼴만 직접 읽는다 (`plan_claims.parse_received_at`) —
  라이브러리 파서는 Python 판마다 받는 범위가 다르고(3.10 은 `.5` 를 거절) 스펙보다 넓었다 (`Z` · 주 날짜 · 기본형 · 7 자리 소수).
- dry-run 의 예고(놓일 이름 · Progress)는 실제와 같아야 한다 — 번호가 보관과 겹칠 때와 `--discard` 에서 달랐던 것을 고쳤다.
- Windows(NTFS)의 `os.link` · 잠금은 이번에도 재지 못했다 — 구현 뒤 Windows 호스트에서 잰다 (M-028 의 남은 항목).

## References

- `docs/planning/html-plan-absorption-review-2026-11.md` (concept, §10 D1~D5 · §11 정정)
- `docs/planning/claim-plan-requirements-2026-11.md` (requirements, §12 Q1~Q7)
- `docs/planning/plan-workbench-requirements-2026-11.md` (§1.2 경합 실측 · R5.5)
- `workflow-source/core/claim_plan_spec.md` — kit 계약
- `workflow-source/workflow_kit/common/project_docs.py` · `workflow_writes.py` · `tools/backlog_update.py` — 라벨 · Plan 절 · 게이트가 꽂히는 자리
- `workflow-source/workflow_kit/common/file_lock.py` · `compact_relay.py` — 잠금과 자기 무시 디렉터리의 선례
