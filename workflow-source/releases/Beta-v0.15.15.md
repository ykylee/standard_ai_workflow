# Beta v0.15.15 — v0.15.x 정합 보강 close-out + v1.0.0 진입 준비 (2026-07-18)

> v0.15.0 breaking release 이후 누적된 v0.15.1~v0.15.15 follow-up을 공식 패키지로 묶는다.
> Phase 12는 계속 `in_progress`이며, 다음 단계는 v1.0.0 stable guarantee 진입 평가다.

## 1. 릴리스 요약

- Quality Dashboard Panel 1~8의 데이터·Markdown·HTML 교차 정합을 강화했다.
- append-only memory와 v0.15.0 deprecation 종결 상태를 dashboard 및 release pipeline에 반영했다.
- 10개 harness의 디렉터리, 진입 파일, apply guide, README 정합을 검증했다.
- output sample 24개의 `tool_version`을 package SSOT와 맞췄다.
- README, 설치 가이드, quickstart의 stale 버전·harness·smoke 설명을 정정했다.
- `PROJECT_PROFILE.md` canonical 위치를 실제 bootstrap 구현과 같은 `docs/PROJECT_PROFILE.md`로 통일했다.

## 2. v0.15.1~v0.15.10 — 운영 정합과 ADR close-out

- **v0.15.1**: dashboard smoke count parser가 `N+ PASS` 형식을 지원하고 8개 panel 렌더링을 교차 검증한다.
- **v0.15.2**: release maturity refresh에 `--legacy-memory` / `--no-legacy-memory` strict opt-out을 연결했다.
- **v0.15.3**: maturity refresh를 release 오류 시 fallback으로만 수행하도록 정정했다.
- **v0.15.4**: ADR-007 3rd deprecation cycle 후보 재검색을 완료하고 no-op으로 accepted 처리했다.
- **v0.15.5~v0.15.8**: smoke trend, telemetry, memory index, maturity distribution의 dashboard cross-check를 추가했다.
- **v0.15.9**: 10개 harness directory·entry·SSOT set 검증을 추가했다.
- **v0.15.10**: Microsoft Memora 평가 문서를 accepted로 close-out했다.

## 3. v0.15.11~v0.15.15 — sample·사용자 문서·harness 보강

- **v0.15.11**: output sample 24개의 `tool_version`을 `v0.15.0-beta` baseline과 맞추고 pyproject·runtime fallback과 3-way 검증했다.
- **v0.15.12**: 루트 README의 stale push 안내를 정정하고 version·harness·package 설명을 검증했다.
- **v0.15.13**: harness apply guide의 metadata·본문·relative path를 검증하고 MiniMax 경로를 정정했다.
- **v0.15.14**: 설치 가이드의 smoke 수, 버전, 10개 harness 목록을 정정했다.
- **v0.15.15**: quickstart의 harness 목록을 정정하고 aider/goose README를 보강했다.

## 4. 릴리스 포함 후속 — PROJECT_PROFILE canonical path

bootstrap의 실제 생성 위치는 처음부터 다음과 같았다.

```text
docs/PROJECT_PROFILE.md
```

현재 정책·harness·skill·fixture·export package 참조도 이 경로로 통일했다.

- runtime harness package: `bundle/docs/PROJECT_PROFILE.md`
- 기존 잘못된 package 위치 `bundle/ai-workflow/memory/active/PROJECT_PROFILE.md`는 더 이상 생성하지 않는다.
- frozen release memory와 과거 릴리스 노트는 당시 기록 보존을 위해 변경하지 않았다.

## 5. 검증

v0.15.x follow-up 세션 기준 누적 **20종 smoke PASS**, 확인된 회귀 없음.

본 릴리스 준비에서 추가 확인한 항목:

- bootstrap scaffold smoke: PASS
- harness export archive/manifest의 `bundle/docs/PROJECT_PROFILE.md`: PASS
- workflow-linter smoke: PASS
- v0.14.5 deprecation cycle smoke: 4/4 PASS
- `git diff --check`: PASS
- 현재 운영 소스의 기존 `ai-workflow/memory/active/PROJECT_PROFILE.md` 참조: 0건

## 6. 알려진 검증 인프라 이슈

- `check_export_harness_package.py`는 exporter 결과에 `package_root`, `manifest_path`, `archive_path`가 있다고 가정하지만 현재 반환 payload에는 해당 키가 없다. 실제 archive와 manifest는 별도 직접 검증했다.
- repository-wide `check_docs.py`는 과거 fixture·sample·archive의 기존 metadata/link 문제를 함께 보고하므로 현재 full green이 아니다. v1.0.0 진입 평가에서 검증 범위와 historical exclusion 정책을 명시한다.

## 7. 다음 단계

1. Phase 12 close-out 조건을 대상으로 v1.0.0 진입 평가를 수행한다.
2. public API, CLI, Pydantic/JSON schema, Python·dependency 지원 범위와 2년 호환성 보장을 명시한다.
3. 알려진 검증 인프라 이슈를 수정하거나 stable gate에서 허용할 exclusion 정책을 문서화한다.

---

release target: `v0.15.15-beta`
