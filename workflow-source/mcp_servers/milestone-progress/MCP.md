# milestone-progress

- 문서 목적: maturity matrix 와 현재 backlog 를 대조해 milestone 진행률을 평가하는 MCP 도구의 스펙 정의
- 범위: milestone 진행 평가 및 MCP 인터페이스 스펙
- 대상 독자: AI 에이전트, MCP 클라이언트
- 상태: implemented (read-only)
- 최종 수정일: 2026-08-12
- 관련 문서: `../../workflow_kit/common/read_only_bundle.py` (`assess_milestone_progress_payload`), `../../core/maturity_matrix.json`

## 목적

`core/maturity_matrix.json` 의 milestone 정의와 현재 backlog 문서를 대조해,
진행 중 milestone 의 완료율과 다음 행동 제안을 돌려준다.

## 입력 (Input)

- `matrix_path` (string, required): maturity matrix JSON 경로
- `backlog_path` (string, required): 현재 backlog 문서 경로

## 출력 (Output)

- `milestone_id` / `milestone_name` (string): 평가 대상 milestone
- `progress_percentage` (number): 완료율
- `done_count` / `total_count` (int): 완료/전체 항목 수
- `suggestion` (string): 다음 행동 제안

## 특이 사항

- 본 디렉터리의 스크립트는 registry (`read_only_registry.py`) 의 `script_path` 가
  가리키는 실물이다 — 2026-08-12 이전에는 registry 에만 등록되고 디렉터리가 없어
  manifest 가 유령 경로를 광고했다 (TASK-2026-08-11-main-025).
