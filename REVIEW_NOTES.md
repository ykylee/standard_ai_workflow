# Review Notes

- 문서 목적: 외부 관점에서 `standard_ai_workflow` 저장소를 훑어보고 느낀 점, PR 후보, 오픈 질문을 한 곳에 정리한다.
- 범위: 전체 구조, core 문서, 실행형 skill/MCP 프로토타입, 스크립트, 테스트, 배포 구조
- 대상 독자: 저장소 유지보수자, 리뷰 참고자
- 상태: draft (review)
- 최종 수정일: 2026-04-21
- 관련 문서: `README.md`, `core/global_workflow_standard.md`, `core/output_schema_guide.md`

## 0. 검토 맥락

- 동훈님이 Claude 와 같이 저장소를 훑은 결과를 정리한 문서다.
- 동료 리뷰어가 가볍게 읽고 취할 건 취하고 버릴 건 버릴 수 있게 "관찰 → 근거 → 제안" 순서로 정리했다.
- 코드나 문서를 실제로 건드린 변경은 이 브랜치에 함께 커밋된 `.gitignore`, `.github/workflows/smoke.yml` 두 건뿐이다. 그 외 제안은 모두 본 문서 안에 의견으로 두었다.

## 1. 전반 인상

- 문서만 번드르르한 템플릿 키트가 아니라 실행형 프로토타입이다. `python3 scripts/run_demo_workflow.py` 가 바로 실행돼 session-start → backlog-update → doc-sync → validation-plan → code-index-update → merge-doc-reconcile 체인이 구조화된 JSON 을 출력한다.
- `tests/check_*.py` 9 개 전부 통과한다. 특히 `check_docs.py` 가 67 개 md 파일의 메타데이터 6 필드를 강제하는 구조는 초반에 깔아두기 매우 좋은 가드레일이다.
- core(정책) → skills(실행 단위) → mcp(도구) → harnesses(배포 오버레이) → global-snippets(비침투적 주입) 레이어가 실제 의존 방향과 일치한다. 구조 정렬이 단단하다.
- README 가 스스로 "시범 적용 부족", "실패 출력과 `error_code` 수준 계약은 더 고정 필요" 라고 자기 진단을 적어둔 것도 솔직한 포인트다.

## 2. 잘 잡혀 있다고 느낀 것

- 문서 메타데이터 강제와 링크 무결성 검사를 하나의 smoke test 로 묶어둔 것.
- `bootstrap_workflow_kit.py --adoption-mode existing` 이 타깃 저장소를 실제로 스캔해서 `repository_assessment.md` 초안까지 생성한다. 신규/기존 프로젝트를 동등하게 다루는 점이 좋다.
- `core/output_schema_guide.md` 에서 `status` / `tool_version` / `warnings` / `error` / `error_code` 를 공통 필드로 먼저 못 박아둔 것. skill 구현이 흩어지기 전에 해야 하는 순서다.
- `core/global_workflow_standard.md` 1.1 절에서 "handoff, backlog, 보고는 기본 한국어" 를 명시한 것. AI 협업 워크플로우에서 이 선을 안 박으면 은근히 영어로 drift 하기 쉬운데 깔끔하게 처리돼 있다.
- `workflow_kit/common/` 에 파서/링크검사/경로 공용 유틸을 빼둔 점. 5 개 스크립트가 같은 로직을 복붙하지 않게 해준다.

## 3. PR 후보 (작업량/임팩트 순)

### 3.1 본 브랜치에 이미 포함된 변경

- `.gitignore` 보강 — `__pycache__/`, `*.pyc`, `dist/`, `.venv/`, `venv/`, `.DS_Store` 등 실제로 생성되는 산출물 차단. 기존 `.gitignore` 는 11 바이트(`.DS_Store` 한 줄)뿐이라 `scripts/export_harness_package.py` 실행 후 더럽혀진 파일이 커밋으로 샐 위험이 있었다.
- `.github/workflows/smoke.yml` 추가 — 모든 push/PR 에서 `tests/check_*.py` 9 개를 순차 실행한다. 기존 테스트가 전부 pure Python 이라 GitHub Actions 기본 러너만으로 충분하다.

### 3.2 후속 PR 후보 (작은 것)

- **`tool_version` 단일 소스화.** 현재 `prototype-v1` 이 최소 10 개 파일에 하드코딩돼 있다. `workflow_kit/__init__.py` 에 `__version__ = "prototype-v1"` 을 두고, 각 runner 에서 `from workflow_kit import __version__ as TOOL_VERSION` 으로 import 하는 형태로 바꾸면 릴리스 시점에 한 군데만 손대면 된다. 테스트 영향도가 작아서 mechanical 리팩토링에 가깝다.
- **Claude Code 하네스 추가.** `scripts/README.md` 에 이미 `python3 scripts/scaffold_harness.py --harness-name claude-code ...` 예시가 있는데 `harnesses/claude-code/` 는 비어 있다. scaffold 로 starter 를 만들고 `CLAUDE.md`, `.claude/settings.json.example`, `global-snippets/claude-code/` 를 채우면 "주요 하네스 모두 지원" 주장이 실제로 성립한다.
- **`tests/README.md` 에 전체 실행 원샷 명령 추가.** smoke.yml 이 쓰는 것과 동일한 `for t in tests/check_*.py; do python3 "$t" || exit 1; done` 한 줄을 문서화해두면 로컬에서도 CI 와 같은 결과가 나옴을 보장할 수 있다.

