# 24차 세션 기록 — 플러그인 전환 P1: 공유 payload 렌더러 (2026-08-12)

- 문서 목적: 24차 세션의 작업 내용·산출물·다음 시작 포인트 기록
- 범위: TASK-2026-08-12-main-014 (플러그인 전환 P1 — `render_agent_plugin`)
- 상태: done
- 최종 수정일: 2026-08-12
- 관련 문서: [전환 계획 §3-P1](../../../../docs/planning/plugin-transition-plan-2026-08.md), [23차 세션 기록](./plugin_transition_plan_2026-08-12.md)

## 1. 지시

사용자: "TASK-014 착수해줘" — 23차에서 확정한 P1~P5 로드맵의 첫 단계.

## 2. 산출물

1. **`workflow_kit/plugin_payload.py`** — `render_agent_plugin()` 이 `plugin/`
   payload 5파일을 정본에서 생성한다. 디스크를 건드리지 않고
   `{상대경로: 내용}` 을 돌려주므로 **생성과 검증이 같은 함수**를 쓴다 —
   drift 가 생길 자리가 구조적으로 없다.
   - `plugin.json` — name / version(`__version__` 파생) / description
   - `skills/{session-start,backlog-update,doc-sync}/SKILL.md`
   - `mcp.json` — read-only bundle 서버 1개
   - CLI: `python3 -m workflow_kit.plugin_payload --apply` (무인자는 drift 판정)
2. **`plugin/`** — 위 렌더러의 생성물 5파일. `state.json` 과 같은 지위다.
3. **`tests/check_agent_plugin_payload.py`** — 7 case (drift / frontmatter /
   §11 파생 / version / registry 정합 / 규칙 리터럴 부재 / 탐지기 실증).
   smoke 251 → **252**.

## 3. 정본 파생 관계 (사본을 만들지 않은 자리)

| payload 축 | 정본 | 파생 경로 |
|---|---|---|
| §11.1 갱신 명령 | 정본 §11.1 | `find_memory_command()` |
| §11.2 파싱 계약 | 정본 §11.2 | `render_memory_update_section()` |
| 작업 상태값 4종 | 정본 §3 | `rules.task_states` |
| MCP command/args | `bootstrap_lib.mcp` | `mcp_server_command()` |
| MCP 도구 구성 | `read_only_registry` | `tool_specs_for_bundle()` |
| plugin 버전 | `workflow_kit.__version__` | 직접 참조 |

case 6 이 이 모듈에 규칙 문장 리터럴이 없음을 18개 문장 대조로 강제한다 —
`check_standard_single_source` 의 case 2 가 `harnesses/renderers.py` 에 하는 일을
새 렌더러 모듈에 대해 하는 것이다.

## 4. 계획과 달라진 판단 — plugin.json 3필드 고정

Agent Plugins 1.0 은 2026-08-06 출범이고, **이 세션에서 스펙 원문을 확인하지
못했다** (세션 환경의 웹 접근 불가). 확인 안 된 선택 필드를 지어 넣으면 스펙
확정 시 조용히 틀린 값이 된다. 그래서 계획 §3-P1 이 명시한 3필드만 쓰고,
검사 case 4 가 **필드 집합 자체를 고정**한다 — 필드를 늘리려면 그 검사가 먼저
FAIL 하므로 갱신이 명시 task 를 거친다 (계획 §5 "스키마를 fixture 로 고정" 의 구현).

같은 이유로 `mcp.json` 은 사실상 전 하네스 공통인 `mcpServers` 스키마만 쓴다.
`env` 에 `PYTHONPATH` 를 넣지 않았다 — 플러그인은 소비 프로젝트의 체크아웃
구조를 모르고, `wk` 설치 전제가 깨지면 조용한 fallback 없이 드러나야 한다 (원칙 4).

## 5. 검증

- 신설 검사 **7/7**
- **되주입 실증 (저장소 실물)**: `plugin.json` 의 version 을 손으로 바꾸자
  `FAIL: 드리프트: plugin.json` → 재생성 후 7/7 복귀. temp 사본에서는 손 편집 /
  파일 삭제 / 미등록 파일 3종을 case 7 이 상시 실증한다.
- **전량 2축 252/252 ×2 green** (격리 venv, `--tmp-dir` 실디스크)
- mypy strict **192 파일 0** (`workflow-source` 기준 — 저장소 루트에서 돌리면
  설정이 안 먹어 366 errors 로 보인다. 게이트와 같은 cwd 에서 재야 한다)
- self-application 8/8

## 6. 다음 시작 포인트

**TASK-2026-08-12-main-015 (P2)** — Claude Code 어댑터 + marketplace + 자기 적용.
P1 payload 를 참조하는 얇은 manifest (`.claude-plugin/plugin.json`) + hooks
(SessionStart 안내 / SessionEnd → `wk refresh-state`) + 저장소 루트
`marketplace.json`, 그리고 이 저장소에서 `/plugin install` 실측.

P2 의 자기 적용에서 **실 클라이언트가 요구하는 manifest 필드가 드러나면** §4 의
3필드 고정을 거기서 확정한다 (스펙 확인 경로 하나).

## 7. 남은 리스크

- Agent Plugins 1.0 선택 필드 스펙 미확인 (위 §4) — P2 실측 또는 스펙 원문 확인 시 해소.
- `plugin/` 은 아직 릴리스 파이프라인 밖이다 — bump 시 version 자동 동기는 P4
  (TASK-017) 의 범위다. 그전까지는 릴리스 후 `--apply` 재생성이 필요하다.
