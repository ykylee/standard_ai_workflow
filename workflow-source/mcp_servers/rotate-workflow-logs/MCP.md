# rotate-workflow-logs

- 문서 목적: session handoff 의 "최근 완료 작업" 이 상한을 넘지 않도록 오래된 done 항목을 baseline 으로 회전시키는 MCP 도구의 스펙 정의
- 범위: handoff done 목록 회전 알고리즘 및 MCP 인터페이스 스펙
- 대상 독자: AI 에이전트, MCP 클라이언트
- 상태: implemented (**write-capable** — `readOnlyHint=false`, ADR-003 v1.1.7)
- 최종 수정일: 2026-08-12
- 관련 문서: `../../workflow_kit/common/read_only_bundle.py` (`rotate_workflow_logs_payload`), `../../../docs/architecture/ADR-003-read-only-mcp-default-policy.md`

## 목적

handoff §4 "최근 완료 작업" 은 파생 목록이라 상한(기본 10건)이 있다. 상한을 넘긴
오래된 항목을 잘라 handoff bloat 를 막는다.

> **write-capable**: 이 도구는 handoff 파일을 **실제로 rewrite** 한다. bundle 의
> read-only default 의 예외 2종 중 하나로, descriptor 의 `readOnlyHint=false` 와
> registry 의 `WRITE_CAPABLE_TOOL_NAMES` 에 선언돼 있다 (TASK-2026-08-11-main-024).

## 입력 (Input)

- `handoff_path` (string, required): session handoff 문서 경로
- `max_done_items` (string/int, optional): 유지할 done 항목 수 (기본 10)

## 출력 (Output)

- `rotated` (bool): 회전이 실제로 일어났는가
- `rotated_count` / `remaining_count` (int): 회전/잔여 항목 수
- `rotated_items` (list of strings): 회전된 항목
- `written_paths` (list of strings): 실제로 쓴 파일 (회전 시 handoff 경로)

## 특이 사항

- 본 디렉터리의 스크립트는 registry (`read_only_registry.py`) 의 `script_path` 가
  가리키는 실물이다 — 2026-08-12 이전에는 registry 에만 등록되고 디렉터리가 없어
  manifest 가 유령 경로를 광고했다 (TASK-2026-08-11-main-025).
