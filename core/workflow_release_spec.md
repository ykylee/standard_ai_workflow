# Workflow Release Spec

- 문서 목적: 하네스별 워크플로우 패키지를 배포 가능한 산출물로 묶을 때 필요한 release 규격과 산출물 구조를 정의한다.
- 범위: dist 구조, 하네스 패키지 manifest, export 기준, 검증 포인트
- 대상 독자: 저장소 관리자, 배포 담당자, AI workflow 설계자
- 상태: draft
- 최종 수정일: 2026-04-23
- 관련 문서: `./workflow_harness_distribution.md`, `./prototype_promotion_scope.md`, `../scripts/export_harness_package.py`, `../harnesses/README.md`

## 1. release 목표

- 공통 workflow 문서와 하네스 오버레이를 재사용 가능한 배포 단위로 묶는다.
- 하네스별 산출물이 어떤 파일을 포함하는지 manifest 로 추적 가능해야 한다.
- 로컬에서 빠르게 export 해 검토하거나, 이후 CI에서 그대로 재사용할 수 있어야 한다.

## 2. dist 구조

권장 dist 구조는 아래와 같다.

- `dist/harnesses/<target>/`
- `dist/harnesses/<target>/manifest.json`
- `dist/harnesses/<target>/bundle/`
- `dist/harnesses/<target>/bundle/<exported files>`
- `dist/harnesses/<target>/<target>-workflow-kit.zip`
- `dist/harnesses/<target>/bundle/source-docs/schemas/read_only_transport_descriptors.json`
- `dist/harnesses/<target>/bundle/source-docs/schemas/read_only_harness_mcp_examples.json`
- `dist/harnesses/<target>/bundle/source-docs/schemas/read_only_jsonrpc_fixtures.json`

## 3. 하네스 패키지 구성

각 하네스 패키지는 아래 두 레이어를 함께 포함한다.

1. 공통 workflow 레이어
2. 하네스 오버레이 레이어

공통 workflow 레이어 기본 포함 항목:

- `ai-workflow/README.md`
- `ai-workflow/project/project_workflow_profile.md`
- `ai-workflow/project/session_handoff.md`
- `ai-workflow/project/work_backlog.md`
- `ai-workflow/project/backlog/YYYY-MM-DD.md`

하네스 오버레이 레이어 포함 항목:

- Codex: `AGENTS.md`, `.codex/config.toml.example`
- OpenCode: `opencode.json`, `.opencode/skills/...`, `.opencode/agents/...`

## 4. manifest 최소 필드

- `harness`
- `exported_at`
- `source_root`
- `bundle_root`
- `included_files`
- `notes`

## 5. export 검증 포인트

- 선택한 하네스 오버레이 파일이 모두 bundle 에 포함됐는지 확인
- 공통 workflow 문서가 bundle 에 포함됐는지 확인
- manifest 의 포함 파일 목록이 실제 bundle 과 일치하는지 확인
- read-only MCP descriptor 산출물, 하네스별 MCP 예시 draft, JSON-RPC fixture, read-only bundle 안내 문서가 포함됐는지 확인
- zip 산출물이 생성됐는지 확인

## 6. 운영 원칙

- 배포 산출물은 source-of-truth 가 아니라 export 결과물이다.
- 정책 변경은 항상 `core/`, `harnesses/`, `scripts/` 원본에서 수행한다.
- dist 는 재생성 가능해야 하며, export 스크립트가 같은 구조를 반복 생성할 수 있어야 한다.

## 7. 다음 단계와의 관계

- 현재 release spec 은 문서 패키지와 하네스 overlay export 를 기준으로 한다.
- reusable package 또는 MCP server 승격 범위는 [./prototype_promotion_scope.md](./prototype_promotion_scope.md) 에서 별도로 정의한다.
- 즉, 현재의 `dist/` export 와 향후 library/server 배포는 같은 문제가 아니라 두 단계의 별도 배포 축으로 본다.

## 다음에 읽을 문서

- 하네스 배포 전략: [./workflow_harness_distribution.md](./workflow_harness_distribution.md)
- 승격 범위 문서: [./prototype_promotion_scope.md](./prototype_promotion_scope.md)
- 하네스 허브: [../harnesses/README.md](../harnesses/README.md)
