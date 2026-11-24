# Beta v3.3.1 — Go 도구 완결과 셋업 판정 수리 (2026-11-24)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- Go 허브에 남은 도구 10종을 구현했다: `hub_project_export/import/unseal`, `hub_relay_invite/list/revoke`, `hub_wiki_export/import_okf/lint/remote_set`. `workflow-hub admin project export|import|seal|unseal|invite`도 쓴다. 광고한 도구가 모두 구현됐는지 검사가 잰다.
- 진입 파일이 막혀도 셋업이 끝난 것으로 기록되던 결함을 고쳤다. 막힌 단계는 `unconfirmed`로 남는다. 진입 파일이 막혀도 MCP 등록 단계는 나온다.
- `hub_guide_render`가 1.x 지침이 든 파일에 허브 영역을 덧붙이던 것을 `hub_setup_plan`과 같게 막는다.
- 진입 안내에 A2A 승인 경로를 넣었다(표준 2.3).
- **보안**: 프로젝트 이전 묶음에 계정 연결과 실행 승인 기록이 실리던 것을 막았다. 옛 묶음에 실린 것도 들이지 않고, 다른 프로젝트의 줄이 든 묶음을 거절한다.
- **보안**: 바깥에 노출된 허브의 위키 원격 읽기를 기본으로 끈다(`serve --allow-wiki-remote`).

## 검증

- 누적 smoke **358/358 PASS**
- `check_hub_wiki`(26)·`check_hub_transfer`(25)·`check_hub_bootstrap`(16)이 Python·Go를 모두 잰다. 이전은 Python→Go, Go→Python을 포함한 네 방향이다. 되주입 6건을 잡는다.

## 운영 범위

- 평가용 pre-release다. DB 판은 18 그대로다. Go의 PostgreSQL 프로젝트 이전은 측정하지 않았다.
- 봉인된 사본으로 되옮길 때 그 사본의 계정 연결·승인은 거둔다.
