# Skills

- 문서 목적: 표준 워크플로우에서 공통으로 재사용할 skill 구현을 배치할 위치와 역할을 안내한다.
- 범위: skill 프로토타입 디렉터리 구조, 구현 진입점, 초기 도입 후보
- 대상 독자: AI agent 설계자, 개발자, 운영자
- 상태: draft
- 최종 수정일: 2026-04-18
- 관련 문서: `../core/workflow_skill_catalog.md`, `./prototype_layout.md`

## 현재 상태

- 1차 핵심 skill 4종에 대한 프로토타입 디렉터리 구조를 추가했다.
- 현재 단계는 실행 가능한 구현 전이며, 각 디렉터리의 `SKILL.md` 에 목적과 입력/출력 계약 연결, 구현 메모를 정리한 상태다.
- 실제 런타임 코드, 테스트, 배포 스크립트는 아직 없다.
- 예시 프로젝트 기준 end-to-end 실행 흐름은 [../examples/end_to_end_skill_demo.md](../examples/end_to_end_skill_demo.md) 에 정리돼 있다.

## 현재 구조

- [prototype_layout.md](./prototype_layout.md)
- [session-start/SKILL.md](./session-start/SKILL.md)
- [backlog-update/SKILL.md](./backlog-update/SKILL.md)
- [doc-sync/SKILL.md](./doc-sync/SKILL.md)
- [merge-doc-reconcile/SKILL.md](./merge-doc-reconcile/SKILL.md)

## 구현 원칙

- 각 skill 디렉터리는 최소한 `SKILL.md` 를 가져야 한다.
- `SKILL.md` 에는 목적, 입력, 출력, 읽기/쓰기 권한 경계, 후속 구현 포인트가 포함되어야 한다.
- 정책 원문은 `core/` 에 두고, `skills/` 는 실행 절차와 구현 단위에 집중한다.
- 실제 구현이 추가되더라도 수동 대체 절차는 유지되어야 한다.

## 다음 구현 순서 권고

- `session-start`: 문서 읽기 순서와 구조화 출력 프로토타입부터 구현
- `backlog-update`: 날짜별 backlog 초안 생성 및 갱신 보호 로직 구현
- `doc-sync`: 변경 파일 기반 영향 문서 추천 로직 구현
- `merge-doc-reconcile`: 병합 후 재확정 포인트 생성 로직 구현

## 다음에 읽을 문서

- skill 카탈로그: [../core/workflow_skill_catalog.md](../core/workflow_skill_catalog.md)
- 프로토타입 구조 안내: [./prototype_layout.md](./prototype_layout.md)
- end-to-end 데모: [../examples/end_to_end_skill_demo.md](../examples/end_to_end_skill_demo.md)