### 3.3 후속 PR 후보 (조금 더 큰 것)

- **`error_code` 계약 실적용 감사.** `core/output_schema_guide.md` 4.2 절은 실패 시 `{"status":"error","error":"...","error_code":"missing_project_profile",...}` 를 내라고 규정하지만, 실행형 스크립트들은 `resolve_existing_path()` 등에서 `FileNotFoundError` 로 크래시할 가능성이 크다. 최소 한 skill(예: `session-start`)만 먼저 try/except 로 감싸 error JSON 을 실제로 뱉게 하고, 해당 실패 출력을 `check_*.py` 에 케이스로 넣어 두면 다른 skill 이 뒤따를 때 패턴이 된다.
- **`output_samples/*.json` 자동 재생성 도구.** 12 개 샘플 JSON 이 정적이라 runner 출력이 바뀌면 빠르게 stale 된다. `scripts/regenerate_output_samples.py` 를 추가해 로컬 또는 CI 에서 주기적으로 재생성 → diff 확인 → 수동 commit 하는 흐름을 만들면 계약 동기화를 유지하기 쉽다.
- **session-end 흐름.** session-start 는 읽기 전용 프로토타입이 있는데, 대칭되는 "session 종료 시 handoff 자동 갱신" skill 이 안 보인다. 수동 대체는 가능하지만, 비대칭이라 실사용에서 session-start 의 이점이 절반만 나올 가능성이 있다.

## 4. 논의가 필요한 항목 (이슈부터 열기를 권함)

- **작업 기록 최소 필드 15 개가 무겁지 않은가.** `core/global_workflow_standard.md` 4 절의 최소 필드에 `담당`, `호스트명`, `호스트 IP` 가 포함돼 있다. 공개 repo 의 "공통 얇은 표준" 지향과 기업 내부 운영 체계의 중간에 걸친 느낌이다. 두 가지 선택지:
  - (a) 현재 15 개를 유지하되 최소/확장 필드로 재계층화한다. 최소 6~7 개 + 선택 8~9 개.
  - (b) 공개 표준은 6~7 개로 줄이고, `호스트명`/`호스트 IP` 같은 항목은 `project_workflow_profile.md` 가 선택 추가하는 방식으로 밀어낸다.
- **core 문서 중복 가능성.** `workflow_kit_roadmap.md`(256 줄), `workflow_release_spec.md`(78), `prototype_promotion_scope.md`(183), `workflow_configuration_layers.md`(140) 는 "무엇이 prototype 이고 무엇이 release 인가" 를 각도만 바꿔 설명하는 부분이 겹친다. README 의 "다음에 읽을 문서" 도 16 개 링크를 나열 중이다. 신규 기여자 관점에서 "어디부터 읽지" 혼란 위험이 있어서, 4 개를 2 개로 합치거나 상호 참조를 정리하면 진입 난이도가 내려갈 것이다.
- **README 섹션 3 의 "현재 구현 상태" 표와 `project_status_assessment.md` 의 관계.** 두 문서가 같은 상태를 각자 적고 있어서 업데이트 타이밍이 어긋날 위험이 있다. 둘 중 하나를 단일 출처로 정해서 다른 하나는 링크로 리다이렉트하는 게 안전하다.

## 5. 세부 관찰 메모

- `tool_version = "prototype-v1"` 은 `skills/session-start/scripts/run_session_start.py`, `scripts/run_demo_workflow.py`, `scripts/run_existing_project_onboarding.py`, `mcp/*/scripts/run_*.py` 등에 산재한다.
- `README.md` 7 절의 bootstrap 예시는 `--target-root /tmp/sample-repo` 를 제시하지만, macOS/Linux 가정이 강하다. Windows 사용자 비중이 있으면 `%TEMP%` 기반 예시나 `powershell` 블록을 추가 고려할 만하다.
- `global-snippets/codex/`, `global-snippets/opencode/` 가 있는 반면 `global-snippets/claude-code/` 가 없다. 앞서 3.2 의 Claude Code 하네스 추가와 함께 묶어서 다루면 자연스럽다.
- `core/workflow_agent_topology.md` 가 47 줄로 다른 core 문서 대비 매우 짧다. 의도한 축약인지, 아니면 초안 단계인지 문서에 드러나면 좋겠다. 상태는 `draft` 로만 돼 있어 독자가 판단하기 어렵다.

## 6. 총평

현재 상태는 "문서 패키지로 내놔도 무리 없고, 실제 저장소 1~2 곳에 시범 적용하면서 최소 필드 · 중복 문서 쪽만 다듬으면 v1 을 붙일 수 있는" 수준이다. 자기 진단이 정확해서 남은 작업의 방향이 선명하다. 위 PR 후보와 오픈 질문 중 가벼운 쪽부터 먼저 정리해 나가면 중복 논의 없이 다음 단계로 넘어갈 수 있을 것이다.

## 다음에 읽을 문서

- 저장소 개요: [README.md](./README.md)
- 공통 코어 표준: [core/global_workflow_standard.md](./core/global_workflow_standard.md)
- 출력 스키마 가이드: [core/output_schema_guide.md](./core/output_schema_guide.md)
- 분리 체크리스트: [split_checklist.md](./split_checklist.md)
